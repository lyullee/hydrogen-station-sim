from h2station.llm_grounding import build_evidence_manifest, prompt_evidence_summary


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
