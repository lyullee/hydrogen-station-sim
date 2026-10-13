"""Regression checks for the public-experiment release-flow envelope."""

import pytest

from h2station.risk.live import DynamicLeakModel, LeakScenario, LeakSourceState
from h2station.risk.release_uncertainty import release_flow_uncertainty_envelope


def _point_flow(diameter_m: float = 0.001) -> float:
    return DynamicLeakModel().mass_flow_kg_s(
        LeakScenario(
            release_id="test",
            component_id="cascade.high",
            location="N09",
            start_time_s=0.0,
            orifice_diameter_m=diameter_m,
            discharge_coefficient=0.8,
        ),
        LeakSourceState(45.0e6, 288.15),
    )


def test_in_domain_public_envelope_contains_unchanged_point_model():
    point = _point_flow()
    result = release_flow_uncertainty_envelope(
        source_pressure_pa=45.0e6,
        source_temperature_k=288.15,
        ambient_pressure_pa=101325.0,
        orifice_diameter_m=0.001,
        model_discharge_coefficient=0.8,
        point_mass_flow_kg_s=point,
        release_boundary="free_orifice",
        process_flow_limit_kg_s=None,
    )

    assert result["release_flow_uncertainty_status"] == (
        "PUBLIC_EXPERIMENT_ENVELOPE_IN_DOMAIN"
    )
    assert result["release_flow_public_domain"] is True
    assert result["release_flow_point_kg_s"] == pytest.approx(point)
    assert result["release_flow_lower_bound_kg_s"] <= point
    assert result["release_flow_upper_bound_kg_s"] >= point
    assert result["release_flow_empirical_cd_lower"] == pytest.approx(
        1.0217752369302118
    )
    assert result["release_flow_empirical_cd_upper"] == pytest.approx(
        1.1776503580201678
    )
    assert result["release_flow_evidence_doi"] == (
        "10.1016/j.ijhydene.2010.04.055"
    )


def test_flow_limited_boundary_is_not_widened_by_orifice_evidence():
    result = release_flow_uncertainty_envelope(
        source_pressure_pa=45.0e6,
        source_temperature_k=288.15,
        ambient_pressure_pa=101325.0,
        orifice_diameter_m=0.01,
        model_discharge_coefficient=0.8,
        point_mass_flow_kg_s=0.06,
        release_boundary="flow_limited_line",
        process_flow_limit_kg_s=0.05,
    )

    assert result["release_flow_uncertainty_status"] == (
        "PROCESS_FLOW_LIMIT_PRESERVED"
    )
    assert result["release_flow_point_kg_s"] == pytest.approx(0.05)
    assert result["release_flow_lower_bound_kg_s"] == pytest.approx(0.05)
    assert result["release_flow_upper_bound_kg_s"] == pytest.approx(0.05)
    assert result["release_flow_empirical_cd_lower"] is None


def test_outside_campaign_domain_is_explicitly_marked_as_extrapolated():
    point = _point_flow(0.005)
    result = release_flow_uncertainty_envelope(
        source_pressure_pa=100.0e6,
        source_temperature_k=288.15,
        ambient_pressure_pa=101325.0,
        orifice_diameter_m=0.005,
        model_discharge_coefficient=0.8,
        point_mass_flow_kg_s=point,
        release_boundary="free_orifice",
        process_flow_limit_kg_s=None,
    )

    assert result["release_flow_public_domain"] is False
    assert result["release_flow_uncertainty_status"] == (
        "PUBLIC_EXPERIMENT_ENVELOPE_EXTRAPOLATED"
    )
    assert result["release_flow_lower_bound_kg_s"] <= point
    assert result["release_flow_upper_bound_kg_s"] >= point
