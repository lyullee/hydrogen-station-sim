from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_geometry_resolved_protocol_is_pre_access_and_fails_closed() -> None:
    path = ROOT / "research/dickens_typeiii_geometry_resolved_prospective_protocol_2026_10_10.json"
    record = json.loads(path.read_text(encoding="utf-8"))

    assert record["status"] == "pre_access_request"
    assert record["outcome_access_status"] == "awaiting_new_custodian_trace"
    declarations = record["pre_access_declarations"]
    assert declarations["numerical_outcomes_seen_for_this_protocol"] is False
    assert declarations["model_parameters_fitted_to_outcome"] is False
    assert declarations["same_archive_reuse_for_confirmatory_claim"] is False
    assert declarations["time_resolved_inlet_temperature_required"] is True

    geometry = record["geometry_to_freeze_before_outcome_access"]
    assert geometry["inlet_pipe_internal_diameter_m"]["value"] == 0.005
    assert geometry["inlet_pipe_extension_m"]["value"] == 0.082
    assert geometry["tank_internal_length_m"]["value"] is None
    assert geometry["tank_internal_length_m"]["status"] == "custodian_resolution_required"

    screens = record["primary_screens"]
    assert screens["pressure_rmse_mpa_max"] == 2.0
    assert screens["gas_temperature_rmse_k_max"] == 10.0
    assert screens["gas_temperature_peak_absolute_error_k_max"] == 15.0
    assert "all failures" in " ".join(record["analysis_sequence"])

