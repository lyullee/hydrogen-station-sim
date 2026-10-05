import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_public_repository_recheck_keeps_raw_holdout_boundary_explicit():
    record = json.loads((ROOT / "research/public_repository_search_recheck_2026_10_05.json").read_text(encoding="utf-8"))
    assert record["result"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert record["full_loop_holdout_eligible"] is False
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
    assert len(record["searches"]) == 2
    assert len(record["candidates"]) >= 6
    assert all(item["decision"].endswith("EXCLUDED") for item in record["candidates"])
    assert "does not permit goal completion" in record["claim_boundary"]
