"""Inventory controlled HRS data schemas without reading measurements.

This command is deliberately restricted to schema screening.  It helps a data
custodian find candidate station, vehicle-fuelling, and complete-loop events
before a mapping or any model outcome is read.  To support exports with title
rows, it inspects at most the first 40 rows of each table in memory to locate a
probable header.  The report contains only aggregate semantic coverage counts;
it never emits filenames, worksheet names, original headers, source values,
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
from io import BytesIO, StringIO
import json
from pathlib import Path
from typing import Iterable
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_SUFFIXES = frozenset({".csv", ".xlsx", ".xlsm", ".zip"})
TABULAR_SUFFIXES = frozenset({".csv", ".xlsx", ".xlsm"})
HEADER_SEARCH_MAX_ROWS = 40
MAX_ARCHIVE_MEMBER_BYTES = 100 * 1024 * 1024

# These terms are deliberately broad: candidate classification is only a
# request for a custodian review, never automatic tag or unit attribution.
SEMANTIC_TERMS: dict[str, tuple[str, ...]] = {
    "time": (
        "time", "date", "timestamp", "clock", "datetime", "시간", "일시", "시각", "날짜",
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


def _csv_header_bytes(raw: bytes) -> tuple[tuple[str, ...], int] | None:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return _best_header(csv.reader(StringIO(raw.decode(encoding))))
        except UnicodeError:
            continue
    return None


def _excel_headers(source: Path | BytesIO) -> tuple[tuple[tuple[str, ...], int], ...] | None:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("openpyxl is required to screen XLSX/XLSM schemas") from exc
    try:
        workbook = load_workbook(source, read_only=True, data_only=True)
    except Exception:
        return None
    try:
        headers: list[tuple[tuple[str, ...], int]] = []
        for worksheet in workbook.worksheets:
            header = _best_header(
                row
                for row in worksheet.iter_rows(
                    min_row=1,
                    max_row=HEADER_SEARCH_MAX_ROWS,
                    values_only=True,
                )
            )
            if header is not None:
                headers.append(header)
        return tuple(headers)
    finally:
        workbook.close()


def _classify_header(header: Iterable[str]) -> frozenset[str]:
    joined = " ".join(header).casefold()
    return frozenset(
        category
        for category, terms in SEMANTIC_TERMS.items()
        if any(term.casefold() in joined for term in terms)
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


def _archive_headers(path: Path) -> tuple[list[tuple[str, tuple[tuple[str, ...], int] | None]], int]:
    """Read eligible archive members in memory without disclosing their names."""

    result: list[tuple[str, tuple[tuple[str, ...], int] | None]] = []
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
    near_full_loop_candidates = 0
    station_recharge_candidates = 0
    vehicle_fill_candidates = 0
    files_scanned = 0
    archive_members_scanned = 0
    oversized_archive_members_skipped = 0

    for path in _files(input_roots):
        files_scanned += 1
        suffix = path.suffix.casefold()
        container_format_counts[suffix.lstrip(".")] += 1
        if suffix == ".zip":
            headers, skipped = _archive_headers(path)
            oversized_archive_members_skipped += skipped
            archive_members_scanned += len(headers)
        elif suffix == ".csv":
            try:
                headers = [
                    (suffix, _csv_header_bytes(path.read_bytes())),
                ]
            except OSError:
                headers = [(suffix, None)]
        else:
            headers = [(suffix, header) for header in (_excel_headers(path) or ())]
            if not headers:
                headers = [(suffix, None)]
        container_coverages: list[frozenset[str]] = []
        for content_suffix, result in headers:
            tabular_content_format_counts[content_suffix.lstrip(".")] += 1
            if result is None:
                unreadable_tables += 1
                continue
            header, rows_examined = result
            tables_scanned += 1
            schema_search_rows_examined += rows_examined
            coverage = _classify_header(header)
            container_coverages.append(coverage)
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

    return {
        "schema_version": 1,
        "artifact_type": "controlled_hrs_schema_inventory",
        "source_identifiers_published": False,
        "original_headers_published": False,
        "schema_search_max_rows_per_table": HEADER_SEARCH_MAX_ROWS,
        "schema_search_rows_examined": schema_search_rows_examined,
        "measurement_rows_persisted": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "source_files_scanned": files_scanned,
        "source_tables_scanned": tables_scanned,
        "unreadable_tables": unreadable_tables,
        "source_container_format_counts": dict(sorted(container_format_counts.items())),
        "tabular_content_format_counts": dict(sorted(tabular_content_format_counts.items())),
        "archive_members_scanned": archive_members_scanned,
        "oversized_archive_members_skipped": oversized_archive_members_skipped,
        "semantic_channel_table_counts": dict(sorted(coverage_counts.items())),
        "candidate_schema_counts": {
            "full_loop_candidate": full_loop_candidates,
            "co_located_full_loop_candidate": co_located_full_loop_candidates,
            "near_full_loop_missing_one_semantic_group": near_full_loop_candidates,
            "station_recharge_candidate": station_recharge_candidates,
            "vehicle_fill_candidate": vehicle_fill_candidates,
        },
        "claim_boundary": (
            "Header-level semantic screening only. A co-located candidate means only "
            "that separate tables in one workbook or archive have complementary labels; "
            "it does not attest that they can be joined. Candidate counts do not attest "
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
