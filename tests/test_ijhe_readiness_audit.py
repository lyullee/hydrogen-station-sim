from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_ijhe_readiness import audit  # noqa: E402


def test_current_evidence_audit_passes_verified_components_and_blocks_completion():
    report = audit(ROOT)
    gates = {item["id"]: item for item in report["gates"]}

    assert gates["tank_external_validation"]["status"] == "PASS"
    assert gates["methytrucks_hysam_postaccess_diagnostic_integrity"]["status"] == "PASS"
    methytrucks = gates["methytrucks_hysam_postaccess_diagnostic_integrity"]["observed"]
    assert methytrucks["workbook_count"] == 3
    assert 0.9 < methytrucks["flow_to_scale_mass_ratio"] < 1.2
    assert methytrucks["candidate_session_aggregate"]["case_count"] == 5
    assert methytrucks["candidate_session_aggregate"]["project_screen"]["joint_pass_count"] == 5
    assert methytrucks["candidate_volume_sensitivity"]["aggregate"]["project_screen"]["joint_pass_count"] == 1
    assert methytrucks["supplementary_mapping_recheck"]["observed_contents"]["channel_dictionary_present"] is False
    assert methytrucks["prospective_holdout_eligible"] is False
    assert methytrucks["quantitative_full_loop_validation_eligible"] is False
    assert gates["methytrucks_complete_public_measurement_intake_integrity"]["status"] == "PASS"
    complete_methytrucks = gates[
        "methytrucks_complete_public_measurement_intake_integrity"
    ]["observed"]
    assert complete_methytrucks["aggregate"]["workbook_count"] == 15
    assert complete_methytrucks["aggregate"]["sample_count"] == 58_440
    assert complete_methytrucks["aggregate"]["mass_closure_screen_pass_count"] == 8
    assert complete_methytrucks["eligibility"]["prospective_holdout_eligible"] is False
    assert complete_methytrucks["eligibility"][
        "full_loop_station_vehicle_validation_eligible"
    ] is False
    assert gates["methytrucks_group_d_prospective_intake_integrity"]["status"] == "PASS"
    group_d = gates["methytrucks_group_d_prospective_intake_integrity"]["observed"]
    assert group_d["decision"] == "MODEL_SCREEN_NOT_RUN_INELIGIBLE_METADATA"
    assert group_d["sample_count"] == 720
    assert group_d["sampling_interval_s"] == 0.5
    assert group_d["model_executed"] is False
    assert group_d["full_loop_external_validation_supported"] is False
    assert gates["byrnes_typei_thermal_prospective_intake_integrity"]["status"] == "PASS"
    byrnes = gates["byrnes_typei_thermal_prospective_intake_integrity"]["observed"]
    assert byrnes["decision"] == "PROTOCOL_INVALID_PRIOR_OUTCOME_ACCESS"
    assert byrnes["file_count"] == 3
    assert byrnes["resolved_case_count"] == 0
    assert byrnes["mapping_failure_count"] == 6
    assert byrnes["model_executed"] is False
    assert byrnes["thermal_external_validation_supported"] is False
    assert gates["public_tank_runtime_calibration_integrity"]["status"] == "PASS"
    tank_runtime = gates["public_tank_runtime_calibration_integrity"]["observed"]
    assert tank_runtime["runtime"]["api_default_mode"] == "public_type_iv"
    assert tank_runtime["runtime"]["validation_case_count"] == 12
    assert tank_runtime["sources_match"] is True
    assert tank_runtime["recheck_matches"] is True
    assert gates[
        "confidential_station_cascade_sequence_holdout_integrity"
    ]["status"] == "PASS"
    cascade = gates[
        "confidential_station_cascade_sequence_holdout_integrity"
    ]["observed"]
    assert cascade["protocol_hash_matches"] is True
    assert cascade["calibration"]["paired_episode_count"] == 8_106
    assert cascade["holdout"]["paired_episode_count"] == 3_664
    assert cascade["holdout"]["sequential_fraction"] == 0.943777
    assert cascade["decision"]["vehicle_fill_validation"] is False
    assert cascade["decision"]["full_loop_holdout_eligible"] is False
    assert gates[
        "confidential_station_recharge_pressure_forecast_holdout_integrity"
    ]["status"] == "PASS"
    recharge_forecast = gates[
        "confidential_station_recharge_pressure_forecast_holdout_integrity"
    ]["observed"]
    assert recharge_forecast["protocol_hash_matches"] is True
    assert recharge_forecast["calibration"]["case_count"] == 1_024
    assert recharge_forecast["holdout"]["case_count"] == 394
    assert recharge_forecast["holdout"]["combined"][
        "median_absolute_error_mpa"
    ] == 0.055
    assert recharge_forecast["decision"]["runtime_parameter_application"] is False
    assert recharge_forecast["decision"]["vehicle_fill_validation"] is False
    assert gates[
        "confidential_station_lifecycle_pressure_alignment_negative_result_integrity"
    ]["status"] == "PASS"
    lifecycle_alignment = gates[
        "confidential_station_lifecycle_pressure_alignment_negative_result_integrity"
    ]["observed"]
    assert lifecycle_alignment["protocol_hash_matches"] is True
    assert lifecycle_alignment["rows"]["pressure_rows_read"] == 29_361_281
    assert lifecycle_alignment["rows"]["counter_rows_read"] == 26_839_420
    assert lifecycle_alignment["counter_quality"][
        "negative_chronological_steps"
    ] == 2
    assert lifecycle_alignment["calibration"]["combined"][
        "counter_event_recall"
    ] == 0.170591
    assert lifecycle_alignment["holdout"]["combined"][
        "counter_event_recall"
    ] == 0.196032
    assert lifecycle_alignment["holdout"]["combined"][
        "pressure_event_precision"
    ] == 0.902716
    assert lifecycle_alignment["decision"][
        "pressure_completion_counter_alignment_supported"
    ] is False
    assert lifecycle_alignment["decision"][
        "recharge_event_detector_corroborated"
    ] is False
    assert lifecycle_alignment["decision"]["runtime_parameter_application"] is False
    assert lifecycle_alignment["decision"]["vehicle_fill_validation"] is False
    assert gates[
        "local_confidential_station_data_utilization_integrity"
    ]["status"] == "PASS"
    local_data = gates[
        "local_confidential_station_data_utilization_integrity"
    ]["observed"]
    assert local_data["inventory"]["csv_files"] == 33
    assert local_data["inventory"]["unique_csv_payloads"] == 32
    assert local_data["inventory"]["deduplicated_data_rows"] == 56_854_143
    assert local_data["utilization"]["ordered_high_bank_pressure_cycles"] == 16_770
    assert local_data["utilization"]["paired_medium_high_pressure_episodes"] == 11_770
    assert local_data["utilization"]["short_horizon_pressure_forecast_cases"] == 1_418
    assert local_data["assessment"]["local_station_data_is_sparse"] is False
    assert local_data["assessment"]["vehicle_side_full_loop_validation_ready"] is False
    assert local_data["utilization"]["semantic_attestation"][
        "storage_pressure_role_count"
    ] == 2
    assert local_data["utilization"]["semantic_attestation"][
        "flow_units_attested"
    ] is False
    assert gates["local_cross_station_bundle_recheck_integrity"]["status"] == "PASS"
    cross_station = gates["local_cross_station_bundle_recheck_integrity"]["observed"]
    assert cross_station["bundle_count"] == 2
    assert [item["file_count"] for item in cross_station["bundles"]] == [25, 8]
    assert [item["data_rows"] for item in cross_station["bundles"]] == [58_618_858, 653_442]
    assert cross_station["station_side_transfer_candidate"] is True
    assert cross_station["full_loop_external_validation_supported"] is False
    assert gates["local_station_asset_screen_integrity"]["status"] == "PASS"
    local_assets = gates["local_station_asset_screen_integrity"]["observed"]
    assert local_assets["scenario_step_rows"] == 52
    assert local_assets["nonempty_consequence_fields"]["fire"] == 52
    assert local_assets["referenced_standard_families"]["KGS"] == 107
    assert local_assets["coverage"]["vehicle_side_full_loop_validation_ready"] is False
    assert local_assets["coverage"]["quantitative_consequence_validation_ready"] is False
    assert gates["dickens_typeiii_prospective_validation"]["status"] == "FAIL"
    dickens = gates["dickens_typeiii_prospective_validation"]["observed"]
    assert dickens["protocol_frozen_before_outcome_access"] is True
    assert dickens["screen_results"]["pressure_rmse_mpa"] is True
    assert dickens["screen_results"]["gas_temperature_rmse_k"] is False
    assert dickens["joint_primary_screen_pass"] is False
    assert dickens["retained_negative_result"] is True
    assert gates["dickens_mixed_convection_diagnostic_integrity"]["status"] == "PASS"
    mixed = gates["dickens_mixed_convection_diagnostic_integrity"]["observed"]
    assert mixed["run_count"] == 3
    assert mixed["joint_primary_screen_passes"] == 3
    assert mixed["runtime_parameter_updated"] is False
    assert mixed["validation_gate_effect"] == "none"
    assert gates[
        "woodfield_heat_transfer_development_integrity"
    ]["status"] == "PASS"
    woodfield = gates[
        "woodfield_heat_transfer_development_integrity"
    ]["observed"]
    assert woodfield["fill_pressure_rmse_reduction_percent"] > 20.0
    assert woodfield["fill_temperature_envelope_rmse_reduction_percent"] > 60.0
    assert woodfield["discharge_path_unchanged"] is True
    assert woodfield["conservation_pass"] is True
    assert woodfield["maximum_mass_residual_relative"] < 1.0e-9
    assert woodfield["maximum_energy_residual_relative"] < 1.0e-9
    assert woodfield["runtime_parameter_updated"] is False
    assert woodfield["validation_gate_effect"] == "none"
    assert gates["hyram_adapter_verification"]["status"] == "PASS"
    assert gates["molkov_jet_flame_literature_benchmark"]["status"] == "PASS"
    molkov = gates["molkov_jet_flame_literature_benchmark"]["observed"]
    assert molkov["experimental_case_count_reported"] == 123
    assert molkov["benchmark_case_count"] == 25
    assert molkov["mean_absolute_percentage_error"] < 20.0
    assert molkov["within_30_percent_fraction"] >= 0.80
    assert molkov["implementation_hash_matches"] is True
    assert molkov["thermal_harm_distance"] is False
    assert molkov["site_safety_distance"] is False
    assert gates[
        "hydrogen_blend_dispersion_negative_result_integrity"
    ]["status"] == "PASS"
    blend_holdout = gates[
        "hydrogen_blend_dispersion_negative_result_integrity"
    ]["observed"]
    assert blend_holdout["execution_classification"] == (
        "PROSPECTIVE_ENDPOINTS_POST_ACCESS_FORMAT_REPAIR"
    )
    assert blend_holdout["joint_primary_screen_pass"] is False
    assert blend_holdout["claim_supported"] is False
    assert gates["hytunnel_carpark_execution_integrity"]["status"] == "PASS"
    hytunnel_integrity = gates["hytunnel_carpark_execution_integrity"]["observed"]
    assert hytunnel_integrity["raw_file_count"] == 18
    assert hytunnel_integrity["amendment_count"] == 5
    assert hytunnel_integrity["failure_count"] == 0
    assert gates["hytunnel_carpark_dispersion_validation"]["status"] == "FAIL"
    hytunnel_dispersion = gates["hytunnel_carpark_dispersion_validation"]["observed"]
    assert hytunnel_dispersion["eligible_case_count"] == 18
    assert hytunnel_dispersion["pass_count"] == 6
    assert hytunnel_dispersion["joint_screen_pass"] is False
    assert gates["hytunnel_carpark_mass_flow_validation"]["status"] == "FAIL"
    hytunnel_mass_flow = gates["hytunnel_carpark_mass_flow_validation"]["observed"]
    assert hytunnel_mass_flow["eligible_case_count"] == 5
    assert hytunnel_mass_flow["pass_count"] == 3
    assert hytunnel_mass_flow["joint_screen_pass"] is False
    assert gates["elvhys_auxiliary_replay_integrity"]["status"] == "PASS"
    assert gates["elvhys_auxiliary_replay_integrity"]["observed"]["case_count"] == 3
    assert gates["elvhys_auxiliary_replay_integrity"]["observed"][
        "predictive_model_validation_permitted"
    ] is False
    assert gates["elvhys_dataverse_metadata_integrity"]["status"] == "PASS"
    assert gates["elvhys_dataverse_metadata_integrity"]["observed"]["file_count"] == 198
    assert gates["elvhys_dataverse_metadata_integrity"]["observed"][
        "full_loop_station_vehicle_holdout_eligible"
    ] is False
    assert gates["elvhys_detector_holdout_failure_integrity"]["status"] == "PASS"
    elvhys_holdout = gates["elvhys_detector_holdout_failure_integrity"]["observed"]
    assert elvhys_holdout["v1_status"] == "FAIL"
    assert elvhys_holdout["v2_status"] == "FAIL"
    assert elvhys_holdout["baseline_eligible_case_count"] == 14
    assert elvhys_holdout["selected_case_count"] == 15
    assert elvhys_holdout["failed_case_ids"] == [44]
    assert elvhys_holdout["confirmatory_validation_eligible"] is False
    assert gates["preoutcome_design_sensitivity"]["status"] == "PASS"
    assert gates["full_loop_external_validation"]["status"] == "FAIL"
    group_d_full_loop = gates["full_loop_external_validation"]["observed"][
        "methytrucks_group_d_prospective_intake"
    ]
    assert group_d_full_loop["decision"] == "MODEL_SCREEN_NOT_RUN_INELIGIBLE_METADATA"
    assert group_d_full_loop["full_loop_external_validation_supported"] is False
    rheadhy_pretrace = gates["full_loop_external_validation"]["observed"][
        "rheadhy_public_test_matrix_pretrace"
    ]
    assert rheadhy_pretrace["record_doi"] == "10.5281/zenodo.16992589"
    assert rheadhy_pretrace["planned_total_test_count"] == 300
    assert rheadhy_pretrace["machine_readable_test_result_dataset_found"] is False
    assert rheadhy_pretrace["trace_level_protocol_frozen"] is True
    assert rheadhy_pretrace["full_loop_external_validation_supported"] is False
    assert gates[
        "rheadhy_public_test_matrix_pretrace_protocol_integrity"
    ]["status"] == "PASS"
    rheadhy_protocol_gate = gates[
        "rheadhy_public_test_matrix_pretrace_protocol_integrity"
    ]["observed"]
    assert rheadhy_protocol_gate["aggregate_outcomes_already_public"] is True
    assert rheadhy_protocol_gate["raw_time_series_inspected"] is False
    assert rheadhy_protocol_gate["eligibility"][
        "full_loop_external_validation_supported"
    ] is False
    assert gates["public_dispenser_table_download_integrity"]["status"] == "PASS"
    assert gates["green_hysland_trailer_context_integrity"]["status"] == "PASS"
    green = gates["green_hysland_trailer_context_integrity"]["observed"]
    assert green["required_trailer_rows"] is True
    assert green["hrs_provisional_populated"] is False
    assert green["full_loop_external_holdout_eligible"] is False
    assert gates["mendeley_hrs_simulation_dataset_boundary_integrity"]["status"] == "PASS"
    mendeley = gates["mendeley_hrs_simulation_dataset_boundary_integrity"]["observed"]
    assert mendeley["doi"] == "10.17632/mnjs94yzfc.1"
    assert mendeley["cc_by_4_present"] is True
    assert mendeley["simulation_only"] is True
    assert mendeley["full_loop_external_holdout_eligible"] is False
    assert gates["metrohyve_gravimetric_hrs_metrology_boundary_integrity"]["status"] == "PASS"
    metrohyve = gates["metrohyve_gravimetric_hrs_metrology_boundary_integrity"]["observed"]
    assert metrohyve["doi"] == "10.1016/j.flowmeasinst.2020.101743"
    assert metrohyve["component_flow_metrology_eligible"] is True
    assert metrohyve["full_loop_external_holdout_eligible"] is False
    assert gates["multhyfuel_d24_public_experiment_integrity"]["status"] == "PASS"
    multhyfuel = gates["multhyfuel_d24_public_experiment_integrity"]["observed"]
    assert multhyfuel["pdf_pages"] >= 25
    assert multhyfuel["jetfire_700bar_measured_flow_g_s"] == 40.0
    assert multhyfuel["internal_700bar_0_2mm_flow_g_s"] == 9.0
    assert multhyfuel["consequence_benchmark_eligible"] is True
    assert multhyfuel["full_loop_station_vehicle_holdout_eligible"] is False
    assert multhyfuel["saga_effectiveness_eligible"] is False
    assert gates["real_station_article_boundary_integrity"]["status"] == "PASS"
    field_article = gates["real_station_article_boundary_integrity"]["observed"]
    assert field_article["reported_sensor_count"] == 8
    assert field_article["full_loop_external_holdout_eligible"] is False
    assert gates["zbt_hrs_sampling_article_boundary_integrity"]["status"] == "PASS"
    zbt_article = gates["zbt_hrs_sampling_article_boundary_integrity"]["observed"]
    assert zbt_article["storage_banks"] == 7
    assert zbt_article["dispensing_pressure_classes_mpa"] == [35, 70]
    assert zbt_article["raw_synchronized_rows_public"] is False
    assert zbt_article["full_loop_external_holdout_eligible"] is False
    assert gates["llm_evidence_grounding_contract"]["status"] == "PASS"
    assert any(
        "flow-boundary mismatches" in item
        for item in gates["llm_evidence_grounding_contract"]["observed"]["verified_properties"]
    )
    station_thermal = gates["llm_evidence_grounding_contract"]["observed"][
        "confidential_station_thermal_dynamics_boundary"
    ]
    assert station_thermal["status"] == "UNCONFIRMED"
    assert station_thermal["proposals_attested"] is False
    assert station_thermal["result_available"] is False
    assert station_thermal["runtime_parameter_application"] is False
    assert station_thermal["full_loop_holdout_eligible"] is False
    grounding_carb = gates["llm_evidence_grounding_contract"]["observed"][
        "public_carb_hrs_inuse_field_benchmark"
    ]
    assert grounding_carb["stations_tested"] == 22
    assert grounding_carb["stations_passing_all_hgv_4_3_tests"] == 0
    assert grounding_carb["invalid_crc_fail_count"] == 8
    assert grounding_carb["dynamic_model_validation_claimed"] is False
    assert grounding_carb["full_loop_external_holdout_eligible"] is False
    assert gates["public_hitrf_operational_reference_integrity"]["status"] == "PASS"
    hitrf = gates["public_hitrf_operational_reference_integrity"]["observed"]
    assert hitrf["raw_synchronized_logger_public"] is False
    assert hitrf["storage_tiers"] == ["high_pressure", "low_pressure", "medium_pressure"]
    assert hitrf["compression_stage_count"] == 4
    assert gates["carb_hrs_inuse_field_benchmark_integrity"]["status"] == "PASS"
    carb = gates["carb_hrs_inuse_field_benchmark_integrity"]["observed"]
    assert carb["source_hash_verified"] is True
    assert carb["stations_tested"] == 22
    assert carb["stations_passing_all_hgv_4_3_tests"] == 0
    assert carb["invalid_crc_results"] == [13, 8, 1]
    assert carb["data_loss_results"] == [15, 4, 3]
    assert carb["dynamic_model_parameter_calibration"] is False
    assert carb["full_loop_external_holdout"] is False
    assert gates["kgs_real_station_access_boundary_integrity"]["status"] == "PASS"
    kgs_access = gates["kgs_real_station_access_boundary_integrity"]["observed"]
    assert kgs_access["reported_real_hrs_scenarios"] == 6
    assert kgs_access["access_result"] == "REDIRECTED_TO_SIGN_IN"
    assert kgs_access["full_loop_station_vehicle_holdout_eligible"] is False
    assert gates["nbsdc_current_access_recheck_integrity"]["status"] == "PASS"
    nbsdc = gates["nbsdc_current_access_recheck_integrity"]["observed"]
    assert nbsdc["cstr"] == "CSTR:16666.11.nbsdc.aI3fJrzX"
    assert nbsdc["file_count"] == 3
    assert nbsdc["raw_probe_codes"] == [403, 403, 403]
    assert nbsdc["full_loop_public_holdout"] is False
    assert gates["jetfire_supplement_rights_boundary_integrity"]["status"] == "PASS"
    jetfire = gates["jetfire_supplement_rights_boundary_integrity"]["observed"]
    assert jetfire["reported_test_count"] == 17
    assert jetfire["article_open_access"] is False
    assert jetfire["full_loop_external_holdout_eligible"] is False
    assert gates["calstate_back_to_back_article_boundary_integrity"]["status"] == "PASS"
    calstate_b2b = gates["calstate_back_to_back_article_boundary_integrity"]["observed"]
    assert calstate_b2b["article_open_access"] is False
    assert calstate_b2b["public_raw_synchronized_rows"] is False
    assert calstate_b2b["full_loop_external_holdout_eligible"] is False
    assert gates["nrel_h2fills_workbook_provenance_integrity"]["status"] == "PASS"
    assert gates["nrel_hdvs_raw_trace_boundary_integrity"]["status"] == "PASS"
    nrel_boundary = gates["nrel_hdvs_raw_trace_boundary_integrity"]["observed"]
    assert nrel_boundary["nonempty_timed_row_count"] == 351
    assert nrel_boundary["tank_ids"] == [1, 2, 3, 5, 7, 8, 9]
    assert nrel_boundary["full_loop_external_holdout_eligible"] is False
    assert gates["fch2rail_d61_operating_range_boundary_integrity"]["status"] == "PASS"
    fch2rail = gates["fch2rail_d61_operating_range_boundary_integrity"]["observed"]
    assert fch2rail["average_flow_range_g_s"] == [11.54, 19.44]
    assert fch2rail["synchronized_raw_full_loop_holdout_eligible"] is False
    assert gates["fch2rail_ijhe_measurement_access_boundary_integrity"]["status"] == "PASS"
    fch2rail_ijhe = gates["fch2rail_ijhe_measurement_access_boundary_integrity"]["observed"]
    assert fch2rail_ijhe["doi"] == "10.1016/j.ijhydene.2025.04.040"
    assert fch2rail_ijhe["machine_readable_rows_publicly_linked"] is False
    assert fch2rail_ijhe["synchronized_raw_full_loop_holdout_eligible"] is False
    assert gates["public_dispenser_endpoint_diagnostic"]["status"] == "PASS"
    assert gates["grune_ventilation_measurement_inventory"]["status"] == "PASS"
    grune_inventory = gates["grune_ventilation_measurement_inventory"]["observed"]
    assert grune_inventory["profile_count"] == 42
    assert grune_inventory["spatial_point_count"] == 5256
    assert grune_inventory["source_identity_all_match"] is True
    assert gates["grune_ventilation_empirical_envelope_integrity"]["status"] == "PASS"
    grune_envelope = gates["grune_ventilation_empirical_envelope_integrity"]["observed"]
    assert grune_envelope["profiles_used"] == 42
    assert grune_envelope["factor_count"] == 42
    assert grune_envelope["raw_rows_committed"] is False
    assert gates["h2safe_full_scale_indoor_surrogate_intake_integrity"]["status"] == "PASS"
    h2safe = gates["h2safe_full_scale_indoor_surrogate_intake_integrity"]["observed"]
    assert h2safe["doi"] == "10.7799/17118570"
    assert h2safe["case_count"] == 5
    assert h2safe["lab_sensor_coordinate_counts"] == {"Lab-1": 24, "Lab-2": 37}
    assert h2safe["all_trace_columns_coordinate_mapped"] is True
    assert h2safe["hydrogen_threshold_calibration"] is False
    assert h2safe["full_loop_station_vehicle_validation"] is False
    assert h2safe["runtime_parameter_updated"] is False
    assert gates["h2safe_spatial_detector_transfer_validation"]["status"] == "FAIL"
    spatial_stratification = gates[
        "actual_hydrogen_spatial_stratification_evidence"
    ]
    assert spatial_stratification["status"] == "PASS"
    spatial_observed = spatial_stratification["observed"]
    assert spatial_observed["test_gas"] == "hydrogen"
    assert spatial_observed["experiment_count"] == 22
    assert spatial_observed["sensor_count_per_experiment"] == 29
    assert spatial_observed["sensor_case_observation_count"] == 638
    assert spatial_observed["top_alarm_coverage_fraction"] == 1.0
    assert spatial_observed["top_trip_coverage_fraction"] == 1.0
    assert spatial_observed["near_source_bottom_alarm_latency_s"] < 11.0
    assert spatial_observed["post_access_descriptive_evidence"] is True
    assert spatial_observed["runtime_application"] is False
    assert spatial_observed["h2safe_gate_changed"] is False
    reference_detector = gates["physical_hydrogen_reference_leak_detector_response"]
    assert reference_detector["status"] == "PASS"
    assert reference_detector["observed"]["observation_count"] == 45
    assert reference_detector["observed"]["series_count"] == 3
    assert reference_detector["observed"]["joint_pass"] is True
    assert reference_detector["observed"]["runtime_application"] is False
    assert reference_detector["observed"]["spatial_detector_transfer_gate_changed"] is False
    h2safe_spatial = gates["h2safe_spatial_detector_transfer_validation"]["observed"]
    assert h2safe_spatial["experiment_count"] == 5
    assert h2safe_spatial["median_spearman"] > 0.5
    assert h2safe_spatial["screens"]["mean_top5_recall_at_least_0_6"] is False
    assert h2safe_spatial["joint_pass"] is False
    hydelta_holdout = h2safe_spatial["hydelta_actual_hydrogen_holdout"]
    assert hydelta_holdout["audit_integrity"] is True
    assert hydelta_holdout["status"] == "INELIGIBLE_NO_MODEL_EVALUATION"
    assert hydelta_holdout["eligible"] is False
    assert hydelta_holdout["model_evaluation_executed"] is False
    assert hydelta_holdout["runtime_candidate_enabled"] is False
    assert set(hydelta_holdout["failed_required_fields"]) == {
        "source_coordinates",
        "sensor_coordinates_in_same_frame",
        "release_orientation_class",
        "per_sensor_numeric_response",
    }
    sandia = h2safe_spatial["sandia_actual_hydrogen_external_diagnostic"]
    assert sandia["audit_integrity"] is True
    assert sandia["status"] == "EXTERNAL_POST_ACCESS_DIAGNOSTIC_NOT_VALIDATION"
    assert sandia["sensor_count"] == 6
    assert sandia["baseline_spearman_rho"] == 0.6
    assert sandia["candidate_spearman_rho"] > 0.94
    assert sandia["top3_recall"] == 1.0
    assert sandia["independent_validation_pass"] is False
    assert sandia["runtime_candidate_enabled"] is False
    hytunnel_spatial = h2safe_spatial["hytunnel_actual_hydrogen_holdout"]
    assert hytunnel_spatial["audit_integrity"] is True
    assert hytunnel_spatial["dataset_doi"] == "10.23642/USN.14405903"
    assert hytunnel_spatial["experiment_count"] == 18
    assert hytunnel_spatial["median_spearman"] > 0.55
    assert hytunnel_spatial["spearman_at_least_0_4_fraction"] > 0.8
    assert 0.57 < hytunnel_spatial["mean_top5_recall"] < 0.6
    assert hytunnel_spatial["nearest_in_response_quartile_fraction"] > 0.94
    assert hytunnel_spatial["screens"]["mean_top5_recall_at_least_0_6"] is False
    assert hytunnel_spatial["joint_screen_pass"] is False
    assert hytunnel_spatial["runtime_candidate_enabled"] is False
    assert gates["hytunnel_spatial_holdout_execution_integrity"]["status"] == "PASS"
    assert gates["dataverse_hydrogen_explosion_component_inventory"]["status"] == "PASS"
    explosion_inventory = gates["dataverse_hydrogen_explosion_component_inventory"]["observed"]
    assert explosion_inventory["dois"] == [
        "10.18710/WSKBIJ", "10.18710/X044QK", "10.23642/USN.17934047"
    ]
    assert explosion_inventory["experiment_counts"] == {
        "10.18710/WSKBIJ": 51,
        "10.18710/X044QK": 40,
        "10.23642/USN.17934047": None,
    }
    assert explosion_inventory["license_set"] == ["CC BY 4.0", "CC0 1.0"]
    assert explosion_inventory["ignited_sample_sigma_shape"] == [999999, 7]
    assert gates["x044qk_overpressure_rank_holdout_intake_integrity"]["status"] == "PASS"
    x044 = gates["x044qk_overpressure_rank_holdout_intake_integrity"]["observed"]
    assert x044["selected_case_count"] == 6
    assert x044["decision"] == (
        "MODEL_SCREEN_NOT_RUN_INELIGIBLE_UNCALIBRATED_PRESSURE_VOLTAGE"
    )
    assert x044["dynamic_pressure_channel_count"] == 4
    assert set(x044["dynamic_pressure_units"]) == {"V"}
    assert x044["outcome_window_opened"] is False
    assert x044["pressure_peak_outcomes_computed"] is False
    assert x044["hyram_model_executed"] is False
    assert x044["runtime_parameter_updated"] is False
    assert x044["validation_gate_effect"] == "none"
    assert gates["wskbij_large_scale_overpressure_rank_execution_integrity"]["status"] == "PASS"
    wskbij = gates["wskbij_large_scale_overpressure_rank_execution_integrity"]["observed"]
    assert wskbij["dataset_doi"] == "10.18710/WSKBIJ"
    assert wskbij["decision"] == "FAIL"
    assert wskbij["scored_case_count"] == 44
    assert wskbij["retained_stratum_count"] == 6
    assert wskbij["pooled_spearman"] > 0.57
    assert wskbij["within_stratum_spearman"] < 0.0
    assert wskbij["pairwise_concordance"] < 0.5
    assert wskbij["top_third_recall"] < 0.3
    assert wskbij["model_validation_pass"] is False
    assert wskbij["runtime_parameter_updated"] is False
    assert wskbij["apparatus_aware_model_eligible"] is False
    assert wskbij["absolute_overpressure_model_eligible"] is False
    assert wskbij["missing_apparatus_field_count"] >= 10
    assert wskbij["apparatus_metadata_decision"] == "INSUFFICIENT_PUBLIC_METADATA_FOR_APPARATUS_AWARE_MODEL"
    assert wskbij["raw_schema_campaign_count"] == 2
    assert gates["ignited_pressure_peaking_external_validation"]["status"] == "PASS"
    ignited_pressure = gates["ignited_pressure_peaking_external_validation"]["observed"]
    assert ignited_pressure["eligible_case_count"] == 27
    assert ignited_pressure["excluded_case_count"] == 0
    assert ignited_pressure["primary_pass_count"] == 27
    assert ignited_pressure["confirmatory_rule_met"] is True
    assert ignited_pressure["peak_overpressure_mae_kpa"] < 0.7
    assert gates["hiad_action_evidence_integrity"]["status"] == "PASS"
    assert gates["hiad_action_evidence_integrity"]["observed"]["case_count"] == 34
    assert gates["hiad_digital_twin_replay_traceability"]["status"] == "PASS"
    hiad_replay = gates["hiad_digital_twin_replay_traceability"]["observed"]
    assert hiad_replay["aggregate"]["case_count"] == 34
    assert hiad_replay["aggregate"]["integration_trace_pass_count"] == 34
    assert hiad_replay["aggregate"]["representation_case_counts"] == {
        "direct_physical_replay": 29,
        "proxy_partial_replay": 4,
        "response_only_no_physical_model": 1,
        "unmapped": 0,
    }
    assert hiad_replay["runtime"]["family_recipe_pass_count"] == 9
    assert hiad_replay["source_hashes_match"] is True
    assert hiad_replay["public_response_text_used"] is False
    assert hiad_replay["case_narrative_used_for_physical_parameters"] is False
    assert gates["hiad_accident_response_coverage_evaluation"]["status"] == "PASS"
    accident_response = gates["hiad_accident_response_coverage_evaluation"]["observed"]
    assert accident_response["aggregate"]["case_count"] == 34
    assert accident_response["aggregate"]["covered_category_count"] == 8
    assert accident_response["aggregate"]["uncovered_case_category_count"] == 0
    assert accident_response["contract"]["raw_action_text_used"] is False
    assert accident_response["contract"]["effectiveness_claimed"] is False
    assert accident_response["source_hashes_match"] is True
    assert gates["hiad_retrospective_machine_response_benchmark_integrity"]["status"] == "PASS"
    hiad_machine = gates[
        "hiad_retrospective_machine_response_benchmark_integrity"
    ]["observed"]
    assert hiad_machine["case_count"] == 34
    assert hiad_machine["response_count"] == 68
    assert hiad_machine["saga_linked"]["failed_call_count"] == 0
    assert hiad_machine["saga_linked"]["unsupported_claim_response_count"] == 3
    assert hiad_machine["expert_effectiveness_claimed"] is False
    assert gates["hiad_direct_numeric_guard_recheck_integrity"]["status"] == "PASS"
    hiad_guard = gates["hiad_direct_numeric_guard_recheck_integrity"]["observed"]
    assert gates["saga_measurement_guard_equivalence_integrity"]["status"] == "PASS"
    measurement_guard = gates["saga_measurement_guard_equivalence_integrity"][
        "observed"
    ]
    assert measurement_guard["runtime"]["provider_calls"] == 0
    assert measurement_guard["aggregate"]["case_count"] == 5
    assert measurement_guard["aggregate"]["pass_count"] == 5
    assert measurement_guard["aggregate"]["equivalent_grounded_case_count"] == 4
    assert measurement_guard["aggregate"]["unsupported_rejection_case_count"] == 1
    assert hiad_guard["outcome"]["before_unsupported_claim_response_count"] == 3
    assert hiad_guard["outcome"]["after_unsupported_claim_response_count"] == 0

    assert gates["hiad_response_selectivity_robustness_integrity"]["status"] == "PASS"
    selectivity = gates["hiad_response_selectivity_robustness_integrity"]["observed"]
    assert selectivity["source"]["new_provider_calls"] == 0
    assert selectivity["cohort"]["reference_evaluable_event_count"] == 33
    assert selectivity["reference_f1_difference"]["mean_paired_difference"] > 0
    assert hiad_guard["outcome"]["after_provider_failure_count"] == 0
    assert hiad_guard["outcome"]["guard_notice_response_count"] == 5
    stop_reason_counts = gates["public_dispenser_endpoint_diagnostic"]["observed"]["stop_reason_counts"]
    assert isinstance(stop_reason_counts, dict)
    assert sum(stop_reason_counts.values()) == 2
    assert gates["accidental_release_ignition_public_evidence"]["status"] == "PASS"
    accidental = gates["accidental_release_ignition_public_evidence"]["observed"]
    assert accidental["zenodo_doi"] == "10.5281/zenodo.17913628"
    assert accidental["license"] == "CC BY 4.0"
    assert accidental["file_count"] == 3
    assert accidental["eligibility"]["full_loop_station_vehicle_holdout_eligible"] is False
    assert gates["khk_public_accident_report_inventory"]["status"] == "PASS"
    khk = gates["khk_public_accident_report_inventory"]["observed"]
    assert khk["coverage"]["pdf_report_count"] == 23
    assert khk["coverage"]["incident_code_count"] == 26
    assert khk["coverage"]["precaution_report_count"] == 8
    assert khk["rights_and_mirroring"]["raw_pdf_mirrored"] is False
    assert khk["eligibility"]["full_loop_station_vehicle_holdout_eligible"] is False
    assert gates["preslhy_blowdown_external_validation"]["status"] == "PASS"
    assert gates["preslhy_blowdown_external_validation"]["observed"]["aggregate"][
        "joint_primary_pass_fraction"
    ] == 8 / 11
    assert gates["preslhy_partb_ambient_external_validation"]["status"] == "FAIL"
    partb = gates["preslhy_partb_ambient_external_validation"]["observed"]
    assert partb["eligibility"]["eligible_cases"] == 5
    assert partb["aggregate"]["joint_primary_pass_fraction"] == 0.6
    assert partb["aggregate"]["ambient_cryostat_part_b_claim_supported"] is False
    assert partb["protocol_hash_matches"] is True
    assert gates["preslhy_partb_input_interpretation_audit"]["status"] == "PASS"
    partb_input = gates["preslhy_partb_input_interpretation_audit"]["observed"]
    assert partb_input["checks"]["all_checks_pass"] is True
    assert gates["preslhy_revised_holdout_validation"]["status"] == "FAIL"
    revised = gates["preslhy_revised_holdout_validation"]["observed"]
    assert revised["primary_cases"] == 3
    assert revised["aggregate"]["joint_primary_passes"] == 2
    assert revised["aggregate"]["minimum_requirements_met"] is False
    assert revised["aggregate"]["claim_supported"] is False
    assert revised["protocol_hash_matches"] is True
    assert gates["preslhy_e31_80k_holdout_intake_integrity"]["status"] == "PASS"
    e31_80k = gates["preslhy_e31_80k_holdout_intake_integrity"]["observed"]
    assert e31_80k["observed"]["workbooks_read"] == 7
    assert e31_80k["observed"]["temperature_values_measured"] == 7
    assert e31_80k["observed"]["ambient_pressure_values_measured"] == 0
    assert e31_80k["source"]["raw_rows_persisted"] is False
    assert e31_80k["protocol_hash_matches"] is True
    assert gates["proust_independent_release_validation"]["status"] == "FAIL"
    proust = gates["proust_independent_release_validation"]["observed"]
    assert proust["aggregate"]["series"] == 3
    assert proust["aggregate"]["joint_primary_passes"] == 0
    assert proust["aggregate"]["minimum_requirements_met"] is True
    assert proust["aggregate"]["claim_supported"] is False
    assert proust["protocol_hash_matches"] is True
    assert proust["data_hash_matches"] is True
    assert gates["release_network_development_integrity"]["status"] == "PASS"
    assert gates["apparatus_resolved_holdout_executor_integrity"]["status"] == "PASS"
    apparatus = gates["apparatus_resolved_holdout_executor_integrity"]["observed"]
    assert apparatus["template_case_count"] == 8
    assert apparatus["target_campaign_outcome_data_accessed"] is False
    assert apparatus["external_validation_status"] == "NOT_ESTABLISHED"
    assert gates["partial_station_profile_diagnostic_integrity"]["status"] == "PASS"
    partial = gates["partial_station_profile_diagnostic_integrity"]["observed"]
    assert partial["case_count"] == 8
    assert partial["screening_pass_count"] == 0
    assert partial["protocol"]["fresh_holdout"] is False
    assert gates["mc_source_schedule_diagnostic_integrity"]["status"] == "PASS"
    mc_partial = gates["mc_source_schedule_diagnostic_integrity"]["observed"]
    assert mc_partial["case_count"] == 8
    assert mc_partial["screening_pass_count"] == 1
    assert mc_partial["protocol"]["fresh_holdout"] is False
    assert gates["mc_tank_boundary_diagnostic_integrity"]["status"] == "PASS"
    mc_tank = gates["mc_tank_boundary_diagnostic_integrity"]["observed"]
    assert mc_tank["aggregate"]["case_count"] == 8
    assert mc_tank["evidence_role"] == "development_diagnostic_only"
    assert mc_tank["post_outcome"] is True
    assert mc_tank["parameter_fitting"] is False
    assert gates["mc_enthalpy_pressure_sensitivity_integrity"]["status"] == "PASS"
    mc_enthalpy = gates["mc_enthalpy_pressure_sensitivity_integrity"]["observed"]
    assert mc_enthalpy["run_count"] == 3
    assert mc_enthalpy["case_counts"] == [8, 8, 8]
    assert gates["confidential_operational_envelope_calibration_integrity"]["status"] == "PASS"
    operational = gates["confidential_operational_envelope_calibration_integrity"]["observed"]
    assert operational["sampled_rows"] == 10896
    assert operational["recharge_restart_margin_pa"] == 540000.0
    assert operational["simulated_samples"] == 121
    assert operational["esd_triggered"] is False
    assert operational["holdout_calibration_points"] == 998
    assert operational["holdout_points"] == 30
    assert operational["holdout_trajectory_completed"] is True
    assert operational["holdout_fit_used"] is False
    assert operational["holdout_full_loop_validation"] is False
    assert operational["cross_station_profile_count"] == 2
    assert operational["cross_station_pressure_overlap_mpa"] == {
        "min": 56.295,
        "max": 63.36,
    }
    assert gates["confidential_station_equipment_drift_integrity"]["status"] == "PASS"
    drift = gates["confidential_station_equipment_drift_integrity"]["observed"]
    assert drift["matches"] is False
    assert drift["profile_replaced"] is False
    assert drift["default_model_parameters_changed"] is False
    assert drift["mismatch_requires_custodian_review"] is True
    assert operational["cross_station_pressure_plausibility"] is True
    assert operational["cross_station_full_loop_validation"] is False
    recharge = gates[
        "confidential_recharge_multitrace_negative_result_integrity"
    ]
    assert recharge["status"] == "PASS"
    recharge_observed = recharge["observed"]
    assert recharge_observed["files_read"] == 8
    assert recharge_observed["calibration_completed_off_to_on_intervals"] == 89
    assert recharge_observed["candidate_minimum_recharge_off_time_s"] == 290.0
    assert recharge_observed["holdout_completed_off_to_on_intervals"] == 32
    assert recharge_observed["holdout_minimum_off_to_on_s"] == 176.0
    assert recharge_observed["dwell_consistent"] is False
    assert recharge_observed["runtime_parameter_application"] is False
    assert recharge_observed["prior_single_trace_profile_superseded"] is True
    assert recharge_observed["full_station_vehicle_validation"] is False
    pressure_band = gates[
        "confidential_recharge_pressure_band_diagnostic_integrity"
    ]
    assert pressure_band["status"] == "PASS"
    pressure_observed = pressure_band["observed"]
    assert pressure_observed["completed_high_stage_restarts"] == 124
    assert pressure_observed["stop_to_restart_pressure_drop_mpa"] == {
        "p10": 4.36,
        "median": 4.555,
    }
    assert pressure_observed["high_bank_restart_margin_default_mpa"] == 4.5
    assert pressure_observed["minimum_time_dwell_applied"] is False
    assert pressure_observed["independent_holdout"] is False
    assert pressure_observed["full_station_vehicle_validation"] is False
    assert gates["confidential_operational_profile_recheck_integrity"]["status"] == "PASS"
    recheck = gates["confidential_operational_profile_recheck_integrity"]["observed"]
    assert recheck["matches"] is True
    assert recheck["sampled_rows"] == 10896
    assert recheck["profile_replaced"] is False
    assert recheck["opt_in_only"] is True
    assert recheck["full_loop_claim"] is True
    assert gates["confidential_station_channel_quality_integrity"]["status"] == "PASS"
    channel_quality = gates["confidential_station_channel_quality_integrity"]["observed"]
    assert channel_quality["files_read"] == 8
    assert channel_quality["sampled_rows"] == 1092
    assert channel_quality["parseable_timestamp_fraction"] == 1.0
    assert channel_quality["timebase"]["negative_interval_count"] == 0
    assert channel_quality["temperature_or_flow_parameter_fit_supported"] is False
    assert channel_quality["full_loop_holdout_eligible"] is False
    assert gates["confidential_station_schema_intake_integrity"]["status"] == "PASS"
    schema = gates["confidential_station_schema_intake_integrity"]["observed"]
    assert schema["source_bundle_count"] == 2
    assert schema["tagged_channel_counts"]["pressure"] > 0
    assert schema["privacy_bounded_channel_families"]["compressor_pressure"] > 0
    assert schema["vehicle_side_channel_family_count"] == 0
    assert schema["unit_attestation"]["pressure_units_attested"] is False
    assert schema["full_loop_holdout_eligible"] is False

    signal = gates["confidential_signal_consistency_integrity"]
    assert signal["status"] == "PASS"
    signal_observed = signal["observed"]
    assert signal_observed["sampled_rows"] == 3_053_442
    assert signal_observed["candidate_pairs_evaluated"] == 54
    assert signal_observed["strong_consistency_pairs"] == 27
    assert signal_observed["files_with_strong_consistency_pair"] == 17
    assert signal_observed["strong_pair_aggregate"]["correlation_median"] >= 0.99
    assert signal_observed["attestation"]["flow_units_attested"] is False
    assert signal_observed["eligibility"]["absolute_mass_flow_supported"] is False
    assert signal_observed["eligibility"]["full_station_vehicle_validation"] is False

    recharge = gates["confidential_recharge_flow_consistency_integrity"]
    assert recharge["status"] == "PASS"
    recharge_observed = recharge["observed"]
    assert recharge_observed["sampled_rows"] == 567_847
    assert recharge_observed["eligible_recharge_episodes"] == 733
    assert recharge_observed["anonymous_valve_mode_count"] == 4
    assert recharge_observed["reference_model"][
        "inside_conditional_observed_p10_p90"
    ] is True
    assert recharge_observed["eligibility"][
        "runtime_parameter_update_permitted"
    ] is False
    assert recharge_observed["eligibility"][
        "full_station_vehicle_validation"
    ] is False

    thermal = gates["confidential_station_thermal_hypothesis_integrity"]
    assert thermal["status"] == "PASS"
    thermal_observed = thermal["observed"]
    assert thermal_observed["protocol_hash_matches"] is True
    assert thermal_observed["calibration_rows"] == 457_405
    assert thermal_observed["holdout_rows"] == 196_037
    assert all(thermal_observed["component_checks"].values())
    assert thermal_observed["cooler_drop_check"] is True
    assert thermal_observed["mapping_semantics"]["mapping_is_hypothesis"] is True
    assert thermal_observed["eligibility"][
        "station_component_thermal_envelope_supported"
    ] is False
    assert thermal_observed["eligibility"]["runtime_parameter_application"] is False
    history = gates["confidential_station_longitudinal_history_integrity"]
    assert history["status"] == "PASS"
    history_observed = history["observed"]
    assert history_observed["files_read"] == 25
    assert history_observed["raw_data_rows"] == 58_618_833
    assert history_observed["sampled_rows"] == 97_709
    assert history_observed["median_sample_period_s"] == 1.0
    assert history_observed["schema_coverage_overlap_fraction"] == 0.997837
    assert all(history_observed["pressure_flow"]["stability_checks"].values())
    assert history_observed["pressure_flow"]["order_checks"][
        "ordered_group_1"
    ] == 0.999142
    assert all(history_observed["thermal"]["stability_checks"].values())
    assert all(
        value == 1.0
        for value in history_observed["thermal"][
            "plausible_range_fractions"
        ].values()
    )
    assert history_observed["attestation"][
        "flow_totalizer_roles_attested"
    ] is False
    assert history_observed["attestation"]["temperature_roles_attested"] is False
    assert history_observed["eligibility"][
        "station_side_longitudinal_diagnostic_supported"
    ] is True
    assert history_observed["eligibility"]["runtime_parameter_application"] is False
    assert history_observed["eligibility"]["vehicle_fill_validation"] is False
    assert schema["flat_time_axis_candidate_summary"]["candidate_groups"] == 4
    assert schema["flat_time_axis_candidate_summary"][
        "tables_in_candidate_groups"
    ] == 26
    assert schema["synchronized_flat_full_loop_candidate"] == 0
    overlap = schema["time_overlap_candidate_summary"]
    assert overlap["absolute_clock_table_count"] == 33
    assert overlap["multi_table_cluster_count"] == 12
    assert overlap["tables_in_clusters"] == 24
    assert overlap["largest_cluster_tables"] == 3
    assert overlap["exact_full_loop_cluster_count"] == 0
    assert overlap["path_assisted_candidate_count"] == 0
    assert overlap["path_semantics_are_unattested"] is True
    assert schema["time_overlap_full_loop_candidate"] == 0
    release_development = gates["release_network_development_integrity"]["observed"]
    assert release_development["evidence_role"] == "consumed_development_only"
    assert release_development["eligible_as_confirmatory_validation"] is False
    assert release_development["interpretation"]["claim_supported"] is False
    assert gates["schefer_transient_release_validation"]["status"] == "FAIL"
    schefer = gates["schefer_transient_release_validation"]["observed"]
    assert schefer["result"]["points"] == 25
    assert schefer["result"]["nrmse_screen_pass"] is True
    assert schefer["result"]["median_ape_screen_pass"] is False
    assert schefer["result"]["half_peak_time_screen_pass"] is False
    assert schefer["protocol_hash_matches"] is True
    assert schefer["data_hash_matches"] is True
    assert gates["schefer_2007_pressure_decay_validation"]["status"] == "FAIL"
    schefer_2007 = gates["schefer_2007_pressure_decay_validation"]["observed"]
    assert schefer_2007["result"]["points"] == 222
    assert schefer_2007["result"]["nrmse_screen_pass"] is False
    assert schefer_2007["result"]["median_ape_screen_pass"] is False
    assert schefer_2007["result"]["half_pressure_time_screen_pass"] is True
    assert schefer_2007["protocol_hash_matches"] is True
    assert schefer_2007["data_hash_matches"] is True
    assert gates["jankuj_pressure_decay_diagnostic_integrity"]["status"] == "PASS"
    jankuj = gates["jankuj_pressure_decay_diagnostic_integrity"]["observed"]
    assert jankuj["status"] == "INVALIDATED_PRIOR_OUTCOME_ACCESS"
    assert jankuj["evidence_role"] == "post_access_diagnostic_only"
    assert jankuj["protocol"]["prospective_protocol_valid"] is False
    assert jankuj["prior_outcome_access"]["matches_current_workbook"] is True
    assert jankuj["joint_primary_screen_pass"] is False
    assert jankuj["source_depletion_transfer_validation_supported"] is False
    assert gates["grune_2014_pressure_decay_validation"]["status"] == "PENDING"
    grune = gates["grune_2014_pressure_decay_validation"]["observed"]
    assert grune["eligibility"]["minimum_requirements_met"] is False
    assert grune["eligibility"]["measured_half_pressure_time_observed"] is False
    assert grune["result"]["points"] == 51
    assert grune["hashes_match"] is True
    assert gates["ekoto_transient_release_validation"]["status"] == "PASS"
    ekoto = gates["ekoto_transient_release_validation"]["observed"]
    assert ekoto["result"]["points"] == 39
    assert ekoto["result"]["nrmse_screen_pass"] is True
    assert ekoto["result"]["median_ape_screen_pass"] is True
    assert ekoto["result"]["half_peak_time_screen_pass"] is True
    assert ekoto["protocol_hash_matches"] is True
    assert ekoto["data_hash_matches"] is True
    external = gates["full_loop_external_validation"]["observed"]
    assert external["protocol_integrity"] is True
    assert external["aggregate"]["case_count"] == 8
    assert external["aggregate"]["screening_pass_count"] == 0
    assert external["aggregate"]["screening_pass_fraction"] == 0.0
    assert (
        external["new_external_data_search"]["status"]
        == "NO_ELIGIBLE_PUBLIC_RAW_SET_IDENTIFIED"
    )
    assert gates["institutional_ethics_determination"]["status"] == "PENDING"
    assert gates["runtime_public_accident_precedent_routing"]["status"] == "PASS"
    precedent = gates["runtime_public_accident_precedent_routing"]["observed"]
    assert precedent["aggregate"]["public_report_count"] == 23
    assert precedent["aggregate"]["manifest_routing_failure_count"] == 0
    assert precedent["source_hashes_match"] is True
    assert gates[
        "hydelta_controlled_flare_response_grounding_integrity"
    ]["status"] == "PASS"
    flare = gates[
        "hydelta_controlled_flare_response_grounding_integrity"
    ]["observed"]
    assert flare["doi"] == "10.5281/zenodo.20817291"
    assert flare["runtime_checks"]["idle_compact_prompt_omits_flare"] is True
    assert flare["runtime_checks"]["active_compact_prompt_includes_flare"] is True
    assert flare["runtime_use"]["station_release_model_validation"] is False

    assert gates["khk_digital_twin_replay_traceability"]["status"] == "PASS"
    khk_replay = gates["khk_digital_twin_replay_traceability"]["observed"]
    assert khk_replay["aggregate"]["public_report_count"] == 23
    assert khk_replay["aggregate"]["incident_code_count"] == 26
    assert khk_replay["aggregate"]["integration_trace_pass_report_count"] == 22
    assert khk_replay["aggregate"]["integration_trace_pass_incident_code_count"] == 25
    assert khk_replay["aggregate"]["out_of_scope_report_count"] == 1
    assert khk_replay["runtime"]["family_recipe_pass_count"] == 8
    assert khk_replay["source_hashes_match"] is True
    assert khk_replay["model_hashes_match"] is True
    assert khk_replay["claims"]["physics_validation_claimed"] is False
    assert gates["hiad_casebook_machine_preflight_integrity"]["status"] == "PASS"
    assert gates["independent_expert_review_complete"]["status"] == "PENDING"
    assert gates["ijhe_latex_compilation"]["status"] == "PASS"
    compile_result = gates["ijhe_latex_compilation"]["observed"]
    assert compile_result["pdf"]["page_count"] == 23
    assert compile_result["compile_log"]["unresolved_citations"] == 0
    assert compile_result["compile_log"]["unresolved_references"] == 0
    assert compile_result["audit_integrity"]["source_hash_matches"] is True
    assert compile_result["audit_integrity"]["pdf_hash_matches"] is True
    assert report["bounded_ijhe_submission_ready"] is False
    assert report["full_user_objective_ready"] is False
    assert report["goal_completion_permitted"] is False


def test_full_objective_gate_is_stricter_than_bounded_submission_gate():
    report = audit(ROOT)
    bounded = set(report["blocking_bounded_submission_gates"])
    full = set(report["blocking_full_objective_gates"])
    assert bounded < full
    assert "full_loop_external_validation" in full - bounded
    assert "saga_effectiveness_and_safety_supported" in full - bounded
    geometry = next(
        gate for gate in report["gates"]
        if gate["id"] == "station_consequence_geometry_validation"
    )
    assert geometry["status"] == "PASS"
