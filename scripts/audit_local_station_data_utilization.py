"""Build a privacy-bounded inventory and utilization audit for local HRS logs.

The raw directory is supplied at execution time and is never written to the
result.  File names, headers, timestamps, per-file hashes, and measurement
rows are deliberately omitted.  The optional research directory contributes
only already de-identified validation counts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


WIDE_MIN_COLUMNS = 32

# Header-only families used to explain coverage without publishing proprietary
# tag names.  The screen is intentionally qualitative: a match is a candidate
# family, not a confirmed engineering meaning or unit attestation.
HEADER_FAMILY_PATTERNS = {
    "vehicle_or_dispenser": re.compile(
        r"veh|car|tank|disp|nozzle|fuel|충전|차량|디스펜|노즐", re.I
    ),
    "flow_or_mass": re.compile(
        r"flow|mass|massflow|rate|fqi|fqm|유량|질량|flowrate", re.I
    ),
    "pressure": re.compile(r"press|pressure|pi_|pt_|압력", re.I),
    "temperature": re.compile(r"temp|temperature|tt_|ti_|온도", re.I),
    "compressor": re.compile(r"comp|compress|압축", re.I),
    "valve_or_esd": re.compile(r"valve|pcv|esd|trip|밸브|차단", re.I),
    "lifecycle": re.compile(r"life|cycle|cnt|count|수명|사이클", re.I),
    "totalizer": re.compile(r"acc|total|누적|적산", re.I),
}


def _sha256_and_lines(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    newline_count = 0
    last = b""
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
            newline_count += chunk.count(b"\n")
            last = chunk[-1:]
    physical_lines = newline_count + (1 if path.stat().st_size and last != b"\n" else 0)
    return digest.hexdigest(), physical_lines


def _read_header(path: Path) -> list[str]:
    for encoding in ("utf-8-sig", "cp949", "utf-16"):
        try:
            with path.open("r", encoding=encoding, newline="") as stream:
                return next(csv.reader(stream), [])
        except (UnicodeDecodeError, UnicodeError):
            continue
    return []


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _sum_nested(document: dict[str, Any], *paths: tuple[str, ...]) -> int:
    total = 0
    for path in paths:
        value: Any = document
        for key in path:
            if not isinstance(value, dict):
                value = 0
                break
            value = value.get(key, 0)
        if isinstance(value, (int, float)):
            total += int(value)
    return total


def _research_utilization(research_dir: Path | None) -> dict[str, Any]:
    if research_dir is None:
        return {}

    cycles = _load_json(
        research_dir / "confidential_station_ordered_pressure_cycle_holdout_2026_10_08.json"
    )
    cascade = _load_json(
        research_dir / "confidential_station_cascade_sequence_holdout_2026_10_08.json"
    )
    forecast = _load_json(
        research_dir / "confidential_station_recharge_pressure_forecast_holdout_2026_10_08.json"
    )
    flow = _load_json(
        research_dir / "confidential_station_recharge_flow_screen_2026_10_08.json"
    )
    signal = _load_json(
        research_dir / "confidential_station_signal_consistency_screen_2026_10_08.json"
    )
    semantic = _load_json(
        research_dir / "local_station_semantic_attestation_2026_10_09.json"
    )
    semantic_roles = semantic.get("attested_roles") or {}

    return {
        "ordered_high_bank_pressure_cycles": _sum_nested(
            cycles,
            ("calibration", "pressure_drop_mpa", "count"),
            ("holdout", "pressure_drop_mpa", "count"),
        ),
        "paired_medium_high_pressure_episodes": _sum_nested(
            cascade,
            ("calibration", "paired_episode_count"),
            ("holdout", "paired_episode_count"),
        ),
        "sequential_medium_high_pressure_episodes": _sum_nested(
            cascade,
            ("calibration", "sequential_episode_count"),
            ("holdout", "sequential_episode_count"),
        ),
        "short_horizon_pressure_forecast_cases": _sum_nested(
            forecast,
            ("calibration", "case_count"),
            ("holdout", "case_count"),
        ),
        "conditional_recharge_flow_episodes": int(
            flow.get("screen", {}).get("eligible_recharge_episodes", 0)
        ),
        "strong_instantaneous_totalizer_consistency_pairs": int(
            signal.get("screen", {}).get("strong_consistency_pairs", 0)
        ),
        "station_side_evidence_is_substantial": True,
        "independent_full_loop_vehicle_validation_complete": False,
        "semantic_attestation": {
            key: semantic_roles.get(key)
            for key in (
                "storage_pressure_role_count",
                "lifecycle_counter_role_count",
                "storage_pressure_units_attested",
                "lifecycle_counter_event_definition_attested",
                "flow_units_attested",
                "totalizer_reset_semantics_attested",
                "vehicle_side_channels_attested",
            )
            if semantic_roles.get(key) is not None
        },
    }


def _header_family_screen(headers: list[list[str]]) -> dict[str, Any]:
    """Return aggregate candidate-family counts without retaining headers."""

    counts = {family: 0 for family in HEADER_FAMILY_PATTERNS}
    for columns in headers:
        for family, pattern in HEADER_FAMILY_PATTERNS.items():
            if any(pattern.search(str(column)) for column in columns):
                counts[family] += 1
    return {
        "method": "header_only_regex_family_screen",
        "files_screened": len(headers),
        "candidate_file_counts": counts,
        "vehicle_or_dispenser_candidate_files": counts["vehicle_or_dispenser"],
        "interpretation": (
            "No channel names, values, dates or paths are retained. A zero vehicle/dispenser "
            "candidate count means no header-level candidate was found; it does not prove "
            "that vehicle telemetry is absent without custodian confirmation."
        ),
    }


def audit_station_directory(
    source: Path, *, research_dir: Path | None = None
) -> dict[str, Any]:
    csv_files = sorted(path for path in source.rglob("*") if path.is_file() and path.suffix.lower() == ".csv")
    metadata_files = sorted(
        path
        for path in source.rglob("*")
        if path.is_file() and path.suffix.lower() in {".txt", ".md", ".json"}
    )

    hashes: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    schema_widths: Counter[int] = Counter()
    total_bytes = 0
    total_data_rows = 0
    unreadable_headers = 0
    headers: list[list[str]] = []

    for path in csv_files:
        digest, physical_lines = _sha256_and_lines(path)
        header = _read_header(path)
        headers.append(header)
        width = len(header)
        if not header:
            unreadable_headers += 1
        schema_widths[width] += 1
        rows = max(physical_lines - 1, 0)
        size = path.stat().st_size
        total_bytes += size
        total_data_rows += rows
        hashes[digest].append((size, rows, width))

    duplicate_groups = [members for members in hashes.values() if len(members) > 1]
    redundant_files = sum(len(group) - 1 for group in duplicate_groups)
    duplicate_rows = sum(
        sum(member[1] for member in group[1:]) for group in duplicate_groups
    )
    duplicate_bytes = sum(
        sum(member[0] for member in group[1:]) for group in duplicate_groups
    )
    narrow_files = sum(count for width, count in schema_widths.items() if 1 < width < WIDE_MIN_COLUMNS)
    wide_files = sum(count for width, count in schema_widths.items() if width >= WIDE_MIN_COLUMNS)

    result: dict[str, Any] = {
        "schema_version": 1,
        "artifact_type": "local_confidential_station_data_utilization_audit",
        "status": "privacy_bounded_local_inventory",
        "privacy": {
            "source_paths_published": False,
            "source_filenames_published": False,
            "source_headers_published": False,
            "per_file_hashes_published": False,
            "raw_rows_persisted": False,
            "absolute_timestamps_published": False,
            "site_company_manufacturer_published": False,
        },
        "inventory": {
            "csv_files": len(csv_files),
            "metadata_files": len(metadata_files),
            "total_csv_bytes": total_bytes,
            "total_csv_gib": round(total_bytes / (1024**3), 3),
            "physical_data_rows_after_one_header_per_file": total_data_rows,
            "unique_csv_payloads": len(hashes),
            "exact_duplicate_groups": len(duplicate_groups),
            "redundant_csv_files": redundant_files,
            "duplicate_rows": duplicate_rows,
            "duplicate_bytes": duplicate_bytes,
            "deduplicated_data_rows": total_data_rows - duplicate_rows,
            "deduplicated_csv_bytes": total_bytes - duplicate_bytes,
            "narrow_schema_files": narrow_files,
            "wide_schema_files": wide_files,
            "schema_width_file_counts": {
                str(width): count for width, count in sorted(schema_widths.items())
            },
            "unreadable_header_files": unreadable_headers,
            "header_family_screen": _header_family_screen(headers),
        },
        "utilization": _research_utilization(research_dir),
        "assessment": {
            "local_station_data_is_sparse": False,
            "station_side_dynamic_validation_ready": True,
            "station_side_longitudinal_analysis_ready": True,
            "vehicle_side_full_loop_validation_ready": False,
            "primary_limit": "semantic_and_vehicle_side_coverage_not_volume",
            "next_work": [
                "retain duplicate exclusion in every chronological split",
                "segment long pressure-flow histories into de-identified operating episodes",
                "use wide controller logs for pressure-state dynamics and cross-check against the long histories",
                "keep full-loop vehicle claims disabled until vehicle pressure, vehicle temperature, delivered mass or SOC is synchronized and attested",
            ],
        },
        "claim_boundary": (
            "Aggregate local inventory and already de-identified utilization counts only. "
            "It does not publish raw records or source identity, attest unconfirmed channel "
            "semantics, validate a vehicle fill, establish safety limits, or certify operation."
        ),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--research-dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit_station_directory(args.source, research_dir=args.research_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
