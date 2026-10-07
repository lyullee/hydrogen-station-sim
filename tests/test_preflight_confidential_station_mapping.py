from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from preflight_confidential_station_mapping import preflight  # noqa: E402


def _mapping() -> dict[str, object]:
    return {
        "schema_version": 1,
        "time_column": "private_timestamp",
        "time_column_index": None,
        "pressure_columns": [["station_pressure", "private_pressure"]],
        "temperature_columns": [["station_temperature", "private_temperature"]],
        "flow_column": "private_flow",
        "state_columns": [["compressor_state", "private_state"]],
        "lifecycle_columns": [],
        "temperature_boundary_role": None,
        "authorized_boundary_roles": ["station_pressure"],
        "pressure_scale_pa_per_unit": 1.0e6,
        "temperature_scale_k_per_unit": 1.0,
        "temperature_offset_k": 273.15,
        "flow_scale_kg_s_per_unit": 0.001,
        "lifecycle_scale_per_unit": 1.0,
        "time_format": "%Y %m %d %H:%M:%S",
        "time_is_absolute": False,
        "encoding": "cp949",
    }


def _attestation() -> dict[str, object]:
    return {
        "schema_version": 1,
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "tag_names_published": False,
        "source_paths_published": False,
        "timebase_semantics_attested": True,
        "pressure_role_and_unit_semantics_attested": True,
        "temperature_role_and_unit_semantics_attested": False,
        "flow_role_and_unit_semantics_attested": False,
        "state_semantics_attested": False,
        "lifecycle_semantics_attested": False,
        "calibration_metadata_attested": True,
        "authorized_boundary_roles": ["station_pressure"],
    }


def test_preflight_checks_headers_without_exposing_private_channel_names(tmp_path: Path):
    source = tmp_path / "secret-logger.csv"
    source.write_text(
        "private_timestamp,private_pressure,private_temperature,private_flow,private_state\n"
        "2026 01 01 00:00:00,40,20,1,OFF\n",
        encoding="cp949",
    )
    mapping = tmp_path / "secret-mapping.json"
    mapping.write_text(json.dumps(_mapping()), encoding="utf-8")
    attestation = tmp_path / "secret-attestation.json"
    attestation.write_text(json.dumps(_attestation()), encoding="utf-8")

    report = preflight(source, mapping, attestation_path=attestation)
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["raw_rows_persisted"] is False
    assert report["trace_file_count"] == 1
    assert report["header_check_attempted"] is True
    assert report["header_compatible_file_count"] == 1
    assert report["preflight_pass"] is True
    assert report["eligibility"]["station_boundary_calibration_supported"] is True
    assert report["eligibility"]["full_loop_holdout_eligible"] is False
    assert "private_pressure" not in rendered
    assert "secret-logger.csv" not in rendered
    assert "2026 01 01" not in rendered


def test_preflight_rejects_unresolved_template_without_reading_rows(tmp_path: Path):
    source = tmp_path / "private.csv"
    source.write_text("time,pressure\n0,40\n", encoding="utf-8")
    mapping = _mapping()
    mapping["time_column"] = "<select one original header with the logger clock>"
    mapping["pressure_scale_pa_per_unit"] = "<custodian-confirmed Pa per source pressure unit>"
    mapping["flow_column"] = "<optional owner-attested mass-flow header>"
    mapping_path = tmp_path / "template.json"
    mapping_path.write_text(json.dumps(mapping), encoding="utf-8")

    report = preflight(source, mapping_path)

    assert report["preflight_pass"] is False
    assert report["header_check_attempted"] is False
    assert "time_column" in report["template_placeholder_fields"]
    assert "pressure_scale_pa_per_unit" in report["template_placeholder_fields"]
    assert report["attestation"]["provided"] is False
    assert report["eligibility"]["station_boundary_calibration_supported"] is False
