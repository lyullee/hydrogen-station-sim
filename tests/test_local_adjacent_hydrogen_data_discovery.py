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
    assert process["domain_classification"] == "hydrogen_city_or_pipeline_process_context_not_HRS"
    assert "millisecond_unix_epoch" in process["time_semantics_documented_in_local_index"]
    assert "channel_role_and_unit_attestation" in process["semantic_attestation"]


def test_adjacent_inventory_does_not_promote_full_loop_or_runtime_fitting():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["discovery_screen"]["candidate_full_loop_count"] == 0
    assert record["eligibility"]["station_side_runtime_parameter_application"] is False
    assert record["eligibility"]["synchronized_station_dispenser_vehicle_validation"] is False
    assert record["eligibility"]["quantitative_consequence_validation"] is False
