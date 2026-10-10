"""Privacy-bounded schema recheck for an authorized private HRS data root.

This command is deliberately weaker than a validation runner.  It answers only
whether a CSV file appears to contain the semantic channel groups needed for a
station-to-vehicle full-loop candidate.  It never writes rows, headers,
filenames, absolute timestamps, source paths, or site/company identifiers.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Iterable

from full_loop_schema_contract import CONTRACT_REQUIRED, contract_coverage

ROOT = Path(__file__).resolve().parents[1]
MAX_HEADER_BYTES = 512 * 1024
HEADER_ROWS = 40
REQUIRED = frozenset(
    {
        "time",
        "pressure",
        "temperature",
        "mass_flow",
        "vehicle",
        "cascade_or_storage",
        "controller_state",
    }
)
SKIP_PARTS = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "site-packages",
        "dist-info",
        "build",
        "dist",
    }
)
TERMS: dict[str, tuple[str, ...]] = {
    "time": ("time", "timestamp", "datetime", "localtime", "zeit", "时间", "시간", "일시", "시각"),
    "pressure": ("pressure", "press", "pt", "pi", "압력"),
    "temperature": ("temperature", "temp", "tt", "온도"),
    "mass_flow": ("flow", "mass", "rate", "mfm", "fqi", "유량", "질량"),
    "vehicle": ("vehicle", "car", "automobile", "veh", "fcev", "차량", "자동차", "수소차"),
    "cascade_or_storage": ("cascade", "bank", "storage", "vessel", "저장", "뱅크", "용기"),
    "controller_state": ("state", "status", "valve", "esd", "mode", "control", "alarm", "interlock", "밸브", "상태", "제어", "경보", "차단"),
}


@dataclass(frozen=True)
class Header:
    columns: tuple[str, ...]
    delimiter: str
    coverage: frozenset[str]
    contract_coverage: frozenset[str]
    row_index: int


def _outside_repo(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError("private input must be outside the repository worktree")


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-16", "latin1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


def _coverage(labels: Iterable[object]) -> frozenset[str]:
    text = " ".join(str(value or "").strip().lower() for value in labels if str(value or "").strip())
    compact = re.sub(r"[^a-z0-9가-힣]+", " ", text)
    return frozenset(
        group
        for group, terms in TERMS.items()
        if any(term in text or term in compact for term in terms)
    )


def _read_header(path: Path) -> Header | None:
    try:
        with path.open("rb") as handle:
            text = _decode(handle.read(MAX_HEADER_BYTES))
    except (OSError, UnicodeError):
        return None
    rows = [line for line in text.splitlines() if line.strip()]
    if not rows:
        return None
    parsed_by_delimiter: list[tuple[str, list[list[str]]]] = []
    for delimiter in (",", "\t", ";", "|"):
        try:
            parsed = list(csv.reader(rows[:HEADER_ROWS], delimiter=delimiter))
        except csv.Error:
            continue
        parsed_by_delimiter.append((delimiter, parsed))
    if not parsed_by_delimiter:
        return None
    delimiter, parsed = max(
        parsed_by_delimiter,
        key=lambda item: max((len(row) for row in item[1]), default=0),
    )
    candidates: list[tuple[tuple[int, int, int, int], int, list[str], frozenset[str]]] = []
    for index, row in enumerate(parsed):
        coverage = _coverage(row)
        text_cells = sum(bool(re.search(r"[A-Za-z가-힣]", str(value or ""))) for value in row)
        # Prefer a broad, label-like early row.  Numeric data rows therefore do
        # not turn a false positive into a full-loop schema candidate.
        score = (len(coverage), text_cells, len(row), -index)
        candidates.append((score, index, row, coverage))
    if not candidates:
        return None
    _, index, row, coverage = max(candidates, key=lambda item: item[0])
    return Header(
        tuple(str(value or "") for value in row),
        delimiter,
        coverage,
        contract_coverage(row),
        index,
    )


def _iter_csv_files(root: Path):
    for path in root.rglob("*.csv"):
        if any(part.lower() in SKIP_PARTS for part in path.parts):
            continue
        try:
            path.relative_to(ROOT.resolve())
        except ValueError:
            yield path


def audit(root: Path, *, source_label: str) -> dict[str, object]:
    root = _outside_repo(root)
    if not root.is_dir():
        raise NotADirectoryError(root)
    files = 0
    readable = 0
    header_full_loop = 0
    header_full_loop_contract = 0
    header_groups: set[str] = set()
    contract_groups: set[str] = set()
    contract_missing_union: set[str] = set(CONTRACT_REQUIRED)
    monotonic_time_files = 0
    duplicate_time_files = 0
    for path in _iter_csv_files(root):
        files += 1
        header = _read_header(path)
        if header is None:
            continue
        readable += 1
        header_groups.update(header.coverage)
        contract_groups.update(header.contract_coverage)
        contract_missing_union.intersection_update(CONTRACT_REQUIRED - set(header.contract_coverage))
        if REQUIRED <= header.coverage:
            header_full_loop += 1
        if CONTRACT_REQUIRED <= header.contract_coverage:
            header_full_loop_contract += 1
        # The time checks are aggregate integrity hints only.  Values are never
        # retained in the receipt, and a passing check is not validation.
        time_index = next(
            (index for index, label in enumerate(header.columns) if "time" in _coverage((label,))),
            None,
        )
        if time_index is None:
            continue
        monotonic = True
        duplicate = False
        previous: float | None = None
        try:
            with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
                reader = csv.reader(handle, delimiter=header.delimiter)
                for row in reader:
                    if time_index >= len(row):
                        continue
                    try:
                        value = float(row[time_index])
                    except (TypeError, ValueError):
                        continue
                    if previous is not None:
                        monotonic = monotonic and value >= previous
                        duplicate = duplicate or value == previous
                    previous = value
        except OSError:
            continue
        monotonic_time_files += int(monotonic)
        duplicate_time_files += int(duplicate)
    return {
        "schema_version": 1,
        "artifact_type": "private_full_loop_schema_recheck",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_label": source_label,
        "scope": {
            "file_type": "csv",
            "raw_rows_persisted": False,
            "original_headers_persisted": False,
            "filenames_and_source_paths_persisted": False,
            "absolute_timestamps_persisted": False,
            "repository_worktree_excluded": True,
        },
        "aggregate": {
            "csv_files_seen": files,
            "readable_csv_files": readable,
            "files_with_all_required_full_loop_groups": header_full_loop,
            "files_with_full_loop_contract_groups": header_full_loop_contract,
            "observed_semantic_groups": sorted(header_groups),
            "observed_full_loop_contract_groups": sorted(contract_groups),
            "missing_full_loop_contract_groups": sorted(CONTRACT_REQUIRED - contract_groups),
            "contract_groups_missing_from_every_scanned_header": sorted(contract_missing_union),
            "monotonic_numeric_time_files": monotonic_time_files,
            "duplicate_numeric_time_files": duplicate_time_files,
        },
        "admission": {
            "full_loop_external_holdout_eligible": False,
            "reason": "Header coverage cannot attest common-clock station/dispenser/vehicle linkage, units, calibration, rights, or a frozen outcome-free split.",
            "next_checks": [
                "custodian channel-role and unit attestation",
                "common-clock event linkage across station, dispenser and vehicle",
                "calibration and uncertainty metadata",
                "model and split freeze before numerical outcome access",
                "independent reviewer access under declared rights",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-label", default="authorized-private-hrs-root")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.root, source_label=args.source_label)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["aggregate"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
