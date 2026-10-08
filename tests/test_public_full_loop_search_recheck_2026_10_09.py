import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_recheck_keeps_new_experiment_leads_outside_full_loop_holdout():
    record = json.loads(
        (ROOT / "research/public_full_loop_search_recheck_2026_10_09.json")
        .read_text(encoding="utf-8")
    )
    assert record["status"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    leads = record["public_experiment_leads"]
    assert len(leads) == 6
    assert {item["doi"] for item in leads if item.get("doi")} == {
        "10.1016/j.renene.2024.120410",
        "10.1002/ente.202300239",
        "10.1016/j.ijhydene.2025.152513",
        "10.1016/j.ijhydene.2023.04.084",
        "10.1016/j.ijhydene.2020.08.251",
    }
    assert all(
        item["raw_time_series_publicly_retrieved"] is False
        for item in leads
        if item.get("doi")
    )
    supplement = next(item for item in leads if item["id"] == "csic_hrs_operational_strategy_supplement")
    assert supplement["raw_time_series_publicly_retrieved"] is True
    assert "simulation supplement" in supplement["eligible_use"]
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
