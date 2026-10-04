import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_preslhy_repair_is_explicitly_postaccess_and_not_a_new_pass():
    record = json.loads(
        (
            ROOT
            / "research/preslhy_table_boundary_repair_diagnostic_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["evidence_role"] == "post_access_development_repair_diagnostic"
    assert record["raw_outcomes_accessed_before_repair"] is True
    assert record["primary_validation_claim_supported"] is False
    assert record["comparison"]["repaired_post_access_replay"]["claim_supported"] is False
    assert record["comparison"]["repaired_post_access_replay"]["joint_primary_passes"] == 16
    assert len(record["retained_failures"]) == 6
