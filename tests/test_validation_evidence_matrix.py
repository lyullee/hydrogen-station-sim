from __future__ import annotations

import json
from pathlib import Path

from h2station.llm_grounding import build_evidence_manifest


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_validation_matrix_preserves_claim_boundaries_and_metrics() -> None:
    matrix = _load("research/validation_evidence_matrix_2026_10_11.json")
    scope_audit = matrix["scope_manifest_verification"]
    assert scope_audit["status"] == "PASS"
    assert scope_audit["artifact"].endswith("validation_scope_manifest_verification_2026_10_11.json")
    assert "private rows" in scope_audit["claim_boundary"]
    lanes = {lane["id"]: lane for lane in matrix["lanes"]}
    same_site = lanes["same_site_station_side_holdout"]
    assert same_site["label"] == "same_site_station_side_time_ordered_holdout"
    assert same_site["evidence"]["cascade_sequence"]["holdout_pairs"] == 3664
    assert same_site["evidence"]["recharge_pressure_forecast"]["holdout_cases"] == 394
    assert "independent external validation" in same_site["claim_boundary"]

    component = lanes["public_type_iv_component_holdout"]
    assert component["label"] == "independent_external_component_holdout"
    assert component["evidence"]["validation_cases"] == 12
    assert component["evidence"]["new_parameter_fit"] is False
    assert "vehicle" in component["claim_boundary"]

    ignited = lanes["actual_hydrogen_ignited_pressure_peaking"]
    assert ignited["evidence"]["eligible_cases"] == 27
    assert ignited["evidence"]["primary_passes"] == 27
    assert "fueling loop" in ignited["claim_boundary"]

    station_vehicle = matrix["unresolved_or_excluded"]["station_to_vehicle"]
    assert station_vehicle["status"] == "REMOVED_FROM_PRIMARY_GOAL"
    assert station_vehicle["public_eligible_synchronized_raw_set_count"] == 0
    assert len(station_vehicle["required_channels"]) == 9

    human = matrix["unresolved_or_excluded"]["human_saga_effectiveness"]
    assert human["institutional_ethics_determination"] == "PENDING"
    assert human["independent_expert_review_complete"] == "PENDING"
    assert human["frozen_protocol"]["reviewer_count"] == 3
    assert matrix["interpretation"]["full_station_to_vehicle_validation_available"] is False
    assert matrix["interpretation"]["human_effectiveness_claim_permitted"] is False

    incidents = lanes["public_hiad_incident_action_grounding"]
    assert incidents["status"] == "QUALITATIVE_TRACEABILITY_PASS"
    assert incidents["evidence"]["incident_cases"] == 34
    assert incidents["evidence"]["covered_categories"] == 8
    assert incidents["evidence"]["covered_cases"] == 34
    assert incidents["evidence"]["mapped_plans_have_five_stages"] is True


def test_validation_matrix_matches_scope_decision() -> None:
    matrix = _load("research/validation_evidence_matrix_2026_10_11.json")
    scope = _load("research/validation_data_split_and_scope_decision_2026_10_11.json")
    ethics = _load("research/ethics_and_expert_review_scope_decision_2026_10_11.json")
    assert matrix["unresolved_or_excluded"]["station_to_vehicle"]["status"] == (
        "REMOVED_FROM_PRIMARY_GOAL"
    )
    assert scope["station_to_vehicle_public_search"]["primary_goal_effect"] == (
        "REMOVE_FULL_LOOP_EXTERNAL_VALIDATION_FROM_PRIMARY_GOAL"
    )
    assert matrix["unresolved_or_excluded"]["human_saga_effectiveness"][
        "institutional_ethics_determination"
    ] == ethics["institutional_ethics_determination"]
    assert matrix["unresolved_or_excluded"]["human_saga_effectiveness"][
        "independent_expert_review_complete"
    ] == ethics["independent_expert_review_complete"]
    assert scope["ethics_and_expert_evaluation"]["current_status"] == (
        "NOT_COLLECTED_AND_NOT_A_PRIMARY_GOAL_GATE"
    )


def test_llm_grounding_exposes_matrix_without_source_paths_or_raw_rows() -> None:
    manifest = build_evidence_manifest(
        {
            "time_s": 0.0,
            "header_pressure_mpa": 50.0,
            "header_temperature_c": 25.0,
            "header_mass_kg": 10.0,
            "header_inflow_g_s": 0.0,
        },
        {},
        [],
        False,
        question="검증 범위와 독립 외부검증 상태를 알려줘",
    )
    scope = manifest["response_evidence"]["primary_scope_progress"]
    matrix = scope["validation_evidence_matrix"]
    assert matrix["status"] == "frozen_2026_10_11"
    assert matrix["station_to_vehicle_status"] == "REMOVED_FROM_PRIMARY_GOAL"
    assert matrix["public_eligible_synchronized_raw_set_count"] == 0
    assert matrix["full_station_to_vehicle_validation_available"] is False
    assert matrix["human_effectiveness_claim_permitted"] is False
    incident_grounding = matrix["public_hiad_incident_grounding"]
    assert incident_grounding["incident_cases"] == 34
    assert incident_grounding["covered_categories"] == 8
    assert incident_grounding["mapped_plans_have_five_stages"] is True
    assert "research/" not in str(matrix)
    assert "raw_rows" not in str(matrix)
