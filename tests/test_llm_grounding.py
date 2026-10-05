from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def test_manifest_distinguishes_not_requested_from_calculated_impact():
    frame = {"time_s": 12.5}
    signals = {"PT-0901": {"value": 88.0, "unit": "MPa", "quality": "GOOD"}}

    idle = build_evidence_manifest(frame, signals, [], False, question="현재 상태")
    assert idle["impact"]["calculation_status"] == "not_requested"
    assert idle["impact"]["result_count"] == 0
    assert idle["source"]["field_measurement"] is False
    assert idle["runtime_calibration"]["status"] == "reference_defaults"
    assert prompt_evidence_header(idle)["runtime_calibration"]["profile_id"] == (
        "reference_defaults"
    )
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
    local_accident = idle["response_evidence"][
        "confidential_local_accident_response_coverage"
    ]
    assert local_accident["case_count"] == 322
    assert local_accident["mapped_case_count"] == 322
    assert local_accident["required_stage_count"] == 5
    assert local_accident["contract_pass"] is True
    assert local_accident["raw_rows_persisted"] is False
    accidental = idle["response_evidence"]["public_accidental_release_evidence"]
    assert accidental["zenodo_doi"] == "10.5281/zenodo.17913628"
    assert accidental["article_doi"] == "10.1016/j.elstat.2025.104222"
    assert accidental["license"] == "CC BY 4.0"
    assert accidental["consequence_and_ignition_grounding_eligible"] is True
    assert accidental["full_loop_station_vehicle_holdout_eligible"] is False
    assert accidental["numerical_release_model_validation_claimed"] is False
    assert "ignition probability" in accidental["claim_limit"]
    assert all(row["local_sha256_match"] for row in accidental["files"])
    assert "raw_text" not in accidental
    detector = idle["response_evidence"]["public_detector_logic_evidence"]
    assert detector["doi"] == "10.23642/usn.26117989.v2"
    assert detector["rule"]["alarm_threshold_percent"] == 1.0
    assert detector["rule"]["trip_threshold_percent"] == 2.0
    assert detector["aggregate"]["case_count"] == 22
    assert detector["aggregate"]["cases_with_trip_detection"] == 22
    assert "outdoor station dispersion" in detector["claim_limit"]
    early = prompt_evidence_summary(idle)
    assert early["impact_status"] == "not_requested"
    assert early["public_experimental_benchmarks"]["sources"]
    hitrf = idle["response_evidence"]["public_hitrf_operational_reference"]
    assert hitrf["source"]["raw_synchronized_logger_public"] is False
    assert hitrf["storage"]["low_pressure"]["maximum_pressure_mpa"] == 20.0
    assert hitrf["storage"]["medium_pressure"]["tank_count"] == 6
    assert hitrf["storage"]["high_pressure"]["maximum_pressure_mpa"] == 90.0
    assert len(hitrf["compression_stages"]) == 4
    assert hitrf["dispensing_and_thermal"]["chiller_target_temperature_c"] == -40
    assert early["public_hitrf_operational_reference"]["source"][
        "raw_synchronized_logger_public"
    ] is False
    assert early["public_detector_logic_evidence"]["aggregate"]["case_count"] == 22
    assert early["confidential_local_accident_response_coverage"][
        "case_with_missing_stage_count"
    ] == 0
    assert early["confidential_measured_boundary_replay"]["temporal_holdout"][
        "time_ordered_holdout_supported"
    ] is True
    assert early["evidence_digest"] == idle["evidence_digest"]
    header = prompt_evidence_header(idle)
    assert header["public_accident_evidence"]["public_report_count"] == 23
    assert header["public_accident_evidence"]["accidental_release_zenodo_doi"] == (
        "10.5281/zenodo.17913628"
    )
    assert header["public_accident_evidence"]["accidental_release_full_loop"] is False
    assert header["public_accident_evidence"]["action_category_counts"][
        "shutdown_isolation_depressurization"
    ] == 22
    assert header["public_hitrf_operational_reference"]["raw_synchronized_logger_public"] is False
    assert header["public_hitrf_operational_reference"]["storage_tiers"] == [
        "high_pressure", "low_pressure", "medium_pressure"
    ]
    assert header["public_hitrf_operational_reference"]["compression_stage_count"] == 4
    assert header["confidential_local_accident_response_coverage"][
        "case_count"
    ] == 322
    assert header["confidential_local_accident_response_coverage"][
        "contract_pass"
    ] is True
    assert header["confidential_lifecycle_evidence"]["sampled_rows"] == 41752
    assert header["confidential_lifecycle_evidence"]["counter_roles"] == [
        "high_bank_cycles", "medium_bank_cycles"
    ]
    lifecycle = idle["response_evidence"]["confidential_lifecycle_counter_summary"]
    assert lifecycle["cycle_aware_degradation_fit"] is False
    assert lifecycle["counters"]["high_bank_cycles"]["total_positive_increment"] == 1183
    station_calibration = idle["response_evidence"][
        "confidential_station_boundary_calibration"
    ]
    assert station_calibration["sampled_rows"] == 10896
    assert station_calibration["boundary_pressure_mpa"]["min"] == 56.295
    assert station_calibration["recommended_recharge_restart_margin_pa"] == 540000.0
    assert station_calibration["state_transition_count"] == 274
    assert station_calibration["channel_attestation"][
        "pressure_boundary_semantics_attested"
    ] is True
    assert station_calibration["channel_attestation"][
        "mass_flow_units_attested"
    ] is False
    assert station_calibration["full_station_vehicle_validation"] is False
    confidential = idle["response_evidence"]["confidential_measured_boundary_replay"]
    assert confidential["trajectory_completed"] is True
    assert confidential["station_boundary_calibration_supported"] is True
    assert confidential["independent_full_loop_validation_supported"] is False
    assert confidential["raw_rows_persisted"] is False
    assert confidential["source_identifiers_published"] is False
    holdout = confidential["temporal_holdout"]
    assert holdout["trajectory_completed"] is True
    assert holdout["fit_used_holdout"] is False
    assert holdout["outcome_used_for_fit"] is False
    assert holdout["time_ordered_holdout_supported"] is True
    assert holdout["independent_full_loop_validation_supported"] is False
    operational_holdout = confidential["operational_envelope_holdout"]
    assert operational_holdout["calibration_points"] == 998
    assert operational_holdout["holdout_points"] == 30
    assert operational_holdout["fit_used_holdout"] is False
    assert operational_holdout["outcome_used_for_fit"] is False
    assert operational_holdout["trajectory_completed"] is True
    assert operational_holdout["independent_full_loop_validation_supported"] is False
    assert prompt_evidence_header(idle)["confidential_operational_envelope_holdout"][
        "trajectory_completed"
    ] is True
    cross_station = confidential["cross_station_pressure_envelope"]
    assert cross_station["profile_count"] == 2
    assert cross_station["observed_pressure_overlap_mpa"] == {
        "min": 56.295,
        "max": 63.36,
    }
    assert cross_station["pressure_semantics_attested_profiles"] == 2
    assert cross_station["temperature_boundary_attested_profiles"] == 0
    assert cross_station["mass_flow_units_attested_profiles"] == 0
    assert cross_station["station_to_vehicle_validation_supported"] is False
    assert prompt_evidence_header(idle)["confidential_cross_station_pressure_envelope"][
        "cross_station_pressure_plausibility_supported"
    ] is True
    benchmarks = idle["response_evidence"]["public_experimental_benchmarks"]
    assert len(benchmarks["sources"]) == 2
    nrel_trace = next(item for item in benchmarks["sources"] if item["id"] == "NREL_HDVS_2022_TANK_HOSE_TRACE")
    assert nrel_trace["aggregate"]["sample_count"] == 351
    assert nrel_trace["raw_rows_public"] is False
    fast_flow = next(item for item in benchmarks["sources"] if item["id"] == "NREL_HD_FAST_FLOW_2024_REPORT")
    assert fast_flow["aggregate"]["peak_mass_flow_g_s"] == 483.33
    assert "untouched row-level full-loop holdout" in fast_flow["not_eligible_for"]

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


def test_manifest_records_opt_in_measured_boundary_profile():
    frame = {
        "time_s": 12.5,
        "process_operations": {
            "settings": {"measured_boundary_calibration": True},
        },
    }
    manifest = build_evidence_manifest(frame, {}, [], False, question="현재 상태")
    profile = manifest["runtime_calibration"]
    assert profile["status"] == "active"
    assert profile["requested"] is True
    assert profile["profile_id"] == "owner_measured_operational_envelope_v1"
    assert profile["recharge_restart_margin_pa"] == 540000.0
    assert prompt_evidence_summary(manifest)["runtime_calibration"]["status"] == "active"
    assert prompt_evidence_header(manifest)["confidential_station_boundary_calibration"][
        "channel_attestation"
    ]["temperature_boundary_role_attested"] is False
    assert prompt_evidence_header(manifest)["runtime_calibration"]["profile_id"] == (
        "owner_measured_operational_envelope_v1"
    )


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
