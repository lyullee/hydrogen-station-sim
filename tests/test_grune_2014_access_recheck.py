import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_grune_recheck_separates_data_access_from_model_validation():
    record = json.loads(
        (ROOT / "research/grune_2014_publisher_access_recheck_2026_10_11.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["status"] == "publisher_and_repository_recheck_completed"
    assert record["access_result"]["machine_readable_pressure_time_trace_found"] is False
    assert record["eligibility"]["full_raw_holdout_eligible"] is False
    assert record["eligibility"]["grune_2014_pressure_decay_gate_closed"] is False
    assert "neither validates nor invalidates" in record["claim_boundary"]
