from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def _manifest(question: str):
    return build_evidence_manifest(
        {"time_s": 1.0, "header_pressure_mpa": 44.0},
        {},
        [],
        False,
        question=question,
    )


def test_vehicle_side_lead_is_available_with_full_loop_boundary() -> None:
    manifest = _manifest("차량 탱크 압력과 HRS 유량계 질량을 비교할 공개 데이터가 있나?")
    evidence = manifest["response_evidence"][
        "public_vehicle_side_h2_measurement_leads"
    ]
    assert evidence["leads"][0]["article_doi"] == "10.3390/en17071510"
    assert evidence["full_loop_external_validation_supported"] is False
    decision = prompt_decision_evidence(manifest)
    lead = decision["validation_boundaries"]["vehicle_side_measurement_lead"]
    assert lead["claim_supported"] is False
    assert lead["full_loop"] is False
    assert "synchronized timestamped" in " ".join(lead["next_access_request"])
    summary = prompt_evidence_summary(manifest)[
        "public_vehicle_side_h2_measurement_leads"
    ]
    assert summary["parameter_fitting_supported"] is False
    header = prompt_evidence_header(manifest)[
        "public_vehicle_side_h2_measurement_leads"
    ]
    assert header["full_loop_external_validation_supported"] is False


def test_vehicle_side_lead_is_omitted_from_unrelated_compact_prompt() -> None:
    decision = prompt_decision_evidence(_manifest("화재 검지기 상태는?"))
    assert "vehicle_side_measurement_lead" not in decision["validation_boundaries"]
