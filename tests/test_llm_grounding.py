from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def test_manifest_distinguishes_not_requested_from_calculated_impact():
    frame = {"time_s": 12.5, "nozzle_flow_g_s": 0.0}
    signals = {"PT-0901": {"value": 88.0, "unit": "MPa", "quality": "GOOD"}}

    idle = build_evidence_manifest(frame, signals, [], False, question="현재 상태")
    assert idle["impact"]["calculation_status"] == "not_requested"
    assert idle["impact"]["result_count"] == 0
    assert idle["source"]["field_measurement"] is False
    assert idle["runtime_calibration"]["status"] == "reference_defaults"
    assert prompt_evidence_header(idle)["runtime_calibration"]["profile_id"] == (
        "reference_defaults"
    )
    assert idle["evidence_digest"].startswith("sha256:")
    traceability = idle["response_evidence"]["public_incident_traceability"]
    assert traceability["category_count"] == 8
    assert traceability["covered_category_count"] == 8
    assert traceability["case_count"] == 34
    assert traceability["covered_case_count"] == 34
    assert traceability["contract_pass"] is True
    assert "does not judge incident actions" in traceability["claim_limit"]
    taxonomy = traceability["action_taxonomy"]
    assert taxonomy["raw_text_retained"] is False
    assert taxonomy["holdout_use"] is False
    assert taxonomy["category_patterns_version"] == "hiad-action-taxonomy-v1"
    assert sum(taxonomy["category_counts"].values()) > 0
    assert "does not judge whether an action was correct or safe" in taxonomy["claim_limit"]
    accident_inventory = idle["response_evidence"]["public_accident_report_inventory"]
    assert accident_inventory["public_report_count"] == 23
    assert accident_inventory["incident_code_count"] == 26
    assert accident_inventory["precaution_report_count"] == 8
    assert accident_inventory["raw_pdf_mirrored"] is False
    assert accident_inventory["qualitative_scenario_grounding"] is True
    precedent_map = accident_inventory["scenario_precedent_map"]
    assert precedent_map["mapped_report_count"] == 23
    assert precedent_map["unmapped_report_count"] == 0
    assert precedent_map["citation_only"] is True
    assert "playbook_case_counts" not in precedent_map
    assert "representative_precedents" not in precedent_map
    local_accident = idle["response_evidence"][
        "confidential_local_accident_response_coverage"
    ]
    assert local_accident["case_count"] == 322
    assert local_accident["mapped_case_count"] == 322
    assert local_accident["required_stage_count"] == 5
    assert local_accident["scenario_family_candidate_counts"]["gas_release"] == 305
    assert local_accident["scenario_family_candidate_counts"]["hose_connection"] == 261
    assert local_accident["multi_family_case_count"] == 318
    assert local_accident["contract_pass"] is True
    assert local_accident["raw_rows_persisted"] is False
    assert local_accident["local_contract_run"][
        "casebook_generated_with_descriptions"
    ] is False
    assert len(local_accident["local_contract_run"]["casebook_sha256"]) == 64
    assert len(local_accident["local_contract_run"]["response_catalog_sha256"]) == 64
    assert local_accident["local_contract_run"][
        "casebook_and_source_not_committed"
    ] is True
    accidental = idle["response_evidence"]["public_accidental_release_evidence"]
    assert accidental["zenodo_doi"] == "10.5281/zenodo.17913628"
    assert accidental["article_doi"] == "10.1016/j.elstat.2025.104222"
    assert accidental["license"] == "CC BY 4.0"
    assert accidental["consequence_and_ignition_grounding_eligible"] is True
    assert accidental["full_loop_station_vehicle_holdout_eligible"] is False
    assert accidental["numerical_release_model_validation_claimed"] is False
    assert "ignition probability" in accidental["claim_limit"]
    assert all(row["local_sha256_match"] for row in accidental["files"])
    assert "raw_text" not in accidental
    release_boundary = idle["response_evidence"][
        "proust_release_model_validation_boundary"
    ]
    assert release_boundary["evidence_role"] == "post_outcome_diagnostic_only"
    assert release_boundary["baseline_discharge_coefficient"] == 0.8
    assert release_boundary["baseline_joint_primary_pass_count"] == 0
    assert release_boundary["parameter_fitting"] is False
    assert release_boundary["production_model_parameter_changed"] is False
    assert [row["nozzle_diameter_mm"] for row in release_boundary[
        "effective_coefficient_by_diameter"
    ]] == [1.0, 2.0, 3.0]
    assert "corrected discharge law" in release_boundary["claim_limit"]
    detector = idle["response_evidence"]["public_detector_logic_evidence"]
    assert detector["doi"] == "10.23642/usn.26117989.v2"
    assert detector["rule"]["alarm_threshold_percent"] == 1.0
    assert detector["rule"]["trip_threshold_percent"] == 2.0
    assert detector["aggregate"]["case_count"] == 22
    assert detector["aggregate"]["cases_with_trip_detection"] == 22
    assert "outdoor station dispersion" in detector["claim_limit"]
    early = prompt_evidence_summary(idle)
    assert early["impact_status"] == "not_requested"
    assert early["public_experimental_benchmarks"]["sources"]
    instrumentation = idle["response_evidence"][
        "public_measurement_instrumentation"
    ]
    assert instrumentation["source_count"] == 2
    assert instrumentation["file_count"] == 13
    assert instrumentation["observed_sampling_intervals_s"] == [0.5]
    assert instrumentation["station_measurement_auxiliary_eligible"] is True
    assert instrumentation["full_loop_holdout_eligible"] is False
    assert instrumentation["channel_dictionary_present"] is False
    assert early["public_measurement_instrumentation"][
        "vehicle_or_receptacle_channels_identified"
    ] is False
    preslhy = idle["response_evidence"]["preslhy_validation_boundary"]
    assert preslhy["development"]["joint_primary_passes"] == 20
    assert preslhy["independent_holdout"]["joint_primary_passes"] == 2
    assert preslhy["independent_holdout"]["claim_supported"] is False
    assert preslhy["runtime_model_parameter_changed"] is False
    assert early["preslhy_validation_boundary"][
        "independent_holdout"
    ]["minimum_requirements_met"] is False
    screen = early["public_operating_envelope_screen"]
    assert screen["status"] == "screened"
    assert screen["flow_context"] == "idle"
    assert screen["validation_claim"] is False
    assert screen["raw_rows_public"] is False
    hitrf = idle["response_evidence"]["public_hitrf_operational_reference"]
    assert hitrf["source"]["raw_synchronized_logger_public"] is False
    assert hitrf["storage"]["low_pressure"]["maximum_pressure_mpa"] == 20.0
    assert hitrf["storage"]["medium_pressure"]["tank_count"] == 6
    assert hitrf["storage"]["high_pressure"]["maximum_pressure_mpa"] == 90.0
    assert len(hitrf["compression_stages"]) == 4
    assert hitrf["dispensing_and_thermal"]["chiller_target_temperature_c"] == -40
    assert early["public_hitrf_operational_reference"]["source"][
        "raw_synchronized_logger_public"
    ] is False
    assert early["public_detector_logic_evidence"]["aggregate"]["case_count"] == 22
    assert early["confidential_local_accident_response_coverage"][
        "case_with_missing_stage_count"
    ] == 0
    assert early["confidential_local_accident_response_coverage"][
        "scenario_family_candidate_counts"
    ]["fueling_fault"] == 162
    assert early["proust_release_model_validation_boundary"][
        "baseline_joint_primary_pass_count"
    ] == 0
    assert early["proust_release_model_validation_boundary"][
        "parameter_fitting"
    ] is False
    equipment_summary = early[
        "confidential_station_equipment_operational_envelope"
    ]
    assert equipment_summary["station_equipment_envelope_supported"] is True
    assert equipment_summary["vehicle_side_channels_present"] is False
    assert early["confidential_measured_boundary_replay"]["temporal_holdout"][
        "time_ordered_holdout_supported"
    ] is True
    assert early["evidence_digest"] == idle["evidence_digest"]
    header = prompt_evidence_header(idle)
    assert header["public_measurement_instrumentation"]["file_count"] == 13
    assert header["public_measurement_instrumentation"][
        "full_loop_holdout_eligible"
    ] is False
    assert header["preslhy_validation_boundary"][
        "independent_holdout_claim_supported"
    ] is False
    public_links = header["public_source_links"]
    public_link_ids = {row["id"] for row in public_links}
    assert {
        "NREL_HDVS_2022_TANK_HOSE_TRACE",
        "NREL_HD_FAST_FLOW_2024_REPORT",
        "PUBLIC_HITRF_OPERATIONAL_REFERENCE",
        "KHK_PUBLIC_ACCIDENT_REPORTS",
        "PUBLIC_ACCIDENTAL_RELEASE_ARTICLE",
        "PUBLIC_ACCIDENTAL_RELEASE_DATASET",
        "PUBLIC_DETECTOR_LOGIC_DATASET",
    } <= public_link_ids
    assert all(row["url"].startswith(("https://", "http://")) for row in public_links)
    assert not any("confidential" in row["id"].lower() for row in public_links)
    assert prompt_evidence_summary(idle)["public_source_links"] == public_links
    assert header["public_accident_evidence"]["public_report_count"] == 23
    assert header["public_accident_evidence"]["accidental_release_zenodo_doi"] == (
        "10.5281/zenodo.17913628"
    )
    assert header["public_accident_evidence"]["accidental_release_full_loop"] is False
    assert header["confidential_local_accident_response_coverage"][
        "scenario_family_candidate_counts"
    ]["gas_release"] == 305
    assert header["confidential_local_accident_response_coverage"][
        "multi_family_case_count"
    ] == 318
    assert header["public_accident_evidence"]["action_category_counts"][
        "shutdown_isolation_depressurization"
    ] == 22
    assert header["proust_release_model_validation_boundary"][
        "baseline_joint_primary_pass_count"
    ] == 0
    assert header["proust_release_model_validation_boundary"][
        "production_model_parameter_changed"
    ] is False
    assert header["public_hitrf_operational_reference"]["raw_synchronized_logger_public"] is False
    assert header["public_hitrf_operational_reference"]["available"] is True
    assert header["public_hitrf_operational_reference"]["storage_pressure_mpa"] == {
        "high_pressure": 90.0,
        "low_pressure": 20.0,
        "medium_pressure": 41.5,
    }
    assert header["public_hitrf_operational_reference"]["storage_capacity_kg"] == {
        "high_pressure": 90,
        "low_pressure": 190,
        "medium_pressure": 85,
    }
    assert header["public_hitrf_operational_reference"][
        "compression_stages"
    ][0] == {
        "inlet_pressure_bar": 7,
        "outlet_pressure_bar": 415,
        "capacity_kg_per_day": 50,
        "capacity_kg_per_hour": None,
    }
    assert header["public_hitrf_operational_reference"][
        "chiller_target_temperature_c"
    ] == -40
    assert header["public_hitrf_operational_reference"]["storage_tiers"] == [
        "high_pressure", "low_pressure", "medium_pressure"
    ]
    assert header["public_hitrf_operational_reference"]["compression_stage_count"] == 4
    assert header["confidential_local_accident_response_coverage"][
        "case_count"
    ] == 322
    assert header["confidential_local_accident_response_coverage"][
        "contract_pass"
    ] is True
    assert header["confidential_lifecycle_evidence"]["sampled_rows"] == 41752
    assert header["confidential_lifecycle_evidence"]["counter_roles"] == [
        "high_bank_cycles", "medium_bank_cycles"
    ]
    lifecycle = idle["response_evidence"]["confidential_lifecycle_counter_summary"]
    assert lifecycle["cycle_aware_degradation_fit"] is False
    assert lifecycle["counters"]["high_bank_cycles"]["total_positive_increment"] == 1183
    station_calibration = idle["response_evidence"][
        "confidential_station_boundary_calibration"
    ]
    assert station_calibration["sampled_rows"] == 10896
    assert station_calibration["boundary_pressure_mpa"]["min"] == 56.295
    assert station_calibration["recommended_recharge_restart_margin_pa"] == 540000.0
    assert station_calibration["state_transition_count"] == 274
    assert station_calibration["channel_attestation"][
        "pressure_boundary_semantics_attested"
    ] is True
    assert station_calibration["channel_attestation"][
        "mass_flow_units_attested"
    ] is False
    assert station_calibration["full_station_vehicle_validation"] is False
    station_equipment = idle["response_evidence"][
        "confidential_station_equipment_operational_envelope"
    ]
    assert station_equipment["sampled_rows"] == 1426
    assert station_equipment["storage_pressure_mpa"]["min"] == 56.295
    assert station_equipment["station_temperature_degC"]["max"] == 39.4
    assert station_equipment["state_transition_count"] == 44
    assert station_equipment["channel_attestation"][
        "temperature_boundary_role_attested"
    ] is False
    assert station_equipment["station_equipment_envelope_supported"] is True
    assert station_equipment["station_boundary_temperature_calibration_supported"] is False
    assert station_equipment["full_station_vehicle_validation"] is False
    assert station_equipment["default_model_parameters_changed"] is False
    recheck = idle["response_evidence"][
        "confidential_pressure_recheck_decision"
    ]
    assert recheck["candidate_applied_to_runtime"] is False
    assert recheck["production_profile_retained"] == (
        "owner_measured_operational_envelope_v1"
    )
    assert recheck["retained_restart_margin_mpa"] == 0.54
    assert recheck["candidate_restart_margin_mpa"] == 1.7325
    assert "sparse_sampling_gap" in recheck["quality_warnings"]
    assert prompt_evidence_summary(idle)[
        "confidential_pressure_recheck_decision"
    ]["candidate_applied_to_runtime"] is False
    assert prompt_evidence_header(idle)[
        "confidential_pressure_recheck_decision"
    ]["candidate_applied_to_runtime"] is False
    schema = idle["response_evidence"]["confidential_station_schema_intake"]
    assert schema["source_bundle_count"] == 2
    assert schema["tagged_channel_counts"]["pressure"] > 0
    assert schema["privacy_bounded_channel_families"]["compressor_pressure"] > 0
    assert schema["vehicle_side_channel_family_count"] == 0
    assert schema["unit_attestation"]["pressure_units_attested"] is False
    assert schema["full_loop_holdout_eligible"] is False
    schema_header = prompt_evidence_header(idle)["confidential_station_schema_intake"]
    assert schema_header["station_side_schema_intake_supported"] is True
    assert schema_header["privacy_bounded_channel_families"]["flow_rate"] > 0
    assert schema_header["vehicle_side_channel_family_count"] == 0
    equipment_header = prompt_evidence_header(idle)[
        "confidential_station_equipment_operational_envelope"
    ]
    assert equipment_header["state_transition_count"] == 44
    assert equipment_header["station_boundary_temperature_calibration_supported"] is False
    confidential = idle["response_evidence"]["confidential_measured_boundary_replay"]
    assert confidential["trajectory_completed"] is True
    assert confidential["station_boundary_calibration_supported"] is True
    assert confidential["independent_full_loop_validation_supported"] is False
    assert confidential["raw_rows_persisted"] is False
    assert confidential["source_identifiers_published"] is False
    holdout = confidential["temporal_holdout"]
    assert holdout["trajectory_completed"] is True
    assert holdout["fit_used_holdout"] is False
    assert holdout["outcome_used_for_fit"] is False
    assert holdout["time_ordered_holdout_supported"] is True
    assert holdout["independent_full_loop_validation_supported"] is False
    operational_holdout = confidential["operational_envelope_holdout"]
    assert operational_holdout["calibration_points"] == 998
    assert operational_holdout["holdout_points"] == 30
    assert operational_holdout["fit_used_holdout"] is False
    assert operational_holdout["outcome_used_for_fit"] is False
    assert operational_holdout["trajectory_completed"] is True
    assert operational_holdout["independent_full_loop_validation_supported"] is False
    assert prompt_evidence_header(idle)["confidential_operational_envelope_holdout"][
        "trajectory_completed"
    ] is True
    cross_station = confidential["cross_station_pressure_envelope"]
    assert cross_station["profile_count"] == 2
    assert cross_station["observed_pressure_overlap_mpa"] == {
        "min": 56.295,
        "max": 63.36,
    }
    assert cross_station["pressure_semantics_attested_profiles"] == 2
    assert cross_station["temperature_boundary_attested_profiles"] == 0
    assert cross_station["mass_flow_units_attested_profiles"] == 0
    assert cross_station["station_to_vehicle_validation_supported"] is False
    assert prompt_evidence_header(idle)["confidential_cross_station_pressure_envelope"][
        "cross_station_pressure_plausibility_supported"
    ] is True
    benchmarks = idle["response_evidence"]["public_experimental_benchmarks"]
    assert len(benchmarks["sources"]) == 2
    nrel_trace = next(item for item in benchmarks["sources"] if item["id"] == "NREL_HDVS_2022_TANK_HOSE_TRACE")
    assert nrel_trace["aggregate"]["sample_count"] == 351
    assert nrel_trace["raw_rows_public"] is False
    fast_flow = next(item for item in benchmarks["sources"] if item["id"] == "NREL_HD_FAST_FLOW_2024_REPORT")
    assert fast_flow["aggregate"]["peak_mass_flow_g_s"] == 483.33
    assert "untouched row-level full-loop holdout" in fast_flow["not_eligible_for"]

    result = {"node_id": "N09", "node_name": "고압 저장뱅크",
              "calculation_status": "calculated",
              "calculation_basis": "SENSOR_BASED_HYPOTHESIS",
              "pressure_sensor": "PT-0901", "current_pressure_mpa": 88.0,
              "sampled_effect_radius_m": 3.0}
    calculated = build_evidence_manifest(
        frame, signals, [result], True,
        active_conditions=[{"scenario": "고압 저장뱅크 압력 상승", "sensor_id": "PT-0901",
                            "state": "TRIGGER", "response_source_ids": ["HIAD2026", "H2_INCIDENT"]}],
        selected_sensor="PT-0901", question="피해영향은?",
    )
    assert calculated["impact"]["calculation_status"] == "calculated"
    assert calculated["impact"]["results"][0]["pressure_sensor"] == "PT-0901"
    assert calculated["conditions"][0]["label"] == "고압 저장뱅크 압력 상승"
    assert calculated["conditions"][0]["response_source_ids"] == ["H2_INCIDENT", "HIAD2026"]
    assert calculated["response_evidence"]["source_ids"] == ["H2_INCIDENT", "HIAD2026"]
    assert calculated["evidence_digest"] != idle["evidence_digest"]


