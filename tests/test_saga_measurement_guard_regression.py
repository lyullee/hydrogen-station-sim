import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/saga_measurement_guard_regression_2026_10_08.json"


def test_saga_measurement_guard_regression_preserves_grounded_equivalents():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "PASS"
    assert result["runtime"]["provider_calls"] == 0
    assert len(result["runtime"]["saga_commit"]) == 40
    assert len(result["runtime"]["api_sha256"]) == 64
    assert result["aggregate"] == {
        "case_count": 5,
        "pass_count": 5,
        "equivalent_grounded_case_count": 4,
        "unsupported_rejection_case_count": 1,
    }
    assert all(case["passed"] for case in result["cases"])
    assert "does not establish" in result["claim_boundary"]
