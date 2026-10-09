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
