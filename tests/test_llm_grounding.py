import json

import pytest

from h2station.llm_grounding import (
    build_evidence_manifest,
    compact_data_used,
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
    operation_practice = idle["response_evidence"][
        "public_station_operation_practice_reference"
    ]
    assert operation_practice["source"]["url"] == (
        "https://www.calstatela.edu/ecst/h2station/operation"
    )
    assert operation_practice["reported_practices"][
        "cascade_then_compressor_topoff"
    ] is True
    assert operation_practice["reported_practices"][
        "periodic_leak_check_pause_s"
    ] == 5
    assert operation_practice["not_allowed"]
    assert operation_practice["claim_limit"]
    assert "public_station_operation_practice_reference" not in (
        prompt_decision_evidence(idle)["decision_support_evidence"]
    )
    cip_endpoint = idle["response_evidence"][
        "public_cip_dispenser_endpoint_reference"
    ]
    assert cip_endpoint["source"]["doi"] == (
        "10.19799/j.cnki.2095-4239.2020.0049"
    )
    assert len(cip_endpoint["experiments"]) == 2
    assert cip_endpoint["endpoint_tables_verified"] is True
    assert cip_endpoint["time_series_available"] is False
    fueling_manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False,
        question="차량 70 MPa 디스펜서 충전 속도와 프로토콜을 설명해줘",
    )
    fueling_decision = prompt_decision_evidence(fueling_manifest)
    cip_support = fueling_decision["decision_support_evidence"][
        "public_cip_dispenser_endpoint_reference"
    ]
    assert cip_support["experiments"][1]["peak_mass_flow_g_s"] == 36
    assert cip_support["time_series_available"] is False
    assert fueling_decision["validation_boundaries"][
        "public_cip_dispenser_endpoint"
    ]["full_loop_external_validation_ready"] is False
    assert any(
        item["id"] == "PUBLIC_CIP_2020_35_70MPA_ENDPOINTS"
        for item in prompt_evidence_header(fueling_manifest)["public_source_links"]
    )
    candidate_screen = idle["response_evidence"]["local_candidate_full_loop_screen"]
    assert candidate_screen["decision"] == "NO_NEW_FULL_LOOP_MEASURED_COHORT"
    candidates = {item["id"]: item for item in candidate_screen["candidates"]}
    assert candidates["nrel_h2fills_2022_hdvs_typeiv"]["decision"] == (
        "PARTIAL_TANK_BOUNDARY_ONLY"
    )
    assert candidates["dtu_tes_hydrogen_fuelling_station_v2_1"]["decision"] == (
        "SIMULATOR_REFERENCE_ONLY"
    )
    assert candidates["dtu_tes_hydrogen_fuelling_station_v2_1"][
        "measured_time_series_present"
    ] is False
    compact_candidates = prompt_evidence_summary(idle)[
        "local_candidate_full_loop_screen"
    ]
    assert compact_candidates["coverage_assessment"][
        "station_side_dynamic_evidence_is_substantial"
    ] is True
    assert len(compact_candidates["candidates"]) == 3
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
    public_catalog = idle["response_evidence"]["local_public_validation_catalog"]
    assert public_catalog["scope"]["collection_count"] == 37
    assert public_catalog["scope"]["file_count"] == 917
    assert public_catalog["coverage_assessment"][
        "full_loop_holdout_eligible"
    ] is False
    catalog_summary = prompt_evidence_summary(idle)[
        "local_public_validation_catalog"
    ]
    assert catalog_summary["scope"]["size_gb_decimal"] == 6.796
    catalog_header = prompt_evidence_header(idle)[
        "local_public_validation_catalog"
    ]
    assert catalog_header["scope"]["file_count"] == 917
    assert "local_public_validation_catalog" not in prompt_decision_evidence(idle)[
        "validation_boundaries"
    ]
    data_manifest = build_evidence_manifest(
        frame, signals, [], False, question="공개 실측 데이터 검증"
    )
    catalog_decision = prompt_decision_evidence(data_manifest)[
        "validation_boundaries"
    ]["local_public_validation_catalog"]
    assert catalog_decision["public_component_evidence_substantial"] is True
    assert catalog_decision["full_loop_holdout_eligible"] is False
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
    replay = traceability["digital_twin_replay"]
    assert replay["backend"] == "HyRAM+ 6.1 native"
    assert replay["case_count"] == 34
    assert replay["integration_trace_pass_count"] == 34
    assert replay["direct_physical_case_count"] == 29
    assert replay["partial_proxy_case_count"] == 4
    assert replay["response_only_case_count"] == 1
    assert replay["canonical_recipe_pass_count"] == replay["canonical_recipe_count"] == 9
    assert replay["case_narrative_used_for_physical_parameters"] is False
    assert "does not reconstruct any HIAD accident" in replay["claim_limit"]
    summary_replay = prompt_evidence_summary(idle)["public_incident_traceability"][
        "digital_twin_replay"
    ]
    assert summary_replay["direct_physical_case_count"] == 29
    header_replay = prompt_evidence_header(idle)["public_accident_evidence"][
        "hiad_digital_twin_replay"
    ]
    assert header_replay["partial_proxy_case_count"] == 4
    compact_replay = prompt_decision_evidence(idle)["decision_support_evidence"][
        "public_incident"
    ]["digital_twin_replay"]
    assert compact_replay == {
        "direct": 29,
        "proxy": 4,
        "response_only": 1,
        "recipes_passed": 9,
        "recipes_total": 9,
        "incident_parameterized": False,
    }
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
    khk_replay = accident_inventory["digital_twin_replay"]
    assert khk_replay["public_report_count"] == 23
    assert khk_replay["incident_code_count"] == 26
    assert khk_replay["integration_trace_pass_report_count"] == 22
    assert khk_replay["integration_trace_pass_incident_code_count"] == 25
    assert khk_replay["out_of_scope_report_count"] == 1
    assert khk_replay["canonical_recipe_pass_count"] == 8
    assert khk_replay["canonical_recipe_count"] == 8
    assert khk_replay["report_narrative_used_for_physical_parameters"] is False
    summary_khk = prompt_evidence_summary(idle)["public_accident_report_inventory"][
        "digital_twin_replay"
    ]
    assert summary_khk["integration_trace_pass_incident_code_count"] == 25
    header_khk = prompt_evidence_header(idle)["public_accident_evidence"][
        "khk_digital_twin_replay"
    ]
    assert header_khk["out_of_scope_report_count"] == 1
    compact_khk = prompt_decision_evidence(idle)["decision_support_evidence"][
        "khk_trace"
    ]
    assert compact_khk == (
        "25/26 codes; 8/8 recipes; KOH excluded; metadata routing only"
    )
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
    cross_station_bundle = idle["response_evidence"][
        "confidential_cross_station_bundle_recheck"
    ]
    assert cross_station_bundle["bundle_count"] == 2
    assert [item["file_count"] for item in cross_station_bundle["bundles"]] == [25, 8]
    assert cross_station_bundle["station_side_transfer_candidate"] is True
    assert cross_station_bundle["full_loop_external_validation_supported"] is False
    assert prompt_evidence_summary(idle)[
        "confidential_cross_station_bundle_recheck"
    ]["bundle_count"] == 2
    assert prompt_evidence_header(idle)[
        "confidential_cross_station_bundle_recheck"
    ]["station_side_transfer_candidate"] is True
    local_question = build_evidence_manifest(
        {"time_s": 0.0}, {}, [], False,
        question="로컬 충전소 데이터 교차 검증 후보를 설명해줘",
    )
    local_decision = prompt_decision_evidence(local_question)
    assert local_decision["decision_support_evidence"][
        "confidential_cross_station_bundle_recheck"
    ]["station_side_transfer_candidate"] is True
    discovery_decision = local_decision["validation_boundaries"][
        "local_station_data_discovery"
    ]
    assert discovery_decision["wide_equipment_continuity_screen_ready"] is True
    assert discovery_decision["wide_equipment_replay_ready"] is False
    transfer_decision = local_decision["validation_boundaries"][
        "local_station_cross_bundle_transfer"
    ]
    assert transfer_decision["transfer_cycle_count"] == 225
    assert transfer_decision["candidate_corroborated"] is True
    assert transfer_decision["full_loop"] is False
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
    assert accidental["reported_findings"]["experiment_count"] == 3
    assert accidental["reported_findings"]["ignition_observed_case_count"] == 2
    assert accidental["reported_findings"]["no_ignition_case_count"] == 1
    assert accidental["reported_findings"][
        "remote_or_obstructed_ignition_reported"
    ] is True
    assert accidental["reported_findings"][
        "delayed_ignition_delay_s_reported"
    ] == 0.33
    assert accidental["reported_findings"][
        "fire_jet_length_m_greater_than_reported"
    ] == 7.0
    assert accidental["reported_findings"]["ignition_probability_estimated"] is False
    assert accidental["reported_findings"]["ignition_mechanism_confirmed"] is False
    assert "ignition probability" in accidental["claim_limit"]
    assert all(row["local_sha256_match"] for row in accidental["files"])
    assert "raw_text" not in accidental
    summary_accidental = prompt_evidence_summary(idle)[
        "public_accidental_release_evidence"
    ]
    assert summary_accidental["reported_findings"][
        "remote_or_obstructed_ignition_reported"
    ] is True
    header_accidental = prompt_evidence_header(idle)["public_accident_evidence"]
    assert header_accidental["accidental_release_reported_findings"][
        "experiment_count"
    ] == 3
    release_manifest = build_evidence_manifest(
        frame,
        signals,
        [{
            "node_id": "N09",
            "calculation_status": "calculated",
            "release_source_boundary": "HIGH_PRESSURE_RELEASE",
            "literature_delayed_ignition_status": "REPORTED_ONLY",
        }],
        True,
        question="수소 누출과 지연 점화 위험을 분석해줘",
    )
    decision_accidental = prompt_decision_evidence(release_manifest)[
        "decision_support_evidence"
    ]["public_accidental_release"]
    assert decision_accidental["ignition_probability_estimated"] is False
    assert decision_accidental["ignition_mechanism_confirmed"] is False
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
    reference_detector = idle["response_evidence"][
        "public_reference_leak_detector_evidence"
    ]
    assert reference_detector["doi"] == "10.5281/zenodo.12180368"
    assert reference_detector["observation_count"] == 45
    assert reference_detector["detector_class_count"] == 2
    assert reference_detector["evaluated_series_count"] == 3
    assert reference_detector["joint_pass"] is True
    assert all(row["joint_pass"] is True for row in reference_detector["series"])
    assert reference_detector["runtime_application"] is False
    assert reference_detector["spatial_detector_transfer_gate_changed"] is False
    assert reference_detector["full_loop_validation_supported"] is False
    spatial_detector = idle["response_evidence"][
        "public_actual_hydrogen_spatial_stratification_evidence"
    ]
    assert spatial_detector["dataset_doi"] == "10.23642/usn.26117989.v2"
    assert spatial_detector["article_doi"] == "10.1016/j.jlp.2025.105669"
    assert spatial_detector["experiment_count"] == 22
    assert spatial_detector["sensor_case_observation_count"] == 638
    assert spatial_detector["placements"]["top"][
        "alarm_coverage_fraction"
    ] == 1.0
    assert spatial_detector["placements"]["top"][
        "trip_coverage_fraction"
    ] == 1.0
    assert spatial_detector["near_source_bottom"][
        "median_alarm_latency_after_fill_start_s"
    ] < 11.0
    assert spatial_detector["post_access_descriptive_evidence"] is True
    assert spatial_detector["runtime_application"] is False
    assert spatial_detector["h2safe_gate_changed"] is False
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
    assert tank_validation["common_time_base"] is True
    assert tank_validation["hose_pressure_temperature_present"] is True
    assert tank_validation["per_tank_pressure_temperature_mass_present"] is True
    assert tank_validation["partial_station_to_tank_boundary_eligible"] is True
    assert tank_validation["full_loop_external_holdout_eligible"] is False
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
    assert early["public_reference_leak_detector_evidence"][
        "observation_count"
    ] == 45
    assert early["public_actual_hydrogen_spatial_stratification_evidence"][
        "sensor_case_observation_count"
    ] == 638
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
    assert instrumentation["source_count"] == 3
    assert instrumentation["file_count"] == 15
    assert instrumentation["sample_count"] == 58_440
    assert instrumentation["observed_sampling_intervals_s"] == [0.5]
    assert instrumentation["workbooks_with_mass"] == 6
    assert instrumentation["mass_closure_session_count"] == 18
    assert instrumentation["mass_closure_comparable_session_count"] == 9
    assert instrumentation["mass_closure_non_comparable_session_count"] == 9
    assert instrumentation["mass_closure_screen_pass_count"] == 8
    assert instrumentation["mass_closure_comparable_pass_fraction"] == 8 / 9
    assert instrumentation["station_measurement_auxiliary_eligible"] is True
    assert instrumentation["full_loop_holdout_eligible"] is False
    assert instrumentation["channel_dictionary_present"] is False
    assert instrumentation["group_a_c_vehicle_fill_eligible"] is False
    assert instrumentation["official_test_context"]["group_a_npl"][
        "vehicle_receiving_tank"
    ] is False
    assert instrumentation["official_test_context"]["group_c_engie"][
        "vehicle_receiving_tank"
    ] is False
    assert "do not describe them as vehicle fills" in instrumentation[
        "test_class_interpretation"
    ]
    assert early["public_measurement_instrumentation"][
        "vehicle_or_receptacle_channels_identified"
    ] is False
    assert early["public_measurement_instrumentation"][
        "group_a_c_vehicle_fill_eligible"
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
    mixed_convection = closed_loop["mixed_convection_diagnostic"]
    assert mixed_convection["nozzle_diameter_grid_mm"] == [3.0, 5.0, 7.0]
    assert mixed_convection["constant_ua_temperature_stop_count"] == 7
    assert mixed_convection[
        "mixed_convection_temperature_stop_count_range"
    ] == [5, 5]
    assert mixed_convection["joint_screening_pass_count_range"] == [0, 0]
    assert mixed_convection["runtime_default_changed"] is False
    assert mixed_convection["geometry_selection_prohibited"] is True
    assert mixed_convection["claim_prohibited"] is True
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
    assert header["public_measurement_instrumentation"]["file_count"] == 15
    assert header["public_measurement_instrumentation"]["sample_count"] == 58_440
    assert header["public_measurement_instrumentation"][
        "mass_closure_screen_pass_count"
    ] == 8
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
    assert header["closed_loop_validation_boundary"][
        "mixed_convection_diagnostic"
    ]["joint_screening_pass_count_range"] == [0, 0]
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
        "PUBLIC_METHYTRUCKS_20590903",
        "PUBLIC_HITRF_OPERATIONAL_REFERENCE",
        "PUBLIC_STATION_OPERATION_PRACTICE",
        "PUBLIC_STATION_AGGREGATE_BENCHMARK",
        "PUBLIC_3EMOTION_STATION_OPERATING_AGGREGATE",
        "PUBLIC_HIAD_2_2",
        "KHK_PUBLIC_ACCIDENT_REPORTS",
        "PUBLIC_ACCIDENTAL_RELEASE_ARTICLE",
        "PUBLIC_ACCIDENTAL_RELEASE_DATASET",
        "PUBLIC_DETECTOR_LOGIC_DATASET",
        "PUBLIC_REFERENCE_LEAK_DETECTOR_DATASET",
        "PUBLIC_ACTUAL_H2_SPATIAL_STRATIFICATION_ARTICLE",
        "PUBLIC_GRUNE_VENTILATION_DATASET",
        "PUBLIC_HYTF_TANK_TRACE",
    } <= public_link_ids
    assert all(row["url"].startswith(("https://", "http://")) for row in public_links)
    assert not any("confidential" in row["id"].lower() for row in public_links)
    assert prompt_evidence_summary(idle)["public_source_links"] == public_links
    operation_question = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False,
        question="충전 중 리크체크와 예냉 순서를 설명해줘",
    )
    operation_decision = prompt_decision_evidence(operation_question)
    operation_support = operation_decision["decision_support_evidence"][
        "public_station_operation_practice_reference"
    ]
    assert operation_support["reported_practices"][
        "pre_cooler_setpoint_c"
    ] == -36
    assert operation_support["not_allowed"]
    aggregate_header = header["public_station_aggregate_benchmark_reference"]
    assert aggregate_header["source"]["doi"] == "10.1016/j.ijhydene.2023.04.084"
    assert aggregate_header["reported_aggregate"][
        "refueling_event_count_approx"
    ] == 4500
    assert aggregate_header["reported_aggregate"][
        "dispensed_hydrogen_kg_approx"
    ] == 8800
    assert aggregate_header["not_allowed"]
    assert aggregate_header["claim_limit"]
    aggregate_question = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False,
        question="충전소 운영 처리량과 에너지 실적을 설명해줘",
    )
    aggregate_decision = prompt_decision_evidence(aggregate_question)
    aggregate_support = aggregate_decision["decision_support_evidence"][
        "public_station_aggregate_benchmark_reference"
    ]
    assert aggregate_support["reported_aggregate"][
        "refueling_event_count_approx"
    ] == 4500
    assert aggregate_support["reported_aggregate"][
        "reported_2020_q1_energy_kwh_per_kg_range"
    ] == [70, 80]
    assert aggregate_support["not_allowed"]
    idle_decision = prompt_decision_evidence(idle)
    assert "public_station_aggregate_benchmark_reference" not in idle_decision[
        "decision_support_evidence"
    ]
    threeemotion_header = header[
        "public_threeemotion_operating_aggregate_reference"
    ]
    assert threeemotion_header["source"]["doi"] == (
        "10.1051/e3sconf/202233406008"
    )
    assert threeemotion_header["reported_aggregate"][
        "average_daily_mass_per_bus_kg"
    ] == 12.95
    assert threeemotion_header["reported_aggregate"][
        "station_utilization_below_percent"
    ] == 30
    threeemotion_question = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False,
        question="350 bar 버스 충전소의 처리량과 가동률을 설명해줘",
    )
    threeemotion_decision = prompt_decision_evidence(threeemotion_question)
    threeemotion_support = threeemotion_decision["decision_support_evidence"][
        "public_threeemotion_operating_aggregate_reference"
    ]
    assert threeemotion_support["reported_aggregate"][
        "average_daily_mass_per_bus_kg"
    ] == 12.95
    assert threeemotion_support["not_allowed"]
    assert "public_threeemotion_operating_aggregate_reference" not in (
        idle_decision["decision_support_evidence"]
    )
    assert header["public_reference_leak_detector_evidence"]["joint_pass"] is True
    assert header["public_reference_leak_detector_evidence"][
        "runtime_application"
    ] is False
    assert header[
        "public_actual_hydrogen_spatial_stratification_evidence"
    ]["experiment_count"] == 22
    detector_prompt = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False,
        selected_sensor="GD-0901",
        question="가스 검지기 배치를 분석해줘",
    )
    assert "no runtime or station-map validation" in prompt_decision_evidence(
        detector_prompt
    )["decision_support_evidence"]["detector_placement"]
    assert header["public_accident_evidence"]["public_report_count"] == 23
    assert header["public_accident_evidence"]["hiad_public_source"]["version"] == (
        "HIAD 2.2"
    )
    assert header["public_accident_evidence"]["hiad_public_source"][
        "station_record_count"
    ] == 34
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
    station_thermal = idle["response_evidence"][
        "confidential_station_thermal_dynamics"
    ]
    assert station_thermal["status"] == "UNCONFIRMED"
    assert station_thermal["mapped_channel_family_counts"] == {
        "pressure": 2,
        "temperature": 3,
        "flow": 0,
        "discrete_state": 3,
        "lifecycle": 0,
    }
    assert station_thermal["proposed_engineering_units"]["temperature"] == ["degC"]
    assert station_thermal["proposals_attested"] is False
    assert station_thermal["result_available"] is False
    assert station_thermal["runtime_parameter_application"] is False
    assert station_thermal["full_loop_holdout_eligible"] is False
    assert prompt_evidence_summary(idle)["confidential_station_thermal_dynamics"][
        "station_component_thermal_envelope_supported"
    ] is False
    assert prompt_evidence_header(idle)["confidential_station_thermal_dynamics"][
        "result_available"
    ] is False
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
    local_station = idle["response_evidence"][
        "confidential_local_station_data_utilization"
    ]
    assert local_station["inventory"]["csv_files"] == 33
    assert local_station["inventory"]["deduplicated_data_rows"] == 56_854_143
    assert local_station["inventory"]["header_family_screen"][
        "vehicle_or_dispenser_candidate_files"
    ] == 0
    assert local_station["utilization"]["ordered_high_bank_pressure_cycles"] == 16_770
    assert local_station["utilization"]["short_horizon_pressure_forecast_cases"] == 1_418
    assert local_station["assessment"]["local_station_data_is_sparse"] is False
    assert local_station["assessment"]["vehicle_side_full_loop_validation_ready"] is False
    assert local_station["semantic_attestation"]["storage_pressure_role_count"] == 2
    assert local_station["semantic_attestation"]["flow_units_attested"] is False
    signal_consistency = idle["response_evidence"][
        "confidential_station_signal_consistency"
    ]
    assert signal_consistency["candidate_pairs_evaluated"] == 54
    assert signal_consistency["strong_consistency_pairs"] == 27
    assert signal_consistency["files_with_strong_consistency_pair"] == 17
    assert signal_consistency["strong_pair_aggregate"][
        "correlation_median"
    ] == 0.9970854325653027
    assert signal_consistency["flow_units_attested"] is False
    assert signal_consistency["flow_parameter_fit_supported"] is False
    assert prompt_evidence_summary(idle)[
        "confidential_station_signal_consistency"
    ]["strong_consistency_pairs"] == 27
    assert prompt_evidence_header(idle)[
        "confidential_station_signal_consistency"
    ]["absolute_mass_flow_supported"] is False
    transfer = idle["response_evidence"][
        "confidential_local_station_cross_bundle_transfer"
    ]
    assert transfer["candidate_margin_mpa"] == 4.5
    assert transfer["transfer_bundle"]["cycle_count"] == 225
    assert transfer["candidate_inside_transfer_p05_p95"] is True
    assert transfer["fixed_candidate_corroborated_on_transfer_bundle"] is True
    assert transfer["full_loop_external_validation_supported"] is False
    local_discovery = idle["response_evidence"][
        "confidential_local_station_data_discovery"
    ]
    continuity = local_discovery["candidate_groups"][
        "wide_equipment_continuity_screen"
    ]
    assert continuity["wide_file_count"] == 8
    assert continuity["wide_row_count"] == 653442
    assert continuity["timestamp_parse_failures"] == 0
    assert continuity["negative_interval_count"] == 0
    assert continuity["state_transition_count"] == 3873
    assert continuity["claim_boundary"]
    local_summary = prompt_evidence_summary(idle)[
        "confidential_local_station_data_utilization"
    ]
    assert local_summary["inventory"]["unique_csv_payloads"] == 32
    assert local_summary["inventory"]["header_family_screen"][
        "candidate_file_counts"
    ]["pressure"] == 20
    assert local_summary["semantic_attestation"]["storage_pressure_role_count"] == 2
    local_header = prompt_evidence_header(idle)[
        "confidential_local_station_data_utilization"
    ]
    assert local_header["utilization"]["paired_medium_high_pressure_episodes"] == 11_770
    transfer_summary = prompt_evidence_summary(idle)[
        "confidential_local_station_cross_bundle_transfer"
    ]
    assert transfer_summary["transfer_bundle"]["cycle_count"] == 225
    transfer_header = prompt_evidence_header(idle)[
        "confidential_local_station_cross_bundle_transfer"
    ]
    assert transfer_header["candidate_margin_mpa"] == 4.5
    assert transfer_header["fixed_candidate_corroborated_on_transfer_bundle"] is True
    discovery_header = prompt_evidence_header(idle)[
        "confidential_local_station_data_discovery"
    ]
    continuity_header = discovery_header["candidate_groups"][
        "wide_equipment_continuity_screen"
    ]
    assert continuity_header["wide_file_count"] == 8
    assert continuity_header["timestamp_parse_failures"] == 0
    assert continuity_header["state_transition_count"] == 3873
    local_decision = prompt_decision_evidence(idle)["validation_boundaries"][
        "local_station_data_utilization"
    ]
    assert local_decision["deduplicated_data_rows"] == 56_854_143
    assert local_decision["storage_pressure_roles_attested"] is True
    assert local_decision["station_side_dynamic_validation_ready"] is True
    asset_decision = prompt_decision_evidence(idle)["validation_boundaries"][
        "local_station_asset_screen"
    ]
    assert asset_decision["scenario_step_rows"] == 52
    assert asset_decision["hazop_scenario_coverage_substantial"] is True
    assert asset_decision["vehicle_side_full_loop_validation_ready"] is False
    signal_question = build_evidence_manifest(
        {"time_s": 4.0}, {}, [], False,
        question="충전소 유량과 재충전 데이터를 어떻게 검증했어?",
    )
    signal_decision = prompt_decision_evidence(signal_question)
    assert signal_decision["decision_support_evidence"][
        "confidential_station_signal_consistency"
    ]["strong_consistency_pairs"] == 27
    assert signal_decision["validation_boundaries"][
        "station_signal_consistency"
    ]["flow_units_attested"] is False
    local_asset = idle["response_evidence"][
        "confidential_local_station_asset_screen"
    ]
    assert local_asset["scenario_matrix"]["scenario_step_rows"] == 52
    assert local_asset["scenario_matrix"]["nonempty_consequence_fields"][
        "fire"
    ] == 52
    assert local_asset["coverage"]["local_station_data_is_sparse"] is False
    assert local_asset["coverage"]["vehicle_side_full_loop_validation_ready"] is False
    local_asset_summary = prompt_evidence_summary(idle)[
        "confidential_local_station_asset_screen"
    ]
    assert local_asset_summary["scenario_matrix"][
        "referenced_standard_families"
    ]["KGS"] == 107
    local_asset_header = prompt_evidence_header(idle)[
        "confidential_local_station_asset_screen"
    ]
    assert local_asset_header["asset_bundles"][
        "local_tank_operation_sequence_logs"
    ]["repeated_operation_cycles"] == 10
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
    assert len(benchmarks["sources"]) == 4
    nrel_trace = next(item for item in benchmarks["sources"] if item["id"] == "NREL_HDVS_2022_TANK_HOSE_TRACE")
    assert nrel_trace["aggregate"]["sample_count"] == 351
    assert nrel_trace["raw_rows_public"] is False
    fast_flow = next(item for item in benchmarks["sources"] if item["id"] == "NREL_HD_FAST_FLOW_2024_REPORT")
    assert fast_flow["aggregate"]["peak_mass_flow_g_s"] == 483.33
    assert "untouched row-level full-loop holdout" in fast_flow["not_eligible_for"]
    fch2rail = next(item for item in benchmarks["sources"] if item["id"] == "FCH2RAIL_D61_350BAR_REPORT")
    assert fch2rail["aggregate"]["average_flow_min_g_s"] == 11.54
    assert "70 MPa passenger-vehicle validation" in fch2rail["not_eligible_for"]
    kgs_six = next(item for item in benchmarks["sources"] if item["id"] == "KGS_HRS_SIX_SCENARIO_AGGREGATE_2025")
    assert kgs_six["aggregate"]["reported_scenario_count"] == 6
    assert kgs_six["aggregate"]["pressure_accuracy_r2_mean_percent"] == 96.7
    assert "row-level or untouched full-loop holdout" in kgs_six["not_eligible_for"]

    result = {"node_id": "N09", "node_name": "고압 저장뱅크",
              "calculation_status": "calculated",
              "calculation_basis": "SENSOR_BASED_HYPOTHESIS",
              "pressure_sensor": "PT-0901", "current_pressure_mpa": 88.0,
              "sampled_effect_radius_m": 3.0,
              "literature_delayed_ignition_status": "CALCULATED_EXTRAPOLATED",
              "literature_delayed_ignition_5kpa_radial_distance_m": 4.3,
              "literature_delayed_ignition_distance_origin":
              "CENTRE_OF_25_TO_35_VOL_PERCENT_H2_CLOUD",
              "literature_delayed_ignition_site_safety_distance": False,
              "literature_delayed_ignition_doi": "10.3390/hydrogen3040027",
              "literature_delayed_ignition_claim_limit": "not a site safety distance",
              "literature_jet_flame_status": "CALCULATED_IN_VALIDATION_DOMAIN",
              "literature_jet_flame_length_m": 2.7,
              "literature_jet_flame_mass_flow_basis": "HYRAM_ORIFICE_FLOW",
              "literature_jet_flame_is_harm_distance": False,
              "literature_jet_flame_doi": "10.3801/IAFSS.FSS.10-933",
              "literature_jet_flame_claim_limit": "visible flame length only"}
    calculated = build_evidence_manifest(
        frame, signals, [result], True,
        active_conditions=[{"scenario": "고압 저장뱅크 압력 상승", "sensor_id": "PT-0901",
                            "state": "TRIGGER", "response_plan_id": "overpressure",
                            "response_source_ids": ["HIAD2026", "H2_INCIDENT"]}],
        selected_sensor="PT-0901", question="피해영향은?",
    )
    assert calculated["impact"]["calculation_status"] == "calculated"
    assert calculated["impact"]["results"][0]["pressure_sensor"] == "PT-0901"
    assert calculated["impact"]["results"][0][
        "literature_delayed_ignition_5kpa_radial_distance_m"
    ] == 4.3
    assert calculated["impact"]["results"][0][
        "literature_delayed_ignition_site_safety_distance"
    ] is False
    assert calculated["impact"]["results"][0]["literature_jet_flame_length_m"] == 2.7
    assert calculated["impact"]["results"][0]["literature_jet_flame_is_harm_distance"] is False
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
        "effective_volume_multiplier": None,
        "effective_volume_policy": "single_pass_capacity_eos",
        "public_sensitivity_available": True,
        "default_basis": "reference",
        "capacity_eos_opt_in": True,
        "tank_thermal_model": "constant_ua",
        "mixed_convection_opt_in": False,
        "thermal_geometry": {
            "vehicle_internal_diameter_m": None,
            "vehicle_internal_length_m": None,
            "vehicle_inlet_nozzle_diameter_m": None,
            "vehicle_2_internal_diameter_m": None,
            "vehicle_2_internal_length_m": None,
            "vehicle_2_inlet_nozzle_diameter_m": None,
        },
        "thermal_geometry_complete": False,
        "claim_limit": manifest["runtime_geometry"]["claim_limit"],
    }
    assert prompt_evidence_summary(manifest)["runtime_geometry"]["basis"] == (
        "capacity_eos"
    )


