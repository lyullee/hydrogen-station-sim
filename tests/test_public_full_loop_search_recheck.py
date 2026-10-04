import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_full_loop_recheck_preserves_strict_eligibility_boundary():
    record = json.loads((ROOT / "research/public_full_loop_search_recheck_2026_10_05.json").read_text(encoding="utf-8"))
    assert record["result"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
    assert "common elapsed time or timestamp" in record["eligibility_rule"]["required_channels"]
    assert all(item["decision"] != "FULL_LOOP_HOLDOUT" for item in record["candidates"])
    kgs = next(item for item in record["candidates"] if item["id"] == "kgs_oh_hrs_real_station_scenarios_2026_10_05")
    assert kgs["appendix_public_parameter_only"] is True
    assert kgs["raw_synchronized_logger_retrieved"] is False
    assert record["recheck_links"] == ["research/kgs_oh_preprint_appendix_recheck_2026_10_05.json"]


def test_external_search_index_references_recheck():
    index = json.loads((ROOT / "research/external_full_loop_data_search.json").read_text(encoding="utf-8"))
    item = index["public_full_loop_search_recheck_2026_10_04"]
    assert item["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    current = index["public_full_loop_search_recheck_2026_10_05"]
    assert current["record"] == "research/public_full_loop_search_recheck_2026_10_05.json"
    assert current["appendix_recheck"] == "research/kgs_oh_preprint_appendix_recheck_2026_10_05.json"
