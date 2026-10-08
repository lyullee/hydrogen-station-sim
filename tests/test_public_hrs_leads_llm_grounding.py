from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def test_public_hrs_measurement_leads_are_grounded_with_raw_trace_boundary():
    manifest = build_evidence_manifest(
        {"time_s": 2.0},
        {"PT-0901": {"value": 45.0, "unit": "MPa", "quality": "GOOD"}},
        [],
        False,
        selected_sensor="PT-0901",
        question="공개된 HRS 계측자료와 현재 압력을 비교해줘",
    )
    evidence = manifest["response_evidence"]["public_hrs_measurement_leads"]
    assert len(evidence["leads"]) == 4
    assert all(lead["raw_trace_public"] is False for lead in evidence["leads"])
    assert evidence["full_loop_external_validation_supported"] is False
    assert evidence["parameter_fitting_supported"] is False

    summary = prompt_evidence_summary(manifest)["public_hrs_measurement_leads"]
    assert summary["leads"][0]["reported_scope"]
    assert summary["saga_effectiveness_supported"] is False

    decision = prompt_decision_evidence(manifest)
    decision_leads = decision["decision_support_evidence"][
        "public_hrs_measurement_leads"
    ]
    assert decision_leads["lead_count"] == 4
    assert decision_leads["raw_trace_public_count"] == 0
    assert decision["validation_boundaries"]["public_hrs_measurement_leads"][
        "full_loop_external_validation_ready"
    ] is False

    header = prompt_evidence_header(manifest)["public_hrs_measurement_leads"]
    assert header["evidence_artifact"].endswith(
        "public_hrs_measurement_leads_recheck_2026_10_09.json"
    )
    assert header["saga_effectiveness_supported"] is False

