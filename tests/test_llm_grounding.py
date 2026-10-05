from h2station.llm_grounding import build_evidence_manifest


def test_manifest_distinguishes_not_requested_from_calculated_impact():
    frame = {"time_s": 12.5}
    signals = {"PT-0901": {"value": 88.0, "unit": "MPa", "quality": "GOOD"}}

    idle = build_evidence_manifest(frame, signals, [], False, question="현재 상태")
    assert idle["impact"]["calculation_status"] == "not_requested"
    assert idle["impact"]["result_count"] == 0
    assert idle["source"]["field_measurement"] is False
    assert idle["evidence_digest"].startswith("sha256:")
    traceability = idle["response_evidence"]["public_incident_traceability"]
    assert traceability["category_count"] == 8
    assert traceability["covered_category_count"] == 8
    assert traceability["case_count"] == 34
    assert traceability["covered_case_count"] == 34
    assert traceability["contract_pass"] is True
    assert "does not judge incident actions" in traceability["claim_limit"]
    taxonomy = traceability["action_taxonomy"]
    assert taxonomy["raw_text_retained"] is False
    assert taxonomy["holdout_use"] is False
    assert taxonomy["category_patterns_version"] == "hiad-action-taxonomy-v1"
    assert sum(taxonomy["category_counts"].values()) > 0
    assert "does not judge whether an action was correct or safe" in taxonomy["claim_limit"]
    accident_inventory = idle["response_evidence"]["public_accident_report_inventory"]
    assert accident_inventory["public_report_count"] == 23
    assert accident_inventory["incident_code_count"] == 26
    assert accident_inventory["precaution_report_count"] == 8
    assert accident_inventory["raw_pdf_mirrored"] is False
    assert accident_inventory["qualitative_scenario_grounding"] is True
    precedent_map = accident_inventory["scenario_precedent_map"]
    assert precedent_map["mapped_report_count"] == 23
    assert precedent_map["unmapped_report_count"] == 0
    assert precedent_map["citation_only"] is True
    assert "playbook_case_counts" not in precedent_map
    assert "representative_precedents" not in precedent_map

    result = {"node_id": "N09", "node_name": "고압 저장뱅크",
              "calculation_status": "calculated",
              "calculation_basis": "SENSOR_BASED_HYPOTHESIS",
              "pressure_sensor": "PT-0901", "current_pressure_mpa": 88.0,
              "sampled_effect_radius_m": 3.0}
    calculated = build_evidence_manifest(
        frame, signals, [result], True,
        active_conditions=[{"scenario": "고압 저장뱅크 압력 상승", "sensor_id": "PT-0901",
                            "state": "TRIGGER", "response_source_ids": ["HIAD2026", "H2_INCIDENT"]}],
        selected_sensor="PT-0901", question="피해영향은?",
    )
    assert calculated["impact"]["calculation_status"] == "calculated"
    assert calculated["impact"]["results"][0]["pressure_sensor"] == "PT-0901"
    assert calculated["conditions"][0]["label"] == "고압 저장뱅크 압력 상승"
    assert calculated["conditions"][0]["response_source_ids"] == ["H2_INCIDENT", "HIAD2026"]
    assert calculated["response_evidence"]["source_ids"] == ["H2_INCIDENT", "HIAD2026"]
    assert calculated["evidence_digest"] != idle["evidence_digest"]


def test_manifest_marks_attempt_without_result_and_filters_nonfinite_values():
    manifest = build_evidence_manifest(
        {"time_s": float("nan")},
        {"PT-0901": {"value": float("inf"), "unit": "MPa", "quality": "BAD"},
         "TT-0901": {"value": 25.0, "unit": "C", "quality": "GOOD"}},
        [{"node_id": "N09", "calculation_status": "failed",
          "maximum_heat_flux_w_m2": float("nan")}],
        True,
    )
    assert manifest["impact"]["calculation_status"] == "attempted_no_result"
    assert manifest["signals"]["count"] == 1
    assert manifest["signals"]["rows"][0]["tag"] == "TT-0901"
    assert manifest["source"]["simulation_time_s"] is None
