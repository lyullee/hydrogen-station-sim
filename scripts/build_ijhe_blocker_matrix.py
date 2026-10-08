"""Build a compact, claim-bounded blocker matrix for the IJHE objective."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def candidate_count(record: dict[str, Any]) -> int:
    """Read an explicit count or derive it from the canonical candidates list."""

    declared = record.get("candidate_count")
    if isinstance(declared, int) and declared >= 0:
        return declared
    candidates = record.get("candidates")
    return len(candidates) if isinstance(candidates, list) else 0


def build(root: Path) -> dict[str, Any]:
    audit_path = root / "manuscript/ijhe_readiness_audit.json"
    hiad_path = root / "research/hiad_evaluation_readiness.json"
    tracker_path = root / "research/validation_data_acquisition_tracker.json"
    search_path = root / "research/public_full_loop_search_recheck_2026_10_05.json"
    latest_search_path = root / "research/public_full_loop_search_recheck_2026_10_06.json"
    methytrucks_path = root / "research/methytrucks_hysam_postaccess_diagnostic_2026_10_08.json"
    methytrucks_complete_path = root / "research/methytrucks_2026_public_measurement_intake.json"
    methytrucks_group_d_path = root / "research/methytrucks_group_d_prospective_result_2026_10_08.json"
    byrnes_path = root / "research/byrnes_typei_thermal_prospective_result_2026_10_08.json"
    public_update_path = root / "research/public_full_loop_data_update_2026_10_08.json"
    operational_search_path = root / "research/public_operational_benchmark_recheck_2026_10_05.json"
    operational_face_path = root / "research/public_operational_benchmark_face_validity_2026_10_05.json"
    h2safe_spatial_path = root / "research/h2safe_spatial_response_diagnostic_2026_10_08.json"
    h2safe_orientation_path = root / "research/h2safe_orientation_development_2026_10_08.json"
    hydelta_spatial_eligibility_path = root / "research/hydelta_indoor_spatial_holdout_eligibility_2026_10_08.json"
    sandia_spatial_path = root / "research/sandia_warehouse_spatial_diagnostic_2026_10_08.json"
    ignited_pressure_path = root / "research/usn_17934047_ignited_pressure_peaking_result_2026_10_08.json"
    qra_comparison_path = root / "research/qra_multimethod_comparison_2026_10_08.json"
    runtime_qra_path = root / "research/runtime_qra_envelope_comparison_2026_10_08.json"
    audit = load_json(audit_path)
    hiad = load_json(hiad_path)
    tracker = load_json(tracker_path)
    search = load_json(search_path)
    latest_search = load_json(latest_search_path) if latest_search_path.is_file() else {}
    methytrucks = load_json(methytrucks_path)
    methytrucks_complete = load_json(methytrucks_complete_path)
    methytrucks_group_d = load_json(methytrucks_group_d_path)
    byrnes = load_json(byrnes_path)
    public_update = load_json(public_update_path)
    operational_search = load_json(operational_search_path)
    h2safe_spatial = load_json(h2safe_spatial_path)
    h2safe_orientation = load_json(h2safe_orientation_path)
    hydelta_spatial_eligibility = load_json(hydelta_spatial_eligibility_path)
    sandia_spatial = load_json(sandia_spatial_path)
    ignited_pressure = load_json(ignited_pressure_path)
    qra_comparison = load_json(qra_comparison_path)
    runtime_qra = load_json(runtime_qra_path)

    status_by_id = {g["id"]: g for g in audit.get("gates", [])}
    gate = lambda gate_id: status_by_id.get(gate_id, {"status": "MISSING"})

    matrix = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_journal": audit["target_journal"],
        "decision": {
            "bounded_ijhe_submission_ready": audit["bounded_ijhe_submission_ready"],
            "full_user_objective_ready": audit["full_user_objective_ready"],
            "goal_completion_permitted": audit["goal_completion_permitted"],
            "interpretation": (
                "A bounded manuscript may be drafted around model-level and qualitative evidence, "
                "but the validated full-station digital-twin objective cannot be declared complete."
            ),
        },
        "gate_counts": audit["gate_counts"],
        "evidence_snapshot": {
            "tank_model": {
                "gate": gate("tank_external_validation")["status"],
                "evidence": "research/tank_model_validation_v2.json",
                "claim_boundary": "Type-IV tank submodel only; not a full station or safety-distance validation.",
            },
            "typeiii_prospective_fill": {
                "gate": gate("dickens_typeiii_prospective_validation")["status"],
                "diagnostic_gate": gate(
                    "dickens_mixed_convection_diagnostic_integrity"
                )["status"],
                "evidence": [
                    "research/dickens_typeiii_prospective_protocol_2026_10_08.json",
                    "research/dickens_typeiii_prospective_result_2026_10_08.json",
                    "research/dickens_typeiii_mixed_convection_diagnostic_2026_10_08.json",
                ],
                "claim_boundary": "The prospective natural-convection model failed temperature screens. The post-outcome forced-mixing sensitivity identifies a mechanism but cannot revise that decision or set a runtime parameter.",
            },
            "byrnes_typei_thermal_prospective_intake": {
                "gate": gate("byrnes_typei_thermal_prospective_intake_integrity")["status"],
                "evidence": [
                    "research/byrnes_typei_thermal_prospective_protocol_2026_10_08.json",
                    "research/byrnes_typei_thermal_prospective_result_2026_10_08.json",
                ],
                "decision": byrnes["decision"],
                "model_executed": byrnes["model_evaluation"]["executed"],
                "claim_boundary": byrnes["claim_boundary"],
            },
            "llm_grounding": {
                "gate": gate("llm_evidence_grounding_contract")["status"],
                "evidence": "research/llm_evidence_grounding_validation.json",
                "claim_boundary": "Software evidence/contradiction contract only; no operator-effectiveness or safety claim.",
            },
            "public_incident_traceability": {
                "gate": gate("hiad_digital_twin_replay_traceability")["status"],
                "independent_khk_gate": gate(
                    "khk_digital_twin_replay_traceability"
                )["status"],
                "evidence": [
                    "research/khk_hydrogen_station_public_reports_inventory_2026_10_04.json",
                    "research/khk_digital_twin_replay_coverage_2026_10_08.json",
                    "research/hiad_accident_response_coverage_evaluation_2026_10_05.json",
                    "research/hiad_digital_twin_replay_coverage_2026_10_08.json",
                ],
                "claim_boundary": "Qualitative scenario, canonical runtime and response grounding. HIAD contributes 34 metadata traces; independently, 22 KHK reports covering 25 incident codes traverse eight runtime families while one KOH release remains outside the gaseous-H2 scope. No accident reconstruction, frequency, calibrated probability, response-effectiveness or safety claim.",
            },
            "confined_space_consequence_measurements": {
                "gate": gate("grune_ventilation_measurement_inventory")["status"],
                "evidence": "research/grune_ventilation_dataset_inventory_2026_10_05.json",
                "claim_boundary": "Hash-verified CC BY 4.0 concentration/ventilation measurements only; no model comparison, outdoor separation-distance claim or full-loop validation claim.",
            },
            "full_scale_indoor_surrogate_measurements": {
                "gate": gate("h2safe_full_scale_indoor_surrogate_intake_integrity")["status"],
                "evidence": "research/h2safe_indoor_release_intake_2026_10_07.json",
                "claim_boundary": "Hash-verified full-scale indoor helium-surrogate sensor/geometry/HVAC intake only; the public fields do not calibrate H2 thresholds, site layout, outdoor consequence distances or a full filling loop.",
            },
            "h2safe_spatial_detector_transfer": {
                "gate": gate("h2safe_spatial_detector_transfer_validation")["status"],
                "evidence": [
                    "research/h2safe_spatial_response_diagnostic_2026_10_08.json",
                    "research/h2safe_orientation_development_2026_10_08.json",
                    "research/hydelta_indoor_spatial_holdout_eligibility_2026_10_08.json",
                    "research/sandia_warehouse_spatial_diagnostic_2026_10_08.json",
                ],
                "experiment_count": h2safe_spatial["results"]["Y_as_elevation"]["aggregate"]["experiment_count"],
                "median_spearman": h2safe_spatial["results"]["Y_as_elevation"]["aggregate"]["median_spearman"],
                "joint_pass": h2safe_spatial["results"]["Y_as_elevation"]["aggregate"]["joint_pass"],
                "post_access_orientation_candidate": {
                    "internal_reference_screen_pass": h2safe_orientation[
                        "orientation_candidate"
                    ]["aggregate"]["internal_reference_screen_pass"],
                    "independent_validation_pass": h2safe_orientation[
                        "decision"
                    ]["independent_validation_pass"],
                    "runtime_application": h2safe_orientation[
                        "integrity"
                    ]["runtime_application"],
                },
                "actual_hydrogen_holdout_candidate": {
                    "status": hydelta_spatial_eligibility["status"],
                    "eligible": hydelta_spatial_eligibility["decision"][
                        "eligible_for_primary_spatial_holdout"
                    ],
                    "failed_required_fields": hydelta_spatial_eligibility[
                        "decision"
                    ]["failed_required_fields"],
                    "model_evaluation_executed": hydelta_spatial_eligibility[
                        "decision"
                    ]["model_evaluation_executed"],
                    "runtime_candidate_enabled": hydelta_spatial_eligibility[
                        "decision"
                    ]["runtime_candidate_enabled"],
                },
                "actual_hydrogen_external_diagnostic": {
                    "status": sandia_spatial["status"],
                    "sensor_count": len(sandia_spatial["cases"]),
                    "baseline_spearman_rho": sandia_spatial[
                        "baseline_geometry_only"
                    ]["spearman_rho"],
                    "candidate_spearman_rho": sandia_spatial[
                        "orientation_candidate"
                    ]["spearman_rho"],
                    "top3_recall": sandia_spatial["orientation_candidate"][
                        "top3_recall"
                    ],
                    "independent_validation_pass": sandia_spatial["decision"][
                        "independent_validation_pass"
                    ],
                    "runtime_candidate_enabled": sandia_spatial["decision"][
                        "runtime_candidate_enabled"
                    ],
                },
                "claim_boundary": h2safe_spatial["claim_boundary"],
            },
            "consequence_component_evidence": {
                "ignited_confined_pressure_peaking": {
                    "decision": ignited_pressure.get("status"),
                    "primary_pass_count": ignited_pressure.get("aggregate", {}).get("primary_pass_count"),
                    "case_count": ignited_pressure.get("aggregate", {}).get("eligible_case_count"),
                    "claim_boundary": ignited_pressure.get("claim_boundary"),
                },
                "qra_multimethod_context": {
                    "method_count": qra_comparison.get("selection", {}).get("method_count"),
                    "retained_row_count": qra_comparison.get("aggregate", {}).get("observation_count"),
                    "maximum_method_ratio": qra_comparison.get("aggregate", {}).get("matched_input_spread_ratio", {}).get("maximum"),
                    "runtime_thermal_within_envelope": runtime_qra.get("aggregate", {}).get("thermal_within_method_envelope_count"),
                    "runtime_overpressure_within_envelope": runtime_qra.get("aggregate", {}).get("overpressure_within_method_envelope_count"),
                    "runtime_case_count": runtime_qra.get("aggregate", {}).get("case_count"),
                    "experimental_validation": False,
                    "automatic_calibration": False,
                },
            },
            "real_station_candidate": {
                "status": "PUBLIC_ROWS_POST_ACCESS_MAPPING_INCOMPLETE",
                "evidence": [
                    "research/methytrucks_2026_public_measurement_intake.json",
                    "research/methytrucks_hysam_postaccess_diagnostic_2026_10_08.json",
                    "research/public_full_loop_data_update_2026_10_08.json",
                    "research/nbsdc_hrss_operational_access_verification_2026_10_04.json",
                    "research/nbsdc_winter_olympics_access_recheck_2026_10_05.json",
                ],
                "claim_boundary": "Fifteen public MetHyTrucks physical-HRS sampling-system workbooks support post-access component diagnostics, and the three-file Hy-SaM subset supports a no-fit tank diagnostic. The official D3 implementation report classifies Groups A and C as 35 MPa direct/serial sampling-system tests with sampling-hardware sinks rather than vehicle tanks. Missing authoritative channel/unit, geometry and controller metadata plus prior outcome inspection prevent a prospective full-loop claim. NBSDC raw workbooks remain application-controlled.",
            },
            "methytrucks_complete_public_measurement_intake": {
                "gate": gate(
                    "methytrucks_complete_public_measurement_intake_integrity"
                )["status"],
                "evidence": "research/methytrucks_2026_public_measurement_intake.json",
                "workbook_count": methytrucks_complete["aggregate"]["workbook_count"],
                "sample_count": methytrucks_complete["aggregate"]["sample_count"],
                "mass_closure_screen_pass_count": methytrucks_complete["aggregate"][
                    "mass_closure_screen_pass_count"
                ],
                "full_loop_eligible": methytrucks_complete["eligibility"][
                    "full_loop_station_vehicle_validation_eligible"
                ],
                "claim_boundary": methytrucks_complete["claim_boundary"],
            },
            "methytrucks_hysam_postaccess": {
                "status": "PASS_DIAGNOSTIC_ONLY",
                "evidence": "research/methytrucks_hysam_postaccess_diagnostic_2026_10_08.json",
                "case_count": methytrucks["candidate_session_aggregate"]["case_count"],
                "pressure_rmse_case_mean_mpa": methytrucks["candidate_session_aggregate"]["pressure_rmse_mpa"]["case_mean"],
                "temperature_rmse_case_mean_c": methytrucks["candidate_session_aggregate"]["temperature_rmse_c"]["case_mean"],
                "descriptive_joint_screen_pass_fraction": methytrucks["candidate_session_aggregate"]["project_screen"]["joint_pass_fraction"],
                "claim_boundary": methytrucks["claim_boundary"],
            },
            "methytrucks_group_d_prospective": {
                "gate": gate("methytrucks_group_d_prospective_intake_integrity")["status"],
                "evidence": [
                    "research/methytrucks_group_d_prospective_protocol_2026_10_08.json",
                    "research/methytrucks_group_d_prospective_result_2026_10_08.json",
                ],
                "decision": methytrucks_group_d["decision"],
                "sample_count": methytrucks_group_d["workbook_structure"]["sample_count"],
                "unresolved_required": methytrucks_group_d["channel_screen"]["unresolved_required"],
                "model_executed": methytrucks_group_d["model_evaluation"]["executed"],
                "claim_boundary": methytrucks_group_d["claim_boundary"],
            },
        },
        "blocking_matrix": [
            {
                "id": "tank_thermal_transfer_validation",
                "status": gate("dickens_typeiii_prospective_validation")["status"],
                "why_blocked": "The prospectively frozen Type-III fill passed both pressure screens but failed both temperature screens. A post-outcome inlet-jet sensitivity reduced temperature RMSE below the limit across three plausible diameters, but the exact nozzle geometry is absent. A proposed Byrnes Type-I route was invalidated when the same numerical files were found in the already-consumed Zenodo exploratory archive; its mean-temperature schema also differed from the frozen upper/lower endpoint pair.",
                "evidence": [
                    "research/DICKENS_TYPEIII_PROSPECTIVE_VALIDATION_2026_10_08.md",
                    "research/dickens_typeiii_prospective_result_2026_10_08.json",
                    "research/dickens_typeiii_mixed_convection_diagnostic_2026_10_08.json",
                    "research/byrnes_typei_thermal_prospective_protocol_2026_10_08.json",
                    "research/byrnes_typei_thermal_prospective_result_2026_10_08.json",
                ],
                "unblock_criterion": "Freeze the mixed-convection formulation and exact inlet geometry before opening a new filling trace, then pass the joint pressure and temperature screens without post-outcome parameter selection.",
                "next_action": "Prioritize an untouched fill or discharge dataset with a predeclared temperature observable, explicit sensor locations, tank geometry and boundary-flow/pressure data.",
            },
            {
                "id": "full_loop_external_validation",
                "status": gate("full_loop_external_validation")["status"],
                "why_blocked": "The frozen external station-loop holdout has 0/8 engineering-screen passes. The public MetHyTrucks D3 report confirms Groups A and C are 35 MPa direct/serial sampling-system tests, not vehicle-tank filling traces; the post-access Hy-SaM set also has incomplete mapping. A separately frozen Group D H70 vehicle event was retained prospectively, but it lacks vehicle tank pressure and temperature, engineering units and independently documented tank geometry, so no model score was permitted.",
                "evidence": [
                    "data/public_validation/results/closed_loop_external_holdout/validation.json",
                    "research/mc_default_source_boundary_identifiability_2026_10_04.json",
                    "research/public_full_loop_search_recheck_2026_10_04.json",
                    "research/public_full_loop_search_recheck_2026_10_06.json",
                    "research/public_full_loop_data_update_2026_10_08.json",
                    "research/methytrucks_2026_public_measurement_intake.json",
                    "research/methytrucks_hysam_postaccess_diagnostic_2026_10_08.json",
                    "research/methytrucks_group_d_prospective_protocol_2026_10_08.json",
                    "research/methytrucks_group_d_prospective_result_2026_10_08.json",
                    "research/public_operational_benchmark_recheck_2026_10_05.json",
                    "research/public_operational_benchmark_face_validity_2026_10_05.json",
                    "research/nbsdc_hrss_operational_access_verification_2026_10_04.json",
                    "research/nbsdc_winter_olympics_access_recheck_2026_10_05.json",
                ],
                "unblock_criterion": "Obtain a clean, rights-cleared, pre-access frozen external dataset with synchronized station pressure/temperature/mass-flow, protocol/controller, dispenser/nozzle, and vehicle/receptacle channels; resolve the source-boundary/topology ambiguity; then score >=8 cases with >=80% screen pass fraction.",
                "next_action": "Request at least eight disjoint physical-HRS vehicle traces with explicit vehicle pressure/temperature, tank geometry, units and controller/cascade states. Do not spend additional model-scoring effort on MetHyTrucks Groups A/C for the full-loop gate; their official physical test class is now resolved.",
            },
            {
                "id": "consequence_model_external_validation",
                "status": "FAIL_OR_PENDING",
                "why_blocked": "The prospectively frozen ignited confined pressure-peaking component passed 27/27 primary screens, but that narrow result does not validate outdoor jet-fire or blast distance. The seven-method DATA3632 simulation comparison retained 211 rows and shows material method/source-boundary spread: the current runtime lies inside 2/4 thermal envelopes and 0/3 comparable overpressure envelopes. The dispenser mass-flow boundary differs by about 22-fold. Because DATA3632 is a simulation ensemble rather than experimental truth, these findings diagnose the boundary but cannot close the station consequence gate or authorize post-outcome tuning.",
                "evidence": [
                    "manuscript/ijhe_readiness_audit.json",
                    "research/preslhy_blowdown_validation.json",
                    "research/proust_independent_release_validation.json",
                    "research/schefer_transient_release_validation.json",
                    "research/grune_2014_pressure_decay_validation.json",
                    "research/usn_17934047_ignited_pressure_peaking_result_2026_10_08.json",
                    "research/qra_multimethod_comparison_protocol_2026_10_08.json",
                    "research/qra_multimethod_comparison_2026_10_08.json",
                    "research/runtime_qra_envelope_comparison_2026_10_08.json",
                ],
                "unblock_criterion": "Pass a pre-access frozen, rights-cleared physical outdoor jet-fire/overpressure holdout with matched pressure, temperature, aperture or measured mass flow and weather, or narrow every claim to the already passed ignited confined pressure-peaking component.",
                "next_action": "Classify free-orifice and flow-limited line releases explicitly before any calibration; acquire a measured outdoor consequence holdout and keep the simulation-method ensemble as uncertainty context only.",
            },
            {
                "id": "h2safe_spatial_detector_transfer",
                "status": gate("h2safe_spatial_detector_transfer_validation")["status"],
                "why_blocked": "The frozen coordinate-only rank law passed two of four H2SAFE spatial screens. A post-access orientation-class candidate passes all four internal reference screens and reaches Spearman rho 0.943 with top-3 recall 1.0 on a six-sensor Sandia actual-hydrogen summary without fitting. That external diagnostic was formalised after outcome access and cannot revise the gate. The pre-access-frozen HyDelta candidate was ineligible before model execution because required numeric spatial fields are absent.",
                "evidence": [
                    "research/h2safe_spatial_response_diagnostic_2026_10_08.json",
                    "research/H2SAFE_SPATIAL_RESPONSE_DIAGNOSTIC_2026_10_08.md",
                    "research/h2safe_orientation_development_2026_10_08.json",
                    "research/H2SAFE_ORIENTATION_DEVELOPMENT_2026_10_08.md",
                    "research/hydelta_indoor_spatial_holdout_protocol_2026_10_08.json",
                    "research/HYDELTA_INDOOR_SPATIAL_HOLDOUT_PROTOCOL_2026_10_08.md",
                    "research/hydelta_indoor_spatial_holdout_eligibility_2026_10_08.json",
                    "research/HYDELTA_INDOOR_SPATIAL_HOLDOUT_ELIGIBILITY_2026_10_08.md",
                    "research/sandia_warehouse_spatial_diagnostic_2026_10_08.json",
                    "research/SANDIA_WAREHOUSE_SPATIAL_DIAGNOSTIC_2026_10_08.md",
                ],
                "unblock_criterion": "Evaluate the now-frozen orientation-class candidate on an independent indoor release cohort and pass all spatial rank and recall screens without fitting detector amplitudes or hydrogen alarm thresholds on helium data.",
                "next_action": "Request a HyDelta companion export containing experiment ID, source/sensor XYZ, release orientation and per-sensor numerical H2 responses, while screening another untouched actual-hydrogen indoor cohort under the unchanged candidate and thresholds.",
            },
            {
                "id": "saga_human_effectiveness",
                "status": "PENDING",
                "why_blocked": "The HIAD casebook is not frozen, ethics/collection permission is unresolved, no masked holdout responses are present, and no independent expert ratings exist.",
                "evidence": [
                    "research/hiad_evaluation_readiness.json",
                    "research/HIAD_EXPERT_STUDY_PREREGISTRATION.md",
                    "research/ETHICS_DETERMINATION_REQUEST.md",
                    "research/hiad_accident_response_coverage_evaluation_2026_10_05.json",
                ],
                "unblock_criterion": "Institutional determination, coordinator leakage review, frozen 24-event casebook, 168 masked responses, and three qualified independent raters with locked analysis.",
                "next_action": "Obtain the institutional determination and complete the pre-registered human-evaluation workflow before making an effectiveness or safety claim about SAGA.",
            },
            {
                "id": "submission_declarations",
                "status": gate("submission_metadata_and_declarations")["status"],
                "why_blocked": "Author, affiliation, CRediT, conflict, funding and AI-use declarations are not confirmed in the repository.",
                "evidence": ["manuscript/submission_metadata.json"],
                "unblock_criterion": "All author and declaration fields completed and independently checked before submission.",
                "next_action": "Complete the metadata file with the actual author team; do not invent names, affiliations or declarations.",
            },
        ],
        "reproducibility": {
            "audit_sha256": sha256(audit_path),
            "hiad_readiness_sha256": sha256(hiad_path),
            "acquisition_tracker_sha256": sha256(tracker_path),
            "full_loop_search_sha256": sha256(search_path),
            "latest_full_loop_search_sha256": sha256(latest_search_path)
            if latest_search_path.is_file() else None,
            "methytrucks_postaccess_sha256": sha256(methytrucks_path),
            "methytrucks_complete_intake_sha256": sha256(methytrucks_complete_path),
            "methytrucks_group_d_prospective_sha256": sha256(methytrucks_group_d_path),
            "byrnes_typei_thermal_prospective_sha256": sha256(byrnes_path),
            "public_full_loop_update_sha256": sha256(public_update_path),
            "operational_benchmark_recheck_sha256": sha256(operational_search_path),
            "h2safe_orientation_development_sha256": sha256(h2safe_orientation_path),
            "operational_benchmark_face_validity_sha256": sha256(operational_face_path),
            "h2safe_intake_sha256": sha256(
                root / "research/h2safe_indoor_release_intake_2026_10_07.json"
            ),
            "h2safe_spatial_diagnostic_sha256": sha256(h2safe_spatial_path),
            "hydelta_spatial_eligibility_sha256": sha256(
                hydelta_spatial_eligibility_path
            ),
            "sandia_spatial_diagnostic_sha256": sha256(sandia_spatial_path),
            "ignited_pressure_peaking_sha256": sha256(ignited_pressure_path),
            "qra_multimethod_comparison_sha256": sha256(qra_comparison_path),
            "runtime_qra_comparison_sha256": sha256(runtime_qra_path),
            "candidate_route_count": len(tracker.get("candidates") or []),
            "public_full_loop_search_candidate_count": candidate_count(search),
            "latest_public_full_loop_search_candidate_count": candidate_count(latest_search),
            "methytrucks_workbook_count": len(methytrucks.get("workbooks") or []),
            "methytrucks_candidate_session_count": methytrucks["candidate_session_aggregate"]["case_count"],
            "methytrucks_complete_workbook_count": methytrucks_complete["aggregate"]["workbook_count"],
            "methytrucks_complete_sample_count": methytrucks_complete["aggregate"]["sample_count"],
            "methytrucks_group_d_decision": methytrucks_group_d["decision"],
            "public_full_loop_update_status": public_update.get("status"),
            "public_operational_benchmark_candidate_count": candidate_count(operational_search),
        },
        "claim_policy": [
            "Never present a request, metadata page, or public station inventory as raw validation evidence.",
            "Keep component-test failures and model limitations visible in the paper and supplement.",
            "Do not mark the user goal complete until full_loop_external_validation, h2safe_spatial_detector_transfer_validation and saga_effectiveness_and_safety_supported are supported and all pending human/submission gates are closed.",
        ],
    }
    return matrix


def markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# IJHE objective blocker matrix",
        "",
        f"Generated: `{matrix['generated_at']}`",
        "",
        "This is an evidence-readiness record, not a prediction of journal acceptance.",
        "",
        f"- Bounded IJHE submission ready: **{matrix['decision']['bounded_ijhe_submission_ready']}**",
        f"- Full validated-digital-twin objective ready: **{matrix['decision']['full_user_objective_ready']}**",
        f"- Automatic goal completion permitted: **{matrix['decision']['goal_completion_permitted']}**",
        f"- Gate counts: `{matrix['gate_counts']}`",
        "",
        "## Blocking matrix",
        "",
        "| Gate | Status | Unblock criterion |",
        "|---|---|---|",
    ]
    for item in matrix["blocking_matrix"]:
        lines.append(
            f"| `{item['id']}` | **{item['status']}** | {item['unblock_criterion']} |"
        )
    lines += [
        "",
        "## Evidence boundary",
        "",
    ]
    for item in matrix["claim_policy"]:
        lines.append(f"- {item}")
    lines += [
        "",
        "## Reproducibility",
        "",
        f"- Acquisition routes tracked: `{matrix['reproducibility']['candidate_route_count']}`",
        f"- Full-loop search candidates: `{matrix['reproducibility']['public_full_loop_search_candidate_count']}`",
        "- Source hashes are recorded in the JSON companion.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json-output", type=Path, default=Path("research/ijhe_submission_blocker_matrix_2026_10_05.json"))
    parser.add_argument("--report-output", type=Path, default=Path("research/IJHE_SUBMISSION_BLOCKER_MATRIX_2026_10_05.md"))
    args = parser.parse_args()
    root = args.root.resolve()
    matrix = build(root)
    json_path = args.json_output if args.json_output.is_absolute() else root / args.json_output
    md_path = args.report_output if args.report_output.is_absolute() else root / args.report_output
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    md_path.write_text(markdown(matrix), encoding="utf-8", newline="\n")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
