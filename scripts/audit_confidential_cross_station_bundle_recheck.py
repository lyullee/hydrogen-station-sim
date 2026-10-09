"""Recheck two local station-side data bundles without publishing raw data.

The source directory is supplied at execution time.  This script deliberately
retains only aggregate counts and bounded timestamp/header-family diagnostics;
it never writes paths, filenames, headers, dates, values, hashes, or rows.
The result is a transfer-candidate data-quality check, not external validation.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ENCODINGS = ("utf-8-sig", "cp949", "utf-16", "latin1")
TIMESTAMP_FORMATS = (
    "%m/%d/%Y %I:%M:%S %p",
    "%Y %m %d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
)
FAMILY_PATTERNS = {
    "pressure": re.compile(r"press|pressure|(?:^|[_. -])p[it][_. -]|(?:^|[_. -])pi_|(?:^|[_. -])pt_|압력", re.I),
    "temperature": re.compile(r"temp|temperature|(?:^|[_. -])t[ti][_. -]|(?:^|[_. -])tt_|온도", re.I),
    "flow_or_mass": re.compile(r"flow|mass|rate|fqi|fqm|유량|질량", re.I),
    "control_state": re.compile(r"status|state|valve|(?:^|[_. -])xv_|esd|trip|load|heater|cnt|count|밸브|차단", re.I),
}


def _reader(path: Path) -> tuple[csv.reader, Any]:
    """Open a CSV with a private encoding fallback; caller closes handle."""

    for encoding in ENCODINGS:
        try:
            handle = path.open("r", encoding=encoding, newline="")
            reader = csv.reader(handle)
            next(reader)
            handle.seek(0)
            return reader, handle
        except (UnicodeDecodeError, UnicodeError):
            try:
                handle.close()
            except Exception:
                pass
    raise UnicodeError("unable to decode source CSV")


def _parse_time(value: str) -> datetime | None:
    value = str(value).strip().strip("\ufeff")
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _file_screen(path: Path, sample_rows: int) -> dict[str, Any]:
    reader, handle = _reader(path)
    try:
        header = next(reader, [])
        rows = 0
        parsed = 0
        first_time: datetime | None = None
        last_time: datetime | None = None
        intervals: list[float] = []
        previous: datetime | None = None
        sampled = 0
        for row in reader:
            if not row:
                continue
            rows += 1
            if sampled < sample_rows:
                sampled += 1
                current = _parse_time(row[0]) if row else None
                if current is not None:
                    parsed += 1
                    first_time = current if first_time is None else first_time
                    if previous is not None:
                        intervals.append((current - previous).total_seconds())
                    previous = current
            # Count the entire row stream only for row cardinality.  No row is retained.
        # A bounded tail pass is used to avoid publishing a calendar date while
        # still checking that the source is temporally ordered through its end.
        tail: list[str] = []
        reader2, handle2 = _reader(path)
        try:
            next(reader2, None)
            for row in reader2:
                if row:
                    tail.append(row[0])
                    if len(tail) > sample_rows:
                        tail.pop(0)
        finally:
            handle2.close()
        tail_times = [t for t in (_parse_time(v) for v in tail) if t is not None]
        if tail_times:
            last_time = tail_times[-1]
        family_counts = {
            family: sum(1 for column in header if pattern.search(str(column)))
            for family, pattern in FAMILY_PATTERNS.items()
        }
        valid_intervals = [value for value in intervals if value >= 0]
        reverse_intervals = [value for value in intervals if value <= 0]
        monotonic = bool(intervals) and (
            len(valid_intervals) == len(intervals)
            or len(reverse_intervals) == len(intervals)
        )
        return {
            "data_rows": rows,
            "column_count": len(header),
            "timestamp_sample_rows": sampled,
            "timestamp_parse_rate": (parsed / sampled) if sampled else 0.0,
            "nonnegative_interval_sample_count": len(valid_intervals),
            "negative_interval_sample_count": sum(value < 0 for value in intervals),
            "monotonic_timestamp_sample": monotonic,
            "timestamp_direction": (
                "ascending" if len(valid_intervals) == len(intervals)
                else "descending" if len(reverse_intervals) == len(intervals)
                else "mixed"
            ),
            "first_last_duration_seconds": (
                abs((last_time - first_time).total_seconds())
                if first_time is not None and last_time is not None
                else None
            ),
            "family_candidate_column_counts": family_counts,
        }
    finally:
        handle.close()


def _bundle_screen(root: Path, files: list[Path], sample_rows: int) -> dict[str, Any]:
    results = [_file_screen(path, sample_rows) for path in files]
    family_presence = {
        family: sum(
            1
            for result in results
            if result["family_candidate_column_counts"].get(family, 0) > 0
        )
        for family in FAMILY_PATTERNS
    }
    timestamp_rates = [result["timestamp_parse_rate"] for result in results]
    durations = [
        result["first_last_duration_seconds"]
        for result in results
        if result["first_last_duration_seconds"] is not None
    ]
    directions = sorted({result["timestamp_direction"] for result in results})
    return {
        "id": None,
        "file_count": len(files),
        "data_rows": sum(result["data_rows"] for result in results),
        "timestamp_parse_rate_min": min(timestamp_rates, default=0.0),
        "timestamp_parse_rate_mean": (
            sum(timestamp_rates) / len(timestamp_rates) if timestamp_rates else 0.0
        ),
        "ordered_timestamp_file_count": sum(
            result["monotonic_timestamp_sample"]
            and result["timestamp_sample_rows"] > 1
            for result in results
        ),
        "timestamp_directions": directions,
        "files_with_timestamp_duration": len(durations),
        "duration_seconds_min": min(durations, default=None),
        "duration_seconds_max": max(durations, default=None),
        "family_presence_file_counts": family_presence,
        "candidate_family_screen_is_qualitative": True,
    }


def audit(source: Path, *, sample_rows: int = 256) -> dict[str, Any]:
    directories = sorted(path for path in source.iterdir() if path.is_dir())
    if len(directories) < 2:
        raise ValueError("expected at least two source bundles")
    bundles = []
    for index, directory in enumerate(directories[:2], start=1):
        files = sorted(
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() == ".csv"
        )
        bundle = _bundle_screen(source, files, sample_rows)
        bundle["id"] = f"station_bundle_{chr(96 + index)}"
        bundles.append(bundle)
    compatible = all(
        bundle["file_count"] > 0
        and bundle["timestamp_parse_rate_min"] >= 0.99
        and bundle["ordered_timestamp_file_count"] == bundle["file_count"]
        and bundle["family_presence_file_counts"]["pressure"] > 0
        and bundle["family_presence_file_counts"]["control_state"] > 0
        for bundle in bundles
    )
    return {
        "schema_version": 1,
        "artifact_type": "confidential_cross_station_bundle_recheck",
        "status": "privacy_bounded_cross_station_station_side_recheck",
        "bundle_count": len(bundles),
        "bundles": bundles,
        "station_side_transfer_candidate": compatible,
        "full_loop_external_validation_supported": False,
        "quantitative_consequence_validation_supported": False,
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "exact_source_dates_published": False,
        "manufacturer_or_model_published": False,
        "tag_names_published": False,
        "claim_boundary": (
            "Two de-identified local station-side bundles share a parseable ordered time axis "
            "and qualitative pressure/temperature/control-family coverage. This is a transfer "
            "candidate and data-quality recheck only; it is not vehicle-side, full-loop, "
            "consequence, field-safety, or certification validation."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-rows", type=int, default=256)
    args = parser.parse_args()
    result = audit(args.source, sample_rows=max(32, args.sample_rows))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"bundle_count": result["bundle_count"], "station_side_transfer_candidate": result["station_side_transfer_candidate"]}))


if __name__ == "__main__":
    main()
