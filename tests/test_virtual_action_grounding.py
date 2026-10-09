from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_summary,
)


def test_virtual_response_actions_are_available_to_llm_with_effectiveness_boundary():
    manifest = build_evidence_manifest(
        {"time_s": 10.0, "nozzle_flow_g_s": 0.0},
        {},
        [],
        False,
        question="가스 누출 시 가상 안전조치를 실행하고 결과를 확인해줘",
        selected_sensor="GD-0801",
    )
    evidence = manifest["response_evidence"][
        "virtual_response_action_execution_consistency"
    ]
    assert evidence["runtime"]["family_count"] == 9
    assert evidence["runtime"]["family_pass_count"] == 9
    assert evidence["simulation_only"] is True
    assert evidence["saga_effectiveness_supported"] is False
    compact = prompt_decision_evidence(manifest)["decision_support_evidence"][
        "virtual_response_action_execution_consistency"
    ]
    assert compact["runtime"]["all_family_sequences_passed"] is True
    assert compact["operator_benefit_supported"] is False
    summary = prompt_evidence_summary(manifest)[
        "virtual_response_action_execution_consistency"
    ]
    assert summary["failure_feedback_guard"]["feedback_status"] == "failed"