def test_manifest_exposes_qra_method_spread_without_promoting_validation():
    manifest = build_evidence_manifest({"time_s": 2.0}, {}, [], False)
    qra = manifest["response_evidence"]["qra_multimethod_comparison"]

    assert qra["source"]["doi"] == "10.34810/DATA3632"
    assert qra["method_count"] == 7
    assert qra["retained_row_count"] == 211
    assert qra["runtime_thermal_within_envelope_count"] == 2
    assert qra["runtime_overpressure_within_envelope_count"] == 0
    assert qra["experimental_validation"] is False
    assert qra["automatic_calibration_performed"] is False
    dispenser = next(row for row in qra["cases"] if row["equipment"] == "Dispenser")
    assert dispenser["mass_flow_ratio_to_method_median"] > 20.0

    compact = prompt_decision_evidence(manifest)["validation_boundaries"][
        "qra_method_ensemble"
    ]
    assert "simulation-only" in compact
    assert "thermal 2/4" in compact
    assert "overpressure 0/3" in compact
    assert "no automatic tuning" in compact

    summary = prompt_evidence_summary(manifest)["qra_multimethod_comparison"]
    assert summary["matched_group_count"] == 46
    assert summary["maximum_matched_method_ratio"] > 3.3
    links = prompt_evidence_header(manifest)["public_source_links"]
    assert any(row["id"] == "PUBLIC_QRA_MULTIMETHOD_DATA3632" for row in links)


