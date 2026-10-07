"""Inventory controlled HRS data schemas without reading measurements.

This command is deliberately restricted to schema screening.  It helps a data
custodian find candidate station, vehicle-fuelling, and complete-loop events
before a mapping or any model outcome is read. To support exports with title
rows, it inspects at most the first 40 rows of each table to locate a probable
header and up to three following rows to require a strictly monotonic time-like
logger clock. The report contains only aggregate semantic coverage counts; it
never emits filenames, worksheet names, original headers, source values,
timestamps, or data rows.

It is an intake aid, not a validation result.  A full-loop candidate still
needs a custodian mapping, units and calibration attestation, verified time
synchronization, an outcome-free protocol, and an untouched holdout before it
can be evaluated by the model.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date, datetime, time, timezone
from io import BytesIO, StringIO
from itertools import islice
import json
from pathlib import Path
import re
from typing import Iterable
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_SUFFIXES = frozenset({".csv", ".xlsx", ".xlsm", ".zip"})
TABULAR_SUFFIXES = frozenset({".csv", ".xlsx", ".xlsm"})
HEADER_SEARCH_MAX_ROWS = 40
DATA_LIKENESS_SAMPLE_ROWS = 3
MAX_ARCHIVE_MEMBER_BYTES = 100 * 1024 * 1024
TIME_AXIS_TAIL_BYTES = 128 * 1024

# These terms are deliberately broad: candidate classification is only a
# request for a custodian review, never automatic tag or unit attribution.
SEMANTIC_TERMS: dict[str, tuple[str, ...]] = {
    "time": (
        "time", "date", "timestamp", "clock", "datetime", "localtime", "zeit", "시간", "일시", "시각", "날짜",
    ),
    "pressure": ("pressure", "press", "압력"),
    "temperature": ("temp", "temperature", "온도"),
    "mass_flow": ("flow", "mass", "rate", "유량", "질량", "유속", "질량유량"),
    "vehicle": ("vehicle", "car", "automobile", "자동차", "차량", "수소차", "차종", "veh_", "veh-"),
    "cascade_or_storage": (
        "cascade", "bank", "storage", "vessel", "저장", "뱅크", "저장용기", "저장탱크", "casc_",
    ),
    "controller_state": (
        "state", "status", "valve", "esd", "mode", "control", "alarm", "interlock",
        "상태", "밸브", "제어", "모드", "운전", "기동", "정지", "경보", "알람", "차단", "인터록", "시퀀스",
    ),
    "compressor": ("compress", "comp_", "압축", "부스터"),
    "dispenser_or_nozzle": (
        "dispenser", "nozzle", "hose", "refuel", "충전기", "노즐", "호스", "충전",
    ),
}

# Instrument tags are common in controlled logger exports but are too terse to
# be recognized by word matching alone.  These patterns require a complete tag
# token and never attribute a physical role beyond the generic family.
INSTRUMENT_TAG_PATTERNS: dict[str, re.Pattern[str]] = {
    "pressure": re.compile(r"(?:^|[._\s-])(?:pt|pi)(?:$|[._\s-]|\d)", re.IGNORECASE),
    "temperature": re.compile(r"(?:^|[._\s-])tt(?:$|[._\s-]|\d)", re.IGNORECASE),
    "mass_flow": re.compile(
        r"(?:^|[._\s-])(?:ft|fqi|mfm|fwg)(?:$|[._\s-]|\d)", re.IGNORECASE,
    ),
}

FULL_LOOP_REQUIRED = frozenset({
    "time", "pressure", "temperature", "mass_flow", "vehicle",
    "cascade_or_storage", "controller_state",
})
STATION_RECHARGE_REQUIRED = frozenset({
    "time", "pressure", "cascade_or_storage", "controller_state", "compressor",
})
VEHICLE_FILL_REQUIRED = frozenset({
    "time", "pressure", "temperature", "mass_flow", "vehicle", "dispenser_or_nozzle",
})


def _outside_repository(path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{label} must be outside the repository worktree")


def _is_compact_label(value: str) -> bool:
    """Reject prose cells that merely mention several measurement concepts."""

    cleaned = value.strip()
    tag_like = bool(re.fullmatch(r"[A-Za-z0-9_.-]+", cleaned))
    return (
        bool(cleaned)
        and len(cleaned) <= 80
        and len(cleaned.split()) <= 10
        and "\n" not in cleaned
        and (cleaned.count(".") <= 1 or tag_like)
    )


def _best_header(rows: Iterable[Iterable[object]]) -> tuple[tuple[str, ...], int] | None:
    """Choose a likely header without retaining any source content.

    A controlled export can include one or more title rows before its labels.
    Score only the semantic groups and the number of textual cells.  Numeric
    measurement values therefore do not make a row more likely to be chosen.
    """

    selected: tuple[str, ...] | None = None
    selected_index = 0
    selected_score: tuple[int, int, int] | None = None
    rows_examined = 0
    for index, row in enumerate(rows, start=1):
        if index > HEADER_SEARCH_MAX_ROWS:
            break
        rows_examined = index
        candidate = tuple(str(value or "") for value in row)
        coverage = _classify_header(candidate)
        text_cells = sum(
            1
            for value in candidate
            if value.strip() and not _is_number(value)
        )
        # Earlier equivalent label rows win over later rows.
        score = (len(coverage), text_cells, -index)
        if selected_score is None or score > selected_score:
            selected, selected_index, selected_score = candidate, index, score
    if selected is None:
        return None
    return selected, rows_examined


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _row_has_record_shape(row: Iterable[object], expected_columns: int) -> bool:
    """Check only shape, not content, of a row following a proposed header."""

    values = tuple(row)
    populated = sum(
        bool(value is not None and str(value).strip()) for value in values
    )
    return expected_columns >= 2 and populated >= min(2, expected_columns) and (
        len(values) >= expected_columns
    )


def _is_time_observation(value: object) -> float | None:
    """Return a sortable marker only for a plausible logged time observation.

    Header vocabulary alone cannot distinguish a HAZOP worksheet's duration
    column from a logger's sampling clock.  This deliberately small parser is
    used only on the three in-memory data-likeness rows; it persists neither
    original values nor their converted timestamps.
    """

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, date):
        return datetime.combine(value, time.min).timestamp()
    if isinstance(value, time):
        return (
            value.hour * 3600.0
            + value.minute * 60.0
            + value.second
            + value.microsecond / 1_000_000.0
        )
    if isinstance(value, (int, float)):
        try:
            numeric = float(value)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return None
        return numeric if numeric == numeric and abs(numeric) != float("inf") else None
    if not isinstance(value, str):
        return None
    compact = value.strip()
    if not compact:
        return None
    try:
        numeric = float(compact)
        return numeric if numeric == numeric and abs(numeric) != float("inf") else None
    except ValueError:
        pass
    # ISO-like absolute timestamps and clock-only samples cover common logger
    # exports without interpreting arbitrary prose as a time value.
    normalized = compact.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        pass
    # U.S. locale exports from industrial historians commonly render the same
    # clock as ``M/D/YYYY H:MM:SS AM``.  It is used only to establish a
    # monotonically ordered logger candidate; the subsequent private mapping
    # still requires a custodian-declared time format and time basis.
    for time_format in (
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M:%S.%f %p",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S.%f",
        "%Y %m %d %H:%M:%S",
        "%Y %m %d %H:%M:%S.%f",
    ):
        try:
            return datetime.strptime(compact, time_format).replace(
                tzinfo=timezone.utc,
            ).timestamp()
        except ValueError:
            pass
    try:
        parsed = time.fromisoformat(compact)
    except ValueError:
        return None
    return (
        parsed.hour * 3600.0
        + parsed.minute * 60.0
        + parsed.second
        + parsed.microsecond / 1_000_000.0
    )


def _time_series_like_samples(
    labels: tuple[str, ...], samples: Iterable[tuple[object, ...]],
) -> bool:
    """Require a strictly monotonic clock under a time-labelled logger column.

    Some industrial historians export the newest observation first. A
    decreasing sequence remains a genuine logger clock and is normalized by a
    later, explicitly mapped replay/export path. Repeated and mixed-order
    values remain ineligible because they cannot establish a sample order.
    """

    time_indices = [
        index
        for index, label in enumerate(labels)
        if "time" in _classify_header((label,))
    ]
    if not time_indices:
        return False
    rows = tuple(samples)
    for index in time_indices:
        observed = [
            _is_time_observation(row[index] if index < len(row) else None)
            for row in rows
        ]
        observed = [value for value in observed if value is not None]
        deltas = [later - earlier for earlier, later in zip(observed, observed[1:])]
        if len(observed) >= 2 and (
            all(delta > 0.0 for delta in deltas)
            or all(delta < 0.0 for delta in deltas)
        ):
            return True
    return False


def _screen_rows(
    rows: Iterable[Iterable[object]],
) -> tuple[tuple[str, ...], int, bool, bool] | None:
    """Locate a header and retain record-shape and time-series checks.

    At most three following rows are inspected in memory to reject narrative
    sheets that happen to mention operational terms.  No values, headers, or
    row identifiers leave this function.
    """

    buffered = [
        tuple(row)
        for row in islice(rows, HEADER_SEARCH_MAX_ROWS + DATA_LIKENESS_SAMPLE_ROWS)
    ]
    selected = _best_header(buffered[:HEADER_SEARCH_MAX_ROWS])
    if selected is None:
        return None
    header, rows_examined = selected
    header_index = next(
        (
            index
            for index, row in enumerate(buffered[:HEADER_SEARCH_MAX_ROWS])
            if tuple(str(value or "") for value in row) == header
        ),
        None,
    )
    if header_index is None:
        return None
    samples = buffered[
        header_index + 1: header_index + 1 + DATA_LIKENESS_SAMPLE_ROWS
    ]
    record_shaped = any(_row_has_record_shape(row, len(header)) for row in samples)
    return header, rows_examined, record_shaped, _time_series_like_samples(header, samples)


def _csv_encodings(raw: bytes) -> tuple[str, ...]:
    """Prioritize the encoding signalled by BOM or UTF-16 null-byte layout."""

    prefix = raw[:1024]
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return ("utf-16", "utf-16le", "utf-16be", "utf-8-sig", "cp949", "euc-kr")
    if prefix and prefix.count(b"\x00") >= max(2, len(prefix) // 8):
        return ("utf-16le", "utf-16be", "utf-16", "utf-8-sig", "cp949", "euc-kr")
    return ("utf-8-sig", "utf-8", "cp949", "euc-kr", "utf-16le", "utf-16be")


def _csv_header_bytes(raw: bytes) -> tuple[tuple[str, ...], int, bool, bool] | None:
    for encoding in _csv_encodings(raw):
        try:
            return _screen_rows(csv.reader(StringIO(raw.decode(encoding))))
        except UnicodeError:
            continue
    return None


def _csv_header_file(path: Path) -> tuple[tuple[str, ...], int, bool, bool] | None:
    """Screen a CSV prefix without materializing a controlled logger file.

    Operational exports can be several gigabytes.  Schema screening only needs
    the label-search window and three following records, so loading the whole
    file would be both unnecessarily slow and a poor confidentiality boundary.
    The encoding decision is made from a small byte prefix; the selected text
    stream remains lazy while ``_screen_rows`` consumes its bounded window.
    """

    try:
        with path.open("rb") as binary:
            prefix = binary.read(4096)
    except OSError:
        return None

    for encoding in _csv_encodings(prefix):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return _screen_rows(csv.reader(handle))
        except UnicodeError:
            continue
        except OSError:
            return None
    return None


def _strict_time_direction(values: tuple[float, ...]) -> int | None:
    """Return one direction for a bounded time sample, else ``None``."""

    if len(values) < 2:
        return None
    deltas = tuple(later - earlier for earlier, later in zip(values, values[1:]))
    if all(delta > 0.0 for delta in deltas):
        return 1
    if all(delta < 0.0 for delta in deltas):
        return -1
    return None


def _csv_time_axis_fingerprint(
    path: Path,
    header: tuple[str, ...],
) -> tuple[float, ...] | None:
    """Fingerprint a flat CSV clock from bounded head/tail samples.

    The fingerprint exists only in memory and is never written to the report.
    Requiring matching first *and* last samples is materially stronger than
    grouping files by directory or by a common ``0, 1, 2`` relative clock.
    It still establishes only a synchronization *candidate*: an authorized
    mapping must later verify the complete clocks, units, and event identity.
    """

    time_indices = tuple(
        index for index, label in enumerate(header)
        if "time" in _classify_header((label,))
    )
    if not time_indices:
        return None
    try:
        with path.open("rb") as binary:
            prefix = binary.read(16 * 1024)
            binary.seek(0, 2)
            size = binary.tell()
            tail_start = max(0, size - TIME_AXIS_TAIL_BYTES)
            # Keep UTF-16 reads code-unit aligned. A leading partial line is
            # discarded below, so seeking into a multibyte record is harmless.
            if tail_start % 2:
                tail_start += 1
            binary.seek(tail_start)
            tail = binary.read()
    except OSError:
        return None

    for encoding in _csv_encodings(prefix):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                head_rows = [
                    tuple(row)
                    for row in islice(
                        csv.reader(handle),
                        HEADER_SEARCH_MAX_ROWS + DATA_LIKENESS_SAMPLE_ROWS,
                    )
                ]
            decoded_tail = tail.decode(encoding)
        except (UnicodeError, OSError):
            continue
        selected = _best_header(head_rows[:HEADER_SEARCH_MAX_ROWS])
        if selected is None or selected[0] != header:
            continue
        header_index = next(
            (
                index for index, row in enumerate(head_rows)
                if tuple(str(value or "") for value in row) == header
            ),
            None,
        )
        if header_index is None:
            continue
        first_rows = head_rows[
            header_index + 1: header_index + 1 + DATA_LIKENESS_SAMPLE_ROWS
        ]
        # When the tail begins mid-record, the first decoded line is partial.
        # Dropping it also removes a duplicated header for small files.
        tail_text = decoded_tail if tail_start == 0 else decoded_tail.split("\n", 1)[-1]
        try:
            tail_rows = [tuple(row) for row in csv.reader(StringIO(tail_text))]
        except csv.Error:
            continue
        for index in time_indices:
            first = tuple(
                value for value in (
                    _is_time_observation(row[index] if index < len(row) else None)
                    for row in first_rows
                ) if value is not None
            )
            tail_values = tuple(
                value for value in (
                    _is_time_observation(row[index] if index < len(row) else None)
                    for row in tail_rows
                ) if value is not None
            )
            last = tail_values[-DATA_LIKENESS_SAMPLE_ROWS:]
            direction = _strict_time_direction(first)
            if (
                direction is None
                or _strict_time_direction(last) != direction
                or len(first) < DATA_LIKENESS_SAMPLE_ROWS
                or len(last) < DATA_LIKENESS_SAMPLE_ROWS
            ):
                continue
            # Compare the sampled clock shape relative to its first value.
            # Split subsystem exports can encode the same logger axis with a
            # different absolute/relative origin; common head/tail deltas are
            # the bounded evidence that matters for candidate discovery.
            origin = first[0]
            return tuple(
                round(value - origin, 3) for value in (*first, *last)
            ) + (float(direction),)
    return None


def _excel_headers(
    source: Path | BytesIO,
) -> tuple[tuple[tuple[str, ...], int, bool, bool], ...] | None:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("openpyxl is required to screen XLSX/XLSM schemas") from exc
    try:
        workbook = load_workbook(source, read_only=True, data_only=True)
    except Exception:
        return None
    try:
        headers: list[tuple[tuple[str, ...], int, bool, bool]] = []
        for worksheet in workbook.worksheets:
            header = _screen_rows(
                row
                for row in worksheet.iter_rows(
                    min_row=1,
                    max_row=HEADER_SEARCH_MAX_ROWS + DATA_LIKENESS_SAMPLE_ROWS,
                    values_only=True,
                )
            )
            if header is not None:
                headers.append(header)
        return tuple(headers)
    finally:
        workbook.close()


def _classify_header(header: Iterable[str]) -> frozenset[str]:
    compact_labels = tuple(
        value.casefold() for value in header if _is_compact_label(value)
    )
    return frozenset(
        category
        for category, terms in SEMANTIC_TERMS.items()
        if any(
            term.casefold() in label
            for term in terms
            for label in compact_labels
        )
        or (
            category in INSTRUMENT_TAG_PATTERNS
            and any(INSTRUMENT_TAG_PATTERNS[category].search(label) for label in compact_labels)
        )
    )


def _files(input_roots: Iterable[Path]) -> Iterable[Path]:
    for root in input_roots:
        if root.is_file():
            if root.suffix.casefold() in SUPPORTED_SUFFIXES:
                yield root
            continue
        if root.is_dir():
            for candidate in root.rglob("*"):
                if candidate.is_file() and candidate.suffix.casefold() in SUPPORTED_SUFFIXES:
                    yield candidate


def _archive_headers(
    path: Path,
) -> tuple[list[tuple[str, tuple[tuple[str, ...], int, bool, bool] | None]], int]:
    """Read eligible archive members in memory without disclosing their names."""

    result: list[tuple[str, tuple[tuple[str, ...], int, bool, bool] | None]] = []
    oversized = 0
    try:
        with ZipFile(path) as archive:
            for member in archive.infolist():
                suffix = Path(member.filename).suffix.casefold()
                if member.is_dir() or suffix not in TABULAR_SUFFIXES:
                    continue
                if member.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                    oversized += 1
                    continue
                try:
                    raw = archive.read(member)
                except (BadZipFile, OSError):
                    result.append((suffix, None))
                    continue
                if suffix == ".csv":
                    result.append((suffix, _csv_header_bytes(raw)))
                    continue
                headers = _excel_headers(BytesIO(raw))
                if headers is None:
                    result.append((suffix, None))
                else:
                    for sheet_header in headers:
                        result.append((suffix, sheet_header))
    except (BadZipFile, OSError):
        return [("zip", None)], oversized
    return result, oversized


def inventory_schema(input_roots: Iterable[Path]) -> dict[str, object]:
    """Return a privacy-bounded header-only source inventory.

    This function is intentionally usable by tests with temporary files.  The
    CLI applies the stricter outside-repository control boundary.
    """

    container_format_counts: Counter[str] = Counter()
    tabular_content_format_counts: Counter[str] = Counter()
    coverage_counts: Counter[str] = Counter()
    tables_scanned = 0
    schema_search_rows_examined = 0
    unreadable_tables = 0
    full_loop_candidates = 0
    co_located_full_loop_candidates = 0
    measurement_like_tables = 0
    rejected_nonmeasurement_candidate_containers = 0
    near_full_loop_candidates = 0
    station_recharge_candidates = 0
    vehicle_fill_candidates = 0
    files_scanned = 0
    archive_members_scanned = 0
    oversized_archive_members_skipped = 0
    flat_time_axis_groups: dict[
        tuple[float, ...], list[frozenset[str]]
    ] = {}

    for path in _files(input_roots):
        files_scanned += 1
        suffix = path.suffix.casefold()
        container_format_counts[suffix.lstrip(".")] += 1
        if suffix == ".zip":
            headers, skipped = _archive_headers(path)
            oversized_archive_members_skipped += skipped
            archive_members_scanned += len(headers)
        elif suffix == ".csv":
            headers = [(suffix, _csv_header_file(path))]
        else:
            headers = [(suffix, header) for header in (_excel_headers(path) or ())]
            if not headers:
                headers = [(suffix, None)]
        container_coverages: list[frozenset[str]] = []
        nonmeasurement_coverages: list[frozenset[str]] = []
        for content_suffix, result in headers:
            tabular_content_format_counts[content_suffix.lstrip(".")] += 1
            if result is None:
                unreadable_tables += 1
                continue
            header, rows_examined, record_shaped, time_series_like = result
            tables_scanned += 1
            schema_search_rows_examined += rows_examined
            coverage = _classify_header(header)
            measurement_like = (
                bool(coverage)
                and record_shaped
                and time_series_like
                and "time" in coverage
            )
            if not measurement_like:
                nonmeasurement_coverages.append(coverage)
                continue
            measurement_like_tables += 1
            container_coverages.append(coverage)
            if suffix == ".csv":
                fingerprint = _csv_time_axis_fingerprint(path, header)
                if fingerprint is not None:
                    flat_time_axis_groups.setdefault(fingerprint, []).append(coverage)
            for category in coverage:
                coverage_counts[category] += 1
            if FULL_LOOP_REQUIRED.issubset(coverage):
                full_loop_candidates += 1
            elif len(FULL_LOOP_REQUIRED - coverage) == 1:
                near_full_loop_candidates += 1
            if STATION_RECHARGE_REQUIRED.issubset(coverage):
                station_recharge_candidates += 1
            if VEHICLE_FILL_REQUIRED.issubset(coverage):
                vehicle_fill_candidates += 1

        # A single workbook or archive can contain synchronized tables divided
        # by subsystem.  Its union is deliberately reported as a *co-located*
        # candidate only: it does not assert common timestamps, matching units,
        # or a usable joined record.  Flat files are kept table-scoped because
        # directory placement alone says nothing about synchronization.
        if suffix in {".xlsx", ".xlsm", ".zip"} and len(container_coverages) > 1:
            combined_coverage = frozenset().union(*container_coverages)
            if FULL_LOOP_REQUIRED.issubset(combined_coverage):
                co_located_full_loop_candidates += 1
        if suffix in {".xlsx", ".xlsm", ".zip"} and len(nonmeasurement_coverages) > 1:
            if FULL_LOOP_REQUIRED.issubset(frozenset().union(*nonmeasurement_coverages)):
                rejected_nonmeasurement_candidate_containers += 1

    synchronized_flat_groups = tuple(
        coverages for coverages in flat_time_axis_groups.values()
        if len(coverages) > 1
    )
    synchronized_flat_full_loop_candidates = 0
    synchronized_flat_station_recharge_candidates = 0
    synchronized_flat_vehicle_fill_candidates = 0
    for coverages in synchronized_flat_groups:
        combined = frozenset().union(*coverages)
        if FULL_LOOP_REQUIRED.issubset(combined):
            synchronized_flat_full_loop_candidates += 1
        if STATION_RECHARGE_REQUIRED.issubset(combined):
            synchronized_flat_station_recharge_candidates += 1
        if VEHICLE_FILL_REQUIRED.issubset(combined):
            synchronized_flat_vehicle_fill_candidates += 1

    return {
        "schema_version": 3,
        "artifact_type": "controlled_hrs_schema_inventory",
        "source_identifiers_published": False,
        "original_headers_published": False,
        "schema_search_max_rows_per_table": HEADER_SEARCH_MAX_ROWS,
        "data_likeness_sample_rows_per_table": DATA_LIKENESS_SAMPLE_ROWS,
        "schema_search_rows_examined": schema_search_rows_examined,
        "sample_data_rows_structurally_inspected_in_memory": True,
        "measurement_rows_persisted": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "source_files_scanned": files_scanned,
        "source_tables_scanned": tables_scanned,
        "measurement_like_tables": measurement_like_tables,
        "unreadable_tables": unreadable_tables,
        "source_container_format_counts": dict(sorted(container_format_counts.items())),
        "tabular_content_format_counts": dict(sorted(tabular_content_format_counts.items())),
        "archive_members_scanned": archive_members_scanned,
        "oversized_archive_members_skipped": oversized_archive_members_skipped,
        "semantic_channel_table_counts": dict(sorted(coverage_counts.items())),
        "flat_time_axis_candidate_summary": {
            "candidate_groups": len(synchronized_flat_groups),
            "tables_in_candidate_groups": sum(map(len, synchronized_flat_groups)),
            "largest_candidate_group_tables": max(
                (len(group) for group in synchronized_flat_groups), default=0
            ),
            "fingerprints_published": False,
            "absolute_time_samples_published": False,
        },
        "candidate_schema_counts": {
            "full_loop_candidate": full_loop_candidates,
            "co_located_full_loop_candidate": co_located_full_loop_candidates,
            "near_full_loop_missing_one_semantic_group": near_full_loop_candidates,
            "station_recharge_candidate": station_recharge_candidates,
            "vehicle_fill_candidate": vehicle_fill_candidates,
            "synchronized_flat_full_loop_candidate": (
                synchronized_flat_full_loop_candidates
            ),
            "synchronized_flat_station_recharge_candidate": (
                synchronized_flat_station_recharge_candidates
            ),
            "synchronized_flat_vehicle_fill_candidate": (
                synchronized_flat_vehicle_fill_candidates
            ),
            "rejected_nonmeasurement_candidate_container": (
                rejected_nonmeasurement_candidate_containers
            ),
        },
        "claim_boundary": (
            "Header-level semantic screening plus in-memory record-shape and "
            "strictly-monotonic-time checks only. "
            "A co-located candidate means only that separate measurement-like tables in "
            "one workbook or archive have complementary labels. A synchronized-flat "
            "candidate means that separate CSV files have matching bounded head/tail "
            "clock samples and complementary labels. Neither candidate class attests "
            "that the complete records can be joined. Candidate counts do not attest "
            "a tag mapping, units, calibration, time synchronization, event "
            "integrity, model accuracy, safety, or full-loop validation."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Produce a de-identified header-only controlled HRS schema inventory"
    )
    parser.add_argument(
        "--input-root", type=Path, action="append", required=True,
        help="controlled file or directory outside the repository; repeatable",
    )
    parser.add_argument(
        "--output", type=Path, required=True,
        help="aggregate JSON destination outside the repository",
    )
    args = parser.parse_args()
    inputs = [_outside_repository(path, label="input root") for path in args.input_root]
    if not all(path.exists() for path in inputs):
        parser.error("every input root must exist")
    output = _outside_repository(args.output, label="output")
    report = inventory_schema(inputs)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
