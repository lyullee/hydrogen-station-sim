from __future__ import annotations

from fastapi.testclient import TestClient

from h2station.api import app
from h2station.local_evidence import validation_evidence_summary


def test_validation_evidence_surface_is_privacy_bounded_and_claim_limited() -> None:
    summary = validation_evidence_summary()

    assert summary["status"] == "available"
    assert summary["readiness"]["ijhe_gate_counts"] == {
        "PASS": 127,
        "FAIL": 10,
        "PENDING": 7,
    }
    assert summary["readiness"]["full_user_objective_ready"] is False
    assert summary["interpretation"]["data_volume_is_primary_blocker"] is False
    assert summary["interpretation"]["primary_blocker"]
    assert len(summary["validated_or_actionable_now"]) >= 4
    assert any(
        item["id"] == "public_type_iv_tank"
        and item["status"] == "VALIDATED_COMPONENT"
        for item in summary["validated_or_actionable_now"]
    )
    assert any(
        item["id"] == "full_loop_external_validation"
        and item["status"] == "FAIL"
        for item in summary["unresolved_gates"]
    )
    assert summary["minimum_next_input"]["event_count"] == 3
    assert all(value is False for value in summary["privacy"].values())
    rendered = str(summary)
    assert "C:\\" not in rendered
    assert "\\research\\" not in rendered


def test_validation_evidence_endpoint_returns_same_safe_surface() -> None:
    with TestClient(app) as client:
        response = client.get("/api/evidence/validation")

    assert response.status_code == 200
    assert response.json()["readiness"] == validation_evidence_summary()["readiness"]
    assert response.json()["privacy"]["raw_rows_persisted"] is False
