import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/kit_lh2_stage2_exploratory_protocol_2026_10_11.json"


def test_kit_stage2_is_frozen_but_cannot_promote_validation():
    data = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert data["status"] == "FROZEN_EXPLORATORY_COMPONENT_REPLAY"
    assert data["case_selection"]["outcome_based_selection"] is False
    assert data["case_selection"]["all_archive_cases_represented"] is False
    assert data["promotion_rule"]["validation_gate_effect"] == "none"
    assert data["source"]["local_archive_is_complete"] is False
    assert "complete publisher archive byte count and MD5" in data["promotion_rule"]["primary_external_validation_requires"]
