import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research" / "nrel_h2fills_geometry_prospective_protocol_2026_10_12.json"


def test_geometry_protocol_is_frozen_before_outcomes_and_does_not_change_runtime():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert data["status"] == "PROTOCOL_ONLY_NO_OUTCOMES_OPENED"
    assert data["model_rule"]["geometry_basis"] == "capacity_eos"
    assert data["model_rule"]["effective_volume_multiplier"] == 1.0
    assert data["model_rule"]["parameter_fitting"] is False
    assert data["model_rule"]["runtime_default_change"] is False
    controls = data["pre_access_controls"]
    assert controls["protocol_frozen_before_numeric_outcomes"] is True
    assert controls["case_selection_before_numeric_outcomes"] is True
    assert controls["raw_rows_committed"] is False


def test_geometry_protocol_requires_joint_case_screens_and_keeps_claim_bounded():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    limits = data["frozen_screening_limits"]
    assert limits["pressure_rmse_mpa_max"] == 5.0
    assert limits["temperature_rmse_c_max"] == 10.0
    assert limits["mass_final_abs_error_kg_max"] == 0.5
    assert limits["joint_rule"] == "all three screens pass for every eligible case"
    assert data["promotion_rule"]["requires_new_untouched_trace"] is True
    assert data["promotion_rule"]["diagnostic_failure_does_not_change_runtime"] is True
    assert "vehicle" in data["claim_boundary"]
