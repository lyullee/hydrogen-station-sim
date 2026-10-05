import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_search_addendum_keeps_all_new_leads_out_of_full_loop_gate():
    record = json.loads(
        (ROOT / "research/public_full_loop_search_addendum_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["result"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
    assert len(record["candidates"]) == 12
    assert all(item["full_loop_holdout_eligible"] is False for item in record["candidates"])
    assert "common time base" in record["eligibility_rule"]["required"]
