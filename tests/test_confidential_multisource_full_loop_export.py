from __future__ import annotations

import json
import sys
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from export_confidential_full_loop_bundle import OUTPUT_COLUMNS  # noqa: E402
from export_confidential_multisource_full_loop_bundle import (  # noqa: E402
    export_bundle,
    preflight_bundle,
)


def _attestation() -> dict[str, object]:
    return {
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
        "state_semantics": {
            name: "private controlled state semantics" for name in OUTPUT_COLUMNS[7:]
        },
        "metadata": {
            name: "declared in controlled record"
            for name in (
                "initial_conditions", "tank_capacity_or_geometry", "protocol_mode_or_pressure_ramp",
                "units_and_sampling_interval", "source_cascade_state", "compressor_state",
                "precooler_state", "stop_abort_fault_markers", "quality_and_calibration_metadata",
                "reuse_terms", "source_identity", "custodian_or_archive", "acquired_at_utc",
                "license_or_reuse_reference",
            )
        },
        "source_synchronization": {
            "common_time_basis_confirmed": True,
            "alignment_method": "nearest_observation",
        },
    }


def _write_controlled_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "private_station_event.xlsx"
    workbook = Workbook()
    vehicle = workbook.active
    vehicle.title = "private vehicle"
    vehicle.append(["secret vehicle clock", "secret vehicle pressure", "secret vehicle temperature", "secret mass flow"])
    station = workbook.create_sheet("private station")
    station.append([
        "secret station clock", "secret station pressure", "secret delivery temperature",
        "secret cascade pressure", *[f"secret {name}" for name in OUTPUT_COLUMNS[7:]],
    ])
    for index in range(30):
        vehicle.append([index * 2.0, 10 + index, 20 + index / 10, 2.0])
        station.append([
            index * 2.0 + 0.25, 50 - index / 10, -30, 70 - index / 10,
            "mid", "running", "running", "clear", "closed", "clear", "ready",
        ])
    workbook.save(source)
    mapping = {
        "schema_version": 1,
        "sources": [
            {
                "worksheet": "private vehicle", "header_row": 1,
                "time_column": "secret vehicle clock",
                "column_map": {
                    "vehicle_pressure_mpa_abs": "secret vehicle pressure",
                    "temperature_degC": "secret vehicle temperature",
                    "mass_flow_g_s": "secret mass flow",
                },
            },
            {
                "worksheet": "private station", "header_row": 1,
                "time_column": "secret station clock",
                "column_map": {
                    "station_pressure_mpa_abs": "secret station pressure",
                    "delivered_gas_temperature_degC": "secret delivery temperature",
                    "cascade_source_pressure_mpa_abs": "secret cascade pressure",
                    **{name: f"secret {name}" for name in OUTPUT_COLUMNS[7:]},
                },
            },
        ],
        "alignment": {"method": "nearest_observation", "anchor_source": 0, "maximum_offset_s": 0.5},
    }
    mapping_path = tmp_path / "private_mapping.json"
    mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
    attestation_path = tmp_path / "private_attestation.json"
    attestation_path.write_text(json.dumps(_attestation()), encoding="utf-8")
    return source, mapping_path, attestation_path


def test_multisource_preflight_and_export_deidentify_private_workbook(tmp_path: Path):
    source, mapping, attestation = _write_controlled_inputs(tmp_path)
    protocol = ROOT / "research" / "external_hrs_intake_protocol.json"

    preflight = preflight_bundle(source, mapping, attestation, protocol)
    rendered_preflight = json.dumps(preflight)
    assert preflight["ready_for_controlled_export"] is True
    assert preflight["source_rows_read"] is False
    assert "private vehicle" not in rendered_preflight
    assert "secret vehicle clock" not in rendered_preflight

    output = tmp_path / "controlled-export"
    receipt = export_bundle(source, mapping, attestation, output, protocol)
    rendered_receipt = json.dumps(receipt)
    assert receipt["full_loop_trace_ready"] is True
    assert receipt["source_table_count"] == 2
    assert "private station" not in rendered_receipt
    assert "secret station pressure" not in rendered_receipt
    assert (output / "full_loop_event.csv").is_file()


def test_multisource_export_rejects_unattested_time_alignment(tmp_path: Path):
    source, mapping, attestation = _write_controlled_inputs(tmp_path)
    payload = json.loads(attestation.read_text(encoding="utf-8"))
    payload["source_synchronization"]["common_time_basis_confirmed"] = False
    attestation.write_text(json.dumps(payload), encoding="utf-8")
    protocol = ROOT / "research" / "external_hrs_intake_protocol.json"

    try:
        preflight_bundle(source, mapping, attestation, protocol)
    except ValueError as exc:
        assert "common time basis" in str(exc)
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("unattested source alignment was accepted")
