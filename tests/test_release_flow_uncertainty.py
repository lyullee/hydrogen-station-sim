"""Regression checks for the public-experiment release-flow envelope."""

import json
from pathlib import Path

import pytest

from h2station.risk.live import DynamicLeakModel, LeakScenario, LeakSourceState
from h2station.risk.release_uncertainty import (
    HYTUNNEL_EFFECTIVE_CD_LOWER,
    HYTUNNEL_EFFECTIVE_CD_UPPER,
    HYTUNNEL_PRESSURE_MAX_MPA_ABS,
    HYTUNNEL_PRESSURE_MIN_MPA_ABS,
    HYTUNNEL_TEMPERATURE_MAX_K,
    HYTUNNEL_TEMPERATURE_MIN_K,
    release_flow_uncertainty_envelope,
)


ROOT = Path(__file__).resolve().parents[1]


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


def test_hytunnel_actual_hydrogen_envelope_contains_unchanged_point_model():
    point = _point_flow(0.0005)
    result = release_flow_uncertainty_envelope(
        source_pressure_pa=45.0e6,
        source_temperature_k=288.15,
        ambient_pressure_pa=101325.0,
        orifice_diameter_m=0.0005,
        model_discharge_coefficient=0.8,
        point_mass_flow_kg_s=point,
        release_boundary="free_orifice",
        process_flow_limit_kg_s=None,
    )

    assert result["release_flow_uncertainty_status"] == (
        "PUBLIC_ACTUAL_HYDROGEN_ENVELOPE_IN_DOMAIN"
    )
    assert result["release_flow_public_domain"] is True
    assert result["release_flow_point_kg_s"] == pytest.approx(point)
    assert result["release_flow_lower_bound_kg_s"] == pytest.approx(point)
    assert result["release_flow_upper_bound_kg_s"] > point
    assert result["release_flow_empirical_cd_lower"] == pytest.approx(
        HYTUNNEL_EFFECTIVE_CD_LOWER
    )
    assert result["release_flow_empirical_cd_upper"] == pytest.approx(
        HYTUNNEL_EFFECTIVE_CD_UPPER
    )
    assert result["release_flow_evidence_source_id"] == (
        "HYTUNNEL_CS_0_5MM_BLOWDOWN"
    )
    assert result["release_flow_evidence_doi"] == "10.23642/USN.14405903"
    assert result["release_flow_evidence_article_doi"] == "10.3390/en14113008"
    assert result["release_flow_evidence_license"] == "CC BY 4.0"
    assert "post-outcome" in result["release_flow_claim_limit"]
    assert "frozen validation result remains unchanged" in result[
        "release_flow_claim_limit"
    ]


def test_hytunnel_envelope_marks_state_outside_observed_domain():
    point = _point_flow(0.0005)
    result = release_flow_uncertainty_envelope(
        source_pressure_pa=90.0e6,
        source_temperature_k=310.0,
        ambient_pressure_pa=101325.0,
        orifice_diameter_m=0.0005,
        model_discharge_coefficient=0.8,
        point_mass_flow_kg_s=point,
        release_boundary="free_orifice",
        process_flow_limit_kg_s=None,
    )

    assert result["release_flow_public_domain"] is False
    assert result["release_flow_uncertainty_status"] == (
        "PUBLIC_ACTUAL_HYDROGEN_ENVELOPE_EXTRAPOLATED"
    )
    assert result["release_flow_point_kg_s"] == pytest.approx(point)


def test_unrelated_hytunnel_and_proust_diameters_are_not_interpolated():
    point = _point_flow(0.00075)
    result = release_flow_uncertainty_envelope(
        source_pressure_pa=45.0e6,
        source_temperature_k=288.15,
        ambient_pressure_pa=101325.0,
        orifice_diameter_m=0.00075,
        model_discharge_coefficient=0.8,
        point_mass_flow_kg_s=point,
        release_boundary="free_orifice",
        process_flow_limit_kg_s=None,
    )

    assert result["release_flow_evidence_source_id"] == (
        "PROUST_25L_TERMINAL_ORIFICE"
    )
    assert result["release_flow_public_domain"] is False
    assert result["release_flow_uncertainty_status"] == (
        "PUBLIC_EXPERIMENT_ENVELOPE_EXTRAPOLATED"
    )
    assert result["release_flow_empirical_cd_lower"] == pytest.approx(
        1.0217752369302118
    )


def test_hytunnel_runtime_constants_match_post_outcome_diagnostic():
    artifact = json.loads(
        (ROOT / "research/hytunnel_carpark_effective_cd_diagnostic_2026_10_12.json")
        .read_text(encoding="utf-8")
    )
    aggregate = artifact["aggregate"]

    assert artifact["post_outcome_diagnostic"] is True
    assert artifact["runtime_parameter_changed"] is False
    assert artifact["frozen_validation_result_changed"] is False
    assert artifact["validation_gate_effect"] == "none"
    assert aggregate["effective_cd_central_union_lower"] == pytest.approx(
        HYTUNNEL_EFFECTIVE_CD_LOWER
    )
    assert aggregate["effective_cd_central_union_upper"] == pytest.approx(
        HYTUNNEL_EFFECTIVE_CD_UPPER
    )
    assert aggregate["observed_pressure_min_mpa_abs"] == pytest.approx(
        HYTUNNEL_PRESSURE_MIN_MPA_ABS
    )
    assert aggregate["observed_pressure_max_mpa_abs"] == pytest.approx(
        HYTUNNEL_PRESSURE_MAX_MPA_ABS
    )
    assert aggregate["observed_temperature_min_k"] == pytest.approx(
        HYTUNNEL_TEMPERATURE_MIN_K
    )
    assert aggregate["observed_temperature_max_k"] == pytest.approx(
        HYTUNNEL_TEMPERATURE_MAX_K
    )
