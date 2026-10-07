from __future__ import annotations

from h2station.public_tank_calibration import load_public_type_iv_tank_calibration
from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario


def test_public_type_iv_profile_is_passing_and_claim_bounded():
    profile = load_public_type_iv_tank_calibration()
    assert profile is not None
    metadata = profile.runtime_metadata()
    assert metadata["status"] == "active"
    assert metadata["validation_case_count"] == 12
    assert metadata["validation_mean_metrics"]["pressure_rmse_mpa"] < 5.0
    assert "not station-to-vehicle" in metadata["validation_boundary"]


def test_reference_scenario_uses_the_public_type_iv_profile_by_default():
    profile = load_public_type_iv_tank_calibration()
    assert profile is not None
    built = build_reference_scenario(ReferenceScenario(), UnavailableHyRAMBackend())
    assert built.station.partial_station.vehicle_tank.fit.effective_volume_multiplier == (
        profile.effective_volume_multiplier
    )
    assert built.station.partial_station.vehicle_tank.fit.gas_liner_ua_multiplier == (
        profile.gas_liner_ua_multiplier
    )


def test_reference_tank_mode_remains_available_for_sensitivity_work():
    built = build_reference_scenario(
        ReferenceScenario(vehicle_tank_calibration="reference"),
        UnavailableHyRAMBackend(),
    )
    assert built.station.partial_station.vehicle_tank.fit.effective_volume_multiplier == 1.0
    assert built.station.partial_station.vehicle_tank.fit.gas_liner_ua_multiplier == 1.0


def test_llm_evidence_keeps_the_tank_fit_separate_from_full_station_validation():
    manifest = build_evidence_manifest(
        {"time_s": 0.0, "vehicle_tank_calibration": "public_type_iv"},
        {}, [], False,
    )
    calibration = manifest["runtime_vehicle_tank_calibration"]
    assert calibration["status"] == "active"
    assert "not station-to-vehicle" in calibration["validation_boundary"]
    assert prompt_evidence_summary(manifest)["runtime_vehicle_tank_calibration"][
        "validation_case_count"
    ] == 12


def test_llm_evidence_discloses_unresolved_temperature_observation_semantics():
    manifest = build_evidence_manifest(
        {"time_s": 0.0, "vehicle_tank_calibration": "public_type_iv"},
        {}, [], False,
    )

    boundary = manifest["response_evidence"][
        "temperature_observation_semantic_boundary"
    ]
    assert boundary["cross_dataset_semantic_mismatch_detected"] is True
    assert boundary["runtime_temperature_state"] == "gas_temperature"
    assert boundary["operator_selection_prohibited"] is True
    assert boundary["runtime_thermal_observation_changed"] is False
    assert boundary["validation_claim_supported"] is False
    assert len(boundary["candidate_observation_operators"]) == 4

    summary = prompt_decision_evidence(manifest)["validation_boundaries"][
        "station_to_vehicle"
    ]
    assert summary["thermal"] == "unresolved"
    header = prompt_evidence_header(manifest)[
        "temperature_observation_semantic_boundary"
    ]
    assert header["validation_claim_supported"] is False
