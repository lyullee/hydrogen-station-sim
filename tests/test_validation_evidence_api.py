from __future__ import annotations

from fastapi.testclient import TestClient

from h2station.api import app
from h2station.local_evidence import validation_evidence_summary


def test_validation_evidence_surface_is_privacy_bounded_and_claim_limited() -> None:
    summary = validation_evidence_summary()

    assert summary["status"] == "available"
    assert summary["readiness"]["ijhe_gate_counts"] == {
        "PASS": 129,
        "FAIL": 10,
        "PENDING": 7,
    }
    assert summary["readiness"]["full_user_objective_ready"] is False
    assert summary["interpretation"]["data_volume_is_primary_blocker"] is False
    assert summary["interpretation"]["primary_blocker"]
    assert len(summary["validated_or_actionable_now"]) >= 4
    assert any(
        item["id"] == "public_type_iv_tank"
        and item["status"] == "VALIDATED_COMPONENT"
        for item in summary["validated_or_actionable_now"]
    )
    liquid_hrs = next(
        item
        for item in summary["validated_or_actionable_now"]
        if item["id"] == "nbsdc_liquid_hrs_catalogue"
    )
    assert liquid_hrs["status"] == "REQUEST_CANDIDATE"
    assert liquid_hrs["coverage"]["numerical_file_access"] == "application_required"
    assert "custodian approval" in liquid_hrs["not_allowed"].lower()
    assert liquid_hrs["coverage"]["raw_synchronized_archive_located"] is False
    assert not any(
        item["id"] == "full_loop_external_validation"
        for item in summary["unresolved_gates"]
    )
    assert summary["scope_exclusions"][0]["id"] == "full_loop_external_validation"
    assert summary["scope_exclusions"][0]["legacy_status"] == "FAIL"
    assert summary["minimum_next_input"]["event_count"] == 3
    inventory = summary["evidence_inventory"]
    traceability = inventory["public_incident_traceability"]
    assert traceability["status"] == "available"
    assert traceability["source_count"] == 3
    assert traceability["source_hashes_verified"] is True
    assert traceability["hiad"]["case_count"] == 34
    assert traceability["hiad"]["direct_physical_replay_cases"] == 29
    assert traceability["khk"]["public_report_count"] == 23
    assert traceability["khk"]["in_scope_incident_code_count"] == 25
    assert traceability["response_grounding"]["covered_action_category_count"] == 8
    assert traceability["runtime_parameter_application"] is False
    assert traceability["full_loop_holdout_eligible"] is False
    assert "accident reconstruction" in traceability["claim_limit"].lower()
    assert inventory["public_accident_reports"]["report_count"] == 23
    assert inventory["public_accident_reports"]["incident_code_count"] == 26
    assert inventory["public_accidental_release"]["experiment_count"] == 3
    assert inventory["public_accidental_release"]["ignition_observed_case_count"] == 2
    assert inventory["public_experimental_benchmarks"]["source_count"] == 8
    assert inventory["public_experimental_benchmarks"]["actual_hydrogen_archive_count"] == 22
    context = inventory["public_experimental_benchmarks"]["aggregate_operating_context"]
    assert len(context) == 6
    fast_flow = next(
        item for item in context if item["id"] == "NREL_HD_FAST_FLOW_2024_REPORT"
    )
    assert fast_flow["aggregate"]["peak_mass_flow_g_s"] == 483.33
    assert fast_flow["aggregate"]["protocol"] == "SAE J2601-5 MCF-HF-G H70 FM300 T40"
    actual_h2 = next(
        item for item in context if item["id"] == "USN_OPEN_CHANNEL_ACTUAL_H2_2025"
    )
    assert actual_h2["aggregate"]["total_rows_screened"] == 417340
    assert actual_h2["raw_rows_public"] is True
    assert all("C:\\" not in str(item) for item in context)
    assert inventory["public_field_benchmark"]["stations_tested"] == 22
    assert inventory["public_field_benchmark"]["full_loop_holdout_eligible"] is False
    scientific = inventory["local_scientific_container_discovery"]
    assert scientific["status"] == "available"
    assert scientific["scientific_headers_screened_total"] == 1409
    assert scientific["full_loop_candidate_count"] == 0
    assert scientific["partial_loop_candidate_count"] == 8
    assert scientific["runtime_parameter_application"] is False
    assert scientific["full_loop_external_validation_ready"] is False
    calibrated = inventory["public_closed_loop_calibrated_diagnostic"]
    assert calibrated["status"] == "diagnostic_only"
    assert calibrated["case_count"] == 11
    assert calibrated["screening_pass_count"] == 1
    assert calibrated["runtime_parameter_application"] is False
    assert calibrated["full_loop_external_validation_ready"] is False
    assert calibrated["promotion_prohibited"] is True
    assert "not a new independent holdout" in calibrated["claim_limit"].lower()
    geometry = inventory["public_mc_geometry_transfer_diagnostic"]
    assert geometry["status"] == "diagnostic_only"
    assert len(geometry["runs"]) == 3
    capacity_eos = next(
        item for item in geometry["runs"]
        if item["geometry_rule"] == "capacity_eos_volume"
    )
    assert capacity_eos["joint_screening_pass_count"] == 4
    assert geometry["runtime_geometry_changed"] is False
    assert geometry["geometry_rule_selection_prohibited"] is True
    assert geometry["full_loop_external_validation_ready"] is False
    tank_boundary = inventory["public_mc_tank_boundary_diagnostic"]
    assert tank_boundary["status"] == "diagnostic_only"
    assert tank_boundary["case_count"] == 8
    assert tank_boundary["joint_screening_pass_count"] == 0
    assert tank_boundary["runtime_parameter_application"] is False
    assert tank_boundary["promotion_prohibited"] is True
    cumulative_mass = inventory["public_mc_cumulative_mass_sensitivity"]
    assert cumulative_mass["status"] == "diagnostic_only"
    assert cumulative_mass["case_count"] == 8
    assert cumulative_mass["joint_screening_pass_count"] == 0
    assert cumulative_mass["runtime_parameter_application"] is False
    assert cumulative_mass["promotion_prohibited"] is True
    assert "no independent mass channel" in cumulative_mass["source_limitation"].lower()
    soc_boundary = inventory["public_mc_soc_boundary_diagnostic"]
    assert soc_boundary["status"] == "diagnostic_only"
    assert soc_boundary["case_count"] == 8
    assert soc_boundary["soc_definition_screen_pass_count"] == 8
    assert soc_boundary["runtime_parameter_application"] is False
    assert soc_boundary["full_loop_external_validation_ready"] is False
    source_pressure = inventory["public_mc_source_pressure_boundary_diagnostic"]
    assert source_pressure["status"] == "diagnostic_only"
    assert source_pressure["case_count"] == 8
    assert len(source_pressure["runs"]) == 3
    assert all(item["screening_pass_count"] == 0 for item in source_pressure["runs"])
    assert source_pressure["runtime_parameter_application"] is False
    assert source_pressure["full_loop_external_validation_ready"] is False
    assert source_pressure["promotion_prohibited"] is True
    assert "not independent external" in source_pressure["claim_limit"].lower()
    dickens = inventory["public_dickens_geometry_followup_candidate"]
    assert dickens["status"] == "followup_candidate_only"
    assert dickens["source_reference"]["doi"] == "10.1016/J.JPOWSOUR.2006.11.077"
    assert dickens["source_confirmed_geometry"]["inlet_pipe_internal_diameter_m"] == 0.005
    assert dickens["selected_diagnostic"]["all_four_frozen_screens_pass"] is True
    assert dickens["runtime_parameter_application"] is False
    assert dickens["validation_gate_effect"] == "none"
    assert all(
        set(archive) == {
            "scope",
            "machine_readable_files",
            "scientific_headers_screened",
            "scientific_header_parse_errors",
            "full_loop_candidate_count",
            "partial_loop_candidate_count",
        }
        for archive in scientific["archives"]
    )
    assert all(value is False for value in summary["privacy"].values())
    rendered = str(summary)
    assert "C:\\" not in rendered
    assert "\\research\\" not in rendered


def test_validation_evidence_endpoint_returns_same_safe_surface() -> None:
    with TestClient(app) as client:
        response = client.get("/api/evidence/validation")

    assert response.status_code == 200
    assert response.json()["readiness"] == validation_evidence_summary()["readiness"]
    assert response.json()["privacy"]["raw_rows_persisted"] is False
