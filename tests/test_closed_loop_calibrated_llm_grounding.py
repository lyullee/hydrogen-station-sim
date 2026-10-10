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
