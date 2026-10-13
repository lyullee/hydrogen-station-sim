from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def _manifest():
    return build_evidence_manifest(
        {
            "time_s": 10.0,
            "header_pressure_mpa": 70.0,
            "header_temperature_c": 25.0,
            "header_mass_kg": 1.0,
            "nozzle_flow_g_s": 0.0,
        },
        {},
        [],
        False,
        question="공개 실제 수소 제트화염 열복사 자료와 피해영향평가 근거를 설명해줘",
    )


def test_actual_hydrogen_jetfire_diagnostic_is_exposed_with_boundaries():
    manifest = _manifest()
    evidence = manifest["response_evidence"][
        "public_hydrogen_jetfire_postaccess_diagnostic"
    ]

    assert evidence["source"]["dataset_doi"] == "10.5281/zenodo.7895795"
    assert evidence["source"]["actual_hydrogen"] is True
    assert evidence["aggregate"]["workbook_count"] == 9
    assert evidence["aggregate"]["free_jet_distance_trend_count"] == 2
    assert evidence["independent_holdout"] is False
    assert evidence["prospective_validation"] is False
    assert evidence["runtime_parameter_application"] is False
    assert evidence["fire_heat_flux_validation"] is False
    assert evidence["claim_supported"] is False
    assert len(evidence["tests"]) == 9

    summary = prompt_evidence_summary(manifest)[
        "public_hydrogen_jetfire_postaccess_diagnostic"
    ]
    assert summary["aggregate"]["thermal_workbook_count"] == 6
    assert summary["claim_supported"] is False

    decision = prompt_decision_evidence(manifest)
    projected = decision["decision_support_evidence"]["public_hydrogen_jetfire"]
    assert projected["test_count"] == 9
    assert projected["independent_holdout"] is False
    assert projected["fire_heat_flux_validation"] is False
    assert projected["claim_supported"] is False

    header = prompt_evidence_header(manifest)
    assert header[
        "public_hydrogen_jetfire_postaccess_diagnostic"
    ]["claim_supported"] is False
    assert any(
        link["id"] == "PUBLIC_HYTUNNEL_JETFIRE_ZENODO_7895795"
        for link in header["public_source_links"]
    )
