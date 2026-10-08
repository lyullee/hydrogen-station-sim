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
        release_boundary="flow_limited_line",
        process_flow_limit_kg_s=mass_flow,
    )

    result = backend.evaluate_release(request)

    assert result["status"] == "calculated"
    assert result["sampled_effect_radius_m"] == pytest.approx(2.5)
    assert result["sampled_thermal_radius_m"] <= result["sampled_effect_radius_m"]
    assert result["sampled_overpressure_radius_m"] <= result["sampled_effect_radius_m"]
    assert max(
        result["sampled_thermal_radius_m"],
        result["sampled_overpressure_radius_m"],
    ) == pytest.approx(result["sampled_effect_radius_m"])
    assert result["thermal_range_status"] in {
        "WITHIN_SAMPLED_POINTS", "BELOW_THRESHOLD_AT_SAMPLES"
    }
    assert result["overpressure_range_status"] in {
        "WITHIN_SAMPLED_POINTS", "BELOW_THRESHOLD_AT_SAMPLES"
    }
    assert result["sampled_next_distance_m"] == pytest.approx(3.0)
    assert result["effect_range_status"] == "WITHIN_SAMPLED_POINTS"
    assert result["release_angle_rad"] == pytest.approx(0.0)
    assert result["release_source_boundary"] == "flow_limited_line"
    assert result["process_flow_limit_kg_s"] == pytest.approx(mass_flow)
    assert result["observation_locations_m"] == backend.observation_locations
    assert result["observation_point_count"] == len(backend.observation_locations)


def test_site_configured_observation_points_are_preserved(monkeypatch):
    monkeypatch.setenv("H2STATION_HYRAM_LOCATIONS", "[[1,0,1.5],[3,0,1.5]]")
    backend = NativeHyRAMBackend.from_environment()
    assert backend.observation_locations == ((1.0, 0.0, 1.5), (3.0, 0.0, 1.5))


def test_flow_limited_source_is_preserved_in_native_hyram_consequence(monkeypatch):
    pytest.importorskip("hyram")
    monkeypatch.delenv("H2STATION_HYRAM_LOCATIONS", raising=False)
    backend = NativeHyRAMBackend.from_environment()
    request = HyRAMDynamicReleaseRequest(
        release_id="limited-hyram", component_id="dispenser.hose", location="N13",
        time_s=0.0, duration_s=1.0, source_pressure_pa=35.0e6,
        source_temperature_k=288.15, ambient_pressure_pa=101325.0,
        orifice_diameter_m=0.01, discharge_coefficient=0.8,
        mass_flow_override_kg_s=0.06, cumulative_released_mass_kg=0.06,
        release_angle_rad=0.0, release_height_m=1.0, indoor=False,
        annual_frequency_per_year=None, immediate_ignition_probability=None,
        delayed_ignition_probability=None, release_boundary="flow_limited_line",
        process_flow_limit_kg_s=0.06,
    )

    result = backend.evaluate_release(request)

    assert result["flow_limited_equivalent_orifice_applied"] is True
    assert result["flow_limited_consequence_status"] == "EQUIVALENT_AREA_APPLIED"
    assert result["physical_orifice_diameter_m"] == pytest.approx(0.01)
    assert result["consequence_equivalent_orifice_diameter_m"] < 0.01
    assert result["modeled_consequence_mass_flow_kg_s"] == pytest.approx(0.06, rel=.05)
    assert result["mass_flow_override_status"] == "OVERRIDE_RETAINED"
    assert result["literature_delayed_ignition_status"] == "NOT_APPLICABLE_FLOW_LIMITED_SOURCE"
    assert result["literature_delayed_ignition_5kpa_radial_distance_m"] is None


def test_free_orifice_exposes_claim_bounded_delayed_ignition_comparison(monkeypatch):
    pytest.importorskip("hyram")
    monkeypatch.delenv("H2STATION_HYRAM_LOCATIONS", raising=False)
    backend = NativeHyRAMBackend.from_environment()
    request = HyRAMDynamicReleaseRequest(
        release_id="free-orifice-literature", component_id="cascade.high", location="N09",
        time_s=0.0, duration_s=1.0, source_pressure_pa=45.0e6,
        source_temperature_k=288.15, ambient_pressure_pa=101325.0,
        orifice_diameter_m=0.001, discharge_coefficient=0.8,
        mass_flow_override_kg_s=0.01, cumulative_released_mass_kg=0.01,
        release_angle_rad=0.0, release_height_m=1.0, indoor=False,
        annual_frequency_per_year=None, immediate_ignition_probability=None,
        delayed_ignition_probability=None, release_boundary="free_orifice",
        process_flow_limit_kg_s=None,
    )

    result = backend.evaluate_release(request)

    assert result["literature_delayed_ignition_status"] == "CALCULATED_IN_VALIDATION_DOMAIN"
    assert result["literature_delayed_ignition_in_validation_domain"] is True
    assert result["literature_delayed_ignition_5kpa_radial_distance_m"] > 1.5
    assert result["literature_delayed_ignition_site_safety_distance"] is False
    assert result["literature_delayed_ignition_doi"] == "10.3390/hydrogen3040027"