def test_manifest_exposes_mixed_convection_inputs_as_research_only():
    frame = {
        "time_s": 2.0,
        "vehicle_tank_thermal_model": "mixed_convection",
        "vehicle_internal_diameter_m": 0.358,
        "vehicle_internal_length_m": 0.7451,
        "vehicle_inlet_nozzle_diameter_m": 0.005,
        "vehicle_2_internal_diameter_m": 0.358,
        "vehicle_2_internal_length_m": 0.7451,
        "vehicle_2_inlet_nozzle_diameter_m": 0.005,
    }
    manifest = build_evidence_manifest(frame, {}, [], False)
    geometry = manifest["runtime_geometry"]
    assert geometry["tank_thermal_model"] == "mixed_convection"
    assert geometry["mixed_convection_opt_in"] is True
    assert geometry["thermal_geometry_complete"] is True
    assert geometry["thermal_geometry"]["vehicle_inlet_nozzle_diameter_m"] == (
        pytest.approx(0.005)
    )
    assert "미검증 기본값이 아님" in geometry["claim_limit"]

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


def test_compact_data_used_reports_available_and_applied_station_profile():
    base_frame = {
        "time_s": 12.5,
        "process_operations": {
            "settings": {"measured_boundary_calibration": False},
            "trailer_pressure_mpa": 60.0,
        },
    }
    reference = compact_data_used(
        build_evidence_manifest(base_frame, {}, [], False, question="현재 상태")
    )
    calibration = reference["station_calibration"]
    assert calibration["status"] == "reference_defaults"
    assert calibration["requested"] is False
    assert calibration["profile_id"] == "reference_defaults"
    assert calibration["available_profile_id"] == (
        "owner_measured_operational_envelope_v1"
    )
    station_data = reference["station_data"]
    assert station_data["status"] == "substantial_station_side"
    assert station_data["csv_files"] == 33
    assert station_data["deduplicated_rows"] == 56854143
    assert station_data["pressure_cycles"] == 16770
    assert station_data["full_loop_validation"] is False
    endpoint = reference["public_endpoint_benchmark"]
    assert endpoint["source_doi"] == "10.19799/j.cnki.2095-4239.2020.0049"
    assert endpoint["case_count"] == 2
    assert endpoint["time_series_available"] is False
    assert endpoint["full_loop_validation"] is False

    applied_frame = {
        **base_frame,
        "process_operations": {
            **base_frame["process_operations"],
            "settings": {"measured_boundary_calibration": True},
        },
    }
    applied = compact_data_used(
        build_evidence_manifest(applied_frame, {}, [], False, question="현재 상태")
    )["station_calibration"]
    assert applied["status"] == "active"
    assert applied["requested"] is True
    assert applied["profile_id"] == "owner_measured_operational_envelope_v1"
    assert applied["evidence_artifact"]


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


