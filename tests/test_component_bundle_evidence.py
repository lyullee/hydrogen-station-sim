from __future__ import annotations

from h2station.component_bundle_evidence import component_bundle_evidence
from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def _receipt() -> dict:
    return {
        "artifact_type": "controlled_deidentified_hrs_component_bundle_receipt",
        "component_bundle_ready": True,
        "raw_rows_persisted_in_repository": False,
        "runtime_parameter_application": False,
        "full_loop_holdout_eligible": False,
        "event_count": 3,
        "event_summaries": [
            {"rows": 20, "duration_s": 9.5, "min_pressure_mpa_abs": 20.0,
             "max_pressure_mpa_abs": 21.9, "max_mass_flow_g_s": 4.0}
        ] * 3,
        "claim_boundary": "component replay only",
    }


def test_component_receipt_is_sanitized_and_grounded_in_all_prompt_views() -> None:
    receipt = _receipt()
    sanitized = component_bundle_evidence({"component_bundle_receipt": receipt})
    assert sanitized is not None
    assert sanitized["event_count"] == 3
    assert "artifact_type" not in sanitized
    manifest = build_evidence_manifest(
        {"time_s": 1.0, "component_bundle_receipt": receipt}, {}, [], False,
        question="공개 실측 데이터 검증",
    )
    response = manifest["response_evidence"]["confidential_component_bundle"]
    assert response["full_loop_external_validation_supported"] is False
    assert prompt_evidence_summary(manifest)["confidential_component_bundle"]["event_count"] == 3
    decision = prompt_decision_evidence(manifest)["decision_support_evidence"]["confidential_component_bundle"]
    assert decision["station_to_dispenser_boundary_replay_supported"] is True
    assert prompt_evidence_header(manifest)["confidential_component_bundle"]["event_count"] == 3
