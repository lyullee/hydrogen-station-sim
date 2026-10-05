import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hiad_reviewer_handoff_is_machine_ready_but_human_gated():
    record = json.loads(
        (ROOT / "research/hiad_reviewer_handoff_recheck_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["status"] == "PENDING_COORDINATOR_APPROVAL_AND_ETHICS_DETERMINATION"
    assert record["machine_preflight"]["pass"] is True
    assert record["machine_preflight"]["case_count"] == 24
    assert record["review_package"]["prescreen_manifest"]["advisory_only"] is True
    readiness = record["current_readiness"]
    assert readiness["casebook_frozen"] is False
    assert readiness["ethics_and_collection_permitted"] is False
    assert readiness["coordinator_review_complete"] is False
    assert readiness["independent_review_complete"] is False
    assert len(record["required_next_evidence"]) == 5
