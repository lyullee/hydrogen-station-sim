import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_latest_public_full_loop_recheck_keeps_real_context_separate_from_holdout():
    record = json.loads(
        (ROOT / "research/public_full_loop_search_recheck_2026_10_06.json")
        .read_text(encoding="utf-8")
    )
    assert record["result"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
    assert len(record["candidates"]) == 6
    assert all(item["observed_scope"]["full_loop_holdout_eligible"] is False
               for item in record["candidates"])
    assert "written reuse terms" in record["next_action"]
    hysam = next(item for item in record["candidates"] if item["id"] == "methytrucks_hysam_system_measurement_2026_10_06")
    assert hysam["doi"] == "10.5281/zenodo.20590842"
    assert hysam["license"] == "CC BY 4.0"
    assert hysam["observed_scope"]["local_quarantine_hash_match"] is True
    assert hysam["observed_scope"]["full_loop_holdout_eligible"] is False
