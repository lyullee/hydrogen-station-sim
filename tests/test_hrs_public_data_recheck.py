import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_hrs_recheck_preserves_full_loop_boundary():
    record = json.loads(
        (ROOT / "research/hrs_public_data_recheck_2026_10_04.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["decision"] == (
        "PUBLIC_AGGREGATE_AND_EXPERIMENT_SUMMARIES_CONFIRMED_NO_NEW_FULL_LOOP_RAW"
    )
    assert record["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"
    assert len(record["sources"]) == 8
    assert all(source["full_loop_holdout_eligible"] is False for source in record["sources"])
    assert any(source["id"] == "cip_2020_35_70mpa_performance" for source in record["sources"])
    assert any(source["id"] == "zbt_methytrucks_2026_sampling_intercomparison" for source in record["sources"])
    assert any(source["id"] == "cal_state_la_cascade_2023_experiments" for source in record["sources"])
    assert any(source["id"] == "sunhydro_hsdc_operating_data" for source in record["sources"])
    assert all(source["full_loop_holdout_eligible"] is False for source in record["sources"])
    assert "author-request-only source" in record["claim_boundary"]
