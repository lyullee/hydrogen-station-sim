import csv
from datetime import datetime, timedelta
import json
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from export_confidential_full_loop_bundle import (  # noqa: E402
    OUTPUT_COLUMNS,
    export_bundle,
    preflight_bundle,
)


def _write_inputs(tmp_path: Path):
    source = tmp_path / "owner_log.csv"
    source_columns = ["wall_clock"] + [f"raw_{name}" for name in OUTPUT_COLUMNS[1:]]
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=source_columns)
        writer.writeheader()
        for index in range(20):
            writer.writerow({
                "wall_clock": f"2026-01-01T00:00:{index:02d}+00:00",
                "raw_vehicle_pressure_mpa_abs": str(5 + index),
                "raw_temperature_degC": "25",
                "raw_mass_flow_g_s": "10",
                "raw_station_pressure_mpa_abs": str(90 - index / 10),
                "raw_delivered_gas_temperature_degC": "-35",
                "raw_cascade_source_pressure_mpa_abs": "95",
                "raw_cascade_selected_bank": "high",
                "raw_compressor_state": "ready",
                "raw_precooler_state": "ready",
                "raw_leak_check_state": "passed",
                "raw_vent_state": "closed",
                "raw_fault_state": "none",
                "raw_esd_state": "armed",
            })
    mapping = {
        "schema_version": 1,
        "time_format": "%Y-%m-%dT%H:%M:%S%z",
        "column_map": {"time_s": "wall_clock", **{name: f"raw_{name}" for name in OUTPUT_COLUMNS[1:]}},
    }
    attestation = {
        "schema_version": 1,
        "authorised_controlled_evaluation": True,
        "outcomes_accessed_before_protocol_freeze": False,
        "units": {
            "vehicle_pressure_mpa_abs": "MPa_abs",
            "temperature_degC": "degC",
            "mass_flow_g_s": "g/s",
            "station_pressure_mpa_abs": "MPa_abs",
            "delivered_gas_temperature_degC": "degC",
            "cascade_source_pressure_mpa_abs": "MPa_abs",
        },
        "state_semantics": {name: "custodian-attested" for name in OUTPUT_COLUMNS if name in {
            "cascade_selected_bank", "compressor_state", "precooler_state", "leak_check_state",
            "vent_state", "fault_state", "esd_state",
        }},
        "metadata": {
            "initial_conditions": "declared",
            "tank_capacity_or_geometry": "declared",
            "protocol_mode_or_pressure_ramp": "declared",
            "units_and_sampling_interval": "declared",
            "source_cascade_state": "declared",
            "compressor_state": "declared",
            "precooler_state": "declared",
            "stop_abort_fault_markers": "declared",
            "quality_and_calibration_metadata": "declared",
            "reuse_terms": "controlled research use permitted",
            "source_identity": "owner-controlled archive",
            "custodian_or_archive": "authorised custodian",
            "acquired_at_utc": "declared",
            "license_or_reuse_reference": "controlled-access agreement",
        },
    }
    mapping_path = tmp_path / "private_mapping.json"
    attestation_path = tmp_path / "private_attestation.json"
    mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
    attestation_path.write_text(json.dumps(attestation), encoding="utf-8")
    return source, mapping_path, attestation_path


def _write_xlsx_inputs(tmp_path: Path):
    """Create a private-style workbook entirely inside the test temp path."""

    source, mapping_path, attestation_path = _write_inputs(tmp_path)
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping["worksheet"] = "approved_export"
    mapping_path.write_text(json.dumps(mapping), encoding="utf-8")

    workbook_path = tmp_path / "owner_log.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = mapping["worksheet"]
    source_columns = ["wall_clock"] + [f"raw_{name}" for name in OUTPUT_COLUMNS[1:]]
    worksheet.append(source_columns)
    start = datetime(2026, 1, 1)
    for index in range(20):
        worksheet.append([
            start + timedelta(seconds=index),
            5 + index,
            25,
            10,
            90 - index / 10,
            -35,
            95,
            "high",
            "ready",
            "ready",
            "passed",
            "closed",
            "none",
            "armed",
        ])
    workbook.save(workbook_path)
    return workbook_path, mapping_path, attestation_path