def test_manifest_exposes_claim_bounded_measured_cascade_sequence_holdout():
    manifest = build_evidence_manifest(
        {"time_s": 12.5},
        {},
        [],
        False,
        question="실측에서 중압에서 고압 순서가 확인됐나?",
    )
    evidence = manifest["response_evidence"][
        "confidential_station_cascade_sequence_holdout"
    ]
    assert evidence["files_read"] == 12
    assert evidence["calibration"]["paired_episode_count"] == 8_106
    assert evidence["holdout"]["paired_episode_count"] == 3_664
    assert evidence["holdout"]["pair_coverage_fraction"] == 0.703939
    assert evidence["holdout"]["sequential_fraction"] == 0.943777
    assert evidence["cascade_controller_structure_supported"] is True
    assert evidence["runtime_parameter_application"] is False
    assert evidence["vehicle_fill_validation"] is False
    summary = prompt_evidence_summary(manifest)[
        "confidential_station_cascade_sequence_holdout"
    ]
    assert summary["cascade_controller_structure_supported"] is True
    decision = prompt_decision_evidence(manifest)["validation_boundaries"][
        "station_cascade_sequence"
    ]
    assert decision["claim_supported"] is True
    assert decision["vehicle_fill_validation"] is False
    assert decision["full_loop"] is False
    header = prompt_evidence_header(manifest)[
        "confidential_station_cascade_sequence_holdout"
    ]
    assert header["cascade_controller_structure_supported"] is True
    assert header["independent_external_validation"] is False


