import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hiad_handoff_is_ready_but_does_not_claim_human_approval():
    record = json.loads(
        (ROOT / "research/hiad_reviewer_handoff_2026_10_04.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["status"] == "pending_coordinator_approval_and_ethics_determination"
    assert record["casebook"]["case_count"] == 24
    assert record["prescreen"]["advisory_only"] is True
    assert record["prescreen"]["human_review_required_for_every_case"] is True
    assert len(record["next_required_evidence"]) == 5
    assert "not a casebook approval" in record["claim_boundary"]
    assert (ROOT / "research/HIAD_REVIEWER_HANDOFF.md").is_file()
