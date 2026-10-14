import pytest

from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_summary,
)


def test_calibrated_confirmatory_diagnostic_is_grounded_as_non_validation():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="현재 상태"
    )

    evidence = manifest["response_evidence"][
        "closed_loop_calibrated_confirmatory_diagnostic"
    ]
    assert evidence["case_count"] == 11
    assert evidence["screening_pass_count"] == 1
    assert evidence["claim_supported"] is False
    assert evidence["promotion_prohibited"] is True
    assert evidence["production_default_changed"] is False

    compact = prompt_evidence_summary(manifest)[
        "closed_loop_calibrated_confirmatory_diagnostic"
    ]
    assert compact["mean_metrics"]["pressure_rmse_mpa"] == 4.190430944003755
    assert "not a new independent holdout" in compact["claim_limit"]


def test_actual_hydrogen_spatial_benchmark_is_grounded_without_promotion():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="공개 수소 공간분포 근거"
    )
    evidence = manifest["response_evidence"][
        "public_actual_hydrogen_spatial_benchmark"
    ]
    assert evidence["source_doi"] == "10.5281/zenodo.4668554"
    assert evidence["license"] == "CC BY 4.0"
    assert evidence["hydrogen_worksheet_count"] == 41
    assert evidence["coordinate_grid_worksheet_count"] == 42
    assert evidence["independent_holdout"] is False
    assert evidence["runtime_parameter_updated"] is False
    assert evidence["promotion_prohibited"] is True
    diagnostic = evidence["post_access_diagnostic"]
    assert diagnostic["hydrogen_profile_count"] == 41
    assert diagnostic["hydrogen_point_count"] == 5148
    assert diagnostic["independent_holdout"] is False
    assert diagnostic["runtime_parameter_updated"] is False
    assert diagnostic["promotion_prohibited"] is True
    assert diagnostic["threshold_aggregates"]["4.0"][
        "median_point_fraction_at_or_above_threshold"
    ] == pytest.approx(0.2777777777777778)
    compact = prompt_evidence_summary(manifest)[
        "public_actual_hydrogen_spatial_benchmark"
    ]
    assert compact["source_doi"] == evidence["source_doi"]
    assert compact["promotion_prohibited"] is True
    decision = prompt_decision_evidence(manifest)
    prompt_spatial = decision["decision_support_evidence"][
        "public_actual_hydrogen_spatial_benchmark"
    ]
    assert prompt_spatial["source_doi"] == evidence["source_doi"]
    assert prompt_spatial["runtime_parameter_updated"] is False
    assert prompt_spatial["promotion_prohibited"] is True
    assert prompt_spatial["post_access_diagnostic"]["hydrogen_point_count"] == 5148


def test_preslhy_actual_hydrogen_transport_diagnostic_is_grounded_without_promotion():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="수소 누출 검지 지연 근거"
    )
    evidence = manifest["response_evidence"][
        "public_preslhy_concentration_transport_diagnostic"
    ]
    assert evidence["source_doi"] == "10.35097/1187"
    assert evidence["trace_count"] == 33
    assert evidence["error_count"] == 0
    assert evidence["documented_transport_delay_s"] == pytest.approx(3.75)
    assert evidence["raw_onset_lag"]["median_s"] == pytest.approx(4.4)
    assert evidence["corrected_onset_lag"]["median_s"] == pytest.approx(0.65)
    assert evidence["runtime_promotion"] is False
    assert evidence["independent_validation_gate_impact"] == "none"
    decision = prompt_decision_evidence(manifest)
    projected = decision["decision_support_evidence"][
        "public_preslhy_concentration_transport_diagnostic"
    ]
    assert projected["corrected_onset_lag"]["median_s"] == pytest.approx(0.65)
    assert projected["runtime_promotion"] is False


def test_usn_orientation_transfer_diagnostic_is_grounded_without_runtime_routing():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="수소 검지기 위치 검증 근거"
    )
    evidence = manifest["response_evidence"][
        "public_usn_orientation_transfer_diagnostic"
    ]
    assert evidence["dataset_doi"] == "10.23642/USN.26117989.v2"
    assert evidence["article_doi"] == "10.1016/j.jlp.2025.105669"
    assert evidence["experiment_count"] == 22
    assert evidence["joint_screen_pass"] is True
    assert evidence["runtime_detector_routing_changed"] is False
    assert evidence["independent_holdout"] is False
    assert evidence["runtime_application"] is False
    projected = prompt_decision_evidence(manifest)["decision_support_evidence"][
        "public_usn_orientation_transfer_diagnostic"
    ]
    assert projected["mean_top5_recall"] == pytest.approx(0.8727272727272729)
    assert projected["gate_changed"] is False


def test_mc_geometry_transfer_diagnostic_is_grounded_without_rule_promotion():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="탱크 모델 검증 상태"
    )
    evidence = manifest["response_evidence"][
        "public_mc_geometry_transfer_diagnostic"
    ]
    assert evidence["status"] == "diagnostic_only"
    assert evidence["geometry_rule_selection_prohibited"] is True
    assert evidence["full_loop_external_validation_ready"] is False


