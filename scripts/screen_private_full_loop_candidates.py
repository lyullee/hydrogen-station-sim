"""Screen a private CSV candidate manifest without publishing source details.

Keyword candidates frequently include empty schema templates or generated model
exports.  This screen checks only aggregate header families and non-empty row
presence.  It never writes a path, filename, raw header, identifier, value, or
timestamp to the result.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


FAMILY_PATTERNS = {
    "common_clock": re.compile(r"time|timestamp|datetime|date|ts|elapsed", re.I),
    "station_pressure": re.compile(r"station|dispenser|hose|bank|pcv|storage", re.I),
    "vehicle_pressure": re.compile(r"vehicle|chss|receptacle|tank|car", re.I),
    "temperature": re.compile(r"temp|temperature|degc|thermal", re.I),
    "mass_or_flow": re.compile(r"mass|flow|rate|totalizer|transferred", re.I),
    "control_or_esd": re.compile(r"controller|valve|esd|trip|protocol|fault|state|command", re.I),
}


def _header_flags(header: list[str]) -> dict[str, bool]:
    values = [str(item) for item in header]
    lowered = [item.lower() for item in values]
    flags: dict[str, bool] = {}
    for family, pattern in FAMILY_PATTERNS.items():
        flags[family] = any(pattern.search(item) for item in lowered)

    # Pressure and temperature must be vehicle-side to count as a full-loop
    # boundary.  A generic ``tank_pressure`` is retained as a candidate but
    # cannot establish station-to-vehicle roles without an attestation.
    flags["vehicle_pressure"] = any(
        re.search(r"vehicle|chss|receptacle|car", item, re.I)
        and re.search(r"press|pressure|mpa|bar", item, re.I)
        for item in values
    )
    flags["vehicle_temperature"] = any(
        re.search(r"vehicle|chss|receptacle|car", item, re.I)
        and re.search(r"temp|temperature|degc|thermal", item, re.I)
        for item in values
    )
    flags["station_pressure"] = any(
        re.search(r"station|dispenser|hose|bank|pcv|storage", item, re.I)
        and re.search(r"press|pressure|mpa|bar", item, re.I)
        for item in values
    )
    return flags


def _csv_shape(path: Path) -> tuple[list[str], int] | None:
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader, [])
            rows = sum(1 for _ in reader)
        return header, rows
    except (OSError, UnicodeError, csv.Error):
        return None


def screen_manifest(manifest_path: Path) -> dict[str, Any]:
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("private candidate manifest must be a JSON list")

    existing = 0
    parse_errors = 0
    csv_entries = 0
    header_family_counts = Counter()
    complete_nonempty = 0
    complete_empty = 0
    complete_nonempty_sizes = []
    candidate_rows = 0

    required = {
        "common_clock",
        "station_pressure",
        "vehicle_pressure",
        "vehicle_temperature",
        "temperature",
        "mass_or_flow",
        "control_or_esd",
    }
    for entry in entries:
        if not isinstance(entry, dict):
            parse_errors += 1
            continue
        path_value = entry.get("path")
        if not isinstance(path_value, str):
            parse_errors += 1
            continue
        path = Path(path_value)
        if not path.exists() or path.suffix.lower() not in {".csv", ".tsv"}:
            continue
        existing += 1
        shape = _csv_shape(path)
        if shape is None:
            parse_errors += 1
            continue
        csv_entries += 1
        header, rows = shape
        flags = _header_flags(header)
        for family, present in flags.items():
            if present:
                header_family_counts[family] += 1
        if required.issubset(flags) and all(flags.values()):
            if rows > 0:
                complete_nonempty += 1
                candidate_rows += rows
                complete_nonempty_sizes.append(rows)
            else:
                complete_empty += 1

    complete_nonempty_sizes.sort()
    return {
        "schema_version": 1,
        "artifact_type": "privacy_bounded_private_full_loop_candidate_semantic_recheck",
        "recorded_at": "2026-10-11",
        "decision": (
            "MEASURED_FULL_LOOP_CANDIDATE_REQUIRES_ATTESTATION"
            if complete_nonempty
            else "NO_ELIGIBLE_MEASURED_FULL_LOOP_CANDIDATE"
        ),
        "screen": {
            "manifest_entry_count": len(entries),
            "existing_csv_or_tsv_count": existing,
            "parsed_csv_or_tsv_count": csv_entries,
            "parse_error_count": parse_errors,
            "header_family_candidate_counts": dict(sorted(header_family_counts.items())),
            "complete_nonempty_full_loop_schema_count": complete_nonempty,
            "empty_full_loop_schema_template_count": complete_empty,
            "aggregate_rows_in_complete_nonempty_candidates": candidate_rows,
            "complete_candidate_row_count_min": min(complete_nonempty_sizes) if complete_nonempty_sizes else 0,
            "complete_candidate_row_count_max": max(complete_nonempty_sizes) if complete_nonempty_sizes else 0,
        },
        "eligibility": {
            "header_screen_is_sufficient_for_validation": False,
            "raw_rows_are_persisted": False,
            "common_clock_and_units_attested": False,
            "station_vehicle_boundary_attested": False,
            "controller_protocol_esd_attested": False,
            "rights_and_custodian_attested": False,
            "full_loop_holdout_eligible": False,
            "runtime_parameter_application": False,
        },
        "privacy": {
            "source_paths_published": False,
            "source_filenames_published": False,
            "source_headers_published": False,
            "raw_rows_persisted": False,
            "candidate_values_persisted": False,
            "site_company_manufacturer_published": False,
            "calendar_dates_published": False,
        },
        "claim_boundary": (
            "This is a header-family and non-empty-row screen only. A complete "
            "schema candidate still requires pre-access freezing, engineering-unit "
            "and role attestation, rights confirmation, checksum and independent "
            "scoring before it can support validation."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = screen_manifest(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
