import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/sandia_warehouse_spatial_diagnostic_2026_10_08.json"


def _result():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_actual_hydrogen_spatial_diagnostic_improves_fixed_rank_order():
    result = _result()
    assert result["status"] == "EXTERNAL_POST_ACCESS_DIAGNOSTIC_NOT_VALIDATION"
    assert result["source"]["test_gas"] == "hydrogen"
    assert len(result["cases"]) == 6
    assert result["baseline_geometry_only"]["spearman_rho"] == 0.6
    assert result["orientation_candidate"]["spearman_rho"] > 0.94
    assert result["orientation_candidate"]["top3_recall"] == 1.0
    assert result["orientation_candidate"]["highest_ranked_sensor_matches"] is True


def test_actual_hydrogen_diagnostic_does_not_change_runtime_or_validation_gate():
    result = _result()
    lock = result["model_lock"]
    decision = result["decision"]
    assert lock["candidate_frozen_before_numeric_outcome_access"] is True
    assert lock["diagnostic_protocol_frozen_before_outcome_access"] is False
    assert lock["parameters_fitted"] is False
    assert lock["runtime_application"] is False
    assert decision["independent_validation_pass"] is False
    assert decision["h2safe_gate_changed"] is False
    assert decision["runtime_candidate_enabled"] is False
    assert "not a prospective validation" in result["claim_boundary"]
