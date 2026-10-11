import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/grune_2011_conference_source_recheck_2026_10_11.json"


def test_grune_conference_source_keeps_text_anchor_out_of_holdout():
    result = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert result["status"] == "conference_source_context_recheck_completed"
    assert result["source"]["url"].endswith("ichs2011/papers/133.pdf")
    assert result["reported_anchors"]["half_pressure_time_ms"] == 64.0
    assert result["access_result"]["machine_readable_raw_pressure_trace_found"] is False
    assert result["eligibility"]["numeric_holdout_added"] is False
    assert result["eligibility"]["grune_2014_pressure_decay_gate_eligible"] is False
    assert result["eligibility"]["model_promotion"] is False
