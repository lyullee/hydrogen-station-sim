from __future__ import annotations

from fastapi.testclient import TestClient

from h2station.api import app
from h2station.local_evidence import local_station_evidence_summary


def test_local_evidence_summary_is_privacy_bounded() -> None:
    summary = local_station_evidence_summary()

    assert summary["status"] == "available"
    assert summary["measured_station"]["csv_file_count"] == 33
    assert summary["measured_station"]["deduplicated_row_count"] == 56_854_143
    assert summary["wide_equipment_continuity"]["file_count"] == 8
    assert summary["wide_equipment_continuity"]["timestamp_parse_failures"] == 0
    assert summary["coverage"]["local_station_data_is_sparse"] is False
    assert summary["coverage"]["vehicle_side_full_loop_validation_ready"] is False
    assert summary["coverage"]["full_loop_decision"] == "NO_NEW_FULL_LOOP_HOLDOUT"
    assert summary["adjacent_process"]["high_pressure_process"][
        "csv_event_row_count"
    ] == 2_411_774
    assert summary["adjacent_process"]["runtime_parameter_application"] is False
    assert summary["document_archive_discovery"][
        "vehicle_pressure_temperature_flow_time_candidates"
    ] == 0
    assert summary["station_asset_context"]["scenario_matrix"][
        "scenario_step_count"
    ] == 52
    assert summary["station_asset_context"]["operational_logs"][
        "operation_row_count"
    ] == 28_121
    assert summary["station_asset_context"]["engineering_and_visual_context"][
        "operational_video_incomplete_count"
    ] == 9
    assert summary["station_asset_context"]["coverage"][
        "vehicle_side_full_loop_validation_ready"
    ] is False
    revalidation = summary["station_data_revalidation"]
    assert revalidation["inventory"]["csv_file_count"] == 33
    assert revalidation["inventory"]["deduplicated_row_count"] == 56_854_143
    assert revalidation["sampled_candidate_manifest"]["sampled_table_count"] == 20
    assert revalidation["broader_local_screen"][
        "synchronized_station_dispenser_vehicle_candidates"
    ] == 0
    assert revalidation["decision"]["local_data_is_sparse"] is False
    assert revalidation["decision"]["full_loop_external_validation_supported"] is False
    assert all(value is False for value in summary["privacy"].values())
    rendered = str(summary)
    assert "C:\\" not in rendered
    assert "\\research\\" not in rendered


def test_local_evidence_endpoint_and_health_expose_same_safe_summary() -> None:
    with TestClient(app) as client:
        response = client.get("/api/evidence/local-station")
        health = client.get("/api/health")

    assert response.status_code == 200
    assert health.status_code == 200
    assert response.json()["coverage"] == local_station_evidence_summary()["coverage"]
    assert health.json()["local_evidence"]["status"] == "available"
    assert health.json()["local_evidence"]["privacy"]["raw_rows_persisted"] is False
