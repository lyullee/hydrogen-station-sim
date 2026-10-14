import json
from pathlib import Path


ARTIFACT = Path(__file__).parents[1] / "research" / "physics_core_regression_recheck_2026_10_14.json"


def test_physics_core_recheck_is_a_passing_bounded_run():
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    result = payload["result"]
    interpretation = payload["interpretation"]

    assert result["passed"] == 31
    assert result["failed"] == 0
    assert result["skipped"] == 0
    assert interpretation["code_consistency"] == "PASS"
    assert interpretation["independent_validation_gate_changed"] is False
    assert interpretation["runtime_parameter_changed"] is False
    assert "not an independent experimental validation result" in interpretation["claim_boundary"]
