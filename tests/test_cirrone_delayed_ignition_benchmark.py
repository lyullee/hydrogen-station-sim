import json
from pathlib import Path

from scripts.validate_cirrone_delayed_ignition_correlation import build_report


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/cirrone_2022_delayed_ignition_benchmark.json"


def test_persisted_cirrone_benchmark_matches_current_implementation():
    persisted = json.loads(RESULT.read_text(encoding="utf-8"))
    assert persisted == build_report()


def test_cirrone_benchmark_pass_is_claim_bounded():
    result = build_report()
    assert result["status"] == "passed"
    assert result["aggregate"]["inverse_case_count"] == 24
    assert result["aggregate"]["inverse_pass_count"] == 24
    assert result["aggregate"]["all_passed"] is True
    assert result["source"]["experimental_case_count_reported"] == 78
    assert result["runtime_contract"]["hybrid_replacement_of_hyram"] is False
    assert result["runtime_contract"]["flow_limited_source_fails_closed"] is True
    assert result["runtime_contract"]["site_safety_distance"] is False
    assert "not independent validation" in result["claim_boundary"]
