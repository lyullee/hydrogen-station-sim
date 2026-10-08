"""Benchmarks for the Cirrone et al. (2022) delayed-ignition correlation."""

import pytest

from h2station.risk.delayed_ignition import (
    delayed_ignition_envelope,
    delayed_ignition_overpressure_pa,
    delayed_ignition_radial_distance_m,
)


def test_published_vehicle_point_overpressure_is_reproduced():
    # Paper section 5.1: 70 MPa, 2 mm, Rw=2.03 m -> 21.9 kPa.
    pressure = delayed_ignition_overpressure_pa(70e6, 0.002, 2.03)
    assert pressure / 1000.0 == pytest.approx(21.9, abs=0.1)


@pytest.mark.parametrize(
    ("threshold_pa", "published_radial_m"),
    [(1_350.0, 8.8), (16_500.0, 2.4), (100_000.0, 0.9)],
)
def test_published_vehicle_radial_hazard_distances_are_reproduced(
    threshold_pa, published_radial_m
):
    # Paper equations 8--10: distances are from the fast-burning cloud centre.
    distance = delayed_ignition_radial_distance_m(70e6, 0.002, threshold_pa)
    assert distance == pytest.approx(published_radial_m, abs=0.05)


def test_envelope_keeps_published_70_mpa_example_as_extrapolation():
    result = delayed_ignition_envelope(
        storage_pressure_pa=70e6,
        storage_temperature_k=288.0,
        release_diameter_m=0.002,
    )
    assert result["literature_delayed_ignition_status"] == "CALCULATED_EXTRAPOLATED"
    assert result["literature_delayed_ignition_in_validation_domain"] is False
    assert result["literature_delayed_ignition_no_harm_radial_distance_m"] == pytest.approx(
        8.8, abs=0.05
    )
    assert result["literature_delayed_ignition_site_safety_distance"] is False


def test_in_domain_case_is_identified():
    result = delayed_ignition_envelope(
        storage_pressure_pa=20e6,
        storage_temperature_k=250.0,
        release_diameter_m=0.0064,
    )
    assert result["literature_delayed_ignition_status"] == "CALCULATED_IN_VALIDATION_DOMAIN"
    assert result["literature_delayed_ignition_in_validation_domain"] is True


def test_flow_limited_source_fails_closed():
    result = delayed_ignition_envelope(
        storage_pressure_pa=35e6,
        storage_temperature_k=288.0,
        release_diameter_m=0.01,
        release_boundary="flow_limited_line",
    )
    assert result["literature_delayed_ignition_status"] == "NOT_APPLICABLE_FLOW_LIMITED_SOURCE"
    assert result["literature_delayed_ignition_5kpa_radial_distance_m"] is None


@pytest.mark.parametrize("field", ["storage_pressure_pa", "release_diameter_m"])
def test_nonpositive_inputs_are_rejected(field):
    arguments = dict(
        storage_pressure_pa=20e6,
        release_diameter_m=0.001,
        overpressure_threshold_pa=5000.0,
    )
    arguments[field] = 0.0
    with pytest.raises(ValueError, match="positive and finite"):
        delayed_ignition_radial_distance_m(**arguments)
