from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_confidential_boundary_evidence_is_deidentified_and_claim_bounded():
    record = json.loads(
        (ROOT / "research/confidential_measured_boundary_replay_2026_10_06.json")
        .read_text(encoding="utf-8")
    )
    assert record["source_identifiers_published"] is False
    assert record["raw_rows_persisted"] is False
    assert record["provenance_boundary"]["raw_archive_in_repository"] is False
    assert record["controlled_replay"]["trajectory_completed"] is True
    assert record["controlled_replay"]["default_model_parameters_changed"] is False
    assert record["controlled_replay"]["window_selection_uses_outcomes"] is False
    assert record["diagnostic_correction"]["safety_trip_relaxed"] is False
    assert record["eligibility"]["independent_full_loop_validation_supported"] is False
    assert record["eligibility"]["prospective_holdout"] is False
    assert "full_loop_external_validation remains open" in record["gate_impact"]


def test_confidential_boundary_holdout_is_temporal_and_not_full_loop_validation():
    record = json.loads(
        (ROOT / "research/confidential_measured_boundary_holdout_2026_10_06.json")
        .read_text(encoding="utf-8")
    )
    assert record["source_identifiers_published"] is False
    assert record["raw_rows_persisted"] is False
    assert record["provenance_boundary"]["raw_archive_in_repository"] is False
    assert record["split"]["fit_used_holdout"] is False
    assert record["split"]["outcome_used_for_fit"] is False
    assert record["controlled_replay"]["holdout_trajectory_completed"] is True
    assert record["eligibility"]["time_ordered_measured_boundary_holdout_supported"] is True
    assert record["eligibility"]["independent_full_loop_validation_supported"] is False
    assert "station-to-vehicle validation remains open" in record["gate_impact"]


def test_operational_envelope_holdout_is_deidentified_and_not_full_loop_validation():
    record = json.loads(
        (
            ROOT
            / "research/confidential_operational_envelope_holdout_replay_2026_10_06.json"
        ).read_text(encoding="utf-8")
    )
    assert record["artifact_type"] == "confidential_operational_envelope_holdout_replay"
    assert record["raw_rows_persisted"] is False
    assert record["source_identifiers_published"] is False
    assert record["split"]["fit_used_holdout"] is False
    assert record["split"]["outcome_used_for_fit"] is False
    assert record["replay"]["trajectory_completed"] is True
    assert record["eligibility"]["time_ordered_measured_boundary_holdout_supported"] is True
    assert record["eligibility"]["independent_full_loop_validation_supported"] is False


def test_cross_station_pressure_envelope_is_claim_bounded():
    record = json.loads(
        (
            ROOT
            / "research/confidential_cross_station_pressure_envelope_2026_10_06.json"
        ).read_text(encoding="utf-8")
    )
    assert record["source_identifiers_published"] is False
    assert record["raw_rows_persisted"] is False
    assert record["comparison"]["profiles_with_pressure_semantics_attestation"] == 2
    assert record["comparison"]["profiles_with_temperature_boundary_attestation"] == 0
    assert record["comparison"]["profiles_with_mass_flow_units_attestation"] == 0
    assert record["eligibility"]["cross_station_pressure_plausibility_supported"] is True
    assert record["eligibility"]["station_to_vehicle_validation_supported"] is False
    assert record["eligibility"]["default_model_parameters_changed"] is False
