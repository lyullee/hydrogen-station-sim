"""Audit owner-controlled HRS pressure/lifecycle exports without persisting raw data.

The input is intentionally read outside the public repository.  This command
records only aggregate row counts, coarse schema families, time-axis quality and
counter monotonicity.  It never writes paths, filenames, tag names, calendar
values, sample rows or per-file hashes.  The result is therefore useful for
deciding which station-side validation can proceed while keeping the source
archive private.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
from typing import Any


SIZE_BUCKETS = ("<1MiB", "1-100MiB", "100-500MiB", ">=500MiB")
DURATION_BUCKETS = ("<1h", "1-24h", "1-7d", "7-31d", ">=31d")


def _size_bucket(size: int) -> str:
    mib = 1024 * 1024
    if size < mib:
        return "<1MiB"
    if size < 100 * mib:
        return "1-100MiB"
    if size < 500 * mib:
        return "100-500MiB"
    return ">=500MiB"


def _duration_bucket(seconds: float) -> str:
    if seconds < 3600:
        return "<1h"
    if seconds < 24 * 3600:
        return "1-24h"
    if seconds < 7 * 24 * 3600:
        return "1-7d"
    if seconds < 31 * 24 * 3600:
        return "7-31d"
    return ">=31d"


def _encoding_and_headers(path: Path) -> tuple[str, list[str]]:
    raw = path.open("rb").read(256 * 1024)
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "latin-1"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        line = text.splitlines()[0] if text.splitlines() else ""
        delimiter = "," if line.count(",") >= line.count(";") else ";"
        headers = next(csv.reader([line], delimiter=delimiter), [])
        if len(headers) > 1:
            return encoding, [header.strip() for header in headers]
    return "utf-8-sig", []


def _parse_time(value: str) -> datetime | None:
    value = value.strip().strip("\ufeff")
    formats = (
        "%Y-%m-%d %I:%M:%S %p",
        "%Y-%m-%d %I:%M:%S.%f %p",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y/%m/%d %I:%M:%S %p",
        "%Y/%m/%d %H:%M:%S",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %H:%M:%S",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _role_presence(headers: list[str]) -> set[str]:
    normalized = [header.strip().lower() for header in headers]
    roles: set[str] = set()
    if any("pressure" in h or "pt_" in h or "pi_" in h for h in normalized):
        roles.add("pressure")
    if any("temperature" in h or "temp" in h or "tt_" in h or "ti_" in h for h in normalized):
        roles.add("temperature")
    if any("flow" in h or "fqi" in h or "rate" in h or "acc" in h for h in normalized):
        roles.add("flow_or_totalizer")
    if any("status" in h or "alarm" in h or "valve" in h or "xv_" in h or "ii_" in h for h in normalized):
        roles.add("state_or_alarm")
    if any("lifecycle" in h or "_cnt" in h or "count" in h for h in normalized):
        roles.add("lifecycle_counter")
    return roles


def _timestamp_indices(headers: list[str]) -> list[int]:
    return [
        index
        for index, header in enumerate(headers)
        if any(token in header.strip().lower() for token in ("time", "date", "local", "utc", "시간"))
    ]


def _counter_indices(headers: list[str]) -> list[int]:
    return [
        index
        for index, header in enumerate(headers)
        if any(token in header.strip().lower() for token in ("lifecycle", "_cnt", "count"))
    ]


def _audit_file(path: Path) -> dict[str, Any]:
    encoding, headers = _encoding_and_headers(path)
    if not headers:
        return {
            "rows": 0,
            "columns": 0,
            "roles": [],
            "timestamp_parseable": False,
            "timestamp_monotonic": False,
            "timestamp_order": "unknown",
            "duration_s": None,
            "counter_observed": False,
            "counter_numeric_rows": 0,
            "counter_decreases": 0,
            "counter_increases": 0,
            "counter_directional_violations": 0,
        }
    with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
        first_line = handle.readline()
        delimiter = "," if first_line.count(",") >= first_line.count(";") else ";"
        reader = csv.reader(handle, delimiter=delimiter)
        timestamp_indices = _timestamp_indices(headers)
        timestamp_index = timestamp_indices[0] if timestamp_indices else None
        counter_indices = _counter_indices(headers)
        row_count = 0
        first_time: datetime | None = None
        last_time: datetime | None = None
        previous_time: datetime | None = None
        last_time_raw: str | None = None
        timestamp_signs: set[int] = set()
        counter_last: dict[int, float] = {}
        counter_numeric_rows = 0
        counter_decreases = 0
        counter_increases = 0
        for row in reader:
            row_count += 1
            if timestamp_index is not None and timestamp_index < len(row):
                # Parsing every timestamp with strptime is unnecessarily slow
                # for multi-million-row exports.  Parse the endpoints and a
                # sparse sample; the result is a schema/time-axis screen, not
                # a claim of complete clock integrity.
                should_sample = row_count == 1 or row_count % 10_000 == 0
                parsed = _parse_time(row[timestamp_index]) if should_sample else None
                last_time_raw = row[timestamp_index]
                if parsed is not None:
                    first_time = first_time or parsed
                    if previous_time is not None and parsed != previous_time:
                        timestamp_signs.add(1 if parsed > previous_time else -1)
                    previous_time = parsed
                    last_time = parsed
                elif row_count == 1:
                    first_time = _parse_time(row[timestamp_index])
            for index in counter_indices:
                if index >= len(row):
                    continue
                try:
                    value = float(row[index].strip())
                except (TypeError, ValueError):
                    continue
                counter_numeric_rows += 1
                if index in counter_last and value < counter_last[index]:
                    counter_decreases += 1
                elif index in counter_last and value > counter_last[index]:
                    counter_increases += 1
                counter_last[index] = value
        if last_time_raw is not None:
            # Keep only the final timestamp value for duration.  It is parsed
            # once after streaming so no calendar value is persisted.
            last_time = _parse_time(last_time_raw)
    duration_s = None
    if first_time is not None and last_time is not None:
        duration_s = abs((last_time - first_time).total_seconds())
    if not timestamp_signs:
        timestamp_order = "single_value_or_unknown"
    elif timestamp_signs == {1}:
        timestamp_order = "ascending"
    elif timestamp_signs == {-1}:
        timestamp_order = "descending"
    else:
        timestamp_order = "mixed"
    if timestamp_order == "ascending":
        directional_violations = counter_decreases
    elif timestamp_order == "descending":
        directional_violations = counter_increases
    else:
        directional_violations = counter_decreases + counter_increases
    return {
        "rows": row_count,
        "columns": len(headers),
        "roles": sorted(_role_presence(headers)),
        "timestamp_parseable": first_time is not None and last_time is not None,
        "timestamp_monotonic": len(timestamp_signs) <= 1 if first_time is not None else False,
        "timestamp_order": timestamp_order,
        "duration_s": duration_s,
        "counter_observed": bool(counter_indices),
        "counter_numeric_rows": counter_numeric_rows,
        "counter_decreases": counter_decreases,
        "counter_increases": counter_increases,
        "counter_directional_violations": directional_violations,
    }


def audit(root: Path) -> dict[str, Any]:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".csv")
    size_buckets = {bucket: 0 for bucket in SIZE_BUCKETS}
    duration_buckets = {bucket: 0 for bucket in DURATION_BUCKETS}
    role_file_counts: dict[str, int] = {}
    role_row_counts: dict[str, int] = {}
    schema_families: dict[tuple[int, tuple[str, ...]], dict[str, int]] = {}
    total_rows = 0
    timestamp_parseable_files = 0
    timestamp_monotonic_files = 0
    timestamp_order_counts: dict[str, int] = {}
    counter_files = 0
    counter_numeric_rows = 0
    counter_decreases = 0
    counter_increases = 0
    counter_directional_violations = 0
    counter_files_with_parseable_direction = 0

    for path in files:
        size_buckets[_size_bucket(path.stat().st_size)] += 1
        result = _audit_file(path)
        rows = int(result["rows"])
        total_rows += rows
        roles = tuple(result["roles"])
        for role in roles:
            role_file_counts[role] = role_file_counts.get(role, 0) + 1
            role_row_counts[role] = role_row_counts.get(role, 0) + rows
        family = schema_families.setdefault(
            (int(result["columns"]), roles),
            {"file_count": 0, "row_count": 0},
        )
        family["file_count"] += 1
        family["row_count"] += rows
        if result["timestamp_parseable"]:
            timestamp_parseable_files += 1
        if result["timestamp_monotonic"]:
            timestamp_monotonic_files += 1
        order = str(result["timestamp_order"])
        timestamp_order_counts[order] = timestamp_order_counts.get(order, 0) + 1
        if result["duration_s"] is not None:
            duration_buckets[_duration_bucket(float(result["duration_s"]))] += 1
        if result["counter_observed"]:
            counter_files += 1
            counter_numeric_rows += int(result["counter_numeric_rows"])
            counter_decreases += int(result["counter_decreases"])
            counter_increases += int(result["counter_increases"])
            counter_directional_violations += int(result["counter_directional_violations"])
            if result["timestamp_order"] in {"ascending", "descending"}:
                counter_files_with_parseable_direction += 1

    family_rows = []
    for index, ((columns, roles), counts) in enumerate(sorted(schema_families.items()), start=1):
        family_rows.append(
            {
                "id": f"schema_family_{index}",
                "column_count": columns,
                "roles": list(roles),
                **counts,
            }
        )

    return {
        "schema_version": 1,
        "artifact_type": "confidential_private_station_pressure_lifecycle_audit",
        "recorded_at": datetime.now().strftime("%Y-%m"),
        "source_scope": "owner-controlled hydrogen-refuelling-station pressure and lifecycle exports",
        "privacy": {
            "source_identifiers_published": False,
            "source_paths_published": False,
            "source_filenames_published": False,
            "source_headers_published": False,
            "raw_rows_persisted": False,
            "calendar_values_published": False,
            "site_company_location_manufacturer_published": False,
        },
        "inventory": {
            "file_count": len(files),
            "total_row_count": total_rows,
            "size_buckets": size_buckets,
            "schema_families": family_rows,
            "role_file_counts": dict(sorted(role_file_counts.items())),
            "role_row_counts": dict(sorted(role_row_counts.items())),
        },
        "time_axis_screen": {
            "files_with_parseable_timestamp": timestamp_parseable_files,
            "files_with_monotonic_timestamp": timestamp_monotonic_files,
            "timestamp_order_counts": dict(sorted(timestamp_order_counts.items())),
            "duration_buckets": duration_buckets,
            "calendar_values_persisted": False,
        },
        "lifecycle_counter_screen": {
            "files_with_counter": counter_files,
            "counter_files_with_parseable_direction": counter_files_with_parseable_direction,
            "numeric_counter_observations": counter_numeric_rows,
            "counter_decrease_observations_in_file_order": counter_decreases,
            "counter_increase_observations_in_file_order": counter_increases,
            "counter_directional_violations_after_time_order": counter_directional_violations,
            "monotonicity_claim_supported": (
                counter_files > 0
                and counter_files_with_parseable_direction == counter_files
                and counter_directional_violations == 0
            ),
            "counter_semantics_attested": False,
        },
        "reconciliation": {
            "prior_attested_lifecycle_summary_in_repository": True,
            "this_collection_level_screen_replaces_prior_summary": False,
            "merge_decision": "HOLD_UNTIL_FILE_SEGMENT_AND_RESET_MAPPING",
            "reason": (
                "The collection contains multiple time-segment schemas and mixed timestamp direction. "
                "The prior attested summary is retained as a separate bounded result; this broader screen "
                "must not be concatenated into it until segment identity and reset semantics are confirmed."
            ),
        },
        "eligibility": {
            "station_side_pressure_replay_candidate": role_file_counts.get("pressure", 0) > 0,
            "station_side_lifecycle_alignment_candidate": counter_files > 0,
            "station_side_temperature_or_flow_candidate": bool(
                role_file_counts.get("temperature") or role_file_counts.get("flow_or_totalizer")
            ),
            "parameter_fit_authorized": False,
            "vehicle_or_receptacle_channels_present": False,
            "full_loop_holdout_eligible": False,
        },
        "next_custodian_checks": [
            "Confirm engineering units, scaling, quality flags and tag-role mapping before fitting.",
            "Confirm whether lifecycle counters increment on completed 450/850-bar cycles and how resets are encoded.",
            "Freeze relative-time event windows and independent holdouts without publishing calendar dates.",
            "Supply synchronized vehicle/receptacle pressure, temperature and delivered-mass channels for full-loop validation.",
            "Keep the raw archive outside the public repository and retain written reuse permission.",
        ],
        "claim_boundary": (
            "Privacy-bounded station-side schema, time-axis and lifecycle-counter screening only. "
            "This artifact does not attest units, calibration, physical correctness, safety distance, "
            "vehicle filling, full-loop validation or field effectiveness."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
