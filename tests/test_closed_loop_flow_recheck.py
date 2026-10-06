import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/closed_loop_flow_multiplier_recheck_2026_10_06.json"
PRIOR = ROOT / "research/closed_loop_flow_calibration_v2.json"


def test_flow_multiplier_recheck_is_development_only_and_matches_retained_selection():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "h2protocol_closed_loop_flow_multiplier_recheck"
    assert record["evidence_role"] == "development_diagnostic_only"
    assert record["confirmatory_cases_evaluated"] is False
    assert record["production_model_parameter_changed"] is False
    assert record["selected_dispenser_flow_area_multiplier"] == 2.0
    assert record["prior_artifact_sha256"] == hashlib.sha256(PRIOR.read_bytes()).hexdigest()
    assert len(record["development_lab_test_numbers"]) == 8
    assert len(record["confirmatory_lab_test_numbers"]) == 11
