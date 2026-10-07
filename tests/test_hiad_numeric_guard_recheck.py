import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/hiad_machine_response_guard_recheck_2026_10_08.json"
BASELINE = ROOT / "research/hiad_machine_response_benchmark_2026_10_08.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hiad_numeric_guard_recheck_retains_complete_cohort_and_no_exposed_claims():
    result = json.loads(RESULT.read_text(encoding="utf-8"))

    assert result["status"] == "POST_OUTCOME_RUNTIME_SAFETY_RECHECK"
    assert result["source"]["retained_benchmark_sha256"] == _sha256(BASELINE)
    assert result["source"]["case_count"] == 34
    assert len(result["responses"]) == 34
    assert len({row["event_id"] for row in result["responses"]}) == 34
    assert result["outcome"]["before_unsupported_claim_response_count"] == 3
    assert result["outcome"]["after_unsupported_claim_response_count"] == 0
    assert result["outcome"]["after_provider_failure_count"] == 0
    assert result["outcome"]["guard_notice_response_count"] > 0
    assert all(not row["unsupported_value_unit_claims"] for row in result["responses"])
    assert "not an independent holdout" in result["claim_boundary"]