def test_mc_soc_boundary_diagnostic_separates_soc_definition_from_model_error():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="SOC 계측 검증"
    )
    evidence = manifest["response_evidence"]["public_mc_soc_boundary_diagnostic"]
    assert evidence["status"] == "diagnostic_only"
    assert evidence["soc_definition_screen_pass_count"] == 8
    assert evidence["runtime_parameter_application"] is False


def test_mc_tank_boundary_negative_screen_is_explicitly_grounded():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="MC 차량탱크 검증"
    )
    evidence = manifest["response_evidence"][
        "public_mc_tank_boundary_diagnostic"
    ]
    assert evidence["case_count"] == 8
    assert evidence["joint_screening_pass_count"] == 0
    assert evidence["promotion_prohibited"] is True
    compact = prompt_evidence_summary(manifest)[
        "public_mc_tank_boundary_diagnostic"
    ]
    assert compact["aggregate"]["pressure_rmse_mpa_mean"] == 4.375922315837227


def test_mc_capacity_geometry_cross_validation_is_grounded_without_promotion():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="MC 차량탱크 개선 후보"
    )
    evidence = manifest["response_evidence"][
        "public_mc_capacity_geometry_cross_validation"
    ]
    assert evidence["status"] == "development_cross_validation_only"
    assert evidence["fold_count"] == 8
    assert evidence["folds_disjoint"] is True
    assert evidence["joint_screening_pass_count"] == 4
    assert evidence["baseline_comparison"][
        "pressure_rmse_reduction_percent"
    ] > 50.0
    assert evidence["baseline_comparison"][
        "temperature_rmse_reduction_percent"
    ] < 0.0
    assert evidence["external_validation"] is False
    assert evidence["runtime_parameter_application"] is False
    assert evidence["validation_gate_changed"] is False
    assert evidence["promotion_prohibited"] is True
    compact = prompt_evidence_summary(manifest)[
        "public_mc_capacity_geometry_cross_validation"
    ]
    assert compact["joint_screening_pass_fraction"] == 0.5
    assert "temperature" in compact["remaining_limitation"].lower()
    decision = prompt_decision_evidence(manifest)[
        "public_mc_capacity_geometry_cross_validation"
    ]
    assert decision["promotion_prohibited"] is True
    assert decision["validation_gate_changed"] is False


def test_mc_temperature_channel_inventory_is_grounded_without_validation_promotion():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="탱크 온도 층화"
    )
    evidence = manifest["response_evidence"][
        "public_mc_temperature_channel_inventory"
    ]
    assert evidence["case_count"] == 8
    assert evidence["cases_with_individual_channels"] == 8
    assert evidence["runtime_parameter_application"] is False
    assert evidence["full_loop_external_validation_supported"] is False
    assert evidence["claim_supported"] is False
    compact = prompt_evidence_summary(manifest)[
        "public_mc_temperature_channel_inventory"
    ]
    assert compact["stratification_summary"]["maximum_case_peak_spread_c"] == pytest.approx(8.532)


def test_mc_temperature_sensor_envelope_is_grounded_without_operator_selection():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="탱크 온도 센서 열전대 오차"
    )
    evidence = manifest["response_evidence"][
        "public_mc_temperature_sensor_envelope"
    ]
    assert evidence["status"] == "diagnostic_only"
    assert evidence["case_count"] == 8
    assert evidence["observation_operator_selected"] is False
    assert evidence["runtime_parameter_application"] is False
    assert evidence["validation_gate_changed"] is False
    assert evidence["promotion_prohibited"] is True
    assert evidence["raw_rows_exposed"] is False
    gas = evidence["temperature_states"]["gas_temperature"]
    assert gas["inside_envelope_fraction_pooled"] < 0.1
    assert gas["mean_to_envelope_rmse_reduction_percent"] < 10.0
    compact = prompt_evidence_summary(manifest)[
        "public_mc_temperature_sensor_envelope"
    ]
    assert "Sensor spread alone" in compact["finding"]
    decision = prompt_decision_evidence(manifest)[
        "public_mc_temperature_sensor_envelope"
    ]
    assert decision["observation_operator_selected"] is False
    assert decision["promotion_prohibited"] is True


def test_mc_cumulative_mass_sensitivity_is_grounded_without_promotion():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="MC 질량 적분 원인"
    )
    evidence = manifest["response_evidence"][
        "public_mc_cumulative_mass_sensitivity"
    ]
    assert evidence["status"] == "diagnostic_only"
    assert evidence["case_count"] == 8
    assert evidence["joint_screening_pass_count"] == 0
    assert evidence["promotion_prohibited"] is True
    compact = prompt_evidence_summary(manifest)[
        "public_mc_cumulative_mass_sensitivity"
    ]
    assert compact["mass_boundary_mode"] == "cumulative_trapezoid_of_measured_mass_flow"
    assert compact["runtime_parameter_application"] is False