def test_manifest_routes_short_horizon_recharge_forecast_only_when_relevant():
    manifest = build_evidence_manifest(
        {"time_s": 12.5},
        {},
        [],
        False,
        question="고압 뱅크 재충전 압력 상승을 예측할 수 있나?",
    )
    evidence = manifest["response_evidence"][
        "confidential_station_recharge_pressure_forecast_holdout"
    ]
    assert evidence["files_read"] == 8
    assert evidence["sampled_rows"] == 653_442
    assert evidence["calibration_case_count"] == 1_024
    assert evidence["holdout_case_count"] == 394
    assert evidence["holdout_metrics"]["median_absolute_error_mpa"] == 0.055
    assert evidence["short_horizon_station_pressure_forecast_supported"] is True
    assert evidence["runtime_parameter_application"] is False
    summary = prompt_evidence_summary(manifest)[
        "confidential_station_recharge_pressure_forecast_holdout"
    ]
    assert summary["vehicle_fill_validation"] is False
    decision = prompt_decision_evidence(manifest)["validation_boundaries"][
        "station_recharge_pressure_forecast"
    ]
    assert decision["claim_supported"] is True
    assert decision["holdout_cases"] == 394
    assert decision["full_loop"] is False
    header = prompt_evidence_header(manifest)[
        "confidential_station_recharge_pressure_forecast_holdout"
    ]
    assert header["independent_external_validation"] is False

    unrelated = build_evidence_manifest(
        {"time_s": 12.5}, {}, [], False, question="화재 검지기 상태는?"
    )
    assert "station_recharge_pressure_forecast" not in (
        prompt_decision_evidence(unrelated)["validation_boundaries"]
    )


