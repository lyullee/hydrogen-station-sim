"""Audit continuity of owner-managed wide HRS equipment logs.

The source directory is supplied at execution time and is never copied to the
repository.  The audit intentionally emits only aggregate counts: no source
path, filename, header, timestamp, tag, value, or per-file identifier is
retained.  It is a structural quality screen, not a physics or safety-limit
validation.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from statistics import median
from typing import Any, Iterable, TextIO


WIDE_MIN_COLUMNS = 32
TIME_HEADER = re.compile(r"time|date|timestamp|일시|시간|날짜", re.I)
STATE_HEADER = re.compile(
    r"status|state|alarm|run|running|load|valve|esd|trip|mode|상태|운전|경보|밸브|차단",
    re.I,
)


def _open_csv(path: Path) -> tuple[TextIO, csv.reader]:
    """Open a CSV using the common owner-export encodings."""

    for encoding in ("utf-8-sig", "cp949", "utf-16"):
        stream = path.open("r", encoding=encoding, newline="")
        try:
            reader = csv.reader(stream)
            header = next(reader, None)
        except (UnicodeDecodeError, UnicodeError):
            stream.close()
            continue
        if header is not None:
            return stream, _PreloadedReader(header, reader)
        stream.close()
    raise UnicodeDecodeError("unknown", b"", 0, 1, "unsupported CSV encoding")


class _PreloadedReader:
    """Small iterator that returns a decoded header before the remaining rows."""

    def __init__(self, header: list[str], reader: Iterable[list[str]]) -> None:
        self._header = header
        self._reader = iter(reader)
        self._first = True

    def __iter__(self) -> "_PreloadedReader":
        return self

    def __next__(self) -> list[str]:
        if self._first:
            self._first = False
            return self._header
        return next(self._reader)


def _parse_timestamp(value: str) -> datetime | None:
    text = value.strip().strip('"').replace("/", "-")
    if not text:
        return None
    candidates = (
        "%Y %m %d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    )
    for fmt in candidates:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _to_float(value: str) -> float | None:
    text = value.strip().replace(",", "")
    if not text or text.lower() in {"nan", "na", "n/a", "null", "-"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _normal_state(value: str) -> str:
    text = value.strip().casefold()
    if not text:
        return ""
    return text


def _audit_file(path: Path) -> dict[str, Any] | None:
    stream, reader = _open_csv(path)
    try:
        header = next(reader, [])
        if len(header) < WIDE_MIN_COLUMNS:
            return None
        time_index = next(
            (index for index, name in enumerate(header) if TIME_HEADER.search(str(name))),
            0,
        )
        state_indices = [
            index
            for index, name in enumerate(header)
            if STATE_HEADER.search(str(name)) and index != time_index
        ]
        previous_time: datetime | None = None
        intervals: list[float] = []
        rows = 0
        parse_failures = 0
        duplicate_timestamps = 0
        negative_intervals = 0
        state_transitions = 0
        previous_states: dict[int, str] = {}
        numeric_seen = Counter()
        numeric_missing = Counter()

        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            rows += 1
            timestamp = _parse_timestamp(row[time_index] if time_index < len(row) else "")
            if timestamp is None:
                parse_failures += 1
            elif previous_time is not None:
                gap = (timestamp - previous_time).total_seconds()
                if gap == 0:
                    duplicate_timestamps += 1
                elif gap < 0:
                    negative_intervals += 1
                else:
                    intervals.append(gap)
            if timestamp is not None:
                previous_time = timestamp

            for index, value in enumerate(row):
                if index == time_index:
                    continue
                number = _to_float(value)
                if number is not None:
                    numeric_seen[index] += 1
                else:
                    numeric_missing[index] += 1
            for index in state_indices:
                current = _normal_state(row[index] if index < len(row) else "")
                previous = previous_states.get(index)
                if previous is not None and current and current != previous:
                    state_transitions += 1
                if current:
                    previous_states[index] = current
    finally:
        stream.close()

    numeric_columns = len(numeric_seen)
    fully_finite_numeric_columns = sum(
        1 for index, count in numeric_seen.items() if count == rows and numeric_missing[index] == 0
    )
    return {
        "rows": rows,
        "parse_failures": parse_failures,
        "duplicate_timestamps": duplicate_timestamps,
        "negative_intervals": negative_intervals,
        "intervals": intervals,
        "numeric_columns": numeric_columns,
        "fully_finite_numeric_columns": fully_finite_numeric_columns,
        "state_candidate_columns": len(state_indices),
        "state_transitions": state_transitions,
    }


def audit_wide_equipment_directory(source: Path, *, generated_at: str | None = None) -> dict[str, Any]:
    """Return a privacy-bounded aggregate continuity screen."""

    files = sorted(
        path for path in source.rglob("*") if path.is_file() and path.suffix.lower() == ".csv"
    )
    reports = [report for path in files if (report := _audit_file(path)) is not None]
    all_intervals = [gap for report in reports for gap in report["intervals"]]
    row_count = sum(report["rows"] for report in reports)
    parse_failures = sum(report["parse_failures"] for report in reports)
    duplicate_timestamps = sum(report["duplicate_timestamps"] for report in reports)
    negative_intervals = sum(report["negative_intervals"] for report in reports)
    return {
        "schema_version": 1,
        "artifact_type": "local_wide_equipment_continuity_screen",
        "status": "privacy_bounded_structural_continuity_screen",
        "generated_at": generated_at or date.today().isoformat(),
        "privacy": {
            "source_paths_published": False,
            "source_filenames_published": False,
            "source_headers_published": False,
            "source_identifiers_published": False,
            "calendar_dates_published": False,
            "raw_rows_persisted": False,
            "per_file_metrics_published": False,
        },
        "inventory": {
            "wide_file_count": len(reports),
            "wide_row_count": row_count,
            "wide_schema_width_minimum": WIDE_MIN_COLUMNS,
            "timestamp_parse_failures": parse_failures,
            "duplicate_timestamp_count": duplicate_timestamps,
            "negative_interval_count": negative_intervals,
            "files_with_monotonic_time": sum(
                1
                for report in reports
                if report["parse_failures"] == 0 and report["negative_intervals"] == 0
            ),
            "median_positive_interval_s": median(all_intervals) if all_intervals else None,
            "maximum_positive_interval_s": max(all_intervals) if all_intervals else None,
            "numeric_column_count_min": min(
                (report["numeric_columns"] for report in reports), default=0
            ),
            "numeric_columns_fully_finite_total": sum(
                report["fully_finite_numeric_columns"] for report in reports
            ),
            "state_candidate_column_count": sum(report["state_candidate_columns"] for report in reports),
            "state_transition_count": sum(report["state_transitions"] for report in reports),
        },
        "eligibility": {
            "station_equipment_continuity_screen_ready": bool(reports)
            and parse_failures == 0
            and negative_intervals == 0,
            "measured_boundary_replay_ready": False,
            "independent_external_validation": False,
            "full_loop_vehicle_validation": False,
            "quantitative_consequence_validation": False,
            "runtime_parameter_application": False,
        },
        "claim_boundary": (
            "This aggregate screen checks time continuity, numeric completeness and candidate "
            "state transitions only. Units, pressure reference, state meanings and engineering "
            "semantics require custodian attestation before replay or calibration."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generated-at", default=None)
    args = parser.parse_args()
    result = audit_wide_equipment_directory(args.source, generated_at=args.generated_at)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
