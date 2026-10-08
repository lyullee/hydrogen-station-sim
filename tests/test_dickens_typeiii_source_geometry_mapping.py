from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/dickens_typeiii_source_geometry_mapping_2026_10_09.json"


def test_source_geometry_mapping_is_explicit_and_source_confirmed() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    geometry = record["geometry_mapping"]
    assert geometry["inlet_pipe_internal_diameter_m"]["source_value"] == 0.005
    assert geometry["inlet_pipe_extension_m"]["source_value"] == 0.082
    assert geometry["inlet_pipe_internal_diameter_m"]["status"] == "source_confirmed_archived_case_missing"


def test_geometry_mismatch_and_missing_boundary_remain_gated() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["geometry_mapping"]["tank_internal_length_m"]["status"] == "mismatch_requires_resolution"
    boundary = record["boundary_mapping"]
    assert boundary["inlet_temperature_measured_in_source"] is True
    assert boundary["time_resolved_inlet_temperature_available_in_archived_case"] is False
    interpretation = record["diagnostic_interpretation"]
    assert interpretation["frozen_validation_result_changed"] is False
    assert interpretation["runtime_parameter_updated"] is False
    assert interpretation["validation_gate_effect"] == "none"
