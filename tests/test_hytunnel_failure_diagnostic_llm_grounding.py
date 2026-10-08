from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def _manifest():
    return build_evidence_manifest(
        {
            "time_s": 10.0,
            "header_pressure_mpa": 70.0,
            "header_temperature_c": 25.0,
            "header_mass_kg": 1.0,
            "nozzle_flow_g_s": 0.0,
        },
        {},
        [],
        False,
        question="공개 실제 수소 데이터 검증 결과와 한계를 설명해줘",
    )


def test_hytunnel_failure_diagnostic_is_grounded_without_runtime_calibration():
    manifest = _manifest()
    evidence = manifest["response_evidence"]["public_hytunnel_failure_diagnostic"]

    assert evidence["holdout"]["dispersion_joint_screen_pass"] is False
    assert evidence["holdout"]["mass_flow_joint_screen_pass"] is False
    assert evidence["claim_supported"] is False
    assert evidence["runtime_parameter_application"] is False
    assert evidence["default_model_parameters_changed"] is False
    assert evidence["regimes"]["short_release_cases"]["case_count"] == 12

    summary = prompt_evidence_summary(manifest)["public_hytunnel_failure_diagnostic"]
    assert summary["claim_supported"] is False
    assert summary["regimes"]["long_blowdown_cases"]["case_count"] == 6

    decision = prompt_decision_evidence(manifest)
    boundary = decision["validation_boundaries"]["public_hytunnel_carpark"]
    assert boundary["claim_supported"] is False
    assert boundary["dispersion_joint_screen_pass"] is False
    assert boundary["runtime_parameter_application"] is False

    header = prompt_evidence_header(manifest)
    assert header["public_hytunnel_failure_diagnostic"]["claim_supported"] is False
    assert any(
        link["id"] == "PUBLIC_HYTUNNEL_CARPARK_RAW_TIMESERIES"
        for link in header["public_source_links"]
    )
