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
    assert triage["open_gate_count"] == 17
    assert triage["data_volume_is_primary_blocker"] is False
    assert triage["next_actions"]

    decision = prompt_decision_evidence(manifest)["validation_gap_triage"]
    assert decision["primary_blocker"]
    assert decision["bucket_counts"]["full_loop_data"]["FAIL"] == 1

    summary = prompt_evidence_summary(manifest)["validation_gap_triage"]
    assert summary["claim_limit"]
    header = prompt_evidence_header(manifest)["validation_gap_triage"]
    assert header["open_gate_count"] == 17
    assert "\\research\\" not in str(header)