def test_dickens_followup_candidate_is_grounded_without_validation_promotion():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="탱크 열전달 검증"
    )
    evidence = manifest["response_evidence"][
        "public_dickens_geometry_followup_candidate"
    ]
    assert evidence["status"] == "followup_candidate_only"
    assert evidence["selected_diagnostic"]["all_four_frozen_screens_pass"] is True
    assert evidence["full_loop_external_validation_ready"] is False


def test_h2safe_spatial_negative_screen_is_grounded_without_runtime_promotion():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="검지기 공간검증 상태"
    )
    evidence = manifest["response_evidence"]["public_h2safe_spatial_diagnostic"]
    assert evidence["status"] == "diagnostic_only_failed_screen"
    assert evidence["experiment_count"] == 5
    assert evidence["joint_spatial_screen_pass"] is False
    assert evidence["runtime_parameter_application"] is False
    compact = prompt_evidence_summary(manifest)["public_h2safe_spatial_diagnostic"]
    assert compact["promotion_prohibited"] is True
    assert compact["full_loop_external_validation_ready"] is False


def test_h2safe_hvac_input_boundary_is_grounded_without_spatial_promotion():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="H2SAFE 환기 공간 검증 입력 근거"
    )
    evidence = manifest["response_evidence"][
        "public_h2safe_hvac_input_readiness"
    ]
    assert evidence["status"] == "NOT_READY_FOR_PREACCESS_SPATIAL_VALIDATION"
    assert evidence["release_test_count"] == 5
    assert evidence["lab_1_vent_count"] == 10
    assert evidence["lab_2_duct_count"] == 8
    assert evidence["runtime_parameter_application"] is False
    assert evidence["promotion_prohibited"] is True
    assert set(evidence["missing_inputs"]) == {
        "release_direction_vector",
        "ventilation_velocity_vectors",
        "obstruction_geometry",
        "release_to_trace_time_crosswalk",
    }
    compact = prompt_evidence_summary(manifest)[
        "public_h2safe_hvac_input_readiness"
    ]
    assert compact["source_doi"] == "10.7799/17118570"
    assert compact["promotion_prohibited"] is True


def test_h2safe_geometry_containment_is_grounded_without_registration_promotion():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="H2SAFE 형상 좌표 등록 근거"
    )
    evidence = manifest["response_evidence"]["public_h2safe_geometry_containment"]
    assert evidence["status"] == "CONTAINMENT_CONFIRMED_REGISTRATION_UNPROVEN"
    assert evidence["sensor_count"] == 61
    assert evidence["sensor_containment_fraction"] == 1.0
    assert evidence["all_release_points_inside_mesh_bounds"] is True
    assert evidence["runtime_parameter_application"] is False
    assert evidence["preaccess_spatial_validation_ready"] is False
    compact = prompt_evidence_summary(manifest)["public_h2safe_geometry_containment"]
    assert compact["promotion_prohibited"] is True
    assert compact["preaccess_spatial_validation_ready"] is False
    decision = prompt_decision_evidence(manifest)["decision_support_evidence"]
    assert decision["public_h2safe_geometry_containment"]["sensor_count"] == 61


def test_public_actual_h2_channel_dataset_is_grounded_as_component_candidate_only():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="공개 실제 수소 데이터 검증"
    )
    evidence = manifest["response_evidence"]["public_actual_h2_channel_dataset"]
    assert evidence["status"] == "PUBLIC_ACTUAL_H2_DISPERSION_INVENTORY"
    assert evidence["source_doi"].lower() == "10.23642/usn.26117989.v2"
    assert evidence["experiment_count"] == 22
    assert evidence["sensor_count"] == 29
    assert evidence["schema_screen_pass"] is True
    assert evidence["runtime_parameter_application"] is False
    assert evidence["validation_gate_promoted"] is False
    compact = prompt_evidence_summary(manifest)["public_actual_h2_channel_dataset"]
    assert compact["station_to_vehicle_full_loop"] is False
    decision = prompt_decision_evidence(manifest)["decision_support_evidence"]
    assert decision["public_actual_h2_channel_dataset"]["promotion_prohibited"] is True


def test_elvhys_actual_cryogenic_hydrogen_dataset_is_grounded_without_promotion():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="극저온 수소 누출과 점화 근거"
    )
    evidence = manifest["response_evidence"]["public_elvhys_dataset"]
    assert evidence["status"] == "PUBLIC_ELVHYS_ACTUAL_CRYOGENIC_H2_INVENTORY"
    assert evidence["source_doi"] == "10.18710/JXJP0H"
    assert evidence["published_test_plan_count"] == 48
    assert evidence["case_id_count_with_public_data"] == 40
    assert evidence["pressure_peaking_candidate"] is True
    assert evidence["ignition_consequence_candidate"] is True
    assert evidence["runtime_parameter_application"] is False
    compact = prompt_evidence_summary(manifest)["public_elvhys_dataset"]
    assert compact["schema_screen_pass"] is True
    decision = prompt_decision_evidence(manifest)["decision_support_evidence"]
    assert decision["public_elvhys_dataset"]["promotion_prohibited"] is True
