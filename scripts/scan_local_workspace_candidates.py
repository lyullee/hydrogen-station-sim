"""Privacy-bounded discovery scan for local hydrogen-station candidates.

This scanner is intentionally a discovery aid, not a validation importer.  It
keeps only aggregate counts and coarse candidate classes.  Paths, filenames,
headers, timestamps, identifiers and measurement values are never written to
the output.  A candidate becomes eligible for validation only after a separate
custodian attestation establishes units, time alignment, boundary roles and
reuse rights.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Iterable


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
}

MACHINE_EXTENSIONS = {
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".json",
    ".mat",
    ".h5",
    ".hdf5",
    ".txt",
    ".md",
}

PATH_KEYWORDS = re.compile(
    r"vehicle|car|tank|disp|nozzle|fuel|station|hrs|충전|차량|탱크|디스펜|노즐|수소",
    re.IGNORECASE,
)
HEADER_FAMILIES = {
    "vehicle_or_dispenser": re.compile(
        r"veh|vehicle|car|tank|disp|nozzle|fuel|soc|충전|차량|탱크|디스펜|노즐",
        re.IGNORECASE,
    ),
    "pressure": re.compile(
        r"press|pressure|pt[_-]?\d+|pi[_-]?\d+|압력", re.IGNORECASE
    ),
    "temperature": re.compile(
        r"temp|temperature|tt[_-]?\d+|ti[_-]?\d+|온도", re.IGNORECASE
    ),
    "flow_or_mass": re.compile(
        r"flow|mass|rate|totalizer|accum|유량|질량|적산", re.IGNORECASE
    ),
    "protocol_or_control": re.compile(
        r"protocol|command|controller|state|valve|esd|pcv|제어|밸브|차단",
        re.IGNORECASE,
    ),
}
RELEASE_RIG_PATTERN = re.compile(
    r"release|rig|jet|aperture|누출|분출", re.IGNORECASE
)
TIME_PATTERN = re.compile(r"^time$|timestamp|datetime|zeit|시간|시각", re.IGNORECASE)


def _iter_files(roots: Iterable[Path]) -> Iterable[Path]:
    """Yield files without retaining their paths in the result."""

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in MACHINE_EXTENSIONS:
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            yield path


def _read_header(path: Path) -> list[str]:
    if path.suffix.lower() not in {".csv", ".tsv"}:
        return []
    for encoding in ("utf-8-sig", "cp949", "utf-16"):
        try:
            with path.open("r", encoding=encoding, newline="") as stream:
                delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
                return next(csv.reader(stream, delimiter=delimiter), [])
        except (OSError, UnicodeError, csv.Error):
            continue
    return []


def _classify_candidate(path: Path, header: list[str]) -> str:
    text = " ".join([path.stem, *header])
    # ELVHYS-style release-rig traces often contain ``nozzle`` and pressure
    # labels.  Keep them separate from vehicle/dispenser candidates so a
    # keyword hit cannot be mistaken for a full-loop fueling record.
    if RELEASE_RIG_PATTERN.search(text) and HEADER_FAMILIES["pressure"].search(text):
        return "release_rig_experiment_candidate"
    has_time = any(TIME_PATTERN.search(str(column)) for column in header)
    has_pressure = bool(HEADER_FAMILIES["pressure"].search(text))
    has_temperature = bool(HEADER_FAMILIES["temperature"].search(text))
    has_flow = bool(HEADER_FAMILIES["flow_or_mass"].search(text))
    if HEADER_FAMILIES["vehicle_or_dispenser"].search(text):
        # A synchronized vehicle candidate needs a time axis and a flow/mass
        # field in addition to pressure and temperature.  Static QRA result
        # tables often mention dispenser, pressure and temperature but do not
        # contain a measured time series.
        if has_time and has_pressure and has_temperature and has_flow:
            return "vehicle_pressure_temperature_candidate"
        return "vehicle_or_dispenser_candidate"
    if HEADER_FAMILIES["protocol_or_control"].search(text):
        return "control_or_protocol_candidate"
    if HEADER_FAMILIES["flow_or_mass"].search(text):
        return "flow_or_mass_candidate"
    if HEADER_FAMILIES["pressure"].search(text):
        return "pressure_candidate"
    if HEADER_FAMILIES["temperature"].search(text):
        return "temperature_candidate"
    return "unclassified_machine_readable"


def scan_workspace(roots: Iterable[Path]) -> dict:
    files = 0
    path_keyword_candidates = 0
    header_screened = 0
    header_family_counts: Counter[str] = Counter()
    coarse_classes: Counter[str] = Counter()
    parse_errors = 0

    for path in _iter_files(roots):
        files += 1
        if PATH_KEYWORDS.search(path.stem):
            path_keyword_candidates += 1
        header = _read_header(path)
        if path.suffix.lower() in {".csv", ".tsv"}:
            header_screened += 1
            if not header:
                parse_errors += 1
            for family, pattern in HEADER_FAMILIES.items():
                if any(pattern.search(str(column)) for column in header):
                    header_family_counts[family] += 1
        coarse_classes[_classify_candidate(path, header)] += 1

    return {
        "schema_version": 1,
        "artifact_type": "privacy_bounded_local_workspace_candidate_scan",
        "status": "discovery_only",
        "generated_at": date.today().isoformat(),
        "privacy": {
            "source_paths_published": False,
            "source_filenames_published": False,
            "source_headers_published": False,
            "source_identifiers_published": False,
            "raw_rows_persisted": False,
            "candidate_values_persisted": False,
        },
        "scan": {
            "machine_readable_files": files,
            "path_keyword_candidates": path_keyword_candidates,
            "csv_tsv_headers_screened": header_screened,
            "header_parse_errors": parse_errors,
            "header_family_candidate_counts": dict(sorted(header_family_counts.items())),
            "coarse_candidate_classes": dict(sorted(coarse_classes.items())),
        },
        "eligibility": {
            "full_loop_candidate_count": 0,
            "decision": "DISCOVERY_ONLY_UNTIL_ATTESTED",
            "required_attestation": [
                "common time base and units",
                "station/dispenser/vehicle boundary roles",
                "initial conditions and protocol state",
                "reuse rights and custodian confirmation",
            ],
        },
        "claim_boundary": (
            "Aggregate discovery counts only. Keyword or header matches do not prove "
            "measured status, synchronized station-to-vehicle coverage, or validation eligibility."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = scan_workspace(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
