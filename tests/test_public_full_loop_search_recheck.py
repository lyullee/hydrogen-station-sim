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
    assert record["recheck_links"] == [
        "research/kgs_oh_preprint_appendix_recheck_2026_10_05.json",
        "research/jrc_gastef_public_access_recheck_2026_10_05.json",
        "research/prhyde_public_access_recheck_2026_10_05.json",
        "research/h2protocol_case_inventory_recheck_2026_10_05.json",
    ]
    assert record["case_inventory_recheck"] == {
        "record": "research/h2protocol_case_inventory_recheck_2026_10_05.json",
        "fresh_holdout_eligible_case_count": 0,
        "decision": "NO_UNUSED_PUBLIC_H2PROTOCOL_CASE_FOR_FRESH_FULL_LOOP_HOLDOUT",
    }


def test_external_search_index_references_recheck():
    index = json.loads((ROOT / "research/external_full_loop_data_search.json").read_text(encoding="utf-8"))
    item = index["public_full_loop_search_recheck_2026_10_04"]
    assert item["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    current = index["public_full_loop_search_recheck_2026_10_05"]
    assert current["record"] == "research/public_full_loop_search_recheck_2026_10_05.json"
    assert current["appendix_recheck"] == "research/kgs_oh_preprint_appendix_recheck_2026_10_05.json"


def test_jrc_gastef_access_recheck_does_not_promote_missing_raw_archive():
    record = json.loads(
        (ROOT / "research/jrc_gastef_public_access_recheck_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["eligibility_decision"] == "CONTROLLED_ACCESS_LEAD_NO_PUBLIC_RAW_ARCHIVE"
    assert record["access_observation"]["datasets_table_has_public_url"] is False
    assert record["access_observation"]["machine_readable_raw_trace_retrieved"] is False
    assert record["full_loop_holdout_eligible"] is False

    current = json.loads(
        (ROOT / "research/public_full_loop_search_recheck_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    jrc = next(
        item
        for item in current["candidates"]
        if item["id"] == "jrc_gastef_reference_data_public_access_recheck_2026_10_05"
    )
    assert jrc["decision"] == "CONTROLLED_ACCESS_LEAD_NO_PUBLIC_RAW_ARCHIVE"
    assert jrc["observed_scope"]["full_loop_holdout_eligible"] is False


def test_prhyde_public_report_recheck_keeps_raw_logger_access_open():
    record = json.loads(
        (ROOT / "research/prhyde_public_access_recheck_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["eligibility_decision"] == "PUBLIC_EXPERIMENTAL_REPORT_DATA_REQUEST_LEAD_NO_RAW_ARCHIVE"
    assert record["access_observation"]["public_raw_experimental_archive_linked"] is False
    assert record["access_observation"]["machine_readable_time_series_retrieved"] is False
    assert record["full_loop_holdout_eligible"] is False

    current = json.loads(
        (ROOT / "research/public_full_loop_search_recheck_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    prhyde = next(
        item
        for item in current["candidates"]
        if item["id"] == "prhyde_public_experimental_report_access_recheck_2026_10_05"
    )
    assert prhyde["decision"] == "PUBLIC_EXPERIMENTAL_REPORT_DATA_REQUEST_LEAD_NO_RAW_ARCHIVE"
    assert prhyde["observed_scope"]["raw_logger_archive_retrieved"] is False
