"""Recheck mapped private station-channel quality without exporting raw data.

The command is intentionally a quality screen, not a calibration runner.  A
custodian supplies the source-column mapping at execution time.  The output
contains only generic role counts, finite/missing fractions, time-base
coverage and discrete transition counts; source paths, filenames, tags,
timestamps and measured values never leave memory.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import math
from pathlib import Path
from statistics import median
from typing import Any


TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%m/%d/%Y %I:%M:%S %p",
    "%Y %m %d %H:%M:%S",
)


def _files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".csv")


def _parse_time(value: str, formats: tuple[str, ...]) -> float | None:
    raw = value.strip().strip("\ufeff")
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).timestamp()
        except ValueError:
            continue
    try:
        number = float(raw)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _finite(value: str | None) -> bool:
    if value is None or not value.strip():
        return False
    try:
        return math.isfinite(float(value))
    except ValueError:
        return False


def _mapping(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("mapping must be a JSON object")
    return value


def _columns(value: dict[str, Any], key: str) -> list[str]:
    raw = value.get(key) or []
    result: list[str] = []
    for item in raw:
        if isinstance(item, list) and len(item) >= 2:
            result.append(str(item[1]))
        elif isinstance(item, str):
            result.append(item)
    return result


def _state_columns(value: dict[str, Any]) -> list[str]:
    return _columns(value, "state_columns")


def audit(root: Path, mapping_path: Path, *, stride: int = 60, max_rows_per_file: int = 250_000) -> dict[str, Any]:
    if stride < 1 or max_rows_per_file < 1:
        raise ValueError("stride and max_rows_per_file must be positive")
    mapping = _mapping(mapping_path)
    paths = _files(root)
    if not paths:
        raise ValueError("no CSV files found")
    encoding = str(mapping.get("encoding", "utf-8-sig"))
    time_index = mapping.get("time_column_index")
    time_column = mapping.get("time_column")
    formats = tuple(mapping.get("time_formats") or TIME_FORMATS)
    role_columns = {
        "pressure": _columns(mapping, "pressure_columns"),
        "temperature": _columns(mapping, "temperature_columns"),
        "flow": [str(item) for item in (mapping.get("flow_columns") or [])],
        "discrete_state": _state_columns(mapping),
        "lifecycle": _columns(mapping, "lifecycle_columns"),
    }
    if time_index is None and not time_column:
        raise ValueError("time_column or time_column_index is required")
    role_seen = {role: 0 for role in role_columns}
    role_finite = {role: 0 for role in role_columns}
    role_missing = {role: 0 for role in role_columns}
    state_transitions = 0
    total_rows = 0
    sampled_rows = 0
    parseable_times = 0
    interval_values: list[float] = []
    positive_intervals = 0
    negative_intervals = 0
    duplicate_intervals = 0
    duration_values: list[float] = []
    for path in paths:
        with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
            first = handle.readline()
            delimiter = "," if first.count(",") >= first.count(";") else ";"
            headers = next(csv.reader([first], delimiter=delimiter), [])
            headers = [header.strip() for header in headers]
            if time_index is not None:
                index = int(time_index)
                if index < 0 or index >= len(headers):
                    raise ValueError(f"mapped time index is absent from {path.name}")
                selected_time_column = headers[index]
            else:
                selected_time_column = str(time_column)
                if selected_time_column not in headers:
                    raise ValueError(f"mapped time column is absent from {path.name}")
            reader = csv.DictReader(handle, fieldnames=headers, delimiter=delimiter)
            previous_time: float | None = None
            first_time: float | None = None
            last_time: float | None = None
            previous_states: dict[str, str] = {}
            for row_index, row in enumerate(reader):
                total_rows += 1
                if row_index % stride:
                    continue
                if sampled_rows >= max_rows_per_file * len(paths):
                    break
                sampled_rows += 1
                timestamp = _parse_time(str(row.get(selected_time_column, "")), formats)
                if timestamp is not None:
                    parseable_times += 1
                    first_time = timestamp if first_time is None else min(first_time, timestamp)
                    last_time = timestamp if last_time is None else max(last_time, timestamp)
                    if previous_time is not None:
                        delta = timestamp - previous_time
                        if delta > 0.0:
                            positive_intervals += 1
                        elif delta < 0.0:
                            negative_intervals += 1
                        else:
                            duplicate_intervals += 1
                        if delta != 0.0 and len(interval_values) < 100_000:
                            interval_values.append(abs(delta))
                    previous_time = timestamp
                for role, columns in role_columns.items():
                    for column in columns:
                        role_seen[role] += 1
                        if _finite(row.get(column)):
                            role_finite[role] += 1
                        else:
                            role_missing[role] += 1
                for column in role_columns["discrete_state"]:
                    value = str(row.get(column, "")).strip()
                    if column in previous_states and value != previous_states[column]:
                        state_transitions += 1
                    previous_states[column] = value
            if first_time is not None and last_time is not None:
                duration_values.append(max(0.0, last_time - first_time))

    roles: dict[str, dict[str, Any]] = {}
    for role in role_columns:
        seen = role_seen[role]
        roles[role] = {
            "mapped_channel_count": len(role_columns[role]),
            "sampled_observations": seen,
            "finite_observations": role_finite[role],
            "missing_or_non_numeric_observations": role_missing[role],
            "finite_fraction": round(role_finite[role] / seen, 6) if seen else None,
        }
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_channel_quality_recheck",
        "recorded_at": datetime.now().strftime("%Y-%m-%d"),
        "source_scope": "owner-controlled station archive; generic channel-quality aggregate only",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "exact_source_dates_published": False,
        "source_paths_published": False,
        "sampling": {"stride": stride, "max_rows_per_file": max_rows_per_file},
        "files_read": len(paths),
        "rows_seen": total_rows,
        "sampled_rows": sampled_rows,
        "parseable_timestamp_fraction": round(parseable_times / sampled_rows, 6) if sampled_rows else None,
        "timebase": {
            "duration_s_min": min(duration_values) if duration_values else None,
            "duration_s_max": max(duration_values) if duration_values else None,
            "median_interval_s": median(interval_values) if interval_values else None,
            "maximum_interval_s": max(interval_values) if interval_values else None,
            "positive_interval_count": positive_intervals,
            "negative_interval_count": negative_intervals,
            "duplicate_interval_count": duplicate_intervals,
        },
        "roles": roles,
        "discrete_state_transition_count": state_transitions,
        "eligibility": {
            "station_channel_quality_recheck_supported": bool(sampled_rows and parseable_times),
            "temperature_or_flow_parameter_fit_supported": False,
            "full_station_vehicle_validation": False,
            "full_loop_holdout_eligible": False,
        },
        "claim_boundary": (
            "This is a de-identified station-side channel-quality screen. It does not attest units, "
            "calibration, tag semantics, vehicle-side accuracy, safety limits or full-loop validation."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=60)
    parser.add_argument("--max-rows-per-file", type=int, default=250_000)
    args = parser.parse_args()
    result = audit(
        args.input,
        args.mapping,
        stride=args.stride,
        max_rows_per_file=args.max_rows_per_file,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
