"""Prepare a private mapping workbench for one controlled HRS workbook.

The output is intentionally outside the repository.  It contains worksheet
names and original header labels so only an authorised custodian can connect
their actual logger channels to the canonical full-loop contract. It reads at
most the first 43 rows of each worksheet, retains no measurement values, and
requires two increasing time-like observations in a labelled logger clock.
Never commit, publish, or attach the generated files to a manuscript.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from io import StringIO
from itertools import islice
import json
from pathlib import Path
from typing import Any

try:  # Supports both ``python scripts/...`` and test-module imports.
    from audit_controlled_data_schema import (
        DATA_LIKENESS_SAMPLE_ROWS,
        HEADER_SEARCH_MAX_ROWS,
        _classify_header,
        _csv_encodings,
        _outside_repository,
        _screen_rows,
    )
    from export_confidential_full_loop_bundle import OUTPUT_COLUMNS, ROOT, _sha256
except ModuleNotFoundError:  # pragma: no cover - import style depends on launcher
    from scripts.audit_controlled_data_schema import (
        DATA_LIKENESS_SAMPLE_ROWS,
        HEADER_SEARCH_MAX_ROWS,
        _classify_header,
        _csv_encodings,
        _outside_repository,
        _screen_rows,
    )
    from scripts.export_confidential_full_loop_bundle import OUTPUT_COLUMNS, ROOT, _sha256


_REQUIRED_METADATA = (
    "initial_conditions",
    "tank_capacity_or_geometry",
    "protocol_mode_or_pressure_ramp",
    "units_and_sampling_interval",
    "source_cascade_state",
    "compressor_state",
    "precooler_state",
    "stop_abort_fault_markers",
    "quality_and_calibration_metadata",
    "reuse_terms",
    "source_identity",
    "custodian_or_archive",
    "acquired_at_utc",
    "license_or_reuse_reference",
)


def _header_row(rows: tuple[tuple[object, ...], ...], labels: tuple[str, ...]) -> int:
    for number, row in enumerate(rows[:HEADER_SEARCH_MAX_ROWS], start=1):
        if tuple(str(value or "") for value in row) == labels:
            return number
    raise RuntimeError("selected header cannot be located")


def _time_columns(labels: tuple[str, ...]) -> list[str]:
    return [
        label for label in labels
        if "time" in _classify_header((label,))
    ]


def _source_entry(
    rows: tuple[tuple[object, ...], ...],
    *,
    source_file: str | None,
    worksheet: str | None,
) -> dict[str, Any] | None:
    screen = _screen_rows(rows)
    if screen is None:
        return None
    labels, _, record_shaped, time_series_like = screen
    semantic_channels = _classify_header(labels)
    if not (record_shaped and time_series_like and "time" in semantic_channels):
        return None
    entry: dict[str, Any] = {
        "header_row": _header_row(rows, labels),
        "time_column_candidates": _time_columns(labels),
        "original_headers": list(labels),
        "semantic_channels": sorted(semantic_channels),
    }
    if source_file is not None:
        entry["file"] = source_file
    if worksheet is not None:
        entry["worksheet"] = worksheet
    return entry


def _csv_entry(path: Path, *, source_file: str | None) -> dict[str, Any] | None:
    raw = path.read_bytes()
    for encoding in _csv_encodings(raw):
        try:
            rows = tuple(
                tuple(row)
                for row in islice(
                    csv.reader(StringIO(raw.decode(encoding))),
                    HEADER_SEARCH_MAX_ROWS + DATA_LIKENESS_SAMPLE_ROWS,
                )
            )
        except UnicodeError:
            continue
        return _source_entry(rows, source_file=source_file, worksheet=None)
    return None


def _excel_entries(path: Path, *, source_file: str | None) -> list[dict[str, Any]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("openpyxl is required for controlled Excel intake") from exc

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sources: list[dict[str, Any]] = []
        for worksheet in workbook.worksheets:
            rows = tuple(
                worksheet.iter_rows(
                    min_row=1,
                    max_row=HEADER_SEARCH_MAX_ROWS + DATA_LIKENESS_SAMPLE_ROWS,
                    values_only=True,
                )
            )
            entry = _source_entry(
                rows, source_file=source_file, worksheet=worksheet.title,
            )
            if entry is not None:
                sources.append(entry)
        return sources
    finally:
        workbook.close()


def _workbench(input_data: Path) -> dict[str, Any]:
    if input_data.is_file():
        candidates = [input_data]
        input_root = None
    else:
        candidates = sorted(
            path for path in input_data.rglob("*")
            if path.is_file() and path.suffix.casefold() in {".csv", ".xlsx", ".xlsm"}
        )
        input_root = input_data.resolve()

    sources: list[dict[str, Any]] = []
    for path in candidates:
        source_file = (
            path.resolve().relative_to(input_root).as_posix()
            if input_root is not None else None
        )
        if path.suffix.casefold() == ".csv":
            entry = _csv_entry(path, source_file=source_file)
            if entry is not None:
                sources.append(entry)
        else:
            sources.extend(_excel_entries(path, source_file=source_file))

    digest = hashlib.sha256()
    for path in candidates:
        digest.update(_sha256(path).encode("ascii"))

    return {
        "schema_version": 1,
        "artifact_type": "controlled_private_multisource_mapping_workbench",
        "publication_prohibited": True,
        "repository_storage_prohibited": True,
        "source_input_sha256": digest.hexdigest(),
        "input_kind": "directory" if input_data.is_dir() else input_data.suffix.casefold().lstrip("."),
        "sample_data_rows_structurally_inspected_in_memory": True,
        "measurement_values_persisted": False,
        "source_count": len(sources),
        "sources": sources,
        "claim_boundary": (
            "This private workbench is a custodian mapping aid only. It does not "
            "attest units, synchronization, state semantics, a validation event, "
            "model accuracy, safety, or publication readiness."
        ),
    }


def _mapping_template(workbench: dict[str, Any]) -> dict[str, Any]:
    def source_template(source: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "header_row": source["header_row"],
            "event_group_token": "<custodian-approved opaque event-group token shared by this one physical event>",
            "time_column": "<select one time_column_candidate>",
            "time_format": "<optional strptime format or null>",
            "column_map": {
                "<canonical_channel>": "<select an original_header>",
            },
        }
        if source.get("file") is not None:
            result["file"] = source["file"]
        if source.get("worksheet") is not None:
            result["worksheet"] = source["worksheet"]
        return result

    return {
        "schema_version": 1,
        "sources": [source_template(source) for source in workbench["sources"]],
        "alignment": {
            "method": "nearest_observation",
            "anchor_source": 0,
            "maximum_offset_s": "<custodian-approved tolerance>",
        },
        "mapping_instructions": (
            "Replace every placeholder. Each canonical output field except time_s must "
            "be assigned exactly once across sources. Do not infer or interpolate a "
            "missing source channel."
        ),
        "canonical_fields_required": list(OUTPUT_COLUMNS),
    }


def _attestation_template() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "authorised_controlled_evaluation": False,
        "outcomes_accessed_before_protocol_freeze": "<true or false>",
        "units": {
            "vehicle_pressure_mpa_abs": "MPa_abs",
            "temperature_degC": "degC",
            "mass_flow_g_s": "g/s",
            "station_pressure_mpa_abs": "MPa_abs",
            "delivered_gas_temperature_degC": "degC",
            "cascade_source_pressure_mpa_abs": "MPa_abs",
        },
        "state_semantics": {
            field: "<custodian-approved meaning and valid states>"
            for field in OUTPUT_COLUMNS[7:]
        },
        "temperature_observation": {
            "vehicle_temperature_degC": {
                "observation_operator": "<gas_temperature | liner_temperature | shell_temperature | sensor_weighted_tank_temperature>",
                "sensor_location_verified": False,
                "measurement_method": "<custodian-approved sensor position and averaging method>",
                "calibration_or_traceability": "<custodian-approved calibration or traceability declaration>",
            },
            "delivered_gas_temperature_degC": {
                "observation_operator": "delivered_gas_temperature",
                "sensor_location_verified": False,
                "measurement_method": "<custodian-approved sensor position and averaging method>",
                "calibration_or_traceability": "<custodian-approved calibration or traceability declaration>",
            },
        },
        "metadata": {
            field: "<custodian-approved declaration>" for field in _REQUIRED_METADATA
        },
        "source_synchronization": {
            "common_time_basis_confirmed": False,
            "same_physical_event_confirmed": False,
            "alignment_method": "nearest_observation",
        },
        "attestation_instructions": (
            "Set authorization, common_time_basis_confirmed, and "
            "same_physical_event_confirmed true only after a custodian reviews the "
            "event selection, units, thermal sensor meaning and calibration status, state meanings, source "
            "clocks, and confirms that every selected source belongs to one physical event."
        ),
    }


def prepare_workbench(input_data: Path, output_directory: Path) -> dict[str, Any]:
    """Write private mapping and attestation templates outside the repository."""

    input_data = _outside_repository(input_data, label="input data")
    output_directory = _outside_repository(output_directory, label="output directory")
    if not input_data.is_dir() and input_data.suffix.casefold() not in {".csv", ".xlsx", ".xlsm"}:
        raise ValueError("controlled mapping workbench requires a CSV/XLSX/XLSM file or directory")
    if output_directory.exists() and any(output_directory.iterdir()):
        raise ValueError("output directory must be empty")

    workbench = _workbench(input_data)
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "private_source_catalog.json").write_text(
        json.dumps(workbench, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_directory / "event-mapping.template.json").write_text(
        json.dumps(_mapping_template(workbench), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_directory / "event-attestation.template.json").write_text(
        json.dumps(_attestation_template(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    receipt = {
        "schema_version": 1,
        "artifact_type": "controlled_private_multisource_mapping_workbench_receipt",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "publication_prohibited": True,
        "repository_storage_prohibited": True,
        "measurement_values_persisted": False,
        "input_kind": workbench["input_kind"],
        "source_count": workbench["source_count"],
        "source_input_sha256": workbench["source_input_sha256"],
        "output_file_count": 3,
        "claim_boundary": workbench["claim_boundary"],
    }
    (output_directory / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="controlled CSV/XLSX/XLSM file or directory")
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    receipt = prepare_workbench(args.input, args.output_directory)
    print(json.dumps({
        "source_count": receipt["source_count"],
        "output_file_count": receipt["output_file_count"],
        "output_written": True,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
