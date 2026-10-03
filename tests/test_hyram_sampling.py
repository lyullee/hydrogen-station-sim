"""Regression checks for consequence-distance sampling resolution."""

import pytest

from h2station.risk.runtime_backend import NativeHyRAMBackend
from h2station.risk.live import (
    DynamicLeakModel,
    HyRAMDynamicReleaseRequest,
    LeakScenario,
    LeakSourceState,
)


def test_default_samples_resolve_the_old_one_metre_artifact(monkeypatch):
    pytest.importorskip("hyram")
    monkeypatch.delenv("H2STATION_HYRAM_LOCATIONS", raising=False)
    backend = NativeHyRAMBackend.from_environment()
    diameter = 0.001
    pressure = 45e6
    temperature = 298.15
    leak = LeakScenario(
        release_id="sampling-regression", component_id="cascade.low", location="N07",
        start_time_s=0.0, orifice_diameter_m=diameter, discharge_coefficient=0.8,
    )
    mass_flow = DynamicLeakModel().mass_flow_kg_s(
        leak, LeakSourceState(pressure, temperature),
    )
    request = HyRAMDynamicReleaseRequest(
        release_id=leak.release_id, component_id=leak.component_id,
        location=leak.location, time_s=0.0, duration_s=1.0,
        source_pressure_pa=pressure, source_temperature_k=temperature,
        ambient_pressure_pa=101325.0, orifice_diameter_m=diameter,
        discharge_coefficient=0.8, mass_flow_override_kg_s=mass_flow,
        cumulative_released_mass_kg=mass_flow, release_angle_rad=0.0,
        release_height_m=1.0, indoor=False,
        annual_frequency_per_year=None, immediate_ignition_probability=None,
        delayed_ignition_probability=None,
    )

    result = backend.evaluate_release(request)

    assert result["status"] == "calculated"
    assert result["sampled_effect_radius_m"] == pytest.approx(2.5)
    assert result["sampled_next_distance_m"] == pytest.approx(3.0)
    assert result["effect_range_status"] == "WITHIN_SAMPLED_POINTS"
    assert result["release_angle_rad"] == pytest.approx(0.0)
    assert result["observation_locations_m"] == backend.observation_locations
    assert result["observation_point_count"] == len(backend.observation_locations)


def test_site_configured_observation_points_are_preserved(monkeypatch):
    monkeypatch.setenv("H2STATION_HYRAM_LOCATIONS", "[[1,0,1.5],[3,0,1.5]]")
    backend = NativeHyRAMBackend.from_environment()
    assert backend.observation_locations == ((1.0, 0.0, 1.5), (3.0, 0.0, 1.5))
