import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_field_lead_recheck_keeps_raw_holdout_boundary():
    record = json.loads(
        (ROOT / "research/public_field_lead_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["result"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert record["full_loop_holdout_eligible"] is False
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
    assert len(record["candidates"]) == 4
    assert all("decision" in item for item in record["candidates"])
    assert "goal must remain incomplete" in record["claim_boundary"]
