#!/usr/bin/env python3
"""Audit the public Figshare open-channel hydrogen-dispersion release.

The release is useful for a component-level spatial-dispersion screen.  It is
deliberately kept separate from the HRS full-loop evidence gate: it has no
station controller, cascade, dispenser or vehicle-receptacle channels.

The script records the Figshare API manifest and, when ``--raw-dir`` is
provided, audits locally downloaded ZIPs without copying their raw rows into
the repository.  The optional structural screen is descriptive only; it does
not fit model parameters or promote a validation claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ARTICLE_ID = 26117989
API_URL = f"https://api.figshare.com/v2/articles/{ARTICLE_ID}"
DATASET_URL = (
    "https://figshare.com/articles/dataset/"
    "Experimental_Data_of_Hydrogen_Dispersion_in_an_Open-ended_Rectangular_Channel/"
    f"{ARTICLE_ID}"
)
ARTICLE_DOI = "10.23642/usn.26117989.v2"
LICENSE = "CC BY 4.0"
GEOMETRY = {
    "source": "10.1016/j.ijhydene.2024.10.038",
    "channel_length_m": 5.8,
    "channel_width_m": 0.9,
    "channel_height_m": 0.8,
    "volume_m3": 4.176,
    "sensor_count": 29,
    "inlet_diameter_mm": 4.6,
    "inlet_location": "ceiling, 0.5 m from closed end and 0.45 m from side wall",
}


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "h2station-public-intake/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - used only to compare Figshare's file checksum
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def numeric(value: str) -> float | None:
    try:
        return float(value.strip())
    except (AttributeError, TypeError, ValueError):
        return None


def csv_schema(raw: bytes) -> dict[str, Any]:
    """Extract a conservative schema and monotonicity screen from one CSV."""

    text = raw.decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    header_index = next(
        (
            i
            for i, row in enumerate(rows)
            if "flow time [s]" in row and "filling pressure [bar]" in row
        ),
        None,
    )
    if header_index is None:
        return {"header_found": False, "row_count": len(rows)}

    header = rows[header_index]
    flow_idx = header.index("flow time [s]")
    pressure_idx = header.index("filling pressure [bar]")
    mass_indices = [
        i for i, name in enumerate(header) if name.lower().startswith("mass flow meter")
    ]
    sensor_indices = [
        i
        for i, name in enumerate(header)
        if re.search(r"sensor\s*\d+", name, flags=re.IGNORECASE)
    ]
    flow_values: list[float] = []
    pressure_values: list[float] = []
    mass_values: list[float] = []
    sensor_rows = 0
    sensor_time_idx = next(
        (i for i, name in enumerate(header) if name.strip().lower() == "h2 sensor time"),
        None,
    )
    sensor_time_values: list[float] = []
    for row in rows[header_index + 1 :]:
        if len(row) <= max(flow_idx, pressure_idx):
            continue
        flow = numeric(row[flow_idx])
        pressure = numeric(row[pressure_idx])
        if flow is not None:
            flow_values.append(flow)
        if pressure is not None:
            pressure_values.append(pressure)
        for index in mass_indices:
            if len(row) > index:
                value = numeric(row[index])
                if value is not None:
                    mass_values.append(value)
        if sensor_time_idx is not None and len(row) > sensor_time_idx:
            value = numeric(row[sensor_time_idx])
            if value is not None:
                sensor_time_values.append(value)
                if any(len(row) > i and numeric(row[i]) is not None for i in sensor_indices):
                    sensor_rows += 1

    def monotonic(values: list[float]) -> bool | None:
        if len(values) < 2:
            return None
        return all(b >= a for a, b in zip(values, values[1:]))

    return {
        "header_found": True,
        "header_row_index": header_index,
        "row_count": len(rows),
        "column_count": len(header),
        "flow_time_column": header[flow_idx],
        "sensor_time_column": header[sensor_time_idx] if sensor_time_idx is not None else None,
        "sensor_column_count": len(sensor_indices),
        "numeric_flow_rows": len(flow_values),
        "numeric_sensor_rows": sensor_rows,
        "flow_time_monotonic": monotonic(flow_values),
        "sensor_time_monotonic": monotonic(sensor_time_values),
        "flow_time_end_s": max(flow_values) if flow_values else None,
        "filling_pressure_max_bar": max(pressure_values) if pressure_values else None,
        "mass_flow_max_g_s": max(mass_values) if mass_values else None,
    }


def inspect_zip(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        csv_members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        readme_members = [name for name in archive.namelist() if "readme" in name.lower()]
        csv_audit = None
        if csv_members:
            with archive.open(csv_members[0]) as handle:
                csv_audit = csv_schema(handle.read())
        return {
            "local_name": path.name,
            "size_bytes": path.stat().st_size,
            "md5": md5_file(path),
            "sha256": sha256_file(path),
            "zip_members": len(archive.namelist()),
            "csv_members": csv_members,
            "readme_members": readme_members,
            "csv_schema": csv_audit,
        }


def api_files(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    files = []
    for item in metadata.get("files", []):
        files.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "size_bytes": item.get("size"),
                "md5": item.get("md5"),
                "download_url": item.get("download_url"),
            }
        )
    return files


def build_record(metadata: dict[str, Any], raw_dir: Path | None) -> dict[str, Any]:
    files = api_files(metadata)
    local = []
    if raw_dir is not None and raw_dir.exists():
        by_name = {path.name: path for path in raw_dir.glob("*.zip")}
        for item in files:
            path = by_name.get(item["name"])
            if path is None and item["name"].lower().endswith(".zip"):
                # Local downloads are often renamed to the compact test ID
                # (for example T00014.zip) while Figshare retains the full
                # experiment filename (23_FFI_P101_T00014.zip).
                token = Path(item["name"]).stem.split("_")[-1].lower()
                path = next(
                    (candidate for name, candidate in by_name.items() if token == Path(name).stem.lower()),
                    None,
                )
            if path is None:
                continue
            audit = inspect_zip(path)
            audit["api_size_matches"] = (
                audit["size_bytes"] == int(item["size_bytes"])
                if item.get("size_bytes") is not None
                else None
            )
            audit["api_md5_available"] = bool(item.get("md5"))
            audit["api_md5_matches"] = (
                audit["md5"].lower() == str(item["md5"]).lower()
                if item.get("md5")
                else None
            )
            local.append(audit)
    return {
        "schema_version": 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "artifact_type": "figshare_open_channel_hydrogen_dispersion_intake",
        "source": {
            "article_id": ARTICLE_ID,
            "doi": metadata.get("doi") or ARTICLE_DOI,
            "api_url": API_URL,
            "dataset_url": DATASET_URL,
            "title": metadata.get("title"),
            "license": metadata.get("license", {}).get("name")
            if isinstance(metadata.get("license"), dict)
            else metadata.get("license"),
            "published_date": metadata.get("published_date"),
            "file_count": len(files),
            "files": files,
        },
        "geometry": GEOMETRY,
        "eligibility": {
            "classification": "DISPERSION_COMPONENT_HOLDOUT_CANDIDATE",
            "full_loop_external_holdout_eligible": False,
            "raw_files_committed": False,
            "claim_boundary": (
                "Open-ended channel dispersion and detector/spatial proxy evidence only; "
                "not an HRS controller, cascade, dispenser, vehicle, ESD or outdoor-distance holdout."
            ),
            "screen_rule": "Descriptive schema, timing, concentration and mass-flow audit; no fitting or post-outcome tuning.",
        },
        "local_file_audit": {
            "raw_dir_supplied": raw_dir is not None,
            "audited_zip_count": len(local),
            "files": local,
        },
        "decision": {
            "admit_to_full_loop_gate": False,
            "runtime_parameter_application": False,
            "next_action": "Freeze a spatial-dispersion screen before scoring all locally available cases.",
        },
    }


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-json", type=Path, help="Use a saved Figshare API response")
    parser.add_argument("--raw-dir", type=Path, help="Directory containing downloaded Figshare ZIP files")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    metadata = (
        json.loads(args.metadata_json.read_text(encoding="utf-8"))
        if args.metadata_json
        else fetch_json(API_URL)
    )
    title = str(metadata.get("title", ""))
    if "Hydrogen Dispersion" not in title or metadata.get("id") != ARTICLE_ID:
        raise SystemExit("unexpected Figshare article metadata")
    record = build_record(metadata, args.raw_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "file_count": record["source"]["file_count"], "audited_zip_count": record["local_file_audit"]["audited_zip_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
