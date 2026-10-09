from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def test_public_ignited_pressure_peaking_result_is_grounded_with_component_boundary():
    manifest = build_evidence_manifest(
        {"time_s": 10.0, "nozzle_flow_g_s": 0.0},
        {},
        [],
        False,
        question="화재와 과압 피해영향을 공개 실험 근거와 함께 설명해줘",
    )
    evidence = manifest["response_evidence"][
        "public_ignited_pressure_peaking_validation"
    ]
    assert evidence["source"]["dataset_doi"] == "10.23642/USN.17934047"
    assert evidence["aggregate"]["eligible_case_count"] == 27
    assert evidence["aggregate"]["primary_pass_count"] == 27
    assert evidence["aggregate"]["confirmatory_rule_met"] is True
    assert evidence["component_validation_supported"] is True
    assert evidence["station_vehicle_full_loop_supported"] is False
    assert evidence["saga_effectiveness_supported"] is False

    decision = prompt_decision_evidence(manifest)
    compact = decision["decision_support_evidence"][
        "public_ignited_pressure_peaking_validation"
    ]
    assert compact["aggregate"]["peak_overpressure_mae_kpa"] < 1.0
    assert compact["station_controller_validation_supported"] is False
    assert compact["station_vehicle_full_loop_supported"] is False

    summary = prompt_evidence_summary(manifest)
    assert summary["public_ignited_pressure_peaking_validation"][
        "component_validation_supported"
    ] is True
    links = prompt_evidence_header(manifest)["public_source_links"]
    assert any(item["id"] == "PUBLIC_USN_IGNITED_PRESSURE_PEAKING" for item in links)
