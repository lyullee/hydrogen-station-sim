from __future__ import annotations

from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def _manifest():
    return build_evidence_manifest(
        {
            "time_s": 1.0,
            "nozzle_flow_g_s": 0.0,
            "header_pressure_mpa": 44.0,
            "header_temperature_c": 25.0,
            "header_mass_kg": 0.2,
            "header_inflow_g_s": 0.0,
        },
        {"PT-0901": {"value": 44.0, "unit": "MPa", "quality": "GOOD"}},
        [],
        False,
        question="로컬 충전소 데이터가 충분한가?",
    )


def test_local_discovery_is_grounded_without_raw_provenance():
    manifest = _manifest()
    discovery = manifest["response_evidence"][
        "confidential_local_station_data_discovery"
    ]
    assert discovery["candidate_groups"][
        "confidential_station_measurement_bundle"
    ]["physical_rows"] == 59_272_300
    adjacent = discovery["candidate_groups"]["adjacent_h2_operational_telemetry"]
    assert adjacent["telemetry_rows"] == 2_410_985
    assert adjacent["telemetry_signal_key_count"] == 273
    assert "source_paths_published" not in adjacent
    wide = discovery["candidate_groups"]["wide_equipment_boundary_recheck"]
    assert wide["file_count"] == 8
    assert wide["row_count"] == 653442
    assert wide["schema_width"] == 64
    assert wide["vehicle_or_dispenser_candidate_count"] == 0
    assert "source_headers_published" not in wide
    coverage = discovery["coverage_assessment"]
    assert coverage["local_station_data_is_sparse"] is False
    assert coverage["station_side_dynamic_evidence_is_substantial"] is True
    assert coverage["vehicle_side_full_loop_validation_ready"] is False
    header_recheck = discovery["independent_header_recheck"]
    assert header_recheck["files_screened"] == 33
    assert header_recheck["candidate_file_counts"][
        "vehicle_or_dispenser_expanded"
    ] == 0
    assert header_recheck["candidate_file_counts"][
        "vehicle_pressure_temperature_expanded"
    ] == 0
    assert "source_paths_published" not in discovery
    assert "source_filenames_published" not in discovery


def test_local_discovery_reaches_bounded_prompt_views():
    manifest = _manifest()
    revalidation = manifest["response_evidence"][
        "local_station_data_revalidation"
    ]
    assert revalidation["inventory"]["csv_file_count"] == 33
    assert revalidation["inventory"]["deduplicated_row_count"] == 56_854_143
    assert revalidation["broader_local_screen"][
        "synchronized_station_dispenser_vehicle_candidates"
    ] == 0
    assert revalidation["decision"][
        "full_loop_external_validation_supported"
    ] is False
    assert "source_paths_published" not in str(revalidation)
    assert "C:\\" not in str(revalidation)

    bounded = prompt_evidence_summary(manifest)["local_station_data_revalidation"]
    assert bounded["decision"]["runtime_parameter_application"] is False
    decision_revalidation = prompt_decision_evidence(manifest)[
        "validation_boundaries"
    ]["local_station_data_revalidation"]
    assert decision_revalidation["station_side_replay_supported"] is True
    assert decision_revalidation["full_loop_external_validation_supported"] is False

    summary = prompt_evidence_summary(manifest)[
        "confidential_local_station_data_discovery"
    ]
    assert summary["coverage_assessment"][
        "quantitative_consequence_validation_ready"
    ] is False
    decision = prompt_decision_evidence(manifest)["validation_boundaries"][
        "local_station_data_discovery"
    ]
    assert decision["station_data_is_sparse"] is False
    assert decision["adjacent_operational_telemetry_rows"] == 2_410_985
    assert decision["adjacent_operational_full_loop_ready"] is False
    assert decision["wide_equipment_file_count"] == 8
    assert decision["wide_equipment_row_count"] == 653442
    assert decision["wide_equipment_station_side_screen_ready"] is True
    assert decision["wide_equipment_full_loop_ready"] is False
    assert decision["vehicle_side_full_loop_validation_ready"] is False
    header = prompt_evidence_header(manifest)[
        "confidential_local_station_data_discovery"
    ]
    assert header["candidate_groups"][
        "derived_simulator_telemetry_exports"
    ]["independence"] == "not_independent_measured_data"
    assert header["candidate_groups"][
        "adjacent_h2_operational_telemetry"
    ]["telemetry_time_span_hours"] == 24.0

    deep_scan = prompt_evidence_summary(manifest)[
        "confidential_local_data_deep_scan"
    ]
    assert deep_scan["measured_station_bundle"]["deduplicated_rows"] == 56_854_143
    assert deep_scan["broad_candidate_inventory"]["unique_candidate_assets"] == 206
    assert deep_scan["full_loop_decision"][
        "new_eligible_synchronized_station_vehicle_cohort_found"
    ] is False
    decision_deep_scan = prompt_decision_evidence(manifest)[
        "validation_boundaries"
    ]["local_data_deep_scan"]
    assert decision_deep_scan["station_csv_files"] == 33
    assert decision_deep_scan["unique_candidate_assets"] == 206
    assert decision_deep_scan["full_loop_decision"] == "NO_NEW_FULL_LOOP_HOLDOUT"
    header_deep_scan = prompt_evidence_header(manifest)[
        "confidential_local_data_deep_scan"
    ]
    assert header_deep_scan["full_loop_decision"][
        "new_eligible_synchronized_station_vehicle_cohort_found"
    ] is False
    assert "source_paths_published" not in str(header_deep_scan)

    public_candidate_scan = prompt_evidence_summary(manifest)[
        "local_public_candidate_scan"
    ]
    assert public_candidate_scan["scan"][
        "coarse_candidate_classes"
    ]["release_rig_experiment_candidate"] == 58
    assert public_candidate_scan["eligibility"][
        "full_loop_candidate_count"
    ] == 0
    assert "source_paths_published" not in str(public_candidate_scan)

    decision_candidate_scan = prompt_decision_evidence(manifest)[
        "validation_boundaries"
    ]["local_public_candidate_scan"]
    assert decision_candidate_scan["coarse_candidate_classes"][
        "vehicle_or_dispenser_candidate"
    ] == 2
    assert decision_candidate_scan["decision"] == (
        "DISCOVERY_ONLY_UNTIL_ATTESTED"
    )
    assert "source_paths_published" not in str(decision_candidate_scan)

    header_candidate_scan = prompt_evidence_header(manifest)[
        "local_public_candidate_scan"
    ]
    assert header_candidate_scan["eligibility"][
        "full_loop_candidate_count"
    ] == 0
    assert "source_paths_published" not in str(header_candidate_scan)


