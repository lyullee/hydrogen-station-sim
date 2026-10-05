import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_h2protocol_inventory_has_no_fresh_case_and_preserves_boundary():
    record = json.loads(
        (ROOT / "research/h2protocol_case_inventory_recheck_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["decision"] == "NO_UNUSED_PUBLIC_H2PROTOCOL_CASE_FOR_FRESH_FULL_LOOP_HOLDOUT"
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
    tables = record["tables_method"]
    assert tables["processed_case_count"] == 36
    assert tables["unaccounted_case_ids"] == []
    assert tables["fresh_holdout_eligible_case_ids"] == []
    assert "H2P-L10" not in tables["fresh_holdout_eligible_case_ids"]
    mc = record["mc_default"]
    assert mc["processed_case_count"] == 8
    assert mc["unaccounted_case_ids"] == []
    assert mc["fresh_holdout_eligible_case_ids"] == []
    assert len(record["archive_sha256"]) == 6
    assert len(record["next_required_evidence"]) >= 4
