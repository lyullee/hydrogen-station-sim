import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_adjacent_hydrogen_data_discovery_2026_10_09.json"


def test_adjacent_inventory_is_aggregate_only_and_substantial():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "local_adjacent_hydrogen_process_data_discovery"
    assert record["privacy"]["raw_rows_persisted"] is False
    assert record["privacy"]["source_paths_published"] is False
    process = record["collections"]["high_pressure_hydrogen_process"]
    assert process["csv_event_log_count"] == 18
    assert process["csv_event_row_count"] == 2_411_774
    assert process["logical_key_count"] == 273
    assert process["semantic_attestation"] == "required_before_replay_or_calibration"


def test_adjacent_inventory_does_not_promote_full_loop_or_runtime_fitting():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["discovery_screen"]["candidate_full_loop_count"] == 0
    assert record["eligibility"]["station_side_runtime_parameter_application"] is False
    assert record["eligibility"]["synchronized_station_dispenser_vehicle_validation"] is False
    assert record["eligibility"]["quantitative_consequence_validation"] is False