def test_public_operating_envelope_screen_is_descriptive_only():
    manifest = build_evidence_manifest(
        {
            "time_s": 120.0,
            "nozzle_flow_g_s": 200.0,
            "vehicle_pressure_mpa": 52.0,
        },
        {},
        [],
        False,
    )
    screen = manifest["response_evidence"]["public_operating_envelope_screen"]
    assert screen["source_id"] == "NREL_HD_FAST_FLOW_2024_REPORT"
    assert screen["flow_context"] == "within_public_fast_flow_context"
    assert screen["current_simulated_nozzle_flow_g_s"] == 200.0
    assert screen["public_average_flow_g_s"] == 172.3
    assert screen["public_peak_flow_g_s"] == 483.33
    assert screen["validation_claim"] is False
    assert "full-loop" in screen["claim_limit"]
    header = prompt_evidence_header(manifest)
    assert header["public_operating_envelope_screen"]["source_url"].endswith(
        "h2iqhour-03262024.pdf"
    )


def test_manifest_records_opt_in_measured_boundary_profile():
    frame = {
        "time_s": 12.5,
        "process_operations": {
            "settings": {"measured_boundary_calibration": True},
        },
    }
    manifest = build_evidence_manifest(frame, {}, [], False, question="현재 상태")
    profile = manifest["runtime_calibration"]
    assert profile["status"] == "active"
    assert profile["requested"] is True
    assert profile["profile_id"] == "owner_measured_operational_envelope_v1"
    assert profile["recharge_restart_margin_pa"] == 540000.0
    assert prompt_evidence_summary(manifest)["runtime_calibration"]["status"] == "active"
    assert prompt_evidence_header(manifest)["confidential_station_boundary_calibration"][
        "channel_attestation"
    ]["temperature_boundary_role_attested"] is False
    assert prompt_evidence_header(manifest)["runtime_calibration"]["profile_id"] == (
        "owner_measured_operational_envelope_v1"
    )


def test_manifest_marks_attempt_without_result_and_filters_nonfinite_values():
    manifest = build_evidence_manifest(
        {"time_s": float("nan")},
        {"PT-0901": {"value": float("inf"), "unit": "MPa", "quality": "BAD"},
         "TT-0901": {"value": 25.0, "unit": "C", "quality": "GOOD"}},
        [{"node_id": "N09", "calculation_status": "failed",
          "maximum_heat_flux_w_m2": float("nan")}],
        True,
    )
    assert manifest["impact"]["calculation_status"] == "attempted_no_result"
    assert manifest["signals"]["count"] == 1
    assert manifest["signals"]["rows"][0]["tag"] == "TT-0901"
    assert manifest["source"]["simulation_time_s"] is None
