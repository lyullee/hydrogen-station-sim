import json

from h2station.llm_grounding import (
    build_evidence_manifest,
    guard_llm_claims,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def test_manifest_distinguishes_not_requested_from_calculated_impact():
    frame = {
        "time_s": 12.5,
        "nozzle_flow_g_s": 0.0,
        "header_pressure_mpa": 44.8,
        "header_temperature_c": 24.2,
        "header_mass_kg": 0.16,
        "header_inflow_g_s": 12.4,
    }
    signals = {"PT-0901": {"value": 88.0, "unit": "MPa", "quality": "GOOD"}}

    idle = build_evidence_manifest(frame, signals, [], False, question="현재 상태")
    assert idle["impact"]["calculation_status"] == "not_requested"
    assert idle["impact"]["result_count"] == 0
    assert idle["source"]["field_measurement"] is False
    station_context = idle["response_evidence"]["public_real_station_context"]
    assert station_context["source"]["doi"] == "10.1016/j.jclepro.2021.129737"
    assert station_context["full_loop_external_holdout_eligible"] is False
    assert station_context["source"]["public_raw_synchronized_rows"] is False
    assert any(
        scenario.startswith("back-to-back fueling")
        for scenario in station_context["reported_scenarios"]
    )
    assert idle["runtime_calibration"]["status"] == "reference_defaults"
    assert idle["measured_bank_pressure_envelope"] == {}
    assert idle["runtime_geometry"]["basis"] == "reference"
    assert idle["runtime_geometry"]["default_basis"] == "reference"
    assert idle["common_header"]["pressure_mpa_abs"] == 44.8
    assert idle["common_header"]["inventory_kg"] == 0.16
    assert idle["common_header"]["model_status"] == (
        "PROSPECTIVE_NOT_EXTERNALLY_VALIDATED"
    )
    assert prompt_evidence_summary(idle)["common_header"]["bank_inflow_g_s"] == 12.4
    assert prompt_decision_evidence(idle)["common_header"]["temperature_c"] == 24.2
    policy_frame = {
        **frame,
        "detector_policy": {
            "source_artifact": "research/dispersion_detector_logic_validation.json",
            "source_doi": "10.23642/usn.26117989.v2",
            "source_license": "CC BY 4.0",
            "status": "PUBLIC_REPLAY_RULE_APPLIED",
            "alarm_threshold_volpct_h2": 1.0,
            "trip_threshold_volpct_h2": 2.0,
            "persistence_s": 0.5,
            "claim_limit": "does not validate outdoor station dispersion",
        },
    }
    policy_manifest = build_evidence_manifest(policy_frame, signals, [], False)
    assert policy_manifest["detector_policy"]["status"] == "PUBLIC_REPLAY_RULE_APPLIED"
    assert policy_manifest["detector_policy"]["trip_threshold_volpct_h2"] == 2.0
    assert prompt_evidence_summary(policy_manifest)["detector_policy"]["source_doi"] == (
        "10.23642/usn.26117989.v2"
    )
    assert prompt_evidence_header(policy_manifest)["detector_policy"][
        "alarm_threshold_volpct_h2"
    ] == 1.0
    assert prompt_evidence_header(idle)["runtime_calibration"]["profile_id"] == (
        "reference_defaults"
    )
    assert prompt_evidence_header(idle)["public_real_station_context"][
        "full_loop_external_holdout_eligible"
    ] is False
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
    multisource = idle["response_evidence"][
        "confidential_multisource_mapping_feasibility"
    ]
    assert multisource["co_located_workbook_candidates"] == 0
    assert multisource["candidate_worksheet_count"] == 0
    assert multisource["sample_data_rows_structurally_inspected_in_memory"] is True
    assert multisource["measurement_values_persisted"] is False
    assert multisource["unambiguous_full_loop_mapping_available"] is False
    assert multisource["full_loop_holdout_eligible"] is False
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
    cross_release = idle["response_evidence"][
        "cross_campaign_release_validation_boundary"
    ]
    assert cross_release["evidence_role"] == (
        "mixed_external_release_component_validation"
    )
    assert cross_release["eligible_campaign_count"] == 3
    assert cross_release["supported_campaign_count"] == 1
    assert cross_release["failed_campaign_count"] == 2
    assert cross_release["ineligible_campaign_count"] == 1
    assert cross_release["campaigns"]["ekoto_2012"]["claim_supported"] is True
    assert cross_release["campaigns"]["schefer_2006"]["claim_supported"] is False
    assert cross_release["campaigns"]["schefer_2007"]["claim_supported"] is False
    assert cross_release["campaigns"]["grune_2014"][
        "minimum_requirements_met"
    ] is False
    assert cross_release["universal_release_validation_supported"] is False
    assert cross_release["apparatus_resolved_holdout_received"] is False
    assert cross_release["apparatus_resolved_holdout_run"] is False
    assert cross_release["runtime_model_changed_after_outcomes"] is False
    detector = idle["response_evidence"]["public_detector_logic_evidence"]
    assert detector["doi"] == "10.23642/usn.26117989.v2"
    assert detector["rule"]["alarm_threshold_percent"] == 1.0
    assert detector["rule"]["trip_threshold_percent"] == 2.0
    assert detector["aggregate"]["case_count"] == 22
    assert detector["aggregate"]["cases_with_trip_detection"] == 22
    assert "outdoor station dispersion" in detector["claim_limit"]
    dispersion_proxy = idle["response_evidence"]["public_dispersion_proxy_evidence"]
    assert dispersion_proxy["doi"] == "10.23642/usn.26117989.v2"
    assert dispersion_proxy["method"]["case_count"] == 22
    assert dispersion_proxy["method"]["coefficient_volpct_per_g_s"] == 28.449493830243835
    assert "does not validate outdoor station dispersion" in dispersion_proxy["claim_limit"]
    ventilation = idle["response_evidence"]["public_grune_ventilation_evidence"]
    assert ventilation["doi"] == "10.5281/zenodo.4668554"
    assert ventilation["profiles_used"] == 42
    assert ventilation["factor_count"] == 42
    assert ventilation["runtime_parameter_application"].startswith(
        "virtual_detector_proxy_only"
    )
    assert ventilation["runtime_statistic_default"] == "upper"
    assert ventilation["wind_mode_upper_envelope_summary"]["co-flow"]["case_count"] == 12
    h2safe = idle["response_evidence"]["public_h2safe_indoor_surrogate_evidence"]
    assert h2safe["doi"] == "10.7799/17118570"
    assert h2safe["case_count"] == 5
    assert h2safe["lab_sensor_coordinate_counts"] == {"Lab-1": 24, "Lab-2": 37}
    assert h2safe["numerical_hydrogen_alarm_or_trip_threshold_calibration"] is False
    assert h2safe["runtime_parameter_updated"] is False
    tank_validation = idle["response_evidence"]["public_tank_validation_boundary"]
    assert tank_validation["evidence_role"] == (
        "independent_tank_thermal_external_validation"
    )
    assert tank_validation["aggregate"]["tank_count"] == 7
    assert tank_validation["aggregate"]["screening_pass_count"] == 0
    assert tank_validation["claim_supported"] is False
    assert tank_validation["geometry_diagnostic"]["claim_prohibited"] is True
    assert tank_validation["geometry_diagnostic"][
        "ratio_to_frozen_effective_volume_median"
    ] < 1.0
    geometry = idle["response_evidence"]["public_geometry_sensitivity"]
    assert geometry["evidence_role"] == (
        "post_access_public_geometry_sensitivity_diagnostic"
    )
    assert geometry["source"]["tank_count"] == 7
    assert geometry["runtime_rule"]["default_basis"] == "reference"
    assert geometry["runtime_rule"]["default_changed"] is False
    assert geometry["variants"]["capacity_eos_no_volume_fit"][
        "screening_pass_count"
    ] == 7
    assert geometry["claim_supported"] is False
    tank_trace = idle["response_evidence"]["public_tank_trace_boundary"]
    assert tank_trace["evidence_role"] == "public_tank_thermal_boundary_candidate"
    assert tank_trace["experiment"]["sample_count"] == 2536
    assert tank_trace["channel_scope"]["tank_thermocouple_count"] == 14
    assert tank_trace["channel_scope"]["mass_flow_channel_present"] is False
    assert tank_trace["full_loop_external_holdout_eligible"] is False
    assert tank_trace["claim_supported"] is False
    early = prompt_evidence_summary(idle)
    assert early["impact_status"] == "not_requested"
    assert early["public_experimental_benchmarks"]["sources"]
    assert early["public_grune_ventilation_evidence"]["factor_count"] == 42
    assert early["public_h2safe_indoor_surrogate_evidence"]["case_count"] == 5
    assert early["public_dispersion_proxy_evidence"]["method"]["case_count"] == 22
    assert early["public_tank_validation_boundary"]["aggregate"][
        "pressure_rmse_mpa"
    ] == 6.164469743688679
    assert early["public_geometry_sensitivity"]["variants"][
        "capacity_eos_with_frozen_fit"
    ]["pressure_rmse_mean_mpa"] == 3.5380890196945884
    assert early["public_tank_trace_boundary"]["observed_ranges"][
        "p_2_bar"
    ][1] == 699.553778
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
    methytrucks_tank = idle["response_evidence"][
        "methytrucks_tank_diagnostic_boundary"
    ]
    assert methytrucks_tank["scope"]["case_count"] == 5
    assert methytrucks_tank["scope"]["unique_workbook_count"] == 2
    assert methytrucks_tank["scope"]["independent_event_count_claimed"] is False
    assert methytrucks_tank["candidate_244_l_diagnostic"][
        "pressure_rmse_case_mean_mpa"
    ] == 1.2866244910563729
    assert methytrucks_tank["candidate_244_l_diagnostic"][
        "temperature_rmse_case_mean_c"
    ] == 4.57841318799785
    assert methytrucks_tank["alternate_77_l_sensitivity"][
        "descriptive_joint_pass_count"
    ] == 1
    assert methytrucks_tank["mapping_boundary"][
        "workbook_to_sink_crosswalk_present"
    ] is False
    assert methytrucks_tank["prospective_holdout_eligible"] is False
    assert methytrucks_tank["full_loop_validation_eligible"] is False
    assert methytrucks_tank["claim_supported"] is False
    assert early["methytrucks_tank_diagnostic_boundary"][
        "component_diagnostic_eligible"
    ] is True
    preslhy = idle["response_evidence"]["preslhy_validation_boundary"]
    assert preslhy["development"]["joint_primary_passes"] == 20
    assert preslhy["independent_holdout"]["joint_primary_passes"] == 2
    assert preslhy["independent_holdout"]["claim_supported"] is False
    assert preslhy["runtime_model_parameter_changed"] is False
    assert early["preslhy_validation_boundary"][
        "independent_holdout"
    ]["minimum_requirements_met"] is False
    closed_loop = idle["response_evidence"]["closed_loop_validation_boundary"]
    assert closed_loop["aggregate"]["case_count"] == 8
    assert closed_loop["aggregate"]["screening_pass_count"] == 0
    assert closed_loop["aggregate"]["final_stop_reason_counts"][
        "safety-temperature"
    ] == 5
    assert closed_loop["claim_supported"] is False
    assert closed_loop["runtime_model_parameter_changed"] is False
    assert closed_loop["post_freeze_diagnostic"]["claim_prohibited"] is True
    assert early["closed_loop_validation_boundary"]["aggregate"][
        "screening_pass_count"
    ] == 0
    assert early["confidential_multisource_mapping_feasibility"][
        "full_loop_holdout_eligible"
    ] is False
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
    assert early["cross_campaign_release_validation_boundary"][
        "supported_campaign_count"
    ] == 1
    assert early["cross_campaign_release_validation_boundary"][
        "universal_release_validation_supported"
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
    assert header["methytrucks_tank_diagnostic_boundary"][
        "mapping_boundary"
    ]["channel_dictionary_present"] is False
    assert header["methytrucks_tank_diagnostic_boundary"][
        "claim_supported"
    ] is False
    assert header["public_tank_validation_boundary"]["claim_supported"] is False
    assert header["public_tank_validation_boundary"]["aggregate"][
        "temperature_rmse_c"
    ] == 4.624745495755946
    assert header["public_geometry_sensitivity"]["claim_supported"] is False
    assert header["public_geometry_sensitivity"]["runtime_rule"][
        "default_basis"
    ] == "reference"
    assert header["public_tank_trace_boundary"]["source"][
        "repository_commit"
    ] == "4482486fa9ab02360af364f3d1dad5ea48eabaf8"
    assert header["preslhy_validation_boundary"][
        "independent_holdout_claim_supported"
    ] is False
    assert header["closed_loop_validation_boundary"]["claim_supported"] is False
    assert header["closed_loop_validation_boundary"][
        "protocol_frozen_before_data_access"
    ] is True
    assert header["closed_loop_validation_boundary"][
        "post_freeze_diagnostic"
    ]["claim_prohibited"] is True
    assert header["confidential_multisource_mapping_feasibility"][
        "unambiguous_full_loop_mapping_available"
    ] is False
    public_links = header["public_source_links"]
    public_link_ids = {row["id"] for row in public_links}
    assert {
        "NREL_HDVS_2022_TANK_HOSE_TRACE",
        "NREL_HD_FAST_FLOW_2024_REPORT",
        "PUBLIC_METHYTRUCKS_20590761",
        "PUBLIC_METHYTRUCKS_20590842",
        "PUBLIC_HITRF_OPERATIONAL_REFERENCE",
        "KHK_PUBLIC_ACCIDENT_REPORTS",
        "PUBLIC_ACCIDENTAL_RELEASE_ARTICLE",
        "PUBLIC_ACCIDENTAL_RELEASE_DATASET",
        "PUBLIC_DETECTOR_LOGIC_DATASET",
        "PUBLIC_GRUNE_VENTILATION_DATASET",
        "PUBLIC_HYTF_TANK_TRACE",
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
    assert header["cross_campaign_release_validation_boundary"][
        "failed_campaign_count"
    ] == 2
    assert header["cross_campaign_release_validation_boundary"][
        "apparatus_resolved_holdout_received"
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
    assert lifecycle["counter_semantics_attested"] is True
    assert lifecycle["threshold_units_attested"] is True
    assert lifecycle["full_recharge_threshold_bar"] == {
        "medium_bank": 450.0,
        "high_bank": 850.0,
    }
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
    operational_recheck = idle["response_evidence"][
        "confidential_operational_profile_recheck"
    ]
    assert operational_recheck["profile_match"] is True
    assert operational_recheck["sampled_rows"] == 10896
    assert operational_recheck["committed_profile_replaced"] is False
    assert operational_recheck[
        "measured_boundary_calibration_remains_opt_in"
    ] is True
    assert operational_recheck["full_station_vehicle_validation"] is False
    assert prompt_evidence_summary(idle)[
        "confidential_operational_profile_recheck"
    ]["profile_match"] is True
    assert prompt_evidence_header(idle)[
        "confidential_operational_profile_recheck"
    ]["profile_match"] is True
    channel_quality = idle["response_evidence"][
        "confidential_station_channel_quality_recheck"
    ]
    assert channel_quality["files_read"] == 8
    assert channel_quality["sampled_rows"] == 1092
    assert channel_quality["parseable_timestamp_fraction"] == 1.0
    assert channel_quality["temperature_or_flow_parameter_fit_supported"] is False
    assert channel_quality["full_loop_holdout_eligible"] is False
    assert prompt_evidence_summary(idle)[
        "confidential_station_channel_quality_recheck"
    ]["roles"]["pressure"]["finite_fraction"] == 1.0
    assert prompt_evidence_header(idle)[
        "confidential_station_channel_quality_recheck"
    ]["full_station_vehicle_validation"] is False
    channel_envelopes = idle["response_evidence"][
        "confidential_pressure_channel_envelopes"
    ]
    assert channel_envelopes["bank_role_mapping_attested"] is False
    assert channel_envelopes["runtime_parameter_application"] is False
    assert channel_envelopes["channels"]["boundary_channel_1"][
        "pressure_mpa"
    ]["median"] == 43.2896
    channel_header = prompt_evidence_header(idle)[
        "confidential_pressure_channel_envelopes"
    ]
    assert channel_header["channels"]["boundary_channel_2"][
        "pressure_mpa"
    ]["median"] == 82.8211
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
    bank_pressure = idle["response_evidence"][
        "confidential_bank_role_pressure_envelopes"
    ]
    assert bank_pressure["bank_role_mapping_attested"] is True
    assert bank_pressure["pressure_scale_mapping_attested"] is True
    assert bank_pressure["machine_readable_unit_dictionary_present"] is False
    assert bank_pressure["runtime_parameter_application"] is False
    assert bank_pressure["full_loop_holdout_eligible"] is False
    assert bank_pressure["profiles"][0]["bank_roles"][
        "medium_storage_pressure"
    ]["pressure_mpa"]["median"] == 43.2896
    bank_header = prompt_evidence_header(idle)[
        "confidential_bank_role_pressure_envelopes"
    ]
    assert bank_header["profiles"][1]["bank_roles"][
        "high_storage_pressure"
    ]["pressure_mpa"]["p95"] == 83.58
    assert prompt_evidence_summary(idle)[
        "confidential_bank_role_pressure_envelopes"
    ]["default_model_parameters_changed"] is False
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
    private_media = idle["response_evidence"]["confidential_private_media_intake"]
    assert private_media["screen_recorded_logger_candidate"] is True
    assert private_media["machine_readable_trace_present"] is False
    assert private_media["parameter_fit_permitted"] is False
    assert private_media["full_loop_holdout_eligible"] is False
    media_summary = prompt_evidence_summary(idle)["confidential_private_media_intake"]
    assert media_summary["video_count"] > 0
    assert prompt_evidence_header(idle)["confidential_private_media_intake"][
        "machine_readable_trace_present"
    ] is False
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
    assert len(benchmarks["sources"]) == 3
    nrel_trace = next(item for item in benchmarks["sources"] if item["id"] == "NREL_HDVS_2022_TANK_HOSE_TRACE")
    assert nrel_trace["aggregate"]["sample_count"] == 351
    assert nrel_trace["raw_rows_public"] is False
    fast_flow = next(item for item in benchmarks["sources"] if item["id"] == "NREL_HD_FAST_FLOW_2024_REPORT")
    assert fast_flow["aggregate"]["peak_mass_flow_g_s"] == 483.33
    assert "untouched row-level full-loop holdout" in fast_flow["not_eligible_for"]
    fch2rail = next(item for item in benchmarks["sources"] if item["id"] == "FCH2RAIL_D61_350BAR_REPORT")
    assert fch2rail["aggregate"]["average_flow_min_g_s"] == 11.54
    assert "70 MPa passenger-vehicle validation" in fch2rail["not_eligible_for"]

    result = {"node_id": "N09", "node_name": "고압 저장뱅크",
              "calculation_status": "calculated",
              "calculation_basis": "SENSOR_BASED_HYPOTHESIS",
              "pressure_sensor": "PT-0901", "current_pressure_mpa": 88.0,
              "sampled_effect_radius_m": 3.0}
    calculated = build_evidence_manifest(
        frame, signals, [result], True,
        active_conditions=[{"scenario": "고압 저장뱅크 압력 상승", "sensor_id": "PT-0901",
                            "state": "TRIGGER", "response_plan_id": "overpressure",
                            "response_source_ids": ["HIAD2026", "H2_INCIDENT"]}],
        selected_sensor="PT-0901", question="피해영향은?",
    )
    assert calculated["impact"]["calculation_status"] == "calculated"
    assert calculated["impact"]["results"][0]["pressure_sensor"] == "PT-0901"
    assert calculated["conditions"][0]["label"] == "고압 저장뱅크 압력 상승"
    assert calculated["conditions"][0]["response_plan_id"] == "overpressure"
    assert calculated["conditions"][0]["response_source_ids"] == ["H2_INCIDENT", "HIAD2026"]
    assert calculated["response_evidence"]["source_ids"] == ["H2_INCIDENT", "HIAD2026"]
    relevant = calculated["response_evidence"]["relevant_public_accident_precedents"]
    assert relevant["citation_only"] is True
    assert relevant["by_response_plan"]["overpressure"]
    assert prompt_decision_evidence(calculated)["response_guidance"][
        "relevant_public_accident_precedents"
    ]["overpressure"]
    assert prompt_evidence_summary(calculated)["relevant_public_accident_precedents"][
        "by_response_plan"
    ]["overpressure"]
    assert prompt_evidence_header(calculated)["public_accident_evidence"][
        "relevant_precedents_by_response_plan"
    ]["overpressure"]
    assert calculated["evidence_digest"] != idle["evidence_digest"]


def test_manifest_preserves_opt_in_capacity_eos_geometry_basis():
    manifest = build_evidence_manifest(
        {
            "time_s": 2.0,
            "vehicle_geometry_basis": "capacity_eos",
            "vehicle_capacity_kg": 5.0,
            "vehicle_2_capacity_kg": 5.0,
        },
        {},
        [],
        False,
    )
    assert manifest["runtime_geometry"] == {
        "basis": "capacity_eos",
        "vehicle_capacity_kg": 5.0,
        "vehicle_2_capacity_kg": 5.0,
        "public_sensitivity_available": True,
        "default_basis": "reference",
        "capacity_eos_opt_in": True,
        "claim_limit": manifest["runtime_geometry"]["claim_limit"],
    }
    assert prompt_evidence_summary(manifest)["runtime_geometry"]["basis"] == (
        "capacity_eos"
    )

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
        "measured_bank_pressure_envelope": {
            "status": "diagnostic_only",
            "runtime_parameter_application": False,
            "banks": {"medium": {"comparison": "within_observed_robust_range"}},
        },
        "process_operations": {
            "settings": {"measured_boundary_calibration": True},
            "trailer_pressure_mpa": 60.0,
        },
    }
    manifest = build_evidence_manifest(frame, {}, [], False, question="현재 상태")
    profile = manifest["runtime_calibration"]
    assert profile["status"] == "active"
    assert profile["requested"] is True
    assert profile["profile_id"] == "owner_measured_operational_envelope_v1"
    assert profile["recharge_restart_margin_pa"] == 540000.0
    assert profile["current_boundary_pressure_comparison"]["status"] == (
        "within_measured_envelope"
    )
    assert manifest["measured_bank_pressure_envelope"]["banks"]["medium"][
        "comparison"
    ] == "within_observed_robust_range"
    assert prompt_evidence_header(manifest)["measured_bank_pressure_envelope"][
        "runtime_parameter_application"
    ] is False
    assert prompt_evidence_summary(manifest)["runtime_calibration"]["status"] == "active"
    assert prompt_evidence_header(manifest)["confidential_station_boundary_calibration"][
        "channel_attestation"
    ]["temperature_boundary_role_attested"] is False
    assert prompt_evidence_header(manifest)["runtime_calibration"]["profile_id"] == (
        "owner_measured_operational_envelope_v1"
    )


def test_manifest_separates_opt_in_recharge_dynamics_from_boundary_calibration():
    manifest = build_evidence_manifest(
        {
            "time_s": 12.5,
            "process_operations": {
                "settings": {
                    "measured_station_dynamics_calibration": True,
                },
            },
        },
        {},
        [],
        False,
        question="재충전은 왜 대기하나?",
    )
    runtime = manifest["runtime_calibration"]
    assert runtime["status"] == "reference_defaults"
    dynamics = runtime["station_recharge_dynamics"]
    assert dynamics["status"] == "requested_unavailable"
    assert dynamics["requested"] is True

    evidence = manifest["response_evidence"][
        "confidential_station_recharge_dynamics_calibration"
    ]
    assert evidence["files_read"] == 8
    assert evidence["sampled_rows"] == 457405
    assert evidence["candidate_minimum_recharge_off_time_s"] == 290.0
    assert evidence["opt_in_runtime_parameter_available"] is False
    assert evidence["runtime_application_block_reason"] == (
        "chronological_holdout_does_not_support_fitted_restart_dwell"
    )
    assert evidence["prior_single_trace_profile_superseded"] is True
    assert evidence["full_station_vehicle_validation"] is False
    assert evidence["temporal_holdout"]["completed_off_to_on_intervals"] == 32
    assert evidence["temporal_holdout"]["minimum_off_to_on_s"] == 176.0
    assert evidence["temporal_holdout"]["dwell_consistent"] is False
    pressure_band = evidence["observed_high_bank_restart_pressure_band"]
    assert pressure_band["completed_restarts"] == 124
    assert pressure_band["stop_to_restart_drop_mpa"] == {
        "p10": 4.36,
        "median": 4.555,
    }
    assert pressure_band["development_default_mpa"] == 4.5
    assert pressure_band["minimum_time_dwell_applied"] is False
    assert pressure_band["independent_holdout"] is False

    summary = prompt_evidence_summary(manifest)[
        "confidential_station_recharge_dynamics_calibration"
    ]
    assert summary["candidate_minimum_recharge_off_time_s"] == 290.0
    assert summary["default_model_parameters_changed"] is False
    assert summary["observed_high_bank_restart_pressure_band"][
        "development_default_mpa"
    ] == 4.5
    header = prompt_evidence_header(manifest)[
        "confidential_station_recharge_dynamics_calibration"
    ]
    assert header["opt_in_runtime_parameter_available"] is False
    assert header["prior_single_trace_profile_superseded"] is True
    assert header["full_station_vehicle_validation"] is False


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


def test_manifest_keeps_the_per_result_consequence_validation_boundary():
    manifest = build_evidence_manifest(
        {"time_s": 12.5},
        {},
        [{
            "node_id": "N09",
            "calculation_status": "calculated",
            "maximum_heat_flux_w_m2": 6200.0,
            "consequence_validation_scope": "COMPONENT_SCREENING_BOUNDED",
            "geometry_display_mapping_verified": True,
            "source_depletion_external_holdout_supported": False,
            "full_station_vehicle_validation_supported": False,
            "site_specific_safety_distance_supported": False,
            "consequence_validation_artifacts": "research/consequence_geometry_validation.json",
            "consequence_validation_claim_limit": "not a site-specific safety distance",
        }],
        True,
    )
    impact = manifest["impact"]["results"][0]
    assert impact["consequence_validation_scope"] == "COMPONENT_SCREENING_BOUNDED"
    assert impact["geometry_display_mapping_verified"] is True
    assert impact["full_station_vehicle_validation_supported"] is False
    assert impact["site_specific_safety_distance_supported"] is False
    assert "site-specific safety distance" in impact["consequence_validation_claim_limit"]


def test_manifest_and_prompt_keep_validated_ignited_enclosure_evidence():
    manifest = build_evidence_manifest(
        {"time_s": 19.5},
        {},
        [{
            "node_id": "N08",
            "calculation_status": "calculated",
            "indoor_status": "calculated",
            "maximum_indoor_overpressure_pa": 18_900.0,
            "ignited_enclosure_status": "calculated",
            "ignited_enclosure_model": "LACH_GAATHAUG_2021_ZERO_DIMENSIONAL",
            "maximum_ignited_enclosure_overpressure_pa": 18_900.0,
            "ignited_enclosure_peak_time_s": 0.42,
            "ignited_enclosure_average_mass_flow_kg_s": 0.0061,
            "ignited_enclosure_volume_m3": 15.0,
            "ignited_enclosure_vent_area_m2": 0.12,
            "ignited_enclosure_external_holdout_supported": True,
            "ignited_enclosure_validation_artifact": (
                "research/ignited_enclosure_external_validation_2026_10_08.json"
            ),
            "ignited_enclosure_claim_limit": (
                "Validated only inside the published vented-enclosure domain."
            ),
        }],
        True,
    )

    impact = manifest["impact"]["results"][0]
    assert impact["maximum_ignited_enclosure_overpressure_pa"] == 18_900.0
    assert impact["ignited_enclosure_external_holdout_supported"] is True
    assert impact["ignited_enclosure_volume_m3"] == 15.0

    compact = prompt_decision_evidence(manifest)["impact"]["results"][0]
    assert compact["ignited_enclosure_status"] == "calculated"
    assert compact["ignited_enclosure_model"] == (
        "LACH_GAATHAUG_2021_ZERO_DIMENSIONAL"
    )
    assert compact["maximum_ignited_enclosure_overpressure_pa"] == 18_900.0
    assert compact["ignited_enclosure_external_holdout_supported"] is True
    assert compact["ignited_enclosure_vent_area_m2"] == 0.12
    assert "published vented-enclosure domain" in compact[
        "ignited_enclosure_claim_limit"
    ]


def test_prompt_decision_evidence_keeps_limits_without_full_audit_payload():
    manifest = build_evidence_manifest(
        {"time_s": 12.5, "nozzle_flow_g_s": 200.0},
        {},
        [{
            "node_id": "N09", "calculation_status": "calculated",
            "calculation_basis": "SENSOR_BASED_HYPOTHESIS",
            "current_pressure_mpa": 88.0,
            "consequence_validation_scope": "COMPONENT_SCREENING_BOUNDED",
            "full_station_vehicle_validation_supported": False,
            "site_specific_safety_distance_supported": False,
            "consequence_validation_claim_limit": "not a field safety distance",
        }],
        True,
    )
    decision = prompt_decision_evidence(manifest)
    assert decision["evidence_digest"] == manifest["evidence_digest"]
    assert decision["impact"]["results"][0]["consequence_validation_scope"] == (
        "COMPONENT_SCREENING_BOUNDED"
    )
    assert decision["impact"]["results"][0][
        "site_specific_safety_distance_supported"
    ] is False
    assert decision["validation_boundaries"]["station_to_vehicle"][
        "claim_supported"
    ] is False
    assert decision["validation_boundaries"]["station_to_vehicle"][
        "screening_pass_count"
    ] == 0
    assert decision["validation_boundaries"]["public_tank_postaccess"] == {
        "claim_supported": False,
        "case_count": 5,
        "pressure_rmse_mpa": 1.2866244910563729,
        "temperature_rmse_c": 4.57841318799785,
        "geometry_crosswalk": "unresolved",
        "prospective": False,
        "full_loop": False,
    }
    assert decision["validation_boundaries"]["mapping"] == "not_found"
    assert decision["public_operating_envelope_screen"]["validation_claim"] is False
    assert decision["decision_support_evidence"]["public_incident"][
        "contract_pass"
    ] is True
    assert decision["validation_boundaries"]["release_cross_campaign"] == {
        "supported": 1,
        "failed": 2,
        "ineligible": 1,
        "universal": False,
        "apparatus_holdout": False,
    }
    assert len(json.dumps(decision, ensure_ascii=False)) < 3500
    assert "confidential_station_schema_intake" not in json.dumps(
        decision, ensure_ascii=False
    )


def test_llm_claim_guard_replaces_unsupported_positive_validation_claims():
    manifest = build_evidence_manifest({"time_s": 12.5}, {}, [], False)
    answer, audit = guard_llm_claims(
        "현장 검증 완료이며 안전거리는 5 m로 확정되었습니다.\n"
        "현재 압력은 88 MPa입니다.",
        manifest,
    )
    assert audit["status"] == "guarded"
    assert {item["family"] for item in audit["blocked_claims"]} == {
        "full_loop_field_validation", "confirmed_safety_distance",
    }
    assert "현장 검증 완료" not in answer
    assert "근거 경계" in answer
    assert "현재 압력은 88 MPa입니다." in answer


def test_llm_claim_guard_preserves_explicit_limitations_and_calculated_values():
    manifest = build_evidence_manifest(
        {"time_s": 12.5}, {},
        [{"node_id": "N09", "calculation_status": "calculated",
          "sampled_effect_radius_m": 4.0}],
        True,
    )
    answer, audit = guard_llm_claims(
        "이 표본 결과는 현장 검증이 아닙니다.\n"
        "표본 영향거리는 4 m이며 확정 대피거리가 아닙니다.",
        manifest,
    )
    assert audit["status"] == "clear"
    assert answer.count("현장 검증이 아닙니다") == 1
    assert "4 m" in answer


def test_llm_claim_guard_requires_virtual_action_completion_feedback():
    manifest = build_evidence_manifest(
        {
            "time_s": 18.0,
            "virtual_safety": {
                "actions": [{
                    "id": "private-action-id",
                    "kind": "esd.trip",
                    "target": "station",
                    "status": "commanded",
                    "issued_s": 17.8,
                    "note": "private operator note",
                    "baseline_metrics": {"private": 1},
                }],
            },
        },
        {}, [], False,
    )
    safety = manifest["virtual_safety"]
    assert safety["pending_count"] == 1
    assert "private-action-id" not in json.dumps(safety, ensure_ascii=False)
    assert "private operator note" not in json.dumps(safety, ensure_ascii=False)

    answer, audit = guard_llm_claims(
        "ESD가 작동되었습니다.\n밸브 폐쇄 완료되었습니다.\n충전을 중지해야 합니다.",
        manifest,
    )
    assert audit["status"] == "guarded"
    assert "ESD가 작동되었습니다" not in answer
    assert "밸브 폐쇄 완료되었습니다" not in answer
    assert "완료 피드백이 확인되지 않아" in answer
    # An instruction remains intact; only a false completed-state claim is removed.
    assert "충전을 중지해야 합니다" in answer
    assert {item["action_family"] for item in audit["blocked_claims"]} == {
        "esd_trip", "isolation",
    }


def test_llm_claim_guard_preserves_confirmed_virtual_action_completion():
    manifest = build_evidence_manifest(
        {
            "time_s": 18.0,
            "virtual_safety": {
                "actions": [{
                    "kind": "esd.trip", "target": "station",
                    "status": "confirmed", "issued_s": 17.8, "completed_s": 17.8,
                }],
            },
        },
        {}, [], False,
    )
    answer, audit = guard_llm_claims("ESD가 작동되었습니다.", manifest)
    assert audit["status"] == "clear"
    assert answer == "ESD가 작동되었습니다."
