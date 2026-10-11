from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def test_llm_receives_privacy_bounded_validation_gap_next_actions() -> None:
    manifest = build_evidence_manifest(
        {"time_s": 1.0, "header_pressure_mpa": 20.0},
        {"PT-1": {"value": 20.0, "unit": "MPa", "quality": "GOOD"}},
        [],
        False,
        question="공개 실험 데이터와 검증 공백을 알려줘",
    )

    triage = manifest["validation_gap_triage"]
    assert triage["status"] == "available"
    assert triage["artifact_integrity"] is True
    assert triage["open_gate_count"] == 16
    assert triage["data_volume_is_primary_blocker"] is False
    assert triage["next_actions"]
    assert triage["execution_tracks"][0]["priority"] == "P0"
    assert triage["next_actions"][0]["parallel_track"] == "component_model_repairs"
    assert triage["scope_exclusions"][0]["id"] == "full_loop_external_validation"
    assert triage["next_actions"][0]["why_now"]

    decision = prompt_decision_evidence(manifest)["validation_gap_triage"]
    assert decision["primary_blocker"]
    assert "full_loop_data" not in decision["bucket_counts"]

    summary = prompt_evidence_summary(manifest)["validation_gap_triage"]
    assert summary["claim_limit"]
    header = prompt_evidence_header(manifest)["validation_gap_triage"]
    assert header["open_gate_count"] == 16
    assert "\\research\\" not in str(header)

    source_pressure = manifest["response_evidence"][
        "public_mc_source_pressure_boundary_diagnostic"
    ]
    assert source_pressure["status"] == "diagnostic_only"
    assert len(source_pressure["runs"]) == 3
    assert source_pressure["promotion_prohibited"] is True
    assert "not independent external" in source_pressure["claim_limit"].lower()
