import pytest

from h2station.api import FaultInput
from h2station.risk.live import HyRAMDynamicReleaseRequest
from h2station.risk.runtime_backend import (
    NativeHyRAMBackend,
    ignited_enclosure_consequence,
)
from h2station.safety_runtime import FaultEvent, FaultKind


def _request(**changes):
    values = {
        "release_id": "ignited-enclosure",
        "component_id": "cascade.medium",
        "location": "N08",
        "time_s": 10.0,
        "duration_s": 10.0,
        "source_pressure_pa": 68.0e6,
        "source_temperature_k": 298.15,
        "ambient_pressure_pa": 101_325.0,
        "orifice_diameter_m": 0.001,
        "discharge_coefficient": 0.8,
        "mass_flow_override_kg_s": 0.0066,
        "cumulative_released_mass_kg": 0.066,
        "release_angle_rad": 0.0,
        "release_height_m": 1.0,
        "indoor": True,
        "annual_frequency_per_year": None,
        "immediate_ignition_probability": None,
        "delayed_ignition_probability": None,
        "ignited": True,
        "enclosure_volume_m3": 14.9,
        "enclosure_vent_area_m2": 0.0109,
    }
    values.update(changes)
    return HyRAMDynamicReleaseRequest(**values)


def test_validated_ignited_enclosure_endpoint_is_available_at_runtime():
    result = ignited_enclosure_consequence(
        _request(),
        enclosure_volume_m3=14.9,
        enclosure_vent_area_m2=0.0109,
    )

    assert result["ignited_enclosure_status"] == "calculated"
    assert result["maximum_ignited_enclosure_overpressure_pa"] > 10_000.0
    assert result["ignited_enclosure_external_holdout_supported"] is True
    assert "usn_17934047" in result["ignited_enclosure_validation_artifact"]


def test_runtime_marks_geometry_extrapolation_outside_holdout_domain():
    result = ignited_enclosure_consequence(
        _request(),
        enclosure_volume_m3=50.0,
        enclosure_vent_area_m2=0.05,
    )
    assert result["ignited_enclosure_status"] == "calculated"
    assert result["ignited_enclosure_external_holdout_supported"] is False


def test_native_backend_merges_explicit_ignited_pressure_before_risk_scoring(monkeypatch):
    pytest.importorskip("hyram")
    monkeypatch.delenv("H2STATION_HYRAM_INDOOR_JSON", raising=False)
    backend = NativeHyRAMBackend.from_environment()

    result = backend.evaluate_release(_request())

    assert result["ignited_enclosure_status"] == "calculated"
    assert result["maximum_overpressure_pa"] == pytest.approx(
        result["maximum_ignited_enclosure_overpressure_pa"]
    )
    assert result["risk_score"] > 0.0


def test_api_propagates_explicit_ignited_enclosure_parameters():
    event = FaultInput(
        event_id="api-ignited",
        kind="hydrogen-leak",
        target="cascade.medium",
        start_time_s=0.0,
        leak_diameter_mm=1.0,
        indoor=True,
        ignited=True,
        enclosure_volume_m3=14.9,
        enclosure_vent_area_m2=0.0109,
    ).to_event()
    assert event.ignited is True
    assert event.enclosure_volume_m3 == pytest.approx(14.9)
    assert event.enclosure_vent_area_m2 == pytest.approx(0.0109)


def test_ignited_analysis_cannot_be_silently_requested_for_an_outdoor_leak():
    with pytest.raises(ValueError, match="requires an indoor leak"):
        FaultEvent(
            event_id="bad-ignition",
            kind=FaultKind.HYDROGEN_LEAK,
            target="cascade.medium",
            start_time_s=0.0,
            leak_diameter_m=0.001,
            ignited=True,
        )
