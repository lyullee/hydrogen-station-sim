from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from h2station.api import app
from h2station.local_evidence import validation_evidence_summary


ROOT = Path(__file__).resolve().parents[1]


def test_validation_evidence_surface_is_privacy_bounded_and_claim_limited() -> None:
    summary = validation_evidence_summary()
    current_coverage = json.loads(
        (ROOT / "research/data_coverage_summary_2026_10_11.json").read_text(
            encoding="utf-8"
        )
    )
    current_audit = json.loads(
        (ROOT / "manuscript/ijhe_readiness_audit.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["status"] == "available"
    assert summary["readiness"]["ijhe_gate_counts"] == current_coverage[
        "readiness"
    ]["ijhe_gate_counts"]
    assert current_coverage["readiness"]["ijhe_gate_counts"] == current_audit[
        "gate_counts"
    ]
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
    capacity_cv = inventory["public_mc_capacity_geometry_cross_validation"]
    assert capacity_cv["status"] == "development_cross_validation_only"
    assert capacity_cv["fold_count"] == 8
    assert capacity_cv["folds_disjoint"] is True
    assert capacity_cv["joint_screening_pass_count"] == 4
    assert capacity_cv["baseline_comparison"][
        "pressure_rmse_reduction_percent"
    ] > 50.0
    assert capacity_cv["baseline_comparison"][
        "temperature_rmse_reduction_percent"
    ] < 0.0
    assert capacity_cv["external_validation"] is False
    assert capacity_cv["runtime_parameter_application"] is False
    assert capacity_cv["validation_gate_changed"] is False
    assert capacity_cv["promotion_prohibited"] is True
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
    h2safe_hvac = inventory["public_h2safe_hvac_input_readiness"]
    assert h2safe_hvac["status"] == "NOT_READY_FOR_PREACCESS_SPATIAL_VALIDATION"
    assert h2safe_hvac["release_test_count"] == 5
    assert h2safe_hvac["lab_1_vent_count"] == 10
    assert h2safe_hvac["lab_2_duct_count"] == 8
    assert h2safe_hvac["runtime_parameter_application"] is False
    assert h2safe_hvac["promotion_prohibited"] is True
    h2safe_geometry = inventory["public_h2safe_geometry_containment"]
    assert h2safe_geometry["status"] == "CONTAINMENT_CONFIRMED_REGISTRATION_UNPROVEN"
    assert h2safe_geometry["sensor_count"] == 61
    assert h2safe_geometry["sensor_containment_fraction"] == 1.0
    assert h2safe_geometry["all_sensor_points_inside_mesh_bounds"] is True
    assert h2safe_geometry["all_release_points_inside_mesh_bounds"] is True
    assert h2safe_geometry["runtime_parameter_application"] is False
    assert h2safe_geometry["preaccess_spatial_validation_ready"] is False
    assert h2safe_geometry["promotion_prohibited"] is True
    station_vehicle_search = inventory["public_station_vehicle_search_recheck"]
    assert station_vehicle_search["recorded_at"] == "2026-10-12"
    assert station_vehicle_search["source_count"] == 11
    assert station_vehicle_search["full_loop_external_validation_supported"] is False
    assert station_vehicle_search["prospective_holdout_eligible"] is False
    assert station_vehicle_search["runtime_parameter_application"] is False
    assert station_vehicle_search["claim_supported"] is False
    assert "common clock" in station_vehicle_search["reentry_condition"]
    assert all("C:\\" not in str(item) for item in station_vehicle_search["sources"])
    actual_h2_channel = inventory["public_actual_h2_channel_dataset"]
    assert actual_h2_channel["status"] == "PUBLIC_ACTUAL_H2_DISPERSION_INVENTORY"
    assert actual_h2_channel["source_doi"].lower() == "10.23642/usn.26117989.v2"
    assert actual_h2_channel["experiment_count"] == 22
    assert actual_h2_channel["sensor_count"] == 29
    assert actual_h2_channel["schema_screen_pass"] is True
    assert actual_h2_channel["independent_actual_hydrogen_component_candidate"] is True
    assert actual_h2_channel["station_to_vehicle_full_loop"] is False
    assert actual_h2_channel["runtime_parameter_application"] is False
    assert actual_h2_channel["validation_gate_promoted"] is False
    assert actual_h2_channel["promotion_prohibited"] is True
    assert "station twin" in actual_h2_channel["claim_limit"].lower()
    elvhys = inventory["public_elvhys_dataset"]
    assert elvhys["status"] == "PUBLIC_ELVHYS_ACTUAL_CRYOGENIC_H2_INVENTORY"
    assert elvhys["source_doi"] == "10.18710/JXJP0H"
    assert elvhys["published_test_plan_count"] == 48
    assert elvhys["case_id_count_with_public_data"] == 40
    assert elvhys["schema_screen_pass"] is True
    assert elvhys["independent_actual_cryogenic_hydrogen_component_candidate"] is True
    assert elvhys["pressure_peaking_candidate"] is True
    assert elvhys["ignition_consequence_candidate"] is True
    assert elvhys["station_to_vehicle_full_loop"] is False
    assert elvhys["runtime_parameter_application"] is False
    assert elvhys["promotion_prohibited"] is True
    assert "runtime parameters" in elvhys["claim_limit"].lower()
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
