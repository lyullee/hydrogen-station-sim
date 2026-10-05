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
    assert len(record["candidates"]) == 14
    qra = next(
        item
        for item in record["candidates"]
        if item["id"] == "datacite_open_qra_benchmark_2026_10_05"
    )
    assert qra["decision"] == "OPEN_QRA_SIMULATION_CONTEXT_ONLY"
    assert qra["full_loop_holdout_eligible"] is False
    lhrs = next(
        item
        for item in record["candidates"]
        if item["id"] == "nbsdc_liquid_hrs_operating_dataset_access_recheck_2026_10_05"
    )
    assert lhrs["decision"] == "REAL_LHRS_ACCESS_BOUNDARY_NO_RAW_NUMERICAL_HOLDOUT"
    assert lhrs["raw_files_downloaded"] is False
    assert lhrs["full_loop_holdout_eligible"] is False
    assert all(item["full_loop_holdout_eligible"] is False for item in record["candidates"])
    assert "common time base" in record["eligibility_rule"]["required"]



def test_open_qra_boundary_record_preserves_nonvalidation_claim_boundary():
    record = json.loads(
        (ROOT / "research/open_qra_benchmark_boundary_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["source"]["doi"] == "10.34810/DATA3632"
    assert record["license"]["spdx"] == "CC-BY-4.0"
    assert record["dataset_description"]["reported_file_count"] == 279
    assert record["eligibility"]["full_loop_external_holdout_eligible"] is False
    assert record["eligibility"]["independent_qra_context_eligible"] is True
    assert record["goal_completion_permitted"] is False
