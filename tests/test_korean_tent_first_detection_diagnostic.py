from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from diagnose_korean_tent_first_detection import evaluate, rank_nearest  # noqa: E402


def test_nearest_source_baseline_is_deterministic() -> None:
    assert rank_nearest("G1") == ["S3", "S2", "S4", "S1", "S5"]
    assert rank_nearest("G2")[0] == "S5"


def test_published_diagnostic_keeps_runtime_boundary() -> None:
    result = evaluate()
    assert result["metrics"]["case_count"] == 10
    assert result["metrics"]["nearest_source_top1_accuracy"] == 0.7
    assert result["eligibility_decision"]["independent_holdout"] is False
    assert result["eligibility_decision"]["runtime_parameter_updated"] is False
    assert result["eligibility_decision"]["validation_gate_changed"] is False
    assert result["eligibility_decision"]["promotion_prohibited"] is True
