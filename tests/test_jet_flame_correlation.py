"""Checks for the Molkov/Saffers literature flame-length comparison."""

import math

import pytest

from h2station.risk.jet_flame import jet_flame_envelope, jet_flame_length_m


def test_published_dimensional_equation_is_transcribed():
    expected = 76.0 * (0.057 * 0.00794) ** 0.347
    assert jet_flame_length_m(0.057, 0.00794) == pytest.approx(expected, rel=1e-12)


def test_high_pressure_table_subset_point_is_in_domain():
    result = jet_flame_envelope(
        mass_flow_kg_s=0.057,
        release_diameter_m=0.00794,
        storage_pressure_pa=17.2e6,
    )
    assert result["literature_jet_flame_status"] == "CALCULATED_IN_VALIDATION_DOMAIN"
    assert result["literature_jet_flame_in_validation_domain"] is True
    assert result["literature_jet_flame_length_m"] > 0.0
    assert result["literature_jet_flame_is_harm_distance"] is False


def test_zero_release_is_not_presented_as_a_flame():
    result = jet_flame_envelope(
        mass_flow_kg_s=0.0,
        release_diameter_m=0.001,
    )
    assert result["literature_jet_flame_status"] == "NOT_ACTIVE_NO_RELEASE"
    assert result["literature_jet_flame_length_m"] == 0.0


@pytest.mark.parametrize("value", [0.0, -1.0, math.nan, math.inf])
def test_invalid_positive_inputs_are_rejected(value):
    with pytest.raises(ValueError, match="positive and finite"):
        jet_flame_length_m(0.01, value)
