import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gti_report_is_real_station_provenance_but_not_a_public_raw_holdout():
    record = json.loads(
        (
            ROOT
            / "research/gti_hydrogen_station_public_data_recheck_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["source"]["doi"] == "10.2172/1824631"
    assert record["source"]["machine_readable_raw_data_public"] is False
    assert record["eligibility"]["physical_experiment_or_in_use_fill"] is True
    assert record["eligibility"]["full_loop_holdout_eligible"] is False
    assert record["gate_impact"] == "independent_full_loop_gate_remains_open"
    assert "Freeze hashes" in record["next_action"]


def test_external_search_mirror_contains_gti_request_lead():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    candidate = next(
        item
        for item in mirror["candidates"]
        if item["id"] == "gti_hydrogen_station_performance_evaluation_2020"
    )
    assert candidate["public_raw_data"] is False
    assert candidate["inspection"]["full_loop_holdout_eligible"] is False
    followup = mirror["review_log_2026_10_04"]["gti_public_report_followup"]
    assert followup["gate_impact"] == "independent_full_loop_gate_remains_open"
