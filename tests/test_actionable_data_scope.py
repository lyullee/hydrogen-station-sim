from __future__ import annotations

from h2station.llm_grounding import build_evidence_manifest, prompt_decision_evidence


def _manifest():
    return build_evidence_manifest(
        {
            "time_s": 12.0,
            "header_pressure_mpa": 65.0,
            "header_temperature_c": 25.0,
            "header_mass_kg": 40.0,
            "header_inflow_g_s": 0.0,
        },
        {},
        [],
        False,
        question="로컬 충전소 압력 데이터와 공개 실험 데이터를 사용해 분석해줘",
    )


def test_actionable_data_scope_is_privacy_bounded_and_nonempty() -> None:
    manifest = _manifest()
    scope = manifest["response_evidence"]["local_actionable_data_scope"]
    assert scope["runtime_usable_now"]
    assert scope["runtime_usable_now"][0]["holdout_cases"] == 394
    transfer = next(
        item for item in scope["runtime_usable_now"]
        if item["id"] == "station_pressure_cross_bundle_transfer_corroboration"
    )
    assert transfer["transfer_cycles"] == 225
    assert transfer["screen_pass"] is True
    assert transfer["independent_external_validation"] is False
    assert scope["available_but_not_runtime_promoted"][0]["holdout_consistent"] is False
    assert scope["full_loop_holdout"]["synchronized_trace_count"] == 0
    assert scope["artifact"] == "research/local_data_actionable_scope_2026_10_09.json"
    rendered = str(scope)
    assert "raw_rows" not in rendered
    assert "source_paths" not in rendered


def test_decision_prompt_names_usable_data_before_full_loop_boundary() -> None:
    manifest = _manifest()
    decision = prompt_decision_evidence(manifest)
    scope = decision["decision_support_evidence"]["local_actionable_data_scope"]
    assert scope["runtime_usable_now"]
    assert scope["full_loop_holdout"]["synchronized_trace_count"] == 0
