from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from h2station.api import app
from h2station.risk.runtime_backend import (
    HyRAMDynamicReleaseRequest,
    load_hyram_backend,
)


def test_api_job_lifecycle() -> None:
    with TestClient(app) as client:
        for path in ("/", "/styles.css", "/app.js", "/api/health"):
            assert client.get(path).status_code == 200

        response = client.post(
            "/api/simulations",
            json={"duration_s": 0.4, "control_interval_s": 0.2},
        )
        assert response.status_code == 202
        simulation_id = response.json()["id"]

        status = "queued"
        for _ in range(200):
            response = client.get(f"/api/simulations/{simulation_id}")
            assert response.status_code == 200
            status = response.json()["status"]
            if status in {"complete", "failed"}:
                break
            time.sleep(0.05)

        assert status == "complete"
        response = client.get(f"/api/simulations/{simulation_id}/result")
        assert response.status_code == 200
        assert {"series", "events", "risk_updates", "summary"} <= response.json().keys()
        frames = client.get(f"/api/simulations/{simulation_id}/frames").json()["frames"]
        assert frames
        bank_envelope = frames[-1]["measured_bank_pressure_envelope"]
        assert bank_envelope["runtime_parameter_application"] is False
        assert "medium" in bank_envelope["banks"]
        assert "high" in bank_envelope["banks"]


def test_native_hyram_dynamic_release() -> None:
    backend = load_hyram_backend()
    if not backend.available:
        pytest.skip("HyRAM optional dependency is not installed")

    result = backend.evaluate_release(
        HyRAMDynamicReleaseRequest(
            release_id="test-release",
            component_id="storage_hp",
            location="outdoor",
            time_s=1.0,
            duration_s=1.0,
            source_pressure_pa=35.0e6,
            source_temperature_k=293.15,
            ambient_pressure_pa=101325.0,
            orifice_diameter_m=1.0e-3,
            discharge_coefficient=0.8,
            mass_flow_override_kg_s=0.01,
            cumulative_released_mass_kg=0.01,
            release_angle_rad=0.0,
            release_height_m=1.0,
            indoor=False,
            annual_frequency_per_year=1.0e-5,
            immediate_ignition_probability=0.008,
            delayed_ignition_probability=0.004,
        )
    )

    assert result["status"] == "calculated"
    assert result["maximum_heat_flux_w_m2"] >= 0.0
    assert result["maximum_overpressure_pa"] >= 0.0
    assert result["maximum_impulse_pa_s"] >= 0.0
    assert result["visible_flame_length_m"] >= 0.0
    assert result["flammable_contour_volume_fraction"] == pytest.approx(0.04)
    assert result["flammable_plume_streamline_distance_m"] > 0.0
    assert result["modeled_consequence_mass_flow_kg_s"] > 0.0
    assert result["requested_mass_flow_override_kg_s"] == pytest.approx(0.01)