def test_validation_readiness_ledger_reaches_all_llm_views_without_paths():
    manifest = _manifest()
    expected = {
        "PASS": 126,
        "FAIL": 10,
        "PENDING": 7,
    }
    readiness = manifest["response_evidence"]["validation_readiness"]
    assert readiness["status"] == "available"
    assert readiness["ledger_integrity"] is True
    assert readiness["gate_counts"] == expected
    assert readiness["bounded_ijhe_submission_ready"] is False
    assert readiness["full_user_objective_ready"] is False
    assert readiness["goal_completion_permitted"] is False
    assert readiness["full_loop_external_validation_supported"] is False
    assert readiness["expert_effectiveness_evaluation_supported"] is False
    assert readiness["independent_expert_review_complete"] is False
    assert readiness["claim_tier"] == "component_and_station_side_only"
    assert readiness["open_gate_count"] == 17
    assert "full_loop_external_validation" in readiness["open_gate_ids"]
    assert readiness["evidence_use_policy"]["diagnostic"]
    assert "C:\\" not in str(readiness)
    assert "source_paths" not in str(readiness)

    summary = prompt_evidence_summary(manifest)["validation_readiness"]
    assert summary["gate_counts"] == expected
    assert summary["full_user_objective_ready"] is False

    decision = prompt_decision_evidence(manifest)["validation_boundaries"]
    assert decision["r"] == "126/10/7;0l0"

    header = prompt_evidence_header(manifest)["validation_readiness"]
    assert header["gate_counts"] == expected
    assert header["ledger_integrity"] is True


def test_local_attestation_request_is_exposed_without_private_identifiers():
    manifest = _manifest()
    request = manifest["response_evidence"][
        "confidential_local_station_attestation_request"
    ]
    assert request["status"] == "awaiting_custodian_confirmation"
    assert request["observed_local_archive"]["csv_file_count"] == 33
    assert request["observed_local_archive"][
        "deduplicated_data_row_count"
    ] == 56_854_143
    ids = {item["id"] for item in request["requested_attestations"]}
    assert {
        "timebase_and_event_alignment",
        "pressure_reference_and_units",
        "flow_and_totalizer_semantics",
        "vehicle_dispenser_full_loop_channels",
    } <= ids
    assert "source_paths_published" not in request
    assert "source_tags_published" not in request

    summary = prompt_evidence_summary(manifest)[
        "confidential_local_station_attestation_request"
    ]
    assert summary["status"] == "awaiting_custodian_confirmation"
    assert len(summary["requested_attestations"]) >= 8
    decision = prompt_decision_evidence(manifest)["validation_boundaries"][
        "local_station_attestation_request"
    ]
    assert "vehicle_dispenser_full_loop_channels" in decision[
        "requested_attestation_ids"
    ]
    header = prompt_evidence_header(manifest)[
        "confidential_local_station_attestation_request"
    ]
    assert header["observed_local_archive"]["vehicle_side_full_loop_ready"] is False
    assert "source_paths_published" not in str(header)
