import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ijhe_policy_recheck_is_scope_only_and_non_claiming():
    record = json.loads(
        (ROOT / "research/ijhe_publisher_policy_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["status"] == "POLICY_CONTEXT_ONLY"
    assert record["target_journal"]["scope_compatible_with_project"] is True
    assert record["readiness_impact"] == "submission_metadata_and_declarations_remains_pending"
    assert "does not establish external validation" in record["claim_boundary"]
    assert "Guide for Authors" in record["research_data_policy"]["observed_policy"]