def test_manifest_routes_retained_negative_lifecycle_alignment_only_when_relevant():
    manifest = build_evidence_manifest(
        {"time_s": 12.5},
        {},
        [],
        False,
        question="저장 뱅크 완충 압력이 수명 카운터 증가를 검증하나?",
    )
    evidence = manifest["response_evidence"][
        "confidential_station_lifecycle_pressure_alignment_holdout"
    ]
    assert evidence["files"]["pressure_files_read"] == 12
    assert evidence["files"]["counter_files_read"] == 12
    assert evidence["rows"]["pressure_rows_read"] == 29_361_281
    assert evidence["holdout"]["combined"]["counter_event_recall"] == 0.196032
    assert evidence["holdout"]["combined"]["pressure_event_precision"] == 0.902716
    assert evidence["pressure_completion_counter_alignment_supported"] is False
    assert evidence["recharge_event_detector_corroborated"] is False
    assert evidence["runtime_parameter_application"] is False
    assert evidence["vehicle_fill_validation"] is False

    summary = prompt_evidence_summary(manifest)[
        "confidential_station_lifecycle_pressure_alignment_holdout"
    ]
    assert summary["screens"]["holdout_counter_recall_met"] is False
    assert summary["screens"]["recall_stability_met"] is False

    decision = prompt_decision_evidence(manifest)["validation_boundaries"][
        "station_lifecycle_pressure_alignment"
    ]
    assert decision["claim_supported"] is False
    assert decision["recharge_event_detector_corroborated"] is False
    assert decision["calibration_counter_recall"] == 0.170591
    assert decision["holdout_counter_recall"] == 0.196032
    assert decision["holdout_pressure_precision"] == 0.902716
    assert decision["holdout_median_absolute_offset_s"] == 26.0
    assert decision["counter_monotonicity_met"] is False
    assert decision["runtime_parameter_application"] is False
    assert decision["vehicle_fill_validation"] is False
    assert decision["full_loop"] is False

    header = prompt_evidence_header(manifest)[
        "confidential_station_lifecycle_pressure_alignment_holdout"
    ]
    assert header["pressure_completion_counter_alignment_supported"] is False
    assert header["recharge_event_detector_corroborated"] is False
    assert header["independent_external_validation"] is False

    unrelated = build_evidence_manifest(
        {"time_s": 12.5}, {}, [], False, question="화재 검지기 상태는?"
    )
    assert "station_lifecycle_pressure_alignment" not in (
        prompt_decision_evidence(unrelated)["validation_boundaries"]
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
    assert "station_cascade_sequence" not in decision["validation_boundaries"]
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
    assert decision["validation_boundaries"]["station_component_thermal"] == {
        "status": "UNCONFIRMED",
        "proposals_attested": False,
        "component_envelope_supported": False,
    }
    assert len(json.dumps(decision, ensure_ascii=False)) < 3700
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


def test_llm_claim_guard_cannot_be_reenabled_by_stale_full_loop_flags():
    manifest = build_evidence_manifest({"time_s": 12.5}, {}, [], False)
    manifest["full_loop_validation_supported"] = True
    manifest["public_real_station_context"] = {
        "full_loop_external_holdout_eligible": True,
    }
    manifest["closed_loop_validation_boundary"] = {"claim_supported": True}
    answer, audit = guard_llm_claims("충전소-차량 전주기 검증이 완료되었습니다.", manifest)
    assert audit["full_loop_validation_supported"] is False
    assert "전주기 검증이 완료되었습니다" not in answer
    assert "근거 경계" in answer


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