def test_export_removes_source_headers_and_absolute_time(tmp_path):
    source, mapping, attestation = _write_inputs(tmp_path)
    output = tmp_path / "controlled_bundle"
    receipt = export_bundle(
        source, mapping, attestation, output,
        ROOT / "research/external_hrs_intake_protocol.json",
    )
    assert receipt["full_loop_trace_ready"] is True
    assert receipt["rows"] == 20
    exported = (output / "full_loop_event.csv").read_text(encoding="utf-8")
    assert "raw_vehicle_pressure" not in exported
    assert "wall_clock" not in exported
    assert "2026-01-01" not in exported
    assert exported.splitlines()[0].split(",") == list(OUTPUT_COLUMNS)
    assert exported.splitlines()[1].split(",")[0] == "0"
    declaration = json.loads((output / "declaration.json").read_text(encoding="utf-8"))
    assert declaration["source_identifiers_published"] is False
    assert declaration["absolute_timestamps_published"] is False


def test_export_rejects_a_repository_output_path(tmp_path):
    source, mapping, attestation = _write_inputs(tmp_path)
    with pytest.raises(ValueError, match="outside the repository"):
        export_bundle(
            source, mapping, attestation, ROOT / "tmp" / "should-not-contain-private-trace",
            ROOT / "research/external_hrs_intake_protocol.json",
        )


def test_export_rejects_a_nonempty_controlled_output_directory(tmp_path):
    source, mapping, attestation = _write_inputs(tmp_path)
    output = tmp_path / "controlled_bundle"
    output.mkdir()
    (output / "unrelated.txt").write_text("do not mix cases", encoding="utf-8")
    with pytest.raises(ValueError, match="must be empty"):
        export_bundle(
            source, mapping, attestation, output,
            ROOT / "research/external_hrs_intake_protocol.json",
        )


def test_export_requires_attested_state_semantics(tmp_path):
    source, mapping, attestation = _write_inputs(tmp_path)
    payload = json.loads(attestation.read_text(encoding="utf-8"))
    payload["state_semantics"].pop("esd_state")
    attestation.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="state column"):
        export_bundle(
            source, mapping, attestation, tmp_path / "controlled_bundle",
            ROOT / "research/external_hrs_intake_protocol.json",
        )


def test_excel_preflight_does_not_read_rows_or_disclose_private_headers(tmp_path):
    source, mapping, attestation = _write_xlsx_inputs(tmp_path)
    report = preflight_bundle(
        source, mapping, attestation,
        ROOT / "research/external_hrs_intake_protocol.json",
    )
    serialized = json.dumps(report)
    assert report["ready_for_controlled_export"] is True
    assert report["source_format"] == "xlsx"
    assert report["worksheet_mapping_required"] is True
    assert report["source_rows_read"] is False
    assert report["source_headers_exposed"] is False
    assert "raw_vehicle_pressure" not in serialized
    assert "wall_clock" not in serialized


def test_preflight_reports_only_canonical_missing_channels(tmp_path):
    source, mapping, attestation = _write_xlsx_inputs(tmp_path)
    payload = json.loads(mapping.read_text(encoding="utf-8"))
    payload["column_map"]["station_pressure_mpa_abs"] = "secret_station_tag"
    mapping.write_text(json.dumps(payload), encoding="utf-8")
    report = preflight_bundle(
        source, mapping, attestation,
        ROOT / "research/external_hrs_intake_protocol.json",
    )
    serialized = json.dumps(report)
    assert report["ready_for_controlled_export"] is False
    assert report["missing_canonical_channels"] == ["station_pressure_mpa_abs"]
    assert "secret_station_tag" not in serialized


def test_excel_export_is_deidentified_and_preserves_relative_time_only(tmp_path):
    source, mapping, attestation = _write_xlsx_inputs(tmp_path)
    output = tmp_path / "controlled_xlsx_bundle"
    receipt = export_bundle(
        source, mapping, attestation, output,
        ROOT / "research/external_hrs_intake_protocol.json",
    )
    exported = (output / "full_loop_event.csv").read_text(encoding="utf-8")
    assert receipt["input_format"] == "xlsx"
    assert receipt["output_file_count"] == 4
    assert "raw_vehicle_pressure" not in exported
    assert "wall_clock" not in exported
    assert "2026-01-01" not in exported
    assert exported.splitlines()[1].split(",")[0] == "0"
