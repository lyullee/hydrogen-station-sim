"""Versioned SQLite definitions imported from the supplied XLSX, without Excel dependencies."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "hazop.sqlite3"
SHEETS = {
    "설비노드": ("nodes", "node_id"), "센서목록": ("sensors", "sensor_id"),
    "HAZOP_DB": ("rules", "rule_id"), "운전상태": ("gates", "gate_id"),
    "HyRAM_케이스": ("cases", "case_id"), "기준_출처": ("sources", "source_id"),
    "누출구경": ("leak_sizes", "size_id"), "HyRAM_입력": ("inputs", "field"),
    "연동규약": ("protocol", "항목"),
}
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def definition_path() -> Path:
    return Path(os.environ.get("H2STATION_HAZOP_DB", str(DEFAULT_DB)))


def read_xlsx(path: Path) -> dict[str, list[dict]]:
    """Read typed plain table cells; reject formulas in definition tables."""
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            shared = ["".join(x.itertext()) for x in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        rels = {x.attrib["Id"]: x.attrib["Target"] for x in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
        result = {}
        for sheet in ET.fromstring(z.read("xl/workbook.xml")).findall("s:sheets/s:sheet", NS):
            name = sheet.attrib["name"]
            if name not in SHEETS:
                continue
            rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rels[rid]
            member = target.lstrip("/") if target.startswith("/") else "xl/" + target
            matrix = []
            for row in ET.fromstring(z.read(member)).findall("s:sheetData/s:row", NS):
                values = {}
                for c in row.findall("s:c", NS):
                    if c.find("s:f", NS) is not None:
                        raise ValueError(f"Formula not permitted in {name}!{c.attrib['r']}")
                    index = 0
                    for ch in re.match(r"[A-Z]+", c.attrib["r"])[0]:
                        index = index * 26 + ord(ch) - 64
                    raw = c.findtext("s:v", default=None, namespaces=NS)
                    kind = c.attrib.get("t", "n")
                    if kind == "inlineStr": value = "".join(c.find("s:is", NS).itertext())
                    elif raw is None: value = None
                    elif kind == "s": value = shared[int(raw)]
                    elif kind == "b": value = raw == "1"
                    elif kind == "n": value = float(raw)
                    elif kind == "e": raise ValueError(f"Error cell in {name}")
                    else: value = raw
                    values[index - 1] = value
                if values: matrix.append(values)
            headers = matrix[0]
            result[SHEETS[name][0]] = [
                {str(key): row.get(i) for i, key in headers.items()}
                for row in matrix[1:] if row.get(0) is not None
            ]
        if set(result) != {v[0] for v in SHEETS.values()}:
            raise ValueError("Missing definition sheets")
        return result


def import_workbook(workbook: Path, destination: Path = DEFAULT_DB) -> dict:
    from .expressions import dependencies, gate_dependencies, validate_expression
    from .mapping import mapping_catalog

    data = read_xlsx(workbook)
    ids = {}
    for table, key in SHEETS.values():
        keys = [r[key] for r in data[table]]
        if len(keys) != len(set(keys)): raise ValueError(f"Duplicate {key}")
        ids[table] = set(keys)
    for r in data["sensors"]:
        if r["node_id"] not in ids["nodes"]: raise ValueError("Unknown sensor node")
    for r in data["rules"]:
        for col, table in (("node_id", "nodes"), ("sensor_id", "sensors"), ("gate_id", "gates")):
            if r[col] not in ids[table]: raise ValueError(f"{r['rule_id']}: invalid {col}")
        if r["HyRAM_case_id"] and r["HyRAM_case_id"] not in ids["cases"]: raise ValueError("Unknown case")
        for col in ("임계값", "지속_s", "window_s", "복귀값", "복귀지속_s"):
            if not isinstance(r[col], (float, int)) or not math.isfinite(r[col]): raise ValueError(f"Invalid {col}")
        if any(r[k] < 0 for k in ("지속_s", "window_s", "복귀지속_s")): raise ValueError("Negative time")
        if r["연산자"] not in (">=", "<="): raise ValueError("Unsupported comparison")
        if r["복귀연산자"] != ("<" if r["연산자"] == ">=" else ">"): raise ValueError("Invalid reset operator")
        if (r["복귀값"] >= r["임계값"]) if r["연산자"] == ">=" else (r["복귀값"] <= r["임계값"]):
            raise ValueError("Invalid hysteresis")
        if not isinstance(r["래치"], bool) or not isinstance(r["현장활성화"], bool): raise ValueError("Booleans required")
        validate_expression(r["신호식"])
        for tag in dependencies(r["신호식"]):
            if not tag.startswith("MASS_") and tag not in ids["sensors"]: raise ValueError(f"Unknown {tag}")
        for src in r["source_id"].split(";"):
            if src not in ids["sources"]: raise ValueError("Unknown source")
    for g in data["gates"]: gate_dependencies(g["기계식_상태조건"])
    metadata = {"schema_version": "1.0", "source_file": workbook.name,
                "source_sha256": hashlib.sha256(workbook.read_bytes()).hexdigest(),
                "imported_at": datetime.now(timezone.utc).isoformat(),
                "execution_mode": "SIMULATION_ADVISORY", "physical_plc_actions": False}
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="hazop-", suffix=".sqlite3", dir=destination.parent)
    os.close(fd)
    try:
        with closing(sqlite3.connect(temp)) as db, db:
            db.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.executemany("INSERT INTO metadata VALUES (?,?)", [(k, json.dumps(v, ensure_ascii=False)) for k, v in metadata.items()])
            for table, key in SHEETS.values():
                db.execute(f"CREATE TABLE {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
                db.executemany(f"INSERT INTO {table} VALUES (?,?)", [(r[key], json.dumps(r, ensure_ascii=False)) for r in data[table]])
            db.execute("CREATE TABLE mappings (sensor_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.executemany("INSERT INTO mappings VALUES (?,?)", [(r["sensor_id"], json.dumps(r, ensure_ascii=False)) for r in mapping_catalog(data["sensors"])])
            # Queryable numerical rule view, while preserving all original Korean columns.
            db.execute('''CREATE VIEW rule_conditions AS SELECT id AS rule_id,
              json_extract(payload,'$.node_id') AS node_id,
              json_extract(payload,'$.sensor_id') AS sensor_id,
              json_extract(payload,'$.신호식') AS expression,
              json_extract(payload,'$.연산자') AS operator,
              json_extract(payload,'$.임계값') AS threshold,
              json_extract(payload,'$.단위') AS unit,
              json_extract(payload,'$.지속_s') AS persistence_s,
              json_extract(payload,'$.gate_id') AS gate_id FROM rules''')
        os.replace(temp, destination)
    finally:
        if os.path.exists(temp): os.unlink(temp)
    return {**metadata, "counts": {k: len(v) for k, v in data.items()}}


def load_catalog(path: Path | None = None) -> dict:
    path = path or definition_path()
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        result = {table: [json.loads(x[0]) for x in db.execute(f"SELECT payload FROM {table} ORDER BY id")]
                  for table, _ in SHEETS.values()}
        result["metadata"] = {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM metadata")}
        result["mappings"] = [json.loads(x[0]) for x in db.execute("SELECT payload FROM mappings ORDER BY sensor_id")]
    return result


class EventStore:
    """Append-only transitions, separate from the packaged definition database."""
    def __init__(self, path: Path | None = None):
        self.path = path or Path(os.environ.get("H2STATION_HAZOP_EVENTS_DB", str(DEFAULT_DB.parents[3] / "data" / "hazop-events.sqlite3")))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, metadata TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS events (run_id TEXT, sequence INTEGER, payload TEXT NOT NULL, PRIMARY KEY(run_id,sequence))")

    def start(self, run_id: str, metadata: dict):
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.execute("INSERT INTO runs VALUES (?,?)", (run_id, json.dumps(metadata, ensure_ascii=False)))

    def append(self, run_id: str, events: list[dict]):
        if not events: return
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.executemany("INSERT INTO events VALUES (?,?,?)", [(run_id, e["sequence"], json.dumps(e, ensure_ascii=False)) for e in events])

    def events(self, run_id: str) -> list[dict]:
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            return [json.loads(x[0]) for x in db.execute("SELECT payload FROM events WHERE run_id=? ORDER BY sequence", (run_id,))]
