import json
from pathlib import Path

import pytest

from h2station.llm_grounding import build_evidence_manifest, prompt_decision_evidence
from h2station.risk.cabinet_ventilation import (
    HYDROGEN_NORMAL_DENSITY_KG_M3,
    cabinet_ventilation_empirical_screen,
)
from h2station.risk.live import HyRAMDynamicReleaseRequest
from h2station.risk.runtime_backend import NativeHyRAMBackend, UnavailableHyRAMBackend


ROOT = Path(__file__).resolve().parents[1]


def _mass_flow(normal_flow_nm3_h: float) -> float:
    return normal_flow_nm3_h * HYDROGEN_NORMAL_DENSITY_KG_M3 / 3600.0


def test_all_non_indicative_report_rows_replay_exactly():
    evidence = json.loads((
        ROOT / "research/hydelta_natural_ventilation_evidence_2026_10_13.json"
    ).read_text(encoding="utf-8"))
    cases = [
        case
        for case in evidence["measured_case_summary"]
        if not case.get("indicative_only")
    ]
    assert len(cases) == 8

    for case in cases:
        volume = float(str(case["cabinet"]).split()[0])
        result = cabinet_ventilation_empirical_screen(
            enclosure_volume_m3=volume,
            mass_flow_kg_s=_mass_flow(case["hydrogen_flow_nm3_h"]),
        )
        assert result["cabinet_ventilation_screen_status"] == "EXACT_MEASURED_CASE"
        assert result["cabinet_ventilation_public_domain"] is True
        assert result[
            "cabinet_ventilation_lower_max_inside_volpct_h2"
        ] == pytest.approx(case["maximum_inside_volpct_h2"])
        assert result[
            "cabinet_ventilation_upper_max_vent_volpct_h2"
        ] == pytest.approx(case["maximum_vent_opening_volpct_h2"])
        assert result[
            "cabinet_ventilation_lower_flammable_observed"
        ] is case["flammable_mixture_observed"]


@pytest.mark.parametrize(
    ("volume", "flow", "classification"),
    [
        (0.5, 0.30, "LFL_TRANSITION_BETWEEN_MEASURED_BRACKETS"),
        (4.0, 0.30, "BELOW_SOURCE_LFL_AT_BOTH_BRACKETS"),
        (4.0, 2.00, "FLAMMABLE_MIXTURE_REPORTED_AT_BOTH_BRACKETS"),
    ],
)
def test_in_domain_values_return_adjacent_measurement_brackets(
    volume, flow, classification
):
    result = cabinet_ventilation_empirical_screen(
        enclosure_volume_m3=volume,
        mass_flow_kg_s=_mass_flow(flow),
    )

    assert result["cabinet_ventilation_screen_status"] == (
        "BRACKETED_MEASURED_CASES"
    )
    assert result["cabinet_ventilation_classification"] == classification
    assert "NO_INTERPOLATION" in result["cabinet_ventilation_basis"]
    assert result["cabinet_ventilation_safety_clearance_authorized"] is False


@pytest.mark.parametrize(
    ("volume", "flow", "status"),
    [
        (1.0, 0.558, "OUTSIDE_PUBLIC_CABINET_VOLUME_DOMAIN"),
        (0.5, 0.10, "OUTSIDE_PUBLIC_RELEASE_FLOW_DOMAIN"),
        (4.0, 6.00, "OUTSIDE_PUBLIC_RELEASE_FLOW_DOMAIN"),
    ],
)
def test_unsupported_cases_fail_closed_without_concentration_values(
    volume, flow, status
):
    result = cabinet_ventilation_empirical_screen(
        enclosure_volume_m3=volume,
        mass_flow_kg_s=_mass_flow(flow),
    )

    assert result["cabinet_ventilation_screen_status"] == status
    assert result["cabinet_ventilation_public_domain"] is False
    assert "cabinet_ventilation_lower_max_inside_volpct_h2" not in result
    assert result["cabinet_ventilation_requires_measured_clearance"] is True


def test_unavailable_hyram_still_exposes_bounded_public_cabinet_screen():
    flow = _mass_flow(0.558)
    request = HyRAMDynamicReleaseRequest(
        release_id="cabinet",
        component_id="compressor.package",
        location="N06",
        time_s=2.0,
        duration_s=2.0,
        source_pressure_pa=800_000.0,
        source_temperature_k=293.15,
        ambient_pressure_pa=101_325.0,
        orifice_diameter_m=0.0002,
        discharge_coefficient=0.8,
        mass_flow_override_kg_s=flow,
        cumulative_released_mass_kg=flow * 2.0,
        release_angle_rad=0.0,
        release_height_m=1.0,
        indoor=True,
        annual_frequency_per_year=None,
        immediate_ignition_probability=None,
        delayed_ignition_probability=None,
        enclosure_volume_m3=0.5,
    )

    result = UnavailableHyRAMBackend("test").evaluate_release(request)

    assert result["status"] == "unavailable"
    assert result["cabinet_ventilation_screen_status"] == "EXACT_MEASURED_CASE"
    assert result["cabinet_ventilation_evidence_doi"] == (
        "10.5281/zenodo.8164602"
    )


def test_native_hyram_screen_uses_the_mass_flow_actually_modeled(monkeypatch):
    pytest.importorskip("hyram")
    monkeypatch.delenv("H2STATION_HYRAM_LOCATIONS", raising=False)
    backend = NativeHyRAMBackend.from_environment()
    requested_flow = _mass_flow(0.558)
    request = HyRAMDynamicReleaseRequest(
        release_id="cabinet-native",
        component_id="compressor.package",
        location="N06",
        time_s=2.0,
        duration_s=2.0,
        source_pressure_pa=70_000_000.0,
        source_temperature_k=293.15,
        ambient_pressure_pa=101_325.0,
        orifice_diameter_m=0.001,
        discharge_coefficient=0.8,
        mass_flow_override_kg_s=requested_flow,
        cumulative_released_mass_kg=requested_flow * 2.0,
        release_angle_rad=0.0,
        release_height_m=1.0,
        indoor=True,
        annual_frequency_per_year=None,
        immediate_ignition_probability=None,
        delayed_ignition_probability=None,
        enclosure_volume_m3=0.5,
    )

    result = backend.evaluate_release(request)

    modeled_normal_flow = (
        result["modeled_consequence_mass_flow_kg_s"]
        * 3600.0
        / HYDROGEN_NORMAL_DENSITY_KG_M3
    )
    assert result["cabinet_ventilation_input_flow_nm3_h"] == pytest.approx(
        modeled_normal_flow
    )


def test_llm_projection_keeps_measurement_bracket_and_claim_boundary():
    screen = cabinet_ventilation_empirical_screen(
        enclosure_volume_m3=4.0,
        mass_flow_kg_s=_mass_flow(0.9),
    )
    impact = {
        "node_id": "N06",
        "calculation_status": "calculated",
        **screen,
    }
    manifest = build_evidence_manifest(
        {"time_s": 2.0}, {}, [impact], True,
    )
    row = prompt_decision_evidence(manifest)["impact"]["results"][0]

    assert row["cabinet_ventilation_screen_status"] == (
        "BRACKETED_MEASURED_CASES"
    )
    assert row["cabinet_ventilation_classification"] == (
        "LFL_TRANSITION_BETWEEN_MEASURED_BRACKETS"
    )
    assert row["cabinet_ventilation_safety_clearance_authorized"] is False
    assert "현장 안전" in row["cabinet_ventilation_claim_limit"]
