import json
from pathlib import Path


def test_data_scarcity_strategy_keeps_station_scope_actionable_and_full_loop_closed():
    path = Path(__file__).resolve().parents[1] / (
        "research/data_scarcity_validation_strategy_2026_10_09.json"
    )
    record = json.loads(path.read_text(encoding="utf-8"))

    assert record["status"] == "station_side_actionable_full_loop_gate_open"
    inventory = record["local_inventory"]
    assert inventory["csv_files"] == 33
    assert inventory["deduplicated_rows"] == 56854143
    assert inventory["station_side_dynamic_validation_ready"] is True
    assert inventory["vehicle_side_channels_attested"] == 0
    assert inventory["vehicle_side_full_loop_validation_ready"] is False

    public = record["public_evidence_role"]
    assert public["aggregate_operating_context_available"] is True
    assert public["component_and_consequence_traces_available"] is True
    assert public["rights_cleared_synchronized_full_loop_holdout_confirmed"] is False
    assert public["full_loop_claim_permitted"] is False

    request = record["minimum_next_request"]
    assert request["pilot_event_count"] == 3
    assert len(request["required_channels"]) == 6
    assert request["raw_rows_committed"] is False
    assert request["site_identity_committed"] is False
