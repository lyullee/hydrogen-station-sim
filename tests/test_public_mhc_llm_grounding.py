from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_summary,
)
from h2station.local_evidence import public_evidence_inventory_summary


def test_mhc_experiment16_inventory_is_claim_bounded():
    evidence = public_evidence_inventory_summary()["public_mhc_component_screen"]

    assert evidence["status"] == "available"
    assert evidence["source_doi"] == "10.5281/zenodo.18213166"
    assert evidence["experiment_id"] == "Experiment 16"
    assert evidence["record_count"] == 1186
    assert evidence["schema_screen_pass"] is True
    assert evidence["direct_runtime_model_compatibility"] is False
    assert evidence["runtime_parameter_application"] is False
    assert evidence["full_loop_external_holdout_eligible"] is False
    assert "HRS full loop" in evidence["claim_limit"]


def test_mhc_experiment16_is_grounded_for_component_questions_only():
    manifest = build_evidence_manifest(
        {"time_s": 1.0},
        {},
        [],
        False,
        question="압축기 구성요소 공개 검증 데이터와 논문 근거를 설명해줘",
    )

    raw = manifest["response_evidence"]["public_mhc_component_screen"]
    compact = prompt_evidence_summary(manifest)["public_mhc_component_screen"]
    decision = prompt_decision_evidence(manifest)["decision_support_evidence"][
        "public_mhc_component_screen"
    ]
    for projection in (raw, compact, decision):
        assert projection["source_doi"] == "10.5281/zenodo.18213166"
        assert projection["runtime_parameter_application"] is False
        assert projection["full_loop_external_holdout_eligible"] is False
        assert "Experiment 16.xlsx" not in str(projection)
        assert "source_sha256" not in str(projection)


def test_mhc_experiment16_is_omitted_from_unrelated_idle_prompt():
    manifest = build_evidence_manifest(
        {"time_s": 1.0}, {}, [], False, question="현재 온도 상태는 정상인가?"
    )

    assert "public_mhc_component_screen" not in prompt_decision_evidence(manifest)[
        "decision_support_evidence"
    ]
