from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_station_data_revalidation_2026_10_09.json"


def test_local_station_revalidation_is_privacy_bounded_and_matches_inventory() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "local_station_data_revalidation"
    privacy = record["privacy"]
    assert all(value is False for value in privacy.values())
    assert record["revalidation"]["source_inventory_matches_committed_record"] is True
    assert record["measured_station_bundle"]["csv_files"] == 33
    assert record["measured_station_bundle"]["deduplicated_rows"] == 56_854_143
    assert record["sampled_candidate_manifest"]["sampled_table_count"] == 20
    assert record["broader_local_screen"][
        "synchronized_station_dispenser_vehicle_candidates"
    ] == 0
    assert record["decision"]["local_data_is_sparse"] is False
    assert record["decision"]["new_full_loop_measured_cohort_found"] is False
    assert record["decision"]["full_loop_external_validation_supported"] is False
    assert record["decision"]["runtime_parameter_application"] is False
