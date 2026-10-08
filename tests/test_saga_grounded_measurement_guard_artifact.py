import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/saga_grounded_measurement_guard_evaluation_2026_10_08.json"


def test_grounded_measurement_guard_artifact_is_reproducible_and_bounded():
    result = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert result["artifact_type"] == "post_access_development_regression"
    assert result["fix"]["saga_commit"] == "54baa715227b5618861afb80eecdc20605d1842d"
    assert result["after_fix"]["source"]["digital_twin"]["dirty"] is False
    assert result["after_fix"]["source"]["saga_py"]["dirty"] is False
    assert result["after_fix"]["errors"] == []
    assert result["comparison"]["grounded_number_coverage_mean_before"] == 0.0
    assert result["comparison"]["grounded_number_coverage_mean_after"] >= 0.75
    assert result["comparison"]["guard_notice_runs_before"] >= 1
    assert result["comparison"]["guard_notice_runs_after"] == 0
    assert result["comparison"]["unsupported_number_runs_after"] == 0
    assert "not independent SAGA effectiveness" in result["claim_boundary"]

    serialized = ARTIFACT.read_text(encoding="utf-8")
    assert "C:\\Users\\" not in serialized
    assert "gsk_" not in serialized
    assert "sk-" not in serialized
