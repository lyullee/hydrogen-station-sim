"""Evidence-based completion audit for the IJHE validation objective."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


def _json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _gate(
    gate_id: str, status: str, claim: str, evidence: str, requirement: str,
    observed: object = None,
) -> dict[str, object]:
    return {
        "id": gate_id,
        "status": status,
        "claim": claim,
        "evidence": evidence,
        "requirement": requirement,
        "observed": observed,
    }


def _protocol_integrity(root: Path, manifest: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if not manifest:
        return False, ["protocol manifest missing or invalid"]
    mismatches = []
    for relative, expected in (manifest.get("required_file_sha256") or {}).items():
        path = root / relative
        if not path.is_file() or _sha256(path) != expected:
            mismatches.append(relative)
    return not mismatches, mismatches


def _controlled_registry_integrity(registry: dict[str, Any] | None) -> tuple[bool, dict[str, Any]]:
    """Validate the publication-safe surface of a controlled cohort registry."""

    registry = registry or {}
    cases = registry.get("cases") if isinstance(registry.get("cases"), list) else []
    acceptance = registry.get("cohort_acceptance") if isinstance(registry.get("cohort_acceptance"), dict) else {}
    design = registry.get("evidence_design") if isinstance(registry.get("evidence_design"), dict) else {}
    privacy = registry.get("privacy") if isinstance(registry.get("privacy"), dict) else {}
    case_count = registry.get("case_count")
    pass_count = registry.get("case_pass_count")
    pass_fraction = registry.get("case_pass_fraction")
    decisions = [case.get("decision") for case in cases if isinstance(case, dict)]
    case_codes = [case.get("case_code") for case in cases if isinstance(case, dict)]
    result_codes = [case.get("result_code") for case in cases if isinstance(case, dict)]
    expected_pass_count = sum(value == "FROZEN_EVALUATION_PASS" for value in decisions)
    valid_fraction = (
        isinstance(case_count, int) and case_count > 0
        and isinstance(pass_count, int)
        and isinstance(pass_fraction, (int, float))
        and abs(float(pass_fraction) - pass_count / case_count) <= 1.0e-12
    )
    required_metrics = {
        "vehicle_pressure_mpa", "vehicle_temperature_c", "mass_flow_g_s",
        "delivered_temperature_c", "selected_source_pressure_mpa",
        "cascade_low_pressure_mpa", "cascade_medium_pressure_mpa",
        "cascade_high_pressure_mpa",
    }
    metric_aggregate = registry.get("metric_aggregate") if isinstance(registry.get("metric_aggregate"), dict) else {}
    state_aggregate = registry.get("state_metric_aggregate") if isinstance(registry.get("state_metric_aggregate"), dict) else {}
    minimum_case_count = acceptance.get("minimum_case_count")
    minimum_pass_fraction = acceptance.get("minimum_case_pass_fraction")
    passed = bool(
        registry.get("schema_version") == 1
        and registry.get("artifact_type") == "controlled_hrs_privacy_bounded_cohort_registry"
        and registry.get("evaluation_scope") == "cascade_resolved_station_to_vehicle"
        and isinstance(registry.get("source_commit"), str)
        and bool(registry.get("source_commit"))
        and isinstance(case_count, int) and case_count >= 8
        and len(cases) == case_count
        and len(set(case_codes)) == case_count
        and len(set(result_codes)) == case_count
        and all(isinstance(value, str) and value.startswith("case-") for value in case_codes)
        and all(isinstance(value, str) and value.startswith("result-") for value in result_codes)
        and all(value in {"FROZEN_EVALUATION_PASS", "FROZEN_EVALUATION_FAIL"} for value in decisions)
        and pass_count == expected_pass_count
        and valid_fraction
        and float(pass_fraction) >= 0.8
        and isinstance(minimum_case_count, int) and minimum_case_count >= 8
        and isinstance(minimum_pass_fraction, (int, float)) and minimum_pass_fraction >= 0.8
        and acceptance.get("numerical_screen_passed") is True
        and design.get("independent_holdout") is True
        and design.get("model_developers_blinded_to_case_outcomes_before_freeze") is True
        and design.get("rights_cleared_for_controlled_evaluation") is True
        and registry.get("provenance_screen_passed") is True
        and registry.get("full_loop_external_validation_supported") is True
        and required_metrics.issubset(metric_aggregate)
        and {"selected_bank", "compressor_active"}.issubset(state_aggregate)
        and privacy.get("raw_trace_hashes_published") is False
        and privacy.get("raw_result_hashes_published") is False
        and privacy.get("hmac_salt_published") is False
        and privacy.get("source_identifiers_published") is False
        and privacy.get("absolute_timestamps_published") is False
        and privacy.get("raw_rows_persisted") is False
    )
    return passed, {
        "present": bool(registry),
        "integrity_passed": passed,
        "evaluation_scope": registry.get("evaluation_scope"),
        "case_count": case_count,
        "case_pass_count": pass_count,
        "case_pass_fraction": pass_fraction,
        "provenance_screen_passed": registry.get("provenance_screen_passed"),
        "full_loop_external_validation_supported": registry.get("full_loop_external_validation_supported"),
        "raw_trace_hashes_published": privacy.get("raw_trace_hashes_published"),
    }


def audit(root: Path) -> dict[str, object]:
    root = root.resolve()
    gates: list[dict[str, object]] = []

    tank_path = root / "research/tank_model_validation_v2.json"
    tank = _json(tank_path)
    tank_validation = (tank or {}).get("validation") or {}
    tank_observed = {
        "case_count": tank_validation.get("case_count"),
        "pressure_rmse_mpa": ((tank_validation.get("pressure_rmse_mpa") or {}).get("mean")),
        "temperature_rmse_c": ((tank_validation.get("temperature_rmse_c") or {}).get("mean")),
        "soc_rmse_percentage_points": ((tank_validation.get("soc_rmse_percentage_points") or {}).get("mean")),
        "bootstrap_replicates": (((tank or {}).get("uncertainty") or {}).get("replicates")),
    }
    tank_pass = (
        tank_observed["case_count"] == 12
        and tank_observed["bootstrap_replicates"] == 10_000
        and all(
            isinstance(tank_observed[name], (int, float))
            for name in (
                "pressure_rmse_mpa", "temperature_rmse_c",
                "soc_rmse_percentage_points",
            )
        )
    )
    gates.append(_gate(
        "tank_external_validation", "PASS" if tank_pass else "FAIL",
        "Measured-boundary Type-IV tank model is externally evaluated on the frozen public split.",
        str(tank_path.relative_to(root)),
        "12 untouched validation fills, three primary errors and 10,000 case-level bootstrap replicates.",
        tank_observed,
    ))

    methytrucks_path = root / "research/methytrucks_hysam_postaccess_diagnostic_2026_10_08.json"
    methytrucks = _json(methytrucks_path)
    methytrucks_supplement_path = root / "research/methytrucks_supplementary_mapping_recheck_2026_10_08.json"
    methytrucks_supplement = _json(methytrucks_supplement_path)
    methytrucks_access = (methytrucks or {}).get("access_integrity") or {}
    methytrucks_replay = (methytrucks or {}).get("candidate_tank_replay") or {}
    methytrucks_replays = (methytrucks or {}).get("candidate_session_replays") or []
    methytrucks_aggregate = (methytrucks or {}).get("candidate_session_aggregate") or {}
    methytrucks_mass = methytrucks_replay.get("mass_boundary") or {}
    methytrucks_pressure = methytrucks_replay.get("pressure") or {}
    methytrucks_temperature = methytrucks_replay.get("temperature") or {}
    methytrucks_eligibility = (methytrucks or {}).get("eligibility") or {}
    methytrucks_workbooks = (methytrucks or {}).get("workbooks") or []
    methytrucks_sensitivity = (methytrucks or {}).get("candidate_volume_sensitivity") or {}
    methytrucks_ratio = methytrucks_mass.get("flow_to_scale_mass_ratio")
    methytrucks_pass = bool(
        (methytrucks or {}).get("status")
        == "completed_post_access_external_diagnostic"
        and (methytrucks or {}).get("evidence_role")
        == "post_access_external_diagnostic_only"
        and (methytrucks or {}).get("source", {}).get("dataset_doi")
        == "10.5281/zenodo.20590842"
        and (methytrucks or {}).get("source", {}).get("dataset_license")
        == "CC BY 4.0"
        and methytrucks_access.get("all_expected_sha256_match") is True
        and methytrucks_access.get("raw_rows_committed") is False
        and methytrucks_access.get("parameter_fitting_performed") is False
        and len(methytrucks_workbooks) == 3
        and all(item.get("sampling_interval_s") == 0.5 for item in methytrucks_workbooks)
        and isinstance(methytrucks_ratio, (int, float))
        and 0.9 < methytrucks_ratio < 1.2
        and isinstance(methytrucks_pressure.get("rmse_mpa"), (int, float))
        and isinstance(methytrucks_temperature.get("rmse_c"), (int, float))
        and len(methytrucks_replays) == 5
        and methytrucks_aggregate.get("case_count") == 5
        and methytrucks_aggregate.get("selection_is_independent_of_model_prediction") is True
        and all(
            item.get("fit", {}).get("case_specific_fitting") is False
            for item in methytrucks_replays
        )
        and methytrucks_sensitivity.get("alternative_tank_internal_volume_m3") == 0.077
        and methytrucks_sensitivity.get("case_specific_fitting") is False
        and methytrucks_sensitivity.get("selected_for_validation_claim") is False
        and (methytrucks_supplement or {}).get("status")
        == "supplement_downloaded_and_mapping_gap_confirmed"
        and (methytrucks_supplement or {}).get("observed_contents", {}).get(
            "channel_dictionary_present"
        ) is False
        and (methytrucks_supplement or {}).get("observed_contents", {}).get(
            "workbook_test_to_setup_crosswalk_present"
        ) is False
        and methytrucks_eligibility.get("component_diagnostic_eligible") is True
        and methytrucks_eligibility.get("prospective_holdout_eligible") is False
        and methytrucks_eligibility.get("quantitative_full_loop_validation_eligible") is False
    )
    gates.append(_gate(
        "methytrucks_hysam_postaccess_diagnostic_integrity",
        "PASS" if methytrucks_pass else ("FAIL" if methytrucks else "PENDING"),
        "The public MetHyTrucks Hy-SaM archive is hash-audited and replayed without fitting as a claim-bounded post-access tank diagnostic.",
        f"{methytrucks_path.relative_to(root)}; {methytrucks_supplement_path.relative_to(root)}",
        "Three CC BY 4.0 workbooks, 0.5 s synchronized rows, verified hashes, flow-to-scale mass consistency, no case-specific fitting and explicit false prospective/full-loop eligibility flags.",
        {
            "workbook_count": len(methytrucks_workbooks),
            "sampling_intervals_s": sorted({item.get("sampling_interval_s") for item in methytrucks_workbooks}),
            "flow_to_scale_mass_ratio": methytrucks_ratio,
            "pressure_rmse_mpa": methytrucks_pressure.get("rmse_mpa"),
            "temperature_rmse_c": methytrucks_temperature.get("rmse_c"),
            "candidate_session_aggregate": methytrucks_aggregate,
            "candidate_volume_sensitivity": methytrucks_sensitivity,
            "supplementary_mapping_recheck": {
                "status": (methytrucks_supplement or {}).get("status"),
                "observed_contents": (methytrucks_supplement or {}).get("observed_contents"),
                "claim_boundary": (methytrucks_supplement or {}).get("claim_boundary"),
            },
            "prospective_holdout_eligible": methytrucks_eligibility.get("prospective_holdout_eligible"),
            "quantitative_full_loop_validation_eligible": methytrucks_eligibility.get("quantitative_full_loop_validation_eligible"),
            "claim_boundary": (methytrucks or {}).get("claim_boundary"),
        } if methytrucks else "missing",
    ))

    tank_runtime_path = root / "research/public_type_iv_tank_runtime_calibration_2026_10_07.json"
    tank_runtime = _json(tank_runtime_path)
    tank_runtime_hashes = (tank_runtime or {}).get("source_hashes") or {}
    tank_runtime_sources_match = bool(tank_runtime_hashes) and all(
        isinstance(expected, str)
        and (root / relative).is_file()
        and _sha256(root / relative) == expected
        for relative, expected in tank_runtime_hashes.items()
    )
    tank_runtime_recheck = (tank_runtime or {}).get("recheck") or {}
    tank_runtime_recheck_path = root / str(tank_runtime_recheck.get("artifact") or "")
    tank_runtime_pass = bool(
        (tank_runtime or {}).get("artifact_type")
        == "public_type_iv_tank_runtime_calibration_audit"
        and (tank_runtime or {}).get("raw_experimental_rows_persisted") is False
        and (tank_runtime or {}).get("source_workbook_names_persisted") is False
        and (tank_runtime or {}).get("runtime_match") is True
        and (tank_runtime or {}).get("runtime", {}).get("api_default_mode")
        == "public_type_iv"
        and (tank_runtime or {}).get("runtime", {}).get("validation_case_count") == 12
        and tank_runtime_recheck.get("matches_frozen_expected_result") is True
        and tank_runtime_recheck_path.is_file()
        and _sha256(tank_runtime_recheck_path) == tank_runtime_recheck.get("sha256")
        and tank_runtime_sources_match
    )
    gates.append(_gate(
        "public_tank_runtime_calibration_integrity",
        "PASS" if tank_runtime_pass else ("FAIL" if tank_runtime else "PENDING"),
        "The split-validated public Type-IV tank fit is the runtime default and is supplied to the bounded LLM evidence manifest.",
        str(tank_runtime_path.relative_to(root)),
        "Runtime fit, API default, LLM evidence record, frozen recheck and every hashed implementation source agree; no raw experimental rows are retained.",
        {
            "runtime": (tank_runtime or {}).get("runtime"),
            "sources_match": tank_runtime_sources_match,
            "recheck_matches": tank_runtime_recheck.get("matches_frozen_expected_result"),
        } if tank_runtime else "missing",
    ))

    correction_path = root / "research/h2protocol_active_fill_correction.json"
    correction = _json(correction_path)
    corrected_trace = (correction or {}).get("h2p_l29") or {}
    correction_hashes = (correction or {}).get("processed_artifact_hashes") or {}
    correction_pass = bool(
        (correction or {}).get("status")
        == "post-diagnostic preprocessing correction disclosed"
        and corrected_trace.get("old_normalized_sample_count") == 1143
        and corrected_trace.get("corrected_normalized_sample_count") == 399
        and correction_hashes.get("h2protocol_cases_csv_sha256")
        and correction_hashes.get("h2p_l29_trace_csv_sha256")
    )
    gates.append(_gate(
        "active_fill_correction_disclosed",
        "PASS" if correction_pass else "FAIL",
        "The post-diagnostic H2P-L29 normalization correction and its downstream effect are disclosed and hash-linked.",
        str(correction_path.relative_to(root)),
        "Old/new interval evidence, algorithm, processed hashes and downstream claim limit.",
        correction or "missing",
    ))

    development_v2_path = root / "research/closed_loop_development_v2.json"
    internal_v2_path = root / "research/closed_loop_internal_comparison_v2.json"
    development_v2 = _json(development_v2_path)
    internal_v2 = _json(internal_v2_path)
    development_aggregate = (development_v2 or {}).get("aggregate") or {}
    internal_aggregate = (internal_v2 or {}).get("aggregate") or {}
    corrected_pipeline_pass = bool(
        development_aggregate.get("case_count") == 8
        and development_aggregate.get("screening_pass_count") == 1
        and internal_aggregate.get("case_count") == 11
        and internal_aggregate.get("screening_pass_count") == 2
        and (development_v2 or {}).get("dispenser_flow_area_multiplier") == 2.0
        and (development_v2 or {}).get("precooler_duty_multiplier") == 16.0
    )
    gates.append(_gate(
        "corrected_closed_loop_internal_evidence",
        "PASS" if corrected_pipeline_pass else "FAIL",
        "The corrected development pipeline is retained with its low joint-screen pass fractions and internal-comparison status.",
        f"{development_v2_path.relative_to(root)}; {internal_v2_path.relative_to(root)}",
        "8 development and 11 already-inspected comparison cases with selected global parameters and retained failures.",
        {
            "development": development_aggregate,
            "internal_comparison": internal_aggregate,
        },
    ))

    partial_diagnostic_path = root / "data/public_validation/results/partial_station_profile_diagnostic/validation.json"
    partial_diagnostic = _json(partial_diagnostic_path)
    partial_protocol = (partial_diagnostic or {}).get("protocol") or {}
    partial_diagnostic_pass = bool(
        (partial_diagnostic or {}).get("evidence_role") == "development_diagnostic_only"
        and (partial_diagnostic or {}).get("claim_boundary")
        and partial_diagnostic.get("case_count") == 8
        and partial_diagnostic.get("screening_pass_count") == 0
        and partial_protocol.get("fresh_holdout") is False
        and partial_protocol.get("upstream_pressure_trace_available") is False
        and partial_protocol.get("outcomes_inspected_before_run") is True
        and (partial_diagnostic or {}).get("source_worktree_dirty") is False
    )
    gates.append(_gate(
        "partial_station_profile_diagnostic_integrity",
        "PASS" if partial_diagnostic_pass else ("FAIL" if partial_diagnostic else "PENDING"),
        "The profiled partial-station experiment is retained as a bounded diagnostic and cannot be mistaken for full-station validation.",
        str(partial_diagnostic_path.relative_to(root)),
        "Eight declared development cases, explicit missing upstream boundary, no fresh-holdout claim, and retained zero screen passes.",
        {
            "evidence_role": (partial_diagnostic or {}).get("evidence_role"),
            "protocol": partial_protocol,
            "case_count": (partial_diagnostic or {}).get("case_count"),
            "screening_pass_count": (partial_diagnostic or {}).get("screening_pass_count"),
        } if partial_diagnostic else "missing",
    ))

    mc_partial_path = root / "data/public_validation/results/partial_station_mc_protocol_source3_physics_only/validation.json"
    mc_partial = _json(mc_partial_path)
    mc_partial_protocol = (mc_partial or {}).get("protocol") or {}
    mc_partial_pass = bool(
        (mc_partial or {}).get("evidence_role") == "development_diagnostic_only"
        and (mc_partial or {}).get("case_count") == 8
        and (mc_partial or {}).get("screening_pass_count") == 1
        and mc_partial_protocol.get("fresh_holdout") is False
        and mc_partial_protocol.get("outcomes_inspected_before_run") is True
        and mc_partial_protocol.get("source_pressure_profile_used") is True
        and mc_partial_protocol.get("protocol_pressure_profile_used") is True
        and (mc_partial or {}).get("source_worktree_dirty") is False
    )
    gates.append(_gate(
        "mc_source_schedule_diagnostic_integrity",
        "PASS" if mc_partial_pass else ("FAIL" if mc_partial else "PENDING"),
        "The consumed MC Default source-pressure and protocol-schedule sensitivity is retained as diagnostic evidence, not external confirmation.",
        str(mc_partial_path.relative_to(root)),
        "Eight consumed cases, measured source/schedule profiles recorded, physics-only stop declared, and no new-holdout claim.",
        {
            "evidence_role": (mc_partial or {}).get("evidence_role"),
            "protocol": mc_partial_protocol,
            "case_count": (mc_partial or {}).get("case_count"),
            "screening_pass_count": (mc_partial or {}).get("screening_pass_count"),
        } if mc_partial else "missing",
    ))

    mc_tank_boundary_path = root / "research/mc_tank_boundary_diagnostic_2026_10_05.json"
    mc_tank_boundary = _json(mc_tank_boundary_path)
    mc_tank_aggregate = (mc_tank_boundary or {}).get("aggregate") or {}
    mc_tank_boundary_pass = bool(
        (mc_tank_boundary or {}).get("schema_version") == 1
        and (mc_tank_boundary or {}).get("diagnostic_type")
        == "MC Default measured-boundary vehicle-tank replay"
        and (mc_tank_boundary or {}).get("evidence_role")
        == "development_diagnostic_only"
        and (mc_tank_boundary or {}).get("post_outcome") is True
        and (mc_tank_boundary or {}).get("parameter_fitting") is False
        and len((mc_tank_boundary or {}).get("cases") or []) == 8
        and mc_tank_aggregate.get("case_count") == 8
        and len((mc_tank_boundary or {}).get("boundary_conditions") or []) == 3
        and (mc_tank_boundary or {}).get("claim_boundary")
        and (mc_tank_boundary or {}).get("source_commit")
    )
    gates.append(_gate(
        "mc_tank_boundary_diagnostic_integrity",
        "PASS" if mc_tank_boundary_pass else ("FAIL" if mc_tank_boundary else "PENDING"),
        "The MC Default measured-boundary replay isolates vehicle-tank thermodynamics from station control without being promoted to full-loop validation.",
        str(mc_tank_boundary_path.relative_to(root)),
        "Eight consumed cases, measured flow/temperature/source-pressure boundaries, no fitting, explicit post-outcome diagnostic role and claim boundary.",
        {
            "evidence_role": (mc_tank_boundary or {}).get("evidence_role"),
            "post_outcome": (mc_tank_boundary or {}).get("post_outcome"),
            "parameter_fitting": (mc_tank_boundary or {}).get("parameter_fitting"),
            "boundary_conditions": (mc_tank_boundary or {}).get("boundary_conditions"),
            "aggregate": mc_tank_aggregate,
        } if mc_tank_boundary else "missing",
    ))

    mc_enthalpy_path = root / "research/mc_enthalpy_pressure_sensitivity_2026_10_05.json"
    mc_enthalpy = _json(mc_enthalpy_path)
    mc_enthalpy_pass = bool(
        (mc_enthalpy or {}).get("schema_version") == 1
        and (mc_enthalpy or {}).get("diagnostic_type")
        == "MC inlet enthalpy pressure-basis sensitivity"
        and (mc_enthalpy or {}).get("evidence_role") == "development_diagnostic_only"
        and (mc_enthalpy or {}).get("post_outcome") is True
        and (mc_enthalpy or {}).get("parameter_fitting") is False
        and len((mc_enthalpy or {}).get("runs") or []) == 3
        and all(run.get("case_count") == 8 for run in (mc_enthalpy or {}).get("runs", []))
        and (mc_enthalpy or {}).get("claim_boundary")
    )
    gates.append(_gate(
        "mc_enthalpy_pressure_sensitivity_integrity",
        "PASS" if mc_enthalpy_pass else ("FAIL" if mc_enthalpy else "PENDING"),
        "The MC inlet enthalpy pressure-basis ambiguity is quantified without selecting a production boundary or claiming validation.",
        str(mc_enthalpy_path.relative_to(root)),
        "Three fixed-boundary sensitivity runs, eight cases each, no fitting, post-outcome diagnostic role and explicit missing nozzle-upstream pressure boundary.",
        {
            "evidence_role": (mc_enthalpy or {}).get("evidence_role"),
            "run_count": len((mc_enthalpy or {}).get("runs") or []),
            "case_counts": [run.get("case_count") for run in (mc_enthalpy or {}).get("runs", [])],
            "aggregates": [run.get("aggregate") for run in (mc_enthalpy or {}).get("runs", [])],
        } if mc_enthalpy else "missing",
    ))

    mc_measured_boundary_path = root / "research/mc_measured_boundary_diagnostic_2026_10_05.json"
    mc_measured_boundary = _json(mc_measured_boundary_path)
    mc_measured_runs = (mc_measured_boundary or {}).get("runs") or []
    mc_measured_boundary_pass = bool(
        (mc_measured_boundary or {}).get("schema_version") == 1
        and (mc_measured_boundary or {}).get("diagnostic_type")
        == "MC Default measured source-boundary and protocol-schedule replay"
        and (mc_measured_boundary or {}).get("evidence_role")
        == "DEVELOPMENT_DIAGNOSTIC_ONLY"
        and (mc_measured_boundary or {}).get("post_outcome") is True
        and (mc_measured_boundary or {}).get("parameter_fitting") is False
        and (mc_measured_boundary or {}).get("case_count") == 8
        and len(mc_measured_runs) == 4
        and all(
            run.get("aggregate", {}).get("screening_pass_count", 0) <= 1
            and run.get("aggregate", {}).get("temperature_rmse_c", 0.0)
            > (mc_measured_boundary.get("protocol", {}).get("screening_limits", {}).get("temperature_rmse_c", 10.0))
            for run in mc_measured_runs
        )
        and (mc_measured_boundary or {}).get("validation_boundary", {}).get("full_loop_holdout_eligible") is False
        and (mc_measured_boundary or {}).get("validation_boundary", {}).get("goal_completion_permitted") is False
        and (mc_measured_boundary or {}).get("source_commit")
        and (mc_measured_boundary or {}).get("interpretation", {}).get("claim_boundary")
    )
    gates.append(_gate(
        "mc_measured_boundary_diagnostic_integrity",
        "PASS" if mc_measured_boundary_pass else ("FAIL" if mc_measured_boundary else "PENDING"),
        "The measured MC source-boundary/protocol sensitivity replay is retained as negative development evidence and cannot be promoted to full-loop validation.",
        str(mc_measured_boundary_path.relative_to(root)),
        "Four post-outcome runs over eight consumed cases, no fitting, retained joint temperature failures, and explicit false full-loop/goal flags.",
        {
            "run_count": len(mc_measured_runs),
            "case_count": (mc_measured_boundary or {}).get("case_count"),
            "screening_pass_counts": [run.get("aggregate", {}).get("screening_pass_count") for run in mc_measured_runs],
            "aggregate": [run.get("aggregate") for run in mc_measured_runs],
            "goal_completion_permitted": (mc_measured_boundary or {}).get("validation_boundary", {}).get("goal_completion_permitted"),
        } if mc_measured_boundary else "missing",
    ))

    operational_calibration_path = root / (
        "research/confidential_operational_envelope_calibration_summary_2026_10_06.json"
    )
    operational_replay_path = root / (
        "research/confidential_operational_envelope_replay_2026_10_06.json"
    )
    operational_holdout_path = root / (
        "research/confidential_operational_envelope_holdout_replay_2026_10_06.json"
    )
    cross_station_path = root / (
        "research/confidential_cross_station_pressure_envelope_2026_10_06.json"
    )
    operational_calibration = _json(operational_calibration_path)
    operational_replay = _json(operational_replay_path)
    operational_holdout = _json(operational_holdout_path)
    cross_station = _json(cross_station_path)
    operational_eligibility = (operational_calibration or {}).get("eligibility") or {}
    operational_replay_eligibility = (operational_replay or {}).get("eligibility") or {}
    operational_calibration_pass = bool(
        (operational_calibration or {}).get("schema_version") == 1
        and (operational_calibration or {}).get("artifact_type")
        == "confidential_operational_envelope_calibration_summary"
        and (operational_calibration or {}).get("source_identifiers_published") is False
        and (operational_calibration or {}).get("raw_rows_persisted") is False
        and (operational_calibration or {}).get("exact_source_dates_published") is False
        and (operational_calibration or {}).get("files_read") == 8
        and (operational_calibration or {}).get("sampled_rows") == 10896
        and (operational_calibration or {}).get("state_transition_count") == 274
        and (operational_calibration or {}).get("recommended_recharge_restart_margin_pa") == 540000.0
        and operational_eligibility.get("station_boundary_calibration_supported") is True
        and operational_eligibility.get("full_station_vehicle_validation") is False
        and operational_eligibility.get("vehicle_side_channels_present") is False
        and operational_eligibility.get("flow_units_attested") is False
        and (operational_replay or {}).get("schema_version") == 1
        and (operational_replay or {}).get("artifact_type")
        == "confidential_operational_envelope_replay"
        and (operational_replay or {}).get("source_identifiers_published") is False
        and (operational_replay or {}).get("raw_rows_persisted") is False
        and (operational_replay or {}).get("exact_source_dates_published") is False
        and (operational_replay or {}).get("calibration", {}).get("profile_id")
        == (operational_calibration or {}).get("profile_id")
        and (operational_replay or {}).get("calibration", {}).get("aggregate_margin_applied") is True
        and (operational_replay or {}).get("replay", {}).get("simulated_samples") == 121
        and (operational_replay or {}).get("replay", {}).get("esd_triggered") is False
        and operational_replay_eligibility.get("station_boundary_integration_check") is True
        and operational_replay_eligibility.get("independent_full_station_vehicle_validation") is False
        and (operational_holdout or {}).get("schema_version") == 1
        and (operational_holdout or {}).get("artifact_type")
        == "confidential_operational_envelope_holdout_replay"
        and (operational_holdout or {}).get("source_identifiers_published") is False
        and (operational_holdout or {}).get("raw_rows_persisted") is False
        and (operational_holdout or {}).get("split", {}).get("fit_used_holdout") is False
        and (operational_holdout or {}).get("split", {}).get("outcome_used_for_fit") is False
        and (operational_holdout or {}).get("replay", {}).get("trajectory_completed") is True
        and (operational_holdout or {}).get("eligibility", {}).get(
            "time_ordered_measured_boundary_holdout_supported"
        ) is True
        and (operational_holdout or {}).get("eligibility", {}).get(
            "independent_full_loop_validation_supported"
        ) is False
        and (cross_station or {}).get("schema_version") == 1
        and (cross_station or {}).get("artifact_type")
        == "confidential_cross_station_pressure_envelope"
        and (cross_station or {}).get("source_identifiers_published") is False
        and (cross_station or {}).get("raw_rows_persisted") is False
        and (cross_station or {}).get("comparison", {}).get(
            "profiles_with_pressure_semantics_attestation"
        ) == 2
        and (cross_station or {}).get("comparison", {}).get(
            "profiles_with_temperature_boundary_attestation"
        ) == 0
        and (cross_station or {}).get("comparison", {}).get(
            "profiles_with_mass_flow_units_attestation"
        ) == 0
        and (cross_station or {}).get("eligibility", {}).get(
            "cross_station_pressure_plausibility_supported"
        ) is True
        and (cross_station or {}).get("eligibility", {}).get(
            "station_to_vehicle_validation_supported"
        ) is False
    )
    gates.append(_gate(
        "confidential_operational_envelope_calibration_integrity",
        "PASS" if operational_calibration_pass else (
            "FAIL" if operational_calibration or operational_replay else "PENDING"
        ),
        "The owner-controlled operational-envelope aggregate is privacy-bounded and passes through a measured-boundary runtime replay without being promoted to full-loop validation.",
        f"{operational_calibration_path.relative_to(root)}; {operational_replay_path.relative_to(root)}; {operational_holdout_path.relative_to(root)}; {cross_station_path.relative_to(root)}",
        "De-identified aggregate, retained quality boundary, explicit missing vehicle/flow semantics, opt-in profile linkage, a completed protection-aware replay, an untouched chronological suffix holdout and a pressure-only cross-station plausibility check.",
        {
            "files_read": (operational_calibration or {}).get("files_read"),
            "sampled_rows": (operational_calibration or {}).get("sampled_rows"),
            "state_transition_count": (operational_calibration or {}).get("state_transition_count"),
            "recharge_restart_margin_pa": (operational_calibration or {}).get("recommended_recharge_restart_margin_pa"),
            "simulated_samples": (operational_replay or {}).get("replay", {}).get("simulated_samples"),
            "esd_triggered": (operational_replay or {}).get("replay", {}).get("esd_triggered"),
            "full_station_vehicle_validation": operational_eligibility.get("full_station_vehicle_validation"),
            "holdout_calibration_points": (operational_holdout or {}).get("split", {}).get("calibration_points"),
            "holdout_points": (operational_holdout or {}).get("split", {}).get("holdout_points"),
            "holdout_trajectory_completed": (operational_holdout or {}).get("replay", {}).get("trajectory_completed"),
            "holdout_fit_used": (operational_holdout or {}).get("split", {}).get("fit_used_holdout"),
            "holdout_full_loop_validation": (operational_holdout or {}).get("eligibility", {}).get("independent_full_loop_validation_supported"),
            "cross_station_profile_count": len((cross_station or {}).get("profiles") or []),
            "cross_station_pressure_overlap_mpa": (cross_station or {}).get("comparison", {}).get("observed_pressure_overlap_mpa"),
            "cross_station_pressure_plausibility": (cross_station or {}).get("eligibility", {}).get("cross_station_pressure_plausibility_supported"),
            "cross_station_full_loop_validation": (cross_station or {}).get("eligibility", {}).get("station_to_vehicle_validation_supported"),
        } if operational_calibration and operational_replay else "missing",
    ))

    operational_recheck_path = root / (
        "research/confidential_operational_profile_recheck_2026_10_06.json"
    )
    operational_recheck = _json(operational_recheck_path)
    recheck_comparison = (operational_recheck or {}).get(
        "committed_profile_comparison"
    ) or {}
    recheck_runtime = (operational_recheck or {}).get("runtime_decision") or {}
    operational_recheck_pass = bool(
        (operational_recheck or {}).get("schema_version") == 1
        and (operational_recheck or {}).get("artifact_type")
        == "confidential_operational_envelope_recheck"
        and (operational_recheck or {}).get("source_identifiers_published") is False
        and (operational_recheck or {}).get("raw_rows_persisted") is False
        and (operational_recheck or {}).get("exact_source_dates_published") is False
        and (operational_recheck or {}).get("source_paths_published") is False
        and recheck_comparison.get("matches") is True
        and bool(recheck_comparison.get("fields_compared"))
        and bool(recheck_comparison.get("fields_omitted_without_attestation"))
        and recheck_comparison.get("mismatches") == []
        and recheck_runtime.get("committed_profile_replaced") is False
        and recheck_runtime.get("default_model_parameters_changed") is False
        and recheck_runtime.get("measured_boundary_calibration_remains_opt_in") is True
        and recheck_runtime.get("mismatch_requires_custodian_review") is True
        and "vehicle-side validation" in str(
            (operational_recheck or {}).get("claim_boundary", "")
        ).lower()
        and "full-loop" in str(
            (operational_recheck or {}).get("claim_boundary", "")
        ).lower()
    )
    gates.append(_gate(
        "confidential_operational_profile_recheck_integrity",
        "PASS" if operational_recheck_pass else (
            "FAIL" if operational_recheck else "PENDING"
        ),
        "The fresh private-data aggregate recheck matches the committed station-boundary profile without replacing it or widening the validation claim.",
        str(operational_recheck_path.relative_to(root)),
        "Privacy flags, compared-field match, explicit omitted un-attested channels, empty mismatch list, opt-in runtime decision and full-loop claim boundary are all retained.",
        {
            "matches": recheck_comparison.get("matches"),
            "fields_compared": recheck_comparison.get("fields_compared"),
            "fields_omitted_without_attestation": recheck_comparison.get(
                "fields_omitted_without_attestation"
            ),
            "mismatches": recheck_comparison.get("mismatches"),
            "sampled_rows": ((operational_recheck or {}).get("fresh_calibration") or {}).get(
                "sampled_rows"
            ),
            "profile_replaced": recheck_runtime.get("committed_profile_replaced"),
            "opt_in_only": recheck_runtime.get(
                "measured_boundary_calibration_remains_opt_in"
            ),
            "full_loop_claim": "vehicle-side validation" in str(
                (operational_recheck or {}).get("claim_boundary", "")
            ).lower() and "full-loop" in str(
                (operational_recheck or {}).get("claim_boundary", "")
            ).lower(),
        } if operational_recheck else "missing",
    ))

    channel_quality_path = root / (
        "research/confidential_station_channel_quality_recheck_2026_10_06.json"
    )
    channel_quality = _json(channel_quality_path)
    channel_roles = (channel_quality or {}).get("roles") or {}
    channel_timebase = (channel_quality or {}).get("timebase") or {}
    channel_eligibility = (channel_quality or {}).get("eligibility") or {}
    channel_quality_pass = bool(
        (channel_quality or {}).get("schema_version") == 1
        and (channel_quality or {}).get("artifact_type")
        == "confidential_station_channel_quality_recheck"
        and (channel_quality or {}).get("source_identifiers_published") is False
        and (channel_quality or {}).get("raw_rows_persisted") is False
        and (channel_quality or {}).get("exact_source_dates_published") is False
        and (channel_quality or {}).get("source_paths_published") is False
        and (channel_quality or {}).get("files_read") == 8
        and (channel_quality or {}).get("sampled_rows") == 1092
        and (channel_quality or {}).get("parseable_timestamp_fraction") == 1.0
        and channel_timebase.get("positive_interval_count", 0) > 0
        and channel_timebase.get("negative_interval_count") == 0
        and channel_timebase.get("duplicate_interval_count") == 0
        and channel_roles.get("pressure", {}).get("finite_fraction") == 1.0
        and channel_roles.get("flow", {}).get("finite_fraction") == 1.0
        and channel_roles.get("discrete_state", {}).get("finite_fraction") == 1.0
        and 0.0 < channel_roles.get("temperature", {}).get("finite_fraction", 0.0) < 1.0
        and (channel_quality or {}).get("discrete_state_transition_count") == 1283
        and channel_eligibility.get("station_channel_quality_recheck_supported") is True
        and channel_eligibility.get("temperature_or_flow_parameter_fit_supported") is False
        and channel_eligibility.get("full_station_vehicle_validation") is False
        and channel_eligibility.get("full_loop_holdout_eligible") is False
    )
    gates.append(_gate(
        "confidential_station_channel_quality_integrity",
        "PASS" if channel_quality_pass else (
            "FAIL" if channel_quality else "PENDING"
        ),
        "The mapped private station channels have a privacy-bounded timebase and quality recheck while un-attested temperature/flow semantics remain excluded from fitting.",
        str(channel_quality_path.relative_to(root)),
        "Timestamp parsing, monotonicity, finite-channel fractions, discrete transitions, privacy flags and explicit no-full-loop eligibility are retained.",
        {
            "files_read": (channel_quality or {}).get("files_read"),
            "sampled_rows": (channel_quality or {}).get("sampled_rows"),
            "parseable_timestamp_fraction": (channel_quality or {}).get(
                "parseable_timestamp_fraction"
            ),
            "timebase": channel_timebase,
            "roles": channel_roles,
            "discrete_state_transition_count": (channel_quality or {}).get(
                "discrete_state_transition_count"
            ),
            "temperature_or_flow_parameter_fit_supported": channel_eligibility.get(
                "temperature_or_flow_parameter_fit_supported"
            ),
            "full_loop_holdout_eligible": channel_eligibility.get(
                "full_loop_holdout_eligible"
            ),
        } if channel_quality else "missing",
    ))

    equipment_drift_path = root / (
        "research/confidential_station_equipment_drift_recheck_2026_10_06.json"
    )
    equipment_drift = _json(equipment_drift_path)
    drift_comparison = (equipment_drift or {}).get("comparison") or {}
    drift_runtime = (equipment_drift or {}).get("runtime_decision") or {}
    drift_eligibility = (equipment_drift or {}).get("eligibility") or {}
    equipment_drift_pass = bool(
        (equipment_drift or {}).get("schema_version") == 1
        and (equipment_drift or {}).get("artifact_type")
        == "confidential_station_equipment_drift_recheck"
        and (equipment_drift or {}).get("source_identifiers_published") is False
        and (equipment_drift or {}).get("raw_rows_persisted") is False
        and (equipment_drift or {}).get("exact_source_dates_published") is False
        and (equipment_drift or {}).get("source_paths_published") is False
        and (equipment_drift or {}).get("fresh_calibration", {}).get("sampled_rows", 0) > 0
        and drift_comparison.get("matches") is False
        and bool(drift_comparison.get("mismatches"))
        and drift_runtime.get("profile_replaced") is False
        and drift_runtime.get("default_model_parameters_changed") is False
        and drift_runtime.get("measured_boundary_calibration_remains_opt_in") is True
        and drift_runtime.get("mismatch_requires_custodian_review") is True
        and drift_eligibility.get("equipment_drift_recheck_supported") is True
        and drift_eligibility.get("temperature_or_flow_parameter_fit_supported") is False
        and drift_eligibility.get("full_station_vehicle_validation") is False
        and drift_eligibility.get("full_loop_holdout_eligible") is False
    )
    gates.append(_gate(
        "confidential_station_equipment_drift_integrity",
        "PASS" if equipment_drift_pass else (
            "FAIL" if equipment_drift else "PENDING"
        ),
        "A fresh private equipment-log window is checked for drift and is prevented from silently replacing the retained station-boundary profile.",
        str(equipment_drift_path.relative_to(root)),
        "Privacy flags, an explicit mismatch, no automatic profile/model update, custodian review requirement and full-loop exclusion are retained.",
        {
            "sampled_rows": (equipment_drift or {}).get("fresh_calibration", {}).get("sampled_rows"),
            "matches": drift_comparison.get("matches"),
            "mismatch_fields": [item.get("field") for item in drift_comparison.get("mismatches", [])],
            "profile_replaced": drift_runtime.get("profile_replaced"),
            "default_model_parameters_changed": drift_runtime.get("default_model_parameters_changed"),
            "mismatch_requires_custodian_review": drift_runtime.get("mismatch_requires_custodian_review"),
            "full_loop_holdout_eligible": drift_eligibility.get("full_loop_holdout_eligible"),
        } if equipment_drift else "missing",
    ))

    schema_audit_path = root / "research/confidential_station_schema_audit_2026_10.json"
    owner_recheck_path = root / "research/private_owner_data_intake_recheck_2026_10_06.json"
    schema_audit = _json(schema_audit_path)
    owner_recheck = _json(owner_recheck_path)
    schema_inventory = (schema_audit or {}).get("signal_inventory") or {}
    schema_eligibility = (schema_audit or {}).get("eligibility") or {}
    schema_units = (schema_audit or {}).get("unit_attestation") or {}
    schema_recheck = (owner_recheck or {}).get("schema_recheck") or {}
    schema_recheck_values = schema_recheck.get("verified_aggregate") or {}
    schema_audit_pass = bool(
        (schema_audit or {}).get("schema_version") == 1
        and (schema_audit or {}).get("artifact_type") == "confidential_station_schema_audit"
        and (schema_audit or {}).get("source_identifiers_published") is False
        and (schema_audit or {}).get("raw_rows_persisted") is False
        and (schema_audit or {}).get("exact_source_dates_published") is False
        and (schema_audit or {}).get("source_bundle_count") >= 2
        and (schema_audit or {}).get("file_count") > 0
        and (schema_inventory.get("tagged_channel_counts") or {}).get("pressure", 0) > 0
        and schema_eligibility.get("station_side_schema_intake_supported") is True
        and schema_eligibility.get("full_station_vehicle_validation") is False
        and schema_eligibility.get("full_loop_holdout_eligible") is False
        and schema_eligibility.get("vehicle_side_channel_family_count") == 0
        and bool(schema_eligibility.get("station_side_component_families_present"))
        and schema_units.get("machine_readable_unit_dictionary_found") is False
        and schema_units.get("pressure_units_attested") is False
        and schema_units.get("temperature_units_attested") is False
        and schema_units.get("flow_units_attested") is False
        and (owner_recheck or {}).get("privacy", {}).get("raw_files_outside_repository") is True
        and schema_recheck.get("committed_aggregate_match") is True
        and schema_recheck_values.get("file_count") == (schema_audit or {}).get("file_count")
        and schema_recheck_values.get("pressure_channel_count") == (schema_inventory.get("tagged_channel_counts") or {}).get("pressure")
        and schema_recheck_values.get("vehicle_side_channel_family_count") == schema_eligibility.get("vehicle_side_channel_family_count")
        and schema_recheck_values.get("full_loop_holdout_eligible") is False
    )
    gates.append(_gate(
        "confidential_station_schema_intake_integrity",
        "PASS" if schema_audit_pass else ("FAIL" if schema_audit else "PENDING"),
        "The restricted station archive has a de-identified channel-presence inventory that identifies station-side calibration candidates without treating unconfirmed units as measurements.",
        f"{schema_audit_path.relative_to(root)}; {owner_recheck_path.relative_to(root)}",
        "At least two source bundles, pressure/state channel candidates, no raw rows or source identifiers, and an explicit unit-attestation hold.",
        {
            "source_bundle_count": (schema_audit or {}).get("source_bundle_count"),
            "file_count": (schema_audit or {}).get("file_count"),
            "tagged_channel_counts": schema_inventory.get("tagged_channel_counts"),
            "unit_attestation": schema_units,
            "privacy_bounded_channel_families": schema_inventory.get(
                "privacy_bounded_channel_families"
            ),
            "vehicle_side_channel_family_count": schema_eligibility.get(
                "vehicle_side_channel_family_count"
            ),
            "station_side_component_families_present": schema_eligibility.get(
                "station_side_component_families_present"
            ),
            "full_loop_holdout_eligible": schema_eligibility.get("full_loop_holdout_eligible"),
            "owner_schema_recheck": {
                "committed_aggregate_match": schema_recheck.get("committed_aggregate_match"),
                "verified_file_count": schema_recheck_values.get("file_count"),
                "verified_pressure_channel_count": schema_recheck_values.get("pressure_channel_count"),
                "verified_vehicle_side_channel_family_count": schema_recheck_values.get("vehicle_side_channel_family_count"),
            },
        } if schema_audit else "missing; confidential schema intake has not completed",
    ))

    external_loop_path = root / "data/public_validation/results/closed_loop_external_holdout/validation.json"
    external_loop = _json(external_loop_path)
    external_protocol_path = root / "research/mc_default_external_holdout_protocol.json"
    external_protocol = _json(external_protocol_path)
    external_search_path = root / "research/external_full_loop_data_search.json"
    external_search = _json(external_search_path)
    external_search_recheck_path = root / "research/public_full_loop_search_recheck_2026_10_05.json"
    external_search_recheck = _json(external_search_recheck_path)
    external_search_latest_path = root / "research/public_full_loop_search_recheck_2026_10_06.json"
    external_search_latest = _json(external_search_latest_path)
    public_full_loop_update_path = root / "research/public_full_loop_data_update_2026_10_08.json"
    public_full_loop_update = _json(public_full_loop_update_path)
    external_search_sweep_path = root / "research/public_full_loop_search_sweep_2026_10_05.json"
    external_search_sweep = _json(external_search_sweep_path)
    external_operational_recheck_path = root / "research/public_operational_benchmark_recheck_2026_10_05.json"
    external_operational_recheck = _json(external_operational_recheck_path)
    external_operational_face_path = root / "research/public_operational_benchmark_face_validity_2026_10_05.json"
    external_operational_face = _json(external_operational_face_path)
    prospective_release_protocol_path = root / "research/apparatus_resolved_release_protocol.json"
    prospective_release_protocol = _json(prospective_release_protocol_path)
    controlled_registry_path = root / "research/controlled_full_loop_cohort_registry.json"
    controlled_registry = _json(controlled_registry_path)
    controlled_registry_pass, controlled_registry_observed = _controlled_registry_integrity(controlled_registry)
    aggregate = (external_loop or {}).get("aggregate") or {}
    protocol_source = (external_protocol or {}).get("source") or {}
    frozen_model = (external_protocol or {}).get("frozen_model") or {}
    protocol_screens = (external_protocol or {}).get("engineering_screens") or {}
    result_screens = (external_loop or {}).get("screening_limits") or {}
    selected_cases = (external_protocol or {}).get("selected_workbooks") or []
    protocol_integrity = bool(
        (external_protocol or {}).get("status")
        == "frozen_before_workbook_outcome_extraction"
        and (external_protocol or {}).get("outcomes_inspected_before_freeze") is False
        and len(selected_cases) == 8
        and (external_loop or {}).get("archive_sha256")
        == protocol_source.get("archive_sha256")
        and (external_loop or {}).get("frozen_model_commit")
        == frozen_model.get("git_commit")
        and (external_loop or {}).get("post_freeze_parameter_tuning") is False
        and (external_loop or {}).get("schedule_mapping")
        == "publisher pressure-schedule endpoint-equivalent constant APRR"
        and result_screens.get("pressure_rmse_mpa")
        == protocol_screens.get("pressure_rmse_mpa_max")
        and result_screens.get("temperature_rmse_c")
        == protocol_screens.get("temperature_rmse_c_max")
        and result_screens.get("soc_final_abs_error_percentage_points")
        == protocol_screens.get("soc_final_abs_error_percentage_points_max")
    )
    public_external_loop_pass = (
        protocol_integrity
        and (external_loop or {}).get("protocol_frozen_before_data_access") is True
        and aggregate.get("case_count", 0)
        >= protocol_screens.get("minimum_evaluable_cases", 8)
        and aggregate.get("screening_pass_fraction", 0.0)
        >= protocol_screens.get("minimum_joint_screen_pass_fraction", 0.80)
        and (external_loop or {}).get("source_worktree_dirty") is False
    )
    external_loop_pass = public_external_loop_pass or controlled_registry_pass
    gates.append(_gate(
        "full_loop_external_validation",
        "PASS" if external_loop_pass else "FAIL",
        "The complete station controller/cascade/precooler loop meets frozen engineering screens on new external cases.",
        f"{external_loop_path.relative_to(root)}; {external_search_path.relative_to(root)}; "
        f"{external_search_recheck_path.relative_to(root)}; {external_operational_recheck_path.relative_to(root)}; "
        f"{external_search_sweep_path.relative_to(root)}; {external_search_latest_path.relative_to(root)}; "
        f"{public_full_loop_update_path.relative_to(root)}; {methytrucks_path.relative_to(root)}; "
        f"{prospective_release_protocol_path.relative_to(root)}; {controlled_registry_path.relative_to(root)}",
        "Hash-locked protocol and model, clean-source external holdout with >=8 cases and >=80% screen pass fraction.",
        {
            "protocol_integrity": protocol_integrity,
            "public_external_loop_pass": public_external_loop_pass,
            "aggregate": aggregate,
            "controlled_cohort_registry": controlled_registry_observed,
            "new_external_data_search": {
                "status": (external_search or {}).get("status"),
                "next_action": (external_search or {}).get("next_action"),
                "claim_limit": (external_search or {}).get("claim_limit"),
            },
            "search_recheck_2026_10_04": {
                "result": (external_search_recheck or {}).get("result"),
                "gate_impact": (external_search_recheck or {}).get("gate_impact"),
                "candidate_count": len((external_search_recheck or {}).get("candidates") or []),
            },
            "search_recheck_2026_10_06": {
                "result": (external_search_latest or {}).get("result"),
                "gate_impact": (external_search_latest or {}).get("gate_impact"),
                "candidate_count": len((external_search_latest or {}).get("candidates") or []),
                "claim_boundary": (external_search_latest or {}).get("claim_boundary"),
            },
            "public_data_update_2026_10_08": {
                "status": (public_full_loop_update or {}).get("status"),
                "gate_impact": (public_full_loop_update or {}).get("gate_impact"),
                "eligibility": (public_full_loop_update or {}).get("eligibility"),
                "claim_boundary": (public_full_loop_update or {}).get("claim_boundary"),
            },
            "methytrucks_hysam_postaccess_diagnostic": {
                "status": (methytrucks or {}).get("status"),
                "evidence_role": (methytrucks or {}).get("evidence_role"),
                "pressure_rmse_mpa": methytrucks_pressure.get("rmse_mpa"),
                "temperature_rmse_c": methytrucks_temperature.get("rmse_c"),
                "candidate_session_aggregate": methytrucks_aggregate,
                "eligibility": methytrucks_eligibility,
            },
            "live_public_search_sweep_2026_10_05": {
                "result": (external_search_sweep or {}).get("result"),
                "gate_impact": (external_search_sweep or {}).get("gate_impact"),
                "candidate_count": len((external_search_sweep or {}).get("candidates") or []),
                "claim_boundary": (external_search_sweep or {}).get("claim_boundary"),
            },
            "operational_benchmark_recheck_2026_10_05": {
                "result": (external_operational_recheck or {}).get("result"),
                "gate_impact": (external_operational_recheck or {}).get("gate_impact"),
                "candidate_count": len((external_operational_recheck or {}).get("candidates") or []),
            },
            "operational_benchmark_face_validity_2026_10_05": {
                "result": (external_operational_face or {}).get("result"),
                "external_validation_status": (external_operational_face or {}).get("external_validation_status"),
                "goal_completion_permitted": (external_operational_face or {}).get("goal_completion_permitted"),
                "claim_boundary": "Nominal operating-range context only; no synchronized full-loop validation claim.",
            },
            "prospective_apparatus_resolved_release_protocol": {
                "status": (prospective_release_protocol or {}).get("status"),
                "external_validation_status": (prospective_release_protocol or {}).get("promotion_gate", {}).get("external_validation_status"),
                "full_loop_holdout_eligible": (prospective_release_protocol or {}).get("promotion_gate", {}).get("full_loop_holdout_eligible"),
                "goal_completion_permitted": (prospective_release_protocol or {}).get("promotion_gate", {}).get("goal_completion_permitted"),
            },
        } if external_loop else "missing; current internal comparisons pass 0/8 and 0/11",
    ))

    request_package_path = root / "research/full_loop_raw_data_request_package_2026_10_05.json"
    request_package = _json(request_package_path)
    request_channels = (request_package or {}).get("minimum_channels") or []
    request_rights = (request_package or {}).get("rights_requirements") or []
    request_guard = (request_package or {}).get("evaluation_guard") or {}
    request_package_pass = bool(
        (request_package or {}).get("schema_version") == 1
        and (request_package or {}).get("status") == "REQUEST_SPECIFICATION_ONLY"
        and len(request_channels) >= 10
        and len(request_rights) >= 4
        and len((request_package or {}).get("custodian_routes") or []) >= 6
        and request_guard.get("freeze_before_outcome_access") is True
        and request_guard.get("post_freeze_parameter_tuning") is False
        and request_guard.get("goal_completion_permitted") is False
        and "not evidence" in str((request_package or {}).get("claim_boundary", "")).lower()
    )
    gates.append(_gate(
        "full_loop_raw_data_request_package_integrity",
        "PASS" if request_package_pass else ("FAIL" if request_package else "PENDING"),
        "The full-loop acquisition request specifies required channels, reuse rights and a pre-outcome freeze without claiming access or validation.",
        str(request_package_path.relative_to(root)),
        "At least ten required channel/metadata fields, four rights requirements, six custodian routes and an explicit non-claiming evaluation guard.",
        {
            "minimum_channel_count": len(request_channels),
            "rights_requirement_count": len(request_rights),
            "custodian_route_count": len((request_package or {}).get("custodian_routes") or []),
            "freeze_before_outcome_access": request_guard.get("freeze_before_outcome_access"),
            "post_freeze_parameter_tuning": request_guard.get("post_freeze_parameter_tuning"),
            "goal_completion_permitted": request_guard.get("goal_completion_permitted"),
        } if request_package else "missing; full-loop raw-data request package has not been created",
    ))

    field_article_path = root / "research/keti_bam_hrs_article_data_boundary_2026_10_05.json"
    field_article = _json(field_article_path)
    field_source = (field_article or {}).get("source") or {}
    field_evidence = (field_article or {}).get("observed_evidence") or {}
    field_decision = (field_article or {}).get("eligibility_decision") or {}
    field_article_pass = bool(
        (field_article or {}).get("schema_version") == 1
        and field_source.get("doi") == "10.3390/app16157856"
        and field_source.get("license") == "CC BY 4.0"
        and field_evidence.get("facility")
        and field_evidence.get("reported_sensor_count") == 8
        and field_evidence.get("reported_measurements")
        and field_evidence.get("field_integration") is True
        and field_decision.get("full_loop_external_holdout_eligible") is False
        and field_decision.get("reason")
        and field_article.get("claim_boundary")
    )
    gates.append(_gate(
        "real_station_article_boundary_integrity",
        "PASS" if field_article_pass else ("FAIL" if field_article else "PENDING"),
        "The public BAM/KETI field-validation article is recorded as an auditable real-station context and data-request lead without being promoted to raw full-loop validation.",
        str(field_article_path.relative_to(root)),
        "DOI/licence, reported field channels and integration, explicit missing raw-log boundary, and a false full-loop eligibility flag.",
        {
            "doi": field_source.get("doi"),
            "facility": field_evidence.get("facility"),
            "reported_sensor_count": field_evidence.get("reported_sensor_count"),
            "full_loop_external_holdout_eligible": field_decision.get("full_loop_external_holdout_eligible"),
            "claim_boundary": (field_article or {}).get("claim_boundary"),
        } if field_article else "missing; public field article boundary record has not been captured",
    ))

    zbt_article_path = root / "research/zbt_hrs_sampling_article_data_boundary_2026_10_05.json"
    zbt_article = _json(zbt_article_path)
    zbt_source = (zbt_article or {}).get("source") or {}
    zbt_evidence = (zbt_article or {}).get("observed_evidence") or {}
    zbt_config = zbt_evidence.get("station_configuration") or {}
    zbt_decision = (zbt_article or {}).get("eligibility_decision") or {}
    zbt_article_pass = bool(
        (zbt_article or {}).get("schema_version") == 1
        and zbt_source.get("doi") == "10.3390/cleantechnol8030091"
        and "raw measurements" in str(zbt_source.get("license") or "")
        and zbt_evidence.get("facility")
        and zbt_config.get("storage_banks") == 7
        and zbt_config.get("dispensing_pressure_classes_mpa") == [35, 70]
        and zbt_evidence.get("reported_measurements")
        and zbt_evidence.get("raw_synchronized_rows_public") is False
        and zbt_decision.get("full_loop_external_holdout_eligible") is False
        and zbt_decision.get("reason")
        and zbt_article.get("claim_boundary")
    )
    gates.append(_gate(
        "zbt_hrs_sampling_article_boundary_integrity",
        "PASS" if zbt_article_pass else ("FAIL" if zbt_article else "PENDING"),
        "The public ZBT HRS sampling article is recorded as a real multi-bank station data-request lead without being promoted to raw full-loop validation.",
        str(zbt_article_path.relative_to(root)),
        "DOI, real station configuration, logged dispenser/tank evidence, author-request-only raw-data boundary and false full-loop eligibility flag.",
        {
            "doi": zbt_source.get("doi"),
            "facility": zbt_evidence.get("facility"),
            "storage_banks": zbt_config.get("storage_banks"),
            "dispensing_pressure_classes_mpa": zbt_config.get("dispensing_pressure_classes_mpa"),
            "raw_synchronized_rows_public": zbt_evidence.get("raw_synchronized_rows_public"),
            "full_loop_external_holdout_eligible": zbt_decision.get("full_loop_external_holdout_eligible"),
            "claim_boundary": (zbt_article or {}).get("claim_boundary"),
        } if zbt_article else "missing; ZBT HRS sampling article boundary record has not been captured",
    ))

    kgs_access_path = root / "research/kgs_hrs_code_access_recheck_2026_10_05.json"
    kgs_access = _json(kgs_access_path)
    kgs_access_source = (kgs_access or {}).get("source") or {}
    kgs_access_check = (kgs_access or {}).get("anonymous_access_check") or {}
    kgs_access_classification = (kgs_access or {}).get("classification") or {}
    kgs_access_pass = bool(
        (kgs_access or {}).get("schema_version") == 1
        and kgs_access_source.get("published_doi") == "10.1007/s11814-025-00551-9"
        and kgs_access_source.get("preprint_doi") == "10.21203/rs.3.rs-6248350/v1"
        and kgs_access_source.get("reported_real_hrs_scenarios") == 6
        and kgs_access_source.get("reported_measurements")
        and kgs_access_check.get("result") == "REDIRECTED_TO_SIGN_IN"
        and kgs_access_check.get("files_retrieved") == 0
        and kgs_access_classification.get("real_station_provenance") is True
        and kgs_access_classification.get("public_raw_logger_available") is False
        and kgs_access_classification.get("full_loop_station_vehicle_holdout_eligible") is False
        and kgs_access_classification.get("goal_completion_permitted") is False
        and len((kgs_access or {}).get("minimum_requested_package") or []) >= 7
        and (kgs_access or {}).get("claim_boundary")
    )
    gates.append(_gate(
        "kgs_real_station_access_boundary_integrity",
        "PASS" if kgs_access_pass else ("FAIL" if kgs_access else "PENDING"),
        "The KGS-linked real-station fueling study is retained as a high-value acquisition lead with an independently recorded anonymous-access boundary.",
        str(kgs_access_path.relative_to(root)),
        "Published/preprint DOI, six reported scenarios, measured channels, sign-in redirect result, requested raw package and false full-loop/goal flags.",
        {
            "published_doi": kgs_access_source.get("published_doi"),
            "reported_real_hrs_scenarios": kgs_access_source.get("reported_real_hrs_scenarios"),
            "access_result": kgs_access_check.get("result"),
            "files_retrieved": kgs_access_check.get("files_retrieved"),
            "full_loop_station_vehicle_holdout_eligible": kgs_access_classification.get("full_loop_station_vehicle_holdout_eligible"),
        } if kgs_access else "missing",
    ))

    kgs_appendix_path = root / "research/kgs_oh_preprint_appendix_recheck_2026_10_05.json"
    kgs_appendix = _json(kgs_appendix_path)
    kgs_appendix_source = (kgs_appendix or {}).get("source") or {}
    kgs_appendix_access = (kgs_appendix or {}).get("appendix_access") or {}
    kgs_appendix_code = (kgs_appendix or {}).get("code_access") or {}
    kgs_appendix_classification = (kgs_appendix or {}).get("classification") or {}
    kgs_appendix_pass = bool(
        (kgs_appendix or {}).get("schema_version") == 1
        and kgs_appendix_source.get("published_doi") == "10.1007/s11814-025-00551-9"
        and kgs_appendix_source.get("reported_real_hrs_scenarios") == 6
        and kgs_appendix_access.get("pdf_pages") == 2
        and kgs_appendix_access.get("appendix_sha256_matches_expected") is True
        and all((kgs_appendix_access.get("required_table_terms_present") or {}).values())
        and kgs_appendix_access.get("raw_synchronized_logger_present") is False
        and kgs_appendix_code.get("result") == "REDIRECTED_TO_SIGN_IN"
        and kgs_appendix_code.get("files_retrieved") == 0
        and kgs_appendix_classification.get("full_loop_station_vehicle_holdout_eligible") is False
        and kgs_appendix_classification.get("goal_completion_permitted") is False
        and (kgs_appendix or {}).get("claim_boundary")
    )
    gates.append(_gate(
        "kgs_preprint_appendix_access_boundary_integrity",
        "PASS" if kgs_appendix_pass else ("FAIL" if kgs_appendix else "PENDING"),
        "The public KGS/Oh supplement and code link are rechecked and retained without promoting parameter tables to a raw full-loop holdout.",
        str(kgs_appendix_path.relative_to(root)),
        "Two-page appendix hash, Table A.1/A.2/A.3 terms, no synchronized logger rows, sign-in redirect and false eligibility/completion flags.",
        {
            "published_doi": kgs_appendix_source.get("published_doi"),
            "pdf_pages": kgs_appendix_access.get("pdf_pages"),
            "appendix_sha256_matches_expected": kgs_appendix_access.get("appendix_sha256_matches_expected"),
            "code_access_result": kgs_appendix_code.get("result"),
            "full_loop_station_vehicle_holdout_eligible": kgs_appendix_classification.get("full_loop_station_vehicle_holdout_eligible"),
        } if kgs_appendix else "missing",
    ))

    nbsdc_recheck_path = root / "research/nbsdc_winter_olympics_access_recheck_2026_10_05.json"
    nbsdc_recheck = _json(nbsdc_recheck_path)
    nbsdc_source = (nbsdc_recheck or {}).get("source") or {}
    nbsdc_decision = (nbsdc_recheck or {}).get("eligibility_decision") or {}
    nbsdc_probes = ((nbsdc_recheck or {}).get("api_evidence") or {}).get("raw_file_probes") or []
    nbsdc_recheck_pass = bool(
        (nbsdc_recheck or {}).get("schema_version") == 1
        and nbsdc_source.get("cstr") == "CSTR:16666.11.nbsdc.aI3fJrzX"
        and nbsdc_source.get("share_range") == "审批后共享"
        and len((nbsdc_recheck or {}).get("public_file_inventory") or []) == 3
        and len(nbsdc_probes) == 3
        and all((probe.get("response") or {}).get("code") == 403 for probe in nbsdc_probes)
        and nbsdc_decision.get("full_loop_public_holdout") is False
        and nbsdc_decision.get("high_value_request_candidate") is True
        and (nbsdc_recheck or {}).get("claim_boundary")
    )
    gates.append(_gate(
        "nbsdc_current_access_recheck_integrity",
        "PASS" if nbsdc_recheck_pass else ("FAIL" if nbsdc_recheck else "PENDING"),
        "The current NBSDC HRS operational archive metadata and raw-file access boundary are reproducibly recorded without treating gated files as validation data.",
        str(nbsdc_recheck_path.relative_to(root)),
        "CSTR, approval-required sharing range, three-file inventory, three application-required probes, false holdout eligibility and claim boundary.",
        {
            "cstr": nbsdc_source.get("cstr"),
            "share_range": nbsdc_source.get("share_range"),
            "file_count": len((nbsdc_recheck or {}).get("public_file_inventory") or []),
            "raw_probe_codes": [(probe.get("response") or {}).get("code") for probe in nbsdc_probes],
            "full_loop_public_holdout": nbsdc_decision.get("full_loop_public_holdout"),
        } if nbsdc_recheck else "missing",
    ))

    jetfire_path = root / "research/carboni_2022_jetfire_supplement_data_boundary_2026_10_05.json"
    jetfire = _json(jetfire_path)
    jetfire_source = (jetfire or {}).get("source") or {}
    jetfire_artifact = (jetfire or {}).get("artifact_integrity") or {}
    jetfire_evidence = (jetfire or {}).get("observed_evidence") or {}
    jetfire_decision = (jetfire or {}).get("eligibility_decision") or {}
    jetfire_boundary_pass = bool(
        (jetfire or {}).get("schema_version") == 1
        and jetfire_source.get("doi") == "10.1016/j.ijhydene.2022.05.010"
        and jetfire_source.get("supplement_url", "").startswith("https://")
        and jetfire_source.get("article_open_access") is False
        and jetfire_source.get("reuse_license") == "not established"
        and len(jetfire_artifact.get("sha256", "")) == 64
        and jetfire_artifact.get("bytes") == 21579714
        and jetfire_evidence.get("reported_test_count") == 17
        and jetfire_evidence.get("machine_readable_synchronized_time_series") is False
        and jetfire_decision.get("full_loop_external_holdout_eligible") is False
        and jetfire_decision.get("consequence_component_context_eligible") is False
        and (jetfire or {}).get("claim_boundary")
    )
    gates.append(_gate(
        "jetfire_supplement_rights_boundary_integrity",
        "PASS" if jetfire_boundary_pass else ("FAIL" if jetfire else "PENDING"),
        "The publicly reachable IJHE jet-fire supplement is traceable without treating a rights-uncleared plot artifact as validation data.",
        str(jetfire_path.relative_to(root)),
        "DOI/URL, artifact hash and scope, article rights boundary, non-machine-readable limitation, and explicit false eligibility flags.",
        {
            "doi": jetfire_source.get("doi"),
            "sha256": jetfire_artifact.get("sha256"),
            "reported_test_count": jetfire_evidence.get("reported_test_count"),
            "article_open_access": jetfire_source.get("article_open_access"),
            "full_loop_external_holdout_eligible": jetfire_decision.get("full_loop_external_holdout_eligible"),
            "claim_boundary": (jetfire or {}).get("claim_boundary"),
        } if jetfire else "missing; supplement rights/data-boundary record has not been captured",
    ))

    calstate_b2b_path = root / "research/calstate_la_back_to_back_article_data_boundary_2026_10_05.json"
    calstate_b2b = _json(calstate_b2b_path)
    calstate_b2b_source = (calstate_b2b or {}).get("source") or {}
    calstate_b2b_evidence = (calstate_b2b or {}).get("observed_evidence") or {}
    calstate_b2b_decision = (calstate_b2b or {}).get("eligibility_decision") or {}
    calstate_b2b_pass = bool(
        (calstate_b2b or {}).get("schema_version") == 1
        and calstate_b2b_source.get("doi") == "10.1016/j.jclepro.2021.129737"
        and calstate_b2b_source.get("article_open_access") is False
        and calstate_b2b_source.get("reuse_license") == "not established for the operator logs"
        and calstate_b2b_evidence.get("facility")
        and calstate_b2b_evidence.get("field_integration") is True
        and calstate_b2b_evidence.get("public_raw_synchronized_rows") is False
        and calstate_b2b_decision.get("full_loop_external_holdout_eligible") is False
        and (calstate_b2b or {}).get("claim_boundary")
    )
    gates.append(_gate(
        "calstate_back_to_back_article_boundary_integrity",
        "PASS" if calstate_b2b_pass else ("FAIL" if calstate_b2b else "PENDING"),
        "The Cal State LA back-to-back fueling article is recorded as real-station context without promoting non-public operator logs to validation data.",
        str(calstate_b2b_path.relative_to(root)),
        "DOI/rights boundary, facility and field scope, explicit missing raw synchronized rows, and a false full-loop eligibility flag.",
        {
            "doi": calstate_b2b_source.get("doi"),
            "facility": calstate_b2b_evidence.get("facility"),
            "article_open_access": calstate_b2b_source.get("article_open_access"),
            "public_raw_synchronized_rows": calstate_b2b_evidence.get("public_raw_synchronized_rows"),
            "full_loop_external_holdout_eligible": calstate_b2b_decision.get("full_loop_external_holdout_eligible"),
            "claim_boundary": (calstate_b2b or {}).get("claim_boundary"),
        } if calstate_b2b else "missing; Cal State LA back-to-back data-boundary record has not been captured",
    ))

    rheadhy_path = root / "research/rheadhy_2026_campaign_data_boundary_2026_10_05.json"
    rheadhy = _json(rheadhy_path)
    rheadhy_source = (rheadhy or {}).get("source") or {}
    rheadhy_evidence = (rheadhy or {}).get("observed_evidence") or {}
    rheadhy_decision = (rheadhy or {}).get("eligibility_decision") or {}
    rheadhy_pass = bool(
        (rheadhy or {}).get("schema_version") == 1
        and rheadhy_source.get("operator_source")
        and rheadhy_source.get("project_reporting")
        and rheadhy_source.get("project_doi") == "10.3030/101101443"
        and rheadhy_evidence.get("facility")
        and rheadhy_evidence.get("campaign") == "18 refuelling tests over six days"
        and rheadhy_evidence.get("raw_synchronized_rows") is False
        and rheadhy_decision.get("full_loop_external_holdout_eligible") is False
        and (rheadhy or {}).get("claim_boundary")
    )
    gates.append(_gate(
        "rheadhy_campaign_boundary_integrity",
        "PASS" if rheadhy_pass else ("FAIL" if rheadhy else "PENDING"),
        "The public RHeaDHy heavy-duty campaign is recorded as real-station face-validity context without promoting aggregate press-release results to a synchronized full-loop holdout.",
        str(rheadhy_path.relative_to(root)),
        "Operator and EU source links, project DOI, campaign scope, explicit missing raw rows, and a false full-loop eligibility flag.",
        {
            "project_doi": rheadhy_source.get("project_doi"),
            "facility": rheadhy_evidence.get("facility"),
            "campaign": rheadhy_evidence.get("campaign"),
            "raw_synchronized_rows": rheadhy_evidence.get("raw_synchronized_rows"),
            "full_loop_external_holdout_eligible": rheadhy_decision.get("full_loop_external_holdout_eligible"),
            "claim_boundary": (rheadhy or {}).get("claim_boundary"),
        } if rheadhy else "missing; RHeaDHy campaign data-boundary record has not been captured",
    ))

    temperature_diagnostic_path = root / "research/closed_loop_temperature_stop_diagnostic_2026_10_04.json"
    temperature_diagnostic = _json(temperature_diagnostic_path)
    temperature_runs = (temperature_diagnostic or {}).get("runs") or []
    temperature_run = next(
        (run for run in temperature_runs if run.get("temperature_limit_c") == 95.0),
        None,
    )
    temperature_aggregate = (temperature_run or {}).get("aggregate") or {}
    temperature_metrics = temperature_aggregate.get("metrics") or {}
    temperature_diagnostic_pass = bool(
        (temperature_diagnostic or {}).get("diagnostic_type")
        == "post-outcome temperature-stop sensitivity"
        and (temperature_diagnostic or {}).get("post_outcome") is True
        and "none" in str((temperature_diagnostic or {}).get("validation_gate_effect", "")).lower()
        and (temperature_diagnostic or {}).get("parameter_fitting") is False
        and temperature_aggregate.get("case_count") == 8
        and temperature_aggregate.get("screening_pass_count") == 0
        and temperature_aggregate.get("final_stop_reason_counts") == {"none": 8}
        and len((temperature_run or {}).get("cases") or []) == 8
        and abs(float((temperature_metrics.get("pressure_rmse_mpa") or {}).get("mean", 0.0)) - 10.217206686917415) < 1e-9
        and abs(float((temperature_metrics.get("temperature_rmse_c") or {}).get("mean", 0.0)) - 14.301028885284389) < 1e-9
        and abs(float((temperature_metrics.get("soc_rmse_percentage_points") or {}).get("mean", 0.0)) - 12.605456644129966) < 1e-9
    )
    gates.append(_gate(
        "closed_loop_temperature_stop_diagnostic",
        "PASS" if temperature_diagnostic_pass else ("FAIL" if temperature_diagnostic else "PENDING"),
        "The post-outcome temperature-stop sensitivity is archived without changing the frozen external validation decision.",
        str(temperature_diagnostic_path.relative_to(root)),
        "Eight identical MC Default traces, 95 °C counterfactual, no parameter fitting, no screening pass and no temperature-stop termination.",
        {
            "diagnostic_type": (temperature_diagnostic or {}).get("diagnostic_type"),
            "post_outcome": (temperature_diagnostic or {}).get("post_outcome"),
            "aggregate": temperature_aggregate,
            "claim_limit": (temperature_diagnostic or {}).get("validation_gate_effect"),
        } if temperature_diagnostic else "missing",
    ))

    acquisition_tracker_path = root / "research/validation_data_acquisition_tracker.json"
    acquisition_tracker = _json(acquisition_tracker_path)
    acquisition_candidates = (acquisition_tracker or {}).get("candidates") or []
    acquisition_tracker_pass = bool(
        (acquisition_tracker or {}).get("status") == "open_data_not_yet_received"
        and len(acquisition_candidates) >= 15
        and "not evidence" in str((acquisition_tracker or {}).get("claim_boundary", "")).lower()
        and all(
            isinstance(candidate.get("draft"), str)
            and (root / candidate["draft"]).is_file()
            and str(candidate.get("source", "")).startswith(("http://", "https://"))
            for candidate in acquisition_candidates
        )
    )
    gates.append(_gate(
        "validation_data_acquisition_tracker",
        "PASS" if acquisition_tracker_pass else ("FAIL" if acquisition_tracker else "PENDING"),
        "Independent raw-data acquisition routes are recorded with acceptance, rights and claim-boundary checks without treating requests as evidence.",
        str(acquisition_tracker_path.relative_to(root)),
        "At least 15 candidate routes, existing draft request for every route, source URL and explicit non-evidentiary boundary.",
        {
            "status": (acquisition_tracker or {}).get("status"),
            "candidate_count": len(acquisition_candidates),
            "draft_count": sum(
                1 for candidate in acquisition_candidates
                if candidate.get("status") == "request_draft_ready"
            ),
            "claim_boundary": (acquisition_tracker or {}).get("claim_boundary"),
        } if acquisition_tracker else "missing",
    ))

    intake_protocol_path = root / "research/external_hrs_intake_protocol.json"
    intake_validator_path = root / "scripts/validate_external_hrs_manifest.py"
    intake_test_path = root / "tests/test_external_hrs_eligibility.py"
    intake_protocol = _json(intake_protocol_path)
    required_metadata = set((intake_protocol or {}).get("required_metadata") or [])
    provenance_fields = {
        "source_identity", "custodian_or_archive", "acquired_at_utc",
        "license_or_reuse_reference",
    }
    validator_text = (
        intake_validator_path.read_text(encoding="utf-8")
        if intake_validator_path.is_file() else ""
    )
    intake_contract_pass = bool(
        (intake_protocol or {}).get("status") == "prospective_intake_contract"
        and (intake_protocol or {}).get("outcomes_accessed_before_freeze") is False
        and provenance_fields.issubset(required_metadata)
        and intake_validator_path.is_file()
        and intake_test_path.is_file()
        and "SHA-256" in validator_text
        and "CSV/XLSX/Parquet" in validator_text
        and "never opens" in validator_text
    )
    gates.append(_gate(
        "external_hrs_intake_integrity_contract",
        "PASS" if intake_contract_pass else "FAIL",
        "The prospective external HRS intake contract rechecks quarantine-file integrity without parsing measurements and records source/reuse provenance.",
        f"{intake_protocol_path.relative_to(root)}; {intake_validator_path.relative_to(root)}; {intake_test_path.relative_to(root)}",
        "Frozen protocol, required provenance fields, safe paths, byte counts, SHA-256 verification and regression tests that never inspect numeric values.",
        {
            "required_provenance_fields": sorted(provenance_fields),
            "validator_present": intake_validator_path.is_file(),
            "regression_test_present": intake_test_path.is_file(),
        },
    ))

    trace_validator_path = root / "scripts/validate_external_hrs_trace.py"
    trace_test_path = root / "tests/test_external_hrs_trace_quality.py"
    trace_quality = (intake_protocol or {}).get("trace_quality") or {}
    trace_contract_pass = bool(
        isinstance(trace_quality, dict)
        and trace_quality.get("minimum_rows", 0) >= 20
        and 0.0 < trace_quality.get("max_missing_fraction", 0.0) <= 0.01
        and trace_quality.get("max_gap_s", 0.0) > 0.0
        and trace_validator_path.is_file()
        and trace_test_path.is_file()
        and "QUALITY_SCREEN_PASS" in trace_validator_path.read_text(encoding="utf-8")
        and "does not impute" in trace_validator_path.read_text(encoding="utf-8")
    )
    gates.append(_gate(
        "external_hrs_trace_quality_contract",
        "PASS" if trace_contract_pass else "FAIL",
        "The post-intake external HRS trace-quality screen is frozen for time-base, missingness and range checks without imputation or model scoring.",
        f"{intake_protocol_path.relative_to(root)}; {trace_validator_path.relative_to(root)}; {trace_test_path.relative_to(root)}",
        "Predeclared minimum rows, missingness and gap/range limits with regression tests for valid, non-monotonic and incomplete traces.",
        {
            "minimum_rows": trace_quality.get("minimum_rows"),
            "max_missing_fraction": trace_quality.get("max_missing_fraction"),
            "max_gap_s": trace_quality.get("max_gap_s"),
            "validator_present": trace_validator_path.is_file(),
            "regression_test_present": trace_test_path.is_file(),
        },
    ))

    byrnes_protocol_path = root / "research/byrnes_zenodo_exploratory_protocol.json"
    byrnes_result_path = root / "research/byrnes_zenodo_exploratory_result.json"
    byrnes_protocol = _json(byrnes_protocol_path)
    byrnes_result = _json(byrnes_result_path)
    byrnes_aggregate = (byrnes_result or {}).get("aggregate") or {}
    byrnes_screen_pass = bool(
        (byrnes_protocol or {}).get("status") == "exploratory_post_access_screen"
        and (byrnes_protocol or {}).get("evidence_role") == "post_access_exploratory_screening"
        and (byrnes_protocol or {}).get("outcomes_accessed_before_freeze") is True
        and (byrnes_result or {}).get("status") == "completed_post_access_exploratory_screen"
        and (byrnes_result or {}).get("evidence_role") == "post_access_exploratory_screening"
        and byrnes_aggregate.get("case_count") == 3
        and byrnes_aggregate.get("joint_screen_pass_count") == 2
        and byrnes_aggregate.get("claim_supported") is False
        and "not a prospective validation gate" in str(
            (byrnes_result or {}).get("claim_boundary", "")
        )
    )
    gates.append(_gate(
        "byrnes_zenodo_exploratory_screen_integrity",
        "PASS" if byrnes_screen_pass else ("FAIL" if byrnes_result else "PENDING"),
        "The newly located open Byrnes hydrogen-release archive is replayed as transparent post-access exploratory evidence without being promoted to validation.",
        f"{byrnes_protocol_path.relative_to(root)}; {byrnes_result_path.relative_to(root)}",
        "Three retained cases, 2/3 joint screen result, explicit post-access status and false claim-supported flag.",
        {
            "evidence_role": (byrnes_result or {}).get("evidence_role"),
            "aggregate": byrnes_aggregate,
            "claim_boundary": (byrnes_result or {}).get("claim_boundary"),
        } if byrnes_result else "missing",
    ))

    pressure_protocol_path = root / "research/zenodo_4106101_pressure_peaking_protocol.json"
    pressure_result_path = root / "research/zenodo_4106101_pressure_peaking_result.json"
    pressure_protocol = _json(pressure_protocol_path)
    pressure_result = _json(pressure_result_path)
    pressure_aggregate = (pressure_result or {}).get("aggregate") or {}
    pressure_screen_pass = bool(
        (pressure_protocol or {}).get("status")
        == "prospective_protocol_frozen_before_data_access"
        and (pressure_protocol or {}).get("evidence_role")
        == "prospective_external_consequence_validation_protocol"
        and ((pressure_protocol or {}).get("freeze") or {}).get(
            "outcomes_accessed_before_freeze"
        ) is False
        and ((pressure_protocol or {}).get("freeze") or {}).get(
            "protocol_frozen_before_raw_download"
        ) is True
        and (pressure_result or {}).get("status")
        == "completed_prospective_protocol_execution"
        and (pressure_result or {}).get("evidence_role")
        == "prospective_external_consequence_validation_result"
        and pressure_aggregate.get("eligible_case_count") == 10
        and pressure_aggregate.get("joint_primary_pass_count") == 7
        and pressure_aggregate.get("confirmatory_rule_met") is False
        and "not validation of the full HRS fueling loop" in str(
            (pressure_result or {}).get("claim_boundary", "")
        )
    )
    gates.append(_gate(
        "zenodo_4106101_pressure_peaking_screen_integrity",
        "PASS" if pressure_screen_pass else ("FAIL" if pressure_result else "PENDING"),
        "The prospective Zenodo pressure-peaking screen is reproducible and remains explicitly exploratory rather than full-loop validation.",
        f"{pressure_protocol_path.relative_to(root)}; {pressure_result_path.relative_to(root)}",
        "Protocol frozen before outcomes, ten eligible cases, 7/10 joint primary passes, false confirmatory flag and explicit full-loop claim boundary.",
        {
            "evidence_role": (pressure_result or {}).get("evidence_role"),
            "aggregate": pressure_aggregate,
            "claim_boundary": (pressure_result or {}).get("claim_boundary"),
        } if pressure_result else "missing",
    ))

    mendeley_manifest_path = root / "research/mendeley_usn_pressure_peaking_manifest_2026_10_05.json"
    mendeley_manifest = _json(mendeley_manifest_path)
    mendeley_public = (mendeley_manifest or {}).get("public_manifest") or {}
    mendeley_eligibility = (mendeley_manifest or {}).get("eligibility") or {}
    mendeley_manifest_pass = bool(
        (mendeley_manifest or {}).get("status") == "completed_public_manifest_recheck"
        and ((mendeley_manifest or {}).get("source") or {}).get("doi") == "10.17632/pmk59x4hvc.1"
        and ((mendeley_manifest or {}).get("source") or {}).get("license") == "CC BY 4.0"
        and mendeley_public.get("case_count_expected") == 10
        and mendeley_public.get("case_count_with_pressure_and_mass_flow") == 10
        and mendeley_public.get("all_case_identities_present") is True
        and mendeley_eligibility.get("component_consequence_holdout_eligible") is True
        and mendeley_eligibility.get("full_loop_external_holdout_eligible") is False
        and "not a gaseous H70 station-to-vehicle" in str(
            (mendeley_manifest or {}).get("claim_boundary", "")
        )
    )
    gates.append(_gate(
        "mendeley_usn_pressure_peaking_manifest_integrity",
        "PASS" if mendeley_manifest_pass else ("FAIL" if mendeley_manifest else "PENDING"),
        "The CC BY 4.0 Mendeley mirror of the USN pressure-peaking campaign has ten raw pressure/mass-flow cases in its public manifest and remains a consequence-component archive only.",
        str(mendeley_manifest_path.relative_to(root)),
        "Ten case identities, CC BY 4.0 provenance, raw pressure and mass-flow channels, and an explicit non-full-loop boundary.",
        {
            "doi": ((mendeley_manifest or {}).get("source") or {}).get("doi"),
            "license": ((mendeley_manifest or {}).get("source") or {}).get("license"),
            "case_count": mendeley_public.get("case_count_with_pressure_and_mass_flow"),
            "component_consequence_holdout_eligible": mendeley_eligibility.get("component_consequence_holdout_eligible"),
            "full_loop_external_holdout_eligible": mendeley_eligibility.get("full_loop_external_holdout_eligible"),
            "claim_boundary": (mendeley_manifest or {}).get("claim_boundary"),
        } if mendeley_manifest else "missing",
    ))

    elvhys_replay_path = root / "research/elvhys_auxiliary_replay.json"
    elvhys_replay = _json(elvhys_replay_path)
    elvhys_claims = (elvhys_replay or {}).get("claims") or {}
    elvhys_cases = (elvhys_replay or {}).get("cases") or []
    elvhys_concentration_cases = (elvhys_replay or {}).get("concentration_cases") or []
    elvhys_files = (elvhys_replay or {}).get("file_manifest") or []
    elvhys_replay_pass = bool(
        (elvhys_replay or {}).get("status") == "completed_post_access_auxiliary_replay"
        and (elvhys_replay or {}).get("evidence_role")
        == "public_consequence_auxiliary_provenance_and_replay"
        and len(elvhys_cases) == 3
        and len(elvhys_concentration_cases) == 1
        and (elvhys_concentration_cases[0].get("channel_count") == 16)
        and len(elvhys_files) == 9
        and all((case.get("pressure_time") or {}).get("monotonic_strict") is True for case in elvhys_cases)
        and all((case.get("flow_time") or {}).get("monotonic_strict") is True for case in elvhys_cases)
        and elvhys_claims.get("provenance_integrity_pass") is True
        and elvhys_claims.get("predictive_model_validation_permitted") is False
        and elvhys_claims.get("full_loop_station_vehicle_validation_permitted") is False
        and ((elvhys_replay or {}).get("selection") or {}).get("outcomes_accessed_before_freeze") is True
    )
    gates.append(_gate(
        "elvhys_auxiliary_replay_integrity",
        "PASS" if elvhys_replay_pass else ("FAIL" if elvhys_replay else "PENDING"),
        "The public ELVHYS cryogenic pressure-peaking subset is hash-identified and replayed with a strict non-validation claim boundary.",
        str(elvhys_replay_path.relative_to(root)),
        "Three pressure-peaking tests plus one vertical dispersion concentration test, nine source files, monotonic common time bases and explicit prohibition on predictive/full-loop claims.",
        {
            "case_count": len(elvhys_cases),
            "concentration_case_count": len(elvhys_concentration_cases),
            "file_count": len(elvhys_files),
            "predictive_model_validation_permitted": elvhys_claims.get("predictive_model_validation_permitted"),
            "full_loop_station_vehicle_validation_permitted": elvhys_claims.get("full_loop_station_vehicle_validation_permitted"),
        } if elvhys_replay else "missing",
    ))

    elvhys_metadata_path = root / "research/elvhys_dataverse_metadata_audit_2026_10_05.json"
    elvhys_metadata = _json(elvhys_metadata_path)
    elvhys_metadata_source = (elvhys_metadata or {}).get("source") or {}
    elvhys_manifest = (elvhys_metadata or {}).get("archive_manifest") or {}
    elvhys_metadata_scope = (elvhys_metadata or {}).get("experimental_scope") or {}
    elvhys_metadata_eligibility = (elvhys_metadata or {}).get("eligibility") or {}
    elvhys_metadata_files = ((elvhys_metadata or {}).get("file_level_checks") or {}).get(
        "sample_file_manifest", []
    )
    elvhys_metadata_pass = bool(
        (elvhys_metadata or {}).get("schema_version") == 1
        and elvhys_metadata_source.get("doi") == "10.18710/JXJP0H"
        and elvhys_metadata_source.get("license") == "CC0 1.0"
        and elvhys_metadata_source.get("public_access") is True
        and elvhys_manifest.get("file_count") == 198
        and elvhys_manifest.get("category_counts") == {
            "CONC": 40,
            "FLMT": 35,
            "PRES": 40,
            "TEMP": 40,
            "MISC": 40,
            "README": 1,
            "META": 1,
            "SENSOR_DETAILS_PDF": 1,
        }
        and elvhys_metadata_scope.get("reported_test_count") == 48
        and elvhys_metadata_scope.get("date_consistency")
        == "CONFLICT_REQUIRES_CITATION_CLARIFICATION"
        and len(elvhys_metadata_files) == 4
        and all(
            item.get("bytes", 0) > 0
            and item.get("md5")
            and item.get("rows", 0) > 0
            and item.get("end_time_s", 0) > 0
            for item in elvhys_metadata_files
        )
        and elvhys_metadata_eligibility.get("public_consequence_component_eligible") is True
        and elvhys_metadata_eligibility.get("full_loop_station_vehicle_holdout_eligible") is False
        and elvhys_metadata_eligibility.get("goal_completion_permitted") is False
    )
    gates.append(_gate(
        "elvhys_dataverse_metadata_integrity",
        "PASS" if elvhys_metadata_pass else ("FAIL" if elvhys_metadata else "PENDING"),
        "The CC0 ELVHYS consequence archive has a file-level manifest, channel/timebase checks and an explicit cryogenic component-only boundary.",
        str(elvhys_metadata_path.relative_to(root)),
        "198-file API manifest, exact category counts, four sampled files with rows/hashes, recorded date conflict and false full-loop/goal flags.",
        {
            "file_count": elvhys_manifest.get("file_count"),
            "reported_test_count": elvhys_metadata_scope.get("reported_test_count"),
            "sample_file_count": len(elvhys_metadata_files),
            "public_consequence_component_eligible": elvhys_metadata_eligibility.get("public_consequence_component_eligible"),
            "full_loop_station_vehicle_holdout_eligible": elvhys_metadata_eligibility.get("full_loop_station_vehicle_holdout_eligible"),
            "date_consistency": elvhys_metadata_scope.get("date_consistency"),
        } if elvhys_metadata else "missing",
    ))

    elvhys_v1_path = root / "research/elvhys_detector_holdout_result_2026_10_07.json"
    elvhys_v2_path = root / "research/elvhys_detector_holdout_result_v2_2026_10_07.json"
    elvhys_intake_path = root / "research/elvhys_detector_intake_diagnostic_2026_10_08.json"
    elvhys_v1 = _json(elvhys_v1_path)
    elvhys_v2 = _json(elvhys_v2_path)
    elvhys_intake = _json(elvhys_intake_path)
    elvhys_v1_protocol = root / str(((elvhys_v1 or {}).get("protocol") or {}).get("path") or "")
    elvhys_v2_protocol = root / str(((elvhys_v2 or {}).get("protocol") or {}).get("path") or "")
    elvhys_intake_aggregate = (elvhys_intake or {}).get("aggregate") or {}
    elvhys_holdout_integrity_pass = bool(
        (elvhys_v1 or {}).get("status") == "FAIL"
        and (elvhys_v1 or {}).get("retained_failure") is True
        and (elvhys_v1 or {}).get("primary_contract_pass") is False
        and elvhys_v1_protocol.is_file()
        and _sha256(elvhys_v1_protocol)
        == ((elvhys_v1 or {}).get("protocol") or {}).get("sha256")
        and (elvhys_v2 or {}).get("status") == "FAIL"
        and (elvhys_v2 or {}).get("retained_failure") is True
        and (elvhys_v2 or {}).get("primary_contract_pass") is False
        and ((elvhys_v2 or {}).get("execution") or {}).get("failure_encountered_at_test_id") == 44
        and elvhys_v2_protocol.is_file()
        and _sha256(elvhys_v2_protocol)
        == ((elvhys_v2 or {}).get("protocol") or {}).get("sha256")
        and (elvhys_intake or {}).get("outcome_informed") is True
        and (elvhys_intake or {}).get("eligible_as_confirmatory_validation") is False
        and elvhys_intake_aggregate.get("selected_case_count") == 15
        and elvhys_intake_aggregate.get("baseline_eligible_case_count") == 14
        and elvhys_intake_aggregate.get("baseline_ineligible_case_count") == 1
        and elvhys_intake_aggregate.get("failed_case_ids") == [44]
        and elvhys_intake_aggregate.get("case_exclusion_permitted") is False
    )
    gates.append(_gate(
        "elvhys_detector_holdout_failure_integrity",
        "PASS" if elvhys_holdout_integrity_pass else "FAIL",
        "Both prospective ELVHYS detector-intake failures are retained without post-outcome exclusion, and the separate diagnostic reports data usability without promoting a validation claim.",
        f"{elvhys_v1_path.relative_to(root)}; {elvhys_v2_path.relative_to(root)}; {elvhys_intake_path.relative_to(root)}",
        "Both frozen results remain FAIL with matching protocol hashes; the diagnostic must identify 14/15 baseline-eligible cases, retain test 44 and remain ineligible as confirmatory validation.",
        {
            "v1_status": (elvhys_v1 or {}).get("status"),
            "v2_status": (elvhys_v2 or {}).get("status"),
            "v1_retained_failure": (elvhys_v1 or {}).get("retained_failure"),
            "v2_retained_failure": (elvhys_v2 or {}).get("retained_failure"),
            "baseline_eligible_case_count": elvhys_intake_aggregate.get("baseline_eligible_case_count"),
            "selected_case_count": elvhys_intake_aggregate.get("selected_case_count"),
            "failed_case_ids": elvhys_intake_aggregate.get("failed_case_ids"),
            "confirmatory_validation_eligible": (elvhys_intake or {}).get("eligible_as_confirmatory_validation"),
            "interpretation": (elvhys_intake or {}).get("interpretation"),
        },
    ))

    nrel_retrieval_path = root / "research/nrel_h2fills_package_retrieval_check.json"
    nrel_retrieval = _json(nrel_retrieval_path)
    nrel_validation_path = root / "data/public_validation/results/nrel_h2fills_hdvs_typeiv/validation.json"
    nrel_validation = _json(nrel_validation_path)
    nrel_raw_path = root / "data/public_validation/raw/nrel_h2fills_2022_hdvs_typeiv.xlsx"
    nrel_source = (nrel_validation or {}).get("source") or {}
    nrel_identity = (nrel_retrieval or {}).get("workbook_identity") or {}
    nrel_download = (nrel_retrieval or {}).get("retrieval") or {}
    nrel_provenance_pass = bool(
        nrel_identity.get("sha256_matches") is True
        and nrel_identity.get("downloaded_workbook_sha256")
        == nrel_identity.get("locally_screened_workbook_sha256")
        == nrel_source.get("workbook_sha256")
        and nrel_raw_path.is_file()
        and _sha256(nrel_raw_path) == nrel_identity.get("locally_screened_workbook_sha256")
        and nrel_raw_path.stat().st_size == nrel_identity.get("bytes")
        and nrel_download.get("package_sha256_matches_previous_record") is False
        and "does not add a new validation case" in str(
            ((nrel_retrieval or {}).get("interpretation") or {}).get("claim_boundary")
        )
    )
    gates.append(_gate(
        "nrel_h2fills_workbook_provenance_integrity",
        "PASS" if nrel_provenance_pass else "PENDING",
        "The NREL HDVS tank candidate remains byte-identified after a package-container change without being overclaimed as a new full-loop holdout.",
        f"{nrel_retrieval_path.relative_to(root)}; {nrel_validation_path.relative_to(root)}",
        "Downloaded and locally screened workbook digests match the validation record; package drift and the no-new-holdout boundary are explicit.",
        {
            "workbook_sha256": nrel_identity.get("locally_screened_workbook_sha256"),
            "package_sha256_matches_previous_record": nrel_download.get("package_sha256_matches_previous_record"),
            "claim_boundary": ((nrel_retrieval or {}).get("interpretation") or {}).get("claim_boundary"),
        } if nrel_retrieval else "missing",
    ))

    nrel_boundary_path = root / "research/nrel_hdvs_raw_trace_boundary_2026_10_05.json"
    nrel_boundary = _json(nrel_boundary_path)
    nrel_boundary_source = (nrel_boundary or {}).get("source") or {}
    nrel_boundary_experiment = (nrel_boundary or {}).get("experiment") or {}
    nrel_boundary_check = (nrel_boundary or {}).get("boundary_check") or {}
    nrel_boundary_eligibility = (nrel_boundary or {}).get("eligibility") or {}
    nrel_schema_observed: dict[str, Any] = {
        "workbook_present": nrel_raw_path.is_file(),
        "sha256_matches_record": False,
        "data_sheet_max_row": None,
        "data_sheet_max_column": None,
        "nonempty_timed_row_count": None,
        "tank_ids": [],
        "required_channels_present": False,
    }
    if nrel_raw_path.is_file():
        nrel_schema_observed["sha256_matches_record"] = (
            _sha256(nrel_raw_path) == nrel_boundary_source.get("workbook_sha256")
        )
        try:
            import re
            import openpyxl

            workbook = openpyxl.load_workbook(nrel_raw_path, read_only=True, data_only=True)
            data_sheet = workbook["Data"]
            nrel_schema_observed["data_sheet_max_row"] = data_sheet.max_row
            nrel_schema_observed["data_sheet_max_column"] = data_sheet.max_column
            headers = [
                value for value in next(
                    data_sheet.iter_rows(min_row=1, max_row=1, values_only=True)
                ) if value is not None
            ]
            timed_rows = [
                row for row in data_sheet.iter_rows(min_row=2, values_only=True)
                if row and row[0] is not None
            ]
            nrel_schema_observed["nonempty_timed_row_count"] = len(timed_rows)
            nrel_schema_observed["tank_ids"] = sorted({
                int(match.group(1))
                for header in headers
                if (match := re.search(r"tank#(\d+)", str(header)))
            })
            required = {"Time [s]", "P_hose [MPa]", "T_hose [degC]"}
            required.update(
                template.format(id=tank_id)
                for tank_id in nrel_boundary_experiment.get("tank_ids", [])
                for template in nrel_boundary_experiment.get("per_tank_channel_templates", [])
            )
            nrel_schema_observed["required_channels_present"] = required.issubset(set(headers))
            workbook.close()
        except (ImportError, KeyError, OSError, ValueError, StopIteration):
            pass
    nrel_boundary_pass = bool(
        (nrel_boundary or {}).get("schema_version") == 1
        and (nrel_boundary or {}).get("status") == "NREL_HDVS_RAW_TRACE_BOUNDARY_RECHECKED"
        and nrel_boundary_source.get("workbook_sha256") == nrel_source.get("workbook_sha256")
        and nrel_boundary_source.get("workbook_bytes") == nrel_identity.get("bytes")
        and nrel_schema_observed["workbook_present"] is True
        and nrel_schema_observed["sha256_matches_record"] is True
        and nrel_schema_observed["data_sheet_max_row"] == 445
        and nrel_schema_observed["data_sheet_max_column"] == 42
        and nrel_schema_observed["nonempty_timed_row_count"] == 351
        and nrel_schema_observed["tank_ids"] == [1, 2, 3, 5, 7, 8, 9]
        and nrel_schema_observed["required_channels_present"] is True
        and nrel_boundary_check.get("physical_measurement_trace") is True
        and nrel_boundary_check.get("station_controller_or_cascade_state_present") is False
        and nrel_boundary_check.get("esd_or_safety_interlock_trace_present") is False
        and nrel_boundary_check.get("breakaway_hose_nozzle_receptacle_trace_present") is False
        and nrel_boundary_check.get("vehicle_side_protocol_trace_present") is False
        and nrel_boundary_check.get("full_loop_external_holdout_eligible") is False
        and nrel_boundary_eligibility.get("partial_station_to_tank_boundary_eligible") is True
        and nrel_boundary_eligibility.get("goal_completion_permitted") is False
        and bool((nrel_boundary or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "nrel_hdvs_raw_trace_boundary_integrity",
        "PASS" if nrel_boundary_pass else ("FAIL" if nrel_boundary else "PENDING"),
        "The NREL HDVS workbook is schema-checked as a real hose/tank boundary while its missing station and vehicle channels remain explicit.",
        str(nrel_boundary_path.relative_to(root)),
        "Hash-verified workbook, 351 timed rows, seven tank IDs, required hose/tank channels and explicit exclusion of controller/ESD/nozzle/receptacle/vehicle traces.",
        {
            **nrel_schema_observed,
            "partial_station_to_tank_boundary_eligible": nrel_boundary_eligibility.get("partial_station_to_tank_boundary_eligible"),
            "full_loop_external_holdout_eligible": nrel_boundary_eligibility.get("full_loop_external_holdout_eligible"),
        } if nrel_boundary else "missing; NREL HDVS raw trace boundary recheck has not run",
    ))

    fch2rail_boundary_path = root / "research/fch2rail_d61_operating_range_boundary_2026_10_05.json"
    fch2rail_boundary = _json(fch2rail_boundary_path)
    fch2rail_source = (fch2rail_boundary or {}).get("source") or {}
    fch2rail_experiment = (fch2rail_boundary or {}).get("experiment") or {}
    fch2rail_eligibility = (fch2rail_boundary or {}).get("eligibility") or {}
    fch2rail_pass = bool(
        (fch2rail_boundary or {}).get("schema_version") == 1
        and (fch2rail_boundary or {}).get("status") == "PUBLIC_FCH2RAIL_OPERATING_RANGE_BOUNDARY_RECHECKED"
        and fch2rail_source.get("pdf_sha256") == "d55d8d27096e8bcf9529f32a27beb797bff9634f5cfca9c53bdae6914ae27dd2c"
        and fch2rail_source.get("pdf_bytes") == 1582483
        and fch2rail_source.get("pdf_page_count") == 41
        and fch2rail_experiment.get("supply_boundary") == "300 bar tube-trailer storage, no chiller, 10 m hose"
        and fch2rail_experiment.get("sampling_interval_reported_s") == [5, 10]
        and fch2rail_experiment.get("average_flow_range_g_s") == [11.54, 19.44]
        and fch2rail_experiment.get("average_refuelling_speed_range_kg_min") == [0.69, 1.17]
        and fch2rail_eligibility.get("real_hrs_operating_range_context_eligible") is True
        and fch2rail_eligibility.get("trailer_supply_and_large_vehicle_context_eligible") is True
        and fch2rail_eligibility.get("synchronized_raw_full_loop_holdout_eligible") is False
        and fch2rail_eligibility.get("goal_completion_permitted") is False
        and bool((fch2rail_boundary or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "fch2rail_d61_operating_range_boundary_integrity",
        "PASS" if fch2rail_pass else ("FAIL" if fch2rail_boundary else "PENDING"),
        "The public FCH2Rail D6.1 report is hash-locked as independent real-HRS operating-range context without being promoted to a raw full-loop holdout.",
        str(fch2rail_boundary_path.relative_to(root)),
        "Verified report digest/page count, 300-bar trailer/no-chiller/10-m hose boundary, 5/10-s reporting cadence, measured flow/speed ranges and false full-loop eligibility.",
        {
            "pdf_sha256": fch2rail_source.get("pdf_sha256"),
            "average_flow_range_g_s": fch2rail_experiment.get("average_flow_range_g_s"),
            "average_refuelling_speed_range_kg_min": fch2rail_experiment.get("average_refuelling_speed_range_kg_min"),
            "real_hrs_operating_range_context_eligible": fch2rail_eligibility.get("real_hrs_operating_range_context_eligible"),
            "synchronized_raw_full_loop_holdout_eligible": fch2rail_eligibility.get("synchronized_raw_full_loop_holdout_eligible"),
        } if fch2rail_boundary else "missing; FCH2Rail D6.1 operating-range boundary recheck has not run",
    ))

    fch2rail_ijhe_path = root / "research/fch2rail_ijhe_measurement_access_recheck_2026_10_05.json"
    fch2rail_ijhe = _json(fch2rail_ijhe_path)
    fch2rail_ijhe_source = (fch2rail_ijhe or {}).get("source") or {}
    fch2rail_ijhe_boundary = (fch2rail_ijhe or {}).get("observed_measurement_boundary") or {}
    fch2rail_ijhe_eligibility = (fch2rail_ijhe or {}).get("eligibility") or {}
    fch2rail_ijhe_pass = bool(
        (fch2rail_ijhe or {}).get("schema_version") == 1
        and (fch2rail_ijhe or {}).get("status") == "PUBLIC_FCH2RAIL_IJHE_MEASUREMENT_ACCESS_RECHECKED"
        and fch2rail_ijhe_source.get("doi") == "10.1016/j.ijhydene.2025.04.040"
        and fch2rail_ijhe_source.get("pdf_sha256") == "462b57007a42e0a0b359d104d621c4e63f788dcd51b4fe6d995032261cd482b3"
        and fch2rail_ijhe_source.get("pdf_bytes") == 3752323
        and fch2rail_ijhe_source.get("pdf_page_count") == 14
        and fch2rail_ijhe_boundary.get("vehicle_tank_pressure_and_temperature") is True
        and fch2rail_ijhe_boundary.get("dispenser_pressure_temperature_mass_flow") is True
        and fch2rail_ijhe_boundary.get("machine_readable_rows_publicly_linked") is False
        and fch2rail_ijhe_boundary.get("written_derived_metric_reuse_terms") is False
        and fch2rail_ijhe_eligibility.get("real_full_loop_operating_context_eligible") is True
        and fch2rail_ijhe_eligibility.get("synchronized_raw_full_loop_holdout_eligible") is False
        and fch2rail_ijhe_eligibility.get("goal_completion_permitted") is False
        and bool((fch2rail_ijhe or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "fch2rail_ijhe_measurement_access_boundary_integrity",
        "PASS" if fch2rail_ijhe_pass else ("FAIL" if fch2rail_ijhe else "PENDING"),
        "The open FCH2Rail IJHE article is hash-locked as real station-to-vehicle measurement context while its missing raw archive and reuse terms remain explicit.",
        str(fch2rail_ijhe_path.relative_to(root)),
        "Verified article digest/page count, measured channel boundary, explicit no-public-raw statement and false raw-holdout eligibility.",
        {
            "doi": fch2rail_ijhe_source.get("doi"),
            "pdf_sha256": fch2rail_ijhe_source.get("pdf_sha256"),
            "machine_readable_rows_publicly_linked": fch2rail_ijhe_boundary.get("machine_readable_rows_publicly_linked"),
            "synchronized_raw_full_loop_holdout_eligible": fch2rail_ijhe_eligibility.get("synchronized_raw_full_loop_holdout_eligible"),
        } if fch2rail_ijhe else "missing; FCH2Rail IJHE measurement-access recheck has not run",
    ))

    nbsdc_liquid_recheck_path = root / "research/nbsdc_liquid_hrs_public_access_recheck_2026_10_05.json"
    nbsdc_liquid_recheck = _json(nbsdc_liquid_recheck_path)
    nbsdc_liquid_protocol_path = root / "research/nbsdc_liquid_hrs_intake_protocol_2026_10_05.json"
    nbsdc_liquid_protocol = _json(nbsdc_liquid_protocol_path)
    nbsdc_liquid_description = root / "data/public_validation/raw/nbsdc_liquid_hrs_2025/液氢加氢站运行数据集数据说明 .docx"
    nbsdc_liquid_source = (nbsdc_liquid_recheck or {}).get("source") or {}
    nbsdc_liquid_probe = (nbsdc_liquid_recheck or {}).get("raw_download_probes") or {}
    nbsdc_liquid_eligibility = (nbsdc_liquid_recheck or {}).get("eligibility") or {}
    nbsdc_liquid_pass = bool(
        (nbsdc_liquid_recheck or {}).get("schema_version") == 1
        and (nbsdc_liquid_recheck or {}).get("status") == "REAL_LHRS_ACCESS_BOUNDARY_NO_RAW_NUMERICAL_HOLDOUT"
        and nbsdc_liquid_source.get("data_id") == "67d50e37195d260905af9869"
        and nbsdc_liquid_source.get("share_range") == "完全共享"
        and (nbsdc_liquid_recheck or {}).get("metadata_observation", {}).get("file_count") == 7
        and len((nbsdc_liquid_recheck or {}).get("public_file_inventory") or []) == 7
        and nbsdc_liquid_description.is_file()
        and _sha256(nbsdc_liquid_description) == ((nbsdc_liquid_recheck or {}).get("description_file") or {}).get("sha256")
        and nbsdc_liquid_probe.get("portal_body_code") == 403
        and nbsdc_liquid_probe.get("raw_numerical_files_obtained") is False
        and nbsdc_liquid_eligibility.get("full_loop_holdout_eligible") is False
        and (nbsdc_liquid_protocol or {}).get("outcomes_accessed_before_freeze") is False
        and bool((nbsdc_liquid_recheck or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "nbsdc_liquid_hrs_public_access_boundary_integrity",
        "PASS" if nbsdc_liquid_pass else ("FAIL" if nbsdc_liquid_recheck else "PENDING"),
        "The public NBSDC liquid-HRS candidate is recorded with its description hash and application-controlled numerical-file boundary without being overclaimed as validation.",
        f"{nbsdc_liquid_recheck_path.relative_to(root)}; {nbsdc_liquid_protocol_path.relative_to(root)}",
        "Seven-file inventory, description-only hash, 403 raw-file probe, prospective intake contract and explicit full-loop exclusion are consistent.",
        {
            "data_id": nbsdc_liquid_source.get("data_id"),
            "file_count": (nbsdc_liquid_recheck or {}).get("metadata_observation", {}).get("file_count"),
            "description_sha256": ((nbsdc_liquid_recheck or {}).get("description_file") or {}).get("sha256"),
            "portal_body_code": nbsdc_liquid_probe.get("portal_body_code"),
            "full_loop_holdout_eligible": nbsdc_liquid_eligibility.get("full_loop_holdout_eligible"),
        } if nbsdc_liquid_recheck else "missing; NBSDC liquid-HRS access recheck has not run",
    ))

    manuscript_path = root / "manuscript/ijhe_manuscript_draft.tex"
    manuscript = manuscript_path.read_text(encoding="utf-8") if manuscript_path.is_file() else ""
    negative_transparent = (
        "negative full-loop validation result" in manuscript.lower()
        or "did not satisfy the predeclared engineering screens" in manuscript.lower()
    )
    gates.append(_gate(
        "full_loop_negative_result_disclosed",
        "PASS" if negative_transparent else "FAIL",
        "The failed full-loop evaluation is disclosed instead of being hidden.",
        str(manuscript_path.relative_to(root)),
        "Explicit negative result and bounded tank-model claim.",
    ))

    hyram_path = root / "research/hyram_adapter_verification.json"
    hyram = _json(hyram_path)
    hyram_pass = bool(
        (hyram or {}).get("adapter_parity_passed")
        and (((hyram or {}).get("hyram") or {}).get("source_identity_match"))
        and (((hyram or {}).get("upstream_validation") or {}).get("status") == "passed")
    )
    gates.append(_gate(
        "hyram_adapter_verification", "PASS" if hyram_pass else "FAIL",
        "The production adapter is identical to and numerically consistent with HyRAM+ 6.1 within the tested scope.",
        str(hyram_path.relative_to(root)),
        "Source identity, upstream validation suite and production-adapter parity pass.",
        {
            "source_identity_match": (((hyram or {}).get("hyram") or {}).get("source_identity_match")),
            "upstream_status": (((hyram or {}).get("upstream_validation") or {}).get("status")),
            "adapter_parity_passed": (hyram or {}).get("adapter_parity_passed"),
        },
    ))

    geometry_path = root / "research/consequence_geometry_validation.json"
    geometry = _json(geometry_path)
    geometry_checks = (geometry or {}).get("chain_checks") or {}
    geometry_pass = bool(
        (geometry or {}).get("status") == "passed"
        and (geometry or {}).get("independent_dataset_family_count", 0) >= 3
        and geometry_checks and all(geometry_checks.values())
        and (geometry or {}).get("site_specific_claim_permitted") is False
        and (geometry or {}).get("safety_distance_claim_permitted") is False
    )
    gates.append(_gate(
        "station_consequence_geometry_validation",
        "PASS" if geometry_pass else "PENDING",
        "Displayed outdoor free-jet screening geometry is traceably checked against geometrically applicable independent data.",
        str(geometry_path.relative_to(root)),
        "At least three independent applicable evidence families, frozen mapping tests, and explicit non-site-specific limits.",
        geometry or "missing; FFI open-channel data are not applicable to the current outdoor free jet",
    ))

    detector_logic_path = root / "research/dispersion_detector_logic_validation.json"
    detector_logic = _json(detector_logic_path)
    detector_aggregate = (detector_logic or {}).get("aggregate") or {}
    detector_source = (detector_logic or {}).get("source") or {}
    detector_logic_pass = bool(
        (detector_logic or {}).get("status")
        == "completed_bounded_instrumented_detector_logic_evidence"
        and (detector_logic or {}).get("evidence_role")
        == "instrumented_detector_logic_evidence"
        and detector_source.get("doi") == "10.23642/usn.26117989.v2"
        and detector_aggregate.get("case_count") == 22
        and detector_aggregate.get("sensor_count_per_case") == [29]
        and detector_aggregate.get("cases_with_alarm_detection") == 22
        and detector_aggregate.get("cases_with_trip_detection") == 22
        and len(detector_source.get("archive_manifest") or []) == 22
        and bool((detector_logic or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "open_channel_detector_logic_evidence",
        "PASS" if detector_logic_pass else ("FAIL" if detector_logic else "PENDING"),
        "Measured open-channel concentration records replay the declared detector threshold and persistence logic with an explicit non-HRS claim boundary.",
        str(detector_logic_path.relative_to(root)),
        "22 CC BY 4.0 cases, 29 channels per case, archive hashes, exact rule parameters and bounded interpretation.",
        detector_aggregate if detector_logic else "missing; detector-logic replay has not completed",
    ))

    h2safe_path = root / "research/h2safe_public_dataset_intake_2026_10_08.json"
    h2safe = _json(h2safe_path)
    h2safe_source = (h2safe or {}).get("source") or {}
    h2safe_protocol = (h2safe or {}).get("frozen_protocol") or {}
    h2safe_intake = (h2safe or {}).get("intake") or {}
    h2safe_timing = (h2safe or {}).get("timing_crosswalk") or {}
    h2safe_eligibility = (h2safe or {}).get("eligibility_decision") or {}
    h2safe_privacy = (h2safe or {}).get("privacy_and_redistribution") or {}
    h2safe_pass = bool(
        (h2safe or {}).get("artifact_type")
        == "public_h2safe_helium_dataset_intake_audit"
        and h2safe_source.get("doi") == "10.7799/17118570"
        and h2safe_source.get("test_gas") == "helium"
        and h2safe_protocol.get("git_commit_before_raw_access") == "2ed653b"
        and len(str(h2safe_protocol.get("sha256") or "")) == 64
        and h2safe_intake.get("laboratory_count") == 2
        and h2safe_intake.get("test_count") == 5
        and h2safe_intake.get("sample_intervals_s") == [1.0]
        and h2safe_timing.get(
            "unambiguous_release_to_csv_time_crosswalk_present"
        ) is False
        and h2safe_eligibility.get("schema_and_spatial_intake_pass") is True
        and h2safe_eligibility.get(
            "frozen_detection_timing_validation_eligible"
        ) is False
        and h2safe_eligibility.get("frozen_joint_primary_screen_run") is False
        and h2safe_eligibility.get("claim_supported") is False
        and h2safe_eligibility.get("runtime_parameter_application") is False
        and h2safe_privacy.get("raw_rows_committed") is False
        and h2safe_privacy.get("source_archive_committed") is False
        and bool((h2safe or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "h2safe_public_helium_dataset_intake",
        "PASS" if h2safe_pass else ("FAIL" if h2safe else "PENDING"),
        "The public full-scale H2SAFE helium sensor dataset is hash-audited and screened prospectively without being promoted to hydrogen or detector-timing validation.",
        str(h2safe_path.relative_to(root)),
        "Two laboratories, five 1 s time-series tests, frozen pre-access protocol, release-time crosswalk decision and explicit surrogate/full-loop exclusions.",
        {
            "doi": h2safe_source.get("doi"),
            "test_gas": h2safe_source.get("test_gas"),
            "protocol_commit": h2safe_protocol.get("git_commit_before_raw_access"),
            "laboratory_count": h2safe_intake.get("laboratory_count"),
            "test_count": h2safe_intake.get("test_count"),
            "sample_intervals_s": h2safe_intake.get("sample_intervals_s"),
            "timing_crosswalk_available": h2safe_timing.get(
                "unambiguous_release_to_csv_time_crosswalk_present"
            ),
            "timing_validation_eligible": h2safe_eligibility.get(
                "frozen_detection_timing_validation_eligible"
            ),
            "runtime_parameter_application": h2safe_eligibility.get(
                "runtime_parameter_application"
            ),
            "claim_boundary": (h2safe or {}).get("claim_boundary"),
        } if h2safe else "missing; H2SAFE public dataset intake has not run",
    ))

    dispersion_proxy_path = root / (
        "research/dispersion_concentration_proxy_calibration_2026_10_06.json"
    )
    dispersion_proxy = _json(dispersion_proxy_path)
    dispersion_proxy_source = (dispersion_proxy or {}).get("source") or {}
    dispersion_proxy_method = (dispersion_proxy or {}).get("method") or {}
    dispersion_proxy_runtime = (dispersion_proxy or {}).get("runtime_application") or {}
    dispersion_proxy_pass = bool(
        (dispersion_proxy or {}).get("status")
        == "derived_bounded_dispersion_concentration_proxy"
        and dispersion_proxy_source.get("doi") == "10.23642/usn.26117989.v2"
        and dispersion_proxy_source.get("license") == "CC BY 4.0"
        and dispersion_proxy_method.get("case_count") == 22
        and isinstance(dispersion_proxy_method.get("coefficient_volpct_per_g_s"), (int, float))
        and 20.0 <= float(dispersion_proxy_method["coefficient_volpct_per_g_s"]) <= 40.0
        and "clip(" in str(dispersion_proxy_runtime.get("formula") or "")
        and "does not validate outdoor station dispersion" in str(
            (dispersion_proxy or {}).get("claim_boundary") or ""
        )
        and len((dispersion_proxy or {}).get("cases") or []) == 22
    )
    gates.append(_gate(
        "open_channel_concentration_proxy_integrity",
        "PASS" if dispersion_proxy_pass else ("FAIL" if dispersion_proxy else "PENDING"),
        "The virtual detector concentration scale is derived from public measured concentration/flow traces instead of an unexplained saturation constant.",
        str(dispersion_proxy_path.relative_to(root)),
        "22 CC BY 4.0 cases, robust per-case P90/flow statistic, bounded runtime formula and explicit open-channel claim boundary.",
        {
            "doi": dispersion_proxy_source.get("doi"),
            "license": dispersion_proxy_source.get("license"),
            "case_count": dispersion_proxy_method.get("case_count"),
            "coefficient_volpct_per_g_s": dispersion_proxy_method.get("coefficient_volpct_per_g_s"),
            "runtime_formula": dispersion_proxy_runtime.get("formula"),
            "claim_boundary": (dispersion_proxy or {}).get("claim_boundary"),
        } if dispersion_proxy else "missing; public concentration proxy artifact has not been built",
    ))

    grune_inventory_path = root / "research/grune_ventilation_dataset_inventory_2026_10_05.json"
    grune_inventory = _json(grune_inventory_path)
    grune_source = (grune_inventory or {}).get("source") or {}
    grune_measurements = (grune_inventory or {}).get("inventory") or {}
    grune_validation = (grune_inventory or {}).get("validation_status") or {}
    grune_inventory_pass = bool(
        (grune_inventory or {}).get("status")
        == "completed_provenance_and_measurement_inventory"
        and grune_source.get("doi") == "10.5281/zenodo.4668554"
        and grune_source.get("license") == "CC BY 4.0"
        and grune_measurements.get("source_identity_all_match") is True
        and grune_measurements.get("workbook_count") == 4
        and grune_measurements.get("profile_count") == 42
        and grune_measurements.get("spatial_point_count") == 5256
        and not grune_measurements.get("workbook_errors")
        and grune_validation.get("model_comparison_performed") is False
        and grune_validation.get("numeric_validation_gate_closed") is False
        and bool((grune_inventory or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "grune_ventilation_measurement_inventory",
        "PASS" if grune_inventory_pass else ("FAIL" if grune_inventory else "PENDING"),
        "The public Grune/Sempert confined-space ventilation fields are hash-verified and inventoried without being promoted to model validation.",
        str(grune_inventory_path.relative_to(root)),
        "Four CC BY 4.0 workbooks, 42 spatial profiles, 5,256 points and an explicit no-model-comparison boundary.",
        grune_measurements if grune_inventory else "missing; Grune measurement inventory has not run",
    ))

    grune_envelope_path = root / (
        "research/grune_ventilation_empirical_envelope_2026_10_06.json"
    )
    grune_envelope = _json(grune_envelope_path)
    grune_envelope_source = (grune_envelope or {}).get("source") or {}
    grune_envelope_definition = (grune_envelope or {}).get("definition") or {}
    grune_envelope_factors = (grune_envelope or {}).get("factors") or []
    grune_envelope_pass = bool(
        (grune_envelope or {}).get("status")
        == "derived_empirical_ventilation_envelope"
        and grune_envelope_source.get("doi") == "10.5281/zenodo.4668554"
        and grune_envelope_source.get("license") == "CC BY 4.0"
        and grune_envelope_source.get("raw_rows_committed") is False
        and (grune_envelope or {}).get("profiles_used") == 42
        and (grune_envelope or {}).get("factor_count") == 42
        and len(grune_envelope_factors) == 42
        and all(
            isinstance(item, dict)
            and isinstance(item.get("relative_factor"), (int, float))
            and isinstance(item.get("relative_factor_upper"), (int, float))
            and item["relative_factor_upper"] >= item["relative_factor"]
            for item in grune_envelope_factors
        )
        and grune_envelope_definition.get("fallback")
        and grune_envelope_definition.get("upper_envelope")
        and grune_envelope_definition.get("not_a_claim")
    )
    gates.append(_gate(
        "grune_ventilation_empirical_envelope_integrity",
        "PASS" if grune_envelope_pass else ("FAIL" if grune_envelope else "PENDING"),
        "The public measured ventilation envelope is applied only to the virtual detector proxy with an explicit confined-space claim boundary.",
        str(grune_envelope_path.relative_to(root)),
        "42 hash-verified public profiles, derived no-wind-normalized factors, no raw rows committed, and deterministic fallback for unrepresented conditions.",
        {
            "doi": grune_envelope_source.get("doi"),
            "profiles_used": (grune_envelope or {}).get("profiles_used"),
            "factor_count": (grune_envelope or {}).get("factor_count"),
            "upper_factor_count": sum(
                1 for item in grune_envelope_factors
                if isinstance(item, dict) and "relative_factor_upper" in item
            ),
            "raw_rows_committed": grune_envelope_source.get("raw_rows_committed"),
            "runtime_scope": "virtual_detector_proxy_only",
            "runtime_statistic_default": "upper",
            "claim_boundary": grune_envelope_definition.get("not_a_claim"),
        } if grune_envelope else "missing; empirical ventilation envelope has not been built",
    ))

    h2safe_path = root / "research/h2safe_indoor_release_intake_2026_10_07.json"
    h2safe = _json(h2safe_path)
    h2safe_source = (h2safe or {}).get("source") or {}
    h2safe_intake = (h2safe or {}).get("intake") or {}
    h2safe_eligibility = (h2safe or {}).get("eligibility") or {}
    h2safe_cases = [item for item in h2safe_intake.get("cases") or [] if isinstance(item, dict)]
    h2safe_pass = bool(
        (h2safe or {}).get("status")
        == "completed_bounded_full_scale_indoor_surrogate_intake"
        and h2safe_source.get("doi") == "10.7799/17118570"
        and h2safe_source.get("raw_rows_committed") is False
        and h2safe_intake.get("case_count") == 5
        and h2safe_intake.get("lab_sensor_coordinate_counts") == {"Lab-1": 24, "Lab-2": 37}
        and all((case.get("unmapped_sensor_columns") or []) == [] for case in h2safe_cases)
        and h2safe_eligibility.get("timestamped_signal_schema_available") is True
        and h2safe_eligibility.get("numerical_hydrogen_alarm_or_trip_threshold_calibration") is False
        and h2safe_eligibility.get("full_loop_station_vehicle_validation") is False
        and (h2safe or {}).get("runtime_parameter_updated") is False
        and bool((h2safe or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "h2safe_full_scale_indoor_surrogate_intake_integrity",
        "PASS" if h2safe_pass else ("FAIL" if h2safe else "PENDING"),
        "A public full-scale indoor helium-surrogate release package is hash-verified and structurally mapped without being promoted to H2 threshold or full-station validation.",
        str(h2safe_path.relative_to(root)),
        "Five traces, Lab-1/2 coordinate inventories, mapped trace sensors, preserved source hashes, and explicit threshold/full-loop/runtime limits.",
        {
            "doi": h2safe_source.get("doi"),
            "case_count": h2safe_intake.get("case_count"),
            "lab_sensor_coordinate_counts": h2safe_intake.get("lab_sensor_coordinate_counts"),
            "all_trace_columns_coordinate_mapped": all(
                (case.get("unmapped_sensor_columns") or []) == [] for case in h2safe_cases
            ),
            "timestamped_signal_schema_available": h2safe_eligibility.get(
                "timestamped_signal_schema_available"
            ),
            "hydrogen_threshold_calibration": h2safe_eligibility.get(
                "numerical_hydrogen_alarm_or_trip_threshold_calibration"
            ),
            "full_loop_station_vehicle_validation": h2safe_eligibility.get(
                "full_loop_station_vehicle_validation"
            ),
            "runtime_parameter_updated": (h2safe or {}).get("runtime_parameter_updated"),
            "claim_boundary": (h2safe or {}).get("claim_boundary"),
        } if h2safe else "missing; H2SAFE source intake has not been audited",
    ))

    explosion_inventory_path = root / "research/dataverse_hydrogen_explosion_dataset_inventory_2026_10_05.json"
    explosion_inventory = _json(explosion_inventory_path)
    explosion_sources = (explosion_inventory or {}).get("sources") or []
    explosion_by_doi = {item.get("doi"): item for item in explosion_sources}
    explosion_validation = (explosion_inventory or {}).get("validation_status") or {}
    explosion_subset_path = root / "research/usn_17934047_raw_subset_replay_2026_10_05.json"
    explosion_subset = _json(explosion_subset_path)
    explosion_subset_integrity = (explosion_subset or {}).get("replay_integrity") or {}
    explosion_inventory_pass = bool(
        (explosion_inventory or {}).get("status")
        == "completed_dataverse_provenance_and_summary_inventory"
        and set(explosion_by_doi) == {
            "10.18710/WSKBIJ", "10.18710/X044QK", "10.23642/USN.17934047"
        }
        and all(item.get("license") in {"CC0 1.0", "CC BY 4.0"} for item in explosion_sources)
        and all(
            item.get("summary_file_identity_match") is True
            or item.get("sample_file_identity_match") is True
            for item in explosion_sources
        )
        and explosion_by_doi["10.18710/WSKBIJ"].get("published_summary", {}).get("experiment_count") == 51
        and explosion_by_doi["10.18710/X044QK"].get("published_summary", {}).get("experiment_count") == 40
        and explosion_by_doi["10.23642/USN.17934047"].get("raw_sample", {}).get("sigma_shape") == [999999, 7]
        and explosion_by_doi["10.23642/USN.17934047"].get("raw_sample", {}).get("temperature_channel_count") == 4
        and explosion_validation.get("model_comparison_performed") is False
        and explosion_validation.get("numeric_validation_gate_closed") is False
        and explosion_validation.get("full_loop_external_validation_supported") is False
        and bool((explosion_inventory or {}).get("claim_boundary"))
        and (explosion_subset or {}).get("status") == "completed_raw_channel_timebase_replay"
        and explosion_subset_integrity.get("file_count") == 3
        and explosion_subset_integrity.get("all_files_present") is True
        and explosion_subset_integrity.get("all_file_identities_match") is True
        and explosion_subset_integrity.get("all_channel_replays_valid") is True
        and explosion_subset_integrity.get("model_comparison_performed") is False
    )
    gates.append(_gate(
        "dataverse_hydrogen_explosion_component_inventory",
        "PASS" if explosion_inventory_pass else ("FAIL" if explosion_inventory else "PENDING"),
        "Two CC0 DataverseNO release/ignition archives are provenance-checked as independent consequence-component evidence without being promoted to HRS full-loop or model validation.",
        f"{explosion_inventory_path.relative_to(root)}; {explosion_subset_path.relative_to(root)}",
        "WSKBIJ and X044QK API manifests, summary-workbook hashes, 51/40 experiment counts, a three-file CC BY raw-channel replay and explicit false model/full-loop flags.",
        {
            "dois": sorted(explosion_by_doi),
            "experiment_counts": {
                doi: (item.get("published_summary") or {}).get("experiment_count")
                for doi, item in explosion_by_doi.items()
            },
            "ignited_sample_sigma_shape": explosion_by_doi.get("10.23642/USN.17934047", {}).get("raw_sample", {}).get("sigma_shape"),
            "license_set": sorted({item.get("license") for item in explosion_sources}),
            "model_comparison_performed": explosion_validation.get("model_comparison_performed"),
            "full_loop_external_validation_supported": explosion_validation.get("full_loop_external_validation_supported"),
            "raw_subset_file_count": explosion_subset_integrity.get("file_count"),
            "raw_subset_channel_replay_valid": explosion_subset_integrity.get("all_channel_replays_valid"),
            "raw_subset_model_comparison_performed": explosion_subset_integrity.get("model_comparison_performed"),
        } if explosion_inventory else "missing; DataverseNO explosion inventory has not run",
    ))

    playbook_path = root / "src/h2station/data/emergency_playbooks.json"
    playbooks = _json(playbook_path)
    playbook_sources = (playbooks or {}).get("sources") or {}
    incident_plan_ids = {
        "gas_release", "hydrogen_fire", "external_fire", "overpressure",
        "relief_discharge", "fueling_fault", "hose_connection", "structural_damage",
    }
    linked_plan_ids = {
        str(plan.get("id")) for plan in (playbooks or {}).get("plans", [])
        if "HIAD2026" in (plan.get("sources") or [])
    }
    incident_grounding_pass = bool(
        playbook_sources.get("HIAD2026", {}).get("url")
        == "https://minerva.jrc.ec.europa.eu/en/shorturl/capri/hiadpt"
        and incident_plan_ids.issubset(linked_plan_ids)
        and len((playbooks or {}).get("plans", [])) == 16
    )
    gates.append(_gate(
        "incident_playbook_public_evidence",
        "PASS" if incident_grounding_pass else ("FAIL" if playbooks else "PENDING"),
        "High-consequence playbooks expose the public HIAD 2.2 accident/near-miss source alongside standards guidance.",
        str(playbook_path.relative_to(root)),
        "HIAD source URL and links on gas release, fire, overpressure, relief, fueling and hose response families; no efficacy claim.",
        {
            "hiad_source": playbook_sources.get("HIAD2026"),
            "linked_plan_ids": sorted(linked_plan_ids),
            "claim_boundary": "Incident taxonomy and public response-field provenance only; no quantitative effectiveness or probability claim.",
        } if playbooks else "missing; emergency playbook source unavailable",
    ))

    stage_contract_path = root / "research/hiad_response_stage_contract.json"
    stage_contract = _json(stage_contract_path)
    stage_aggregate = (stage_contract or {}).get("aggregate") or {}
    stage_contract_pass = bool(
        (stage_contract or {}).get("status")
        == "completed_metadata_only_response_stage_contract"
        and (stage_contract or {}).get("evidence_role")
        == "metadata_only_response_contract"
        and (stage_contract or {}).get("contract_pass") is True
        and stage_aggregate.get("case_count") == 34
        and stage_aggregate.get("mapped_case_count") == 34
        and stage_aggregate.get("missing_stage_case_count") == 0
        and stage_aggregate.get("normal_quiet_contract_passed") is True
        and stage_aggregate.get("coverage_source_hash_matches") is True
        and stage_aggregate.get("coverage_catalog_hash_matches") is True
    )
    gates.append(_gate(
        "hiad_response_stage_contract",
        "PASS" if stage_contract_pass else ("FAIL" if stage_contract else "PENDING"),
        "Public HIAD metadata mappings carry five staged response fields and keep idle periodic monitoring quiet.",
        str(stage_contract_path.relative_to(root)),
        "34/34 mapped rows, no missing recognition/immediate/stabilize/restart/prevention fields, explicit metadata-only claim boundary.",
        stage_contract or "missing; response-stage contract audit has not run",
    ))

    action_evidence_path = root / "research/hiad_action_evidence.json"
    action_evidence = _json(action_evidence_path)
    action_taxonomy = (action_evidence or {}).get("taxonomy") or {}
    action_source = (action_evidence or {}).get("source") or {}
    action_evidence_pass = bool(
        (action_evidence or {}).get("status")
        == "derived_non_evaluative_action_taxonomy"
        and (action_evidence or {}).get("evidence_role")
        == "public_incident_grounding_summary"
        and (action_evidence or {}).get("case_count") == 34
        and action_source.get("raw_text_retained") is False
        and action_source.get("holdout_use") is False
        and bool(action_taxonomy.get("category_counts"))
        and bool(action_taxonomy.get("field_presence_counts"))
        and bool((action_evidence or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "hiad_action_evidence_integrity",
        "PASS" if action_evidence_pass else ("FAIL" if action_evidence else "PENDING"),
        "The public HIAD HRS action fields are summarized into a non-evaluative, traceable action taxonomy for evidence-grounded guidance.",
        str(action_evidence_path.relative_to(root)),
        "34 HRS cases, source digest, controlled action categories, no copied raw prose and explicit exclusion from the SAGA holdout.",
        {
            "case_count": (action_evidence or {}).get("case_count"),
            "taxonomy": action_taxonomy,
            "source": action_source,
            "claim_boundary": (action_evidence or {}).get("claim_boundary"),
        } if action_evidence else "missing; HIAD action evidence summary has not been built",
    ))

    action_playbook_path = root / "research/hiad_action_playbook_coverage.json"
    action_playbook = _json(action_playbook_path)
    action_playbook_aggregate = (action_playbook or {}).get("aggregate") or {}
    action_playbook_pass = bool(
        (action_playbook or {}).get("status")
        == "completed_public_action_to_playbook_traceability_audit"
        and (action_playbook or {}).get("evidence_role")
        == "public_incident_grounding_traceability_only"
        and action_playbook_aggregate.get("category_count") == 8
        and action_playbook_aggregate.get("covered_category_count") == 8
        and action_playbook_aggregate.get("case_count") == 34
        and action_playbook_aggregate.get("covered_case_count") == 34
        and action_playbook_aggregate.get("contract_pass") is True
        and action_playbook_aggregate.get("missing_plan_ids") == []
        and action_playbook_aggregate.get("incomplete_plan_ids") == []
        and "does not judge incident actions" in str(
            (action_playbook or {}).get("claim_boundary")
        )
    )
    gates.append(_gate(
        "hiad_action_playbook_traceability",
        "PASS" if action_playbook_pass else ("FAIL" if action_playbook else "PENDING"),
        "All public HIAD action categories are traceably connected to complete staged response plans without claiming efficacy.",
        str(action_playbook_path.relative_to(root)),
        "8/8 categories and 34/34 cases mapped; every mapped plan exposes recognition, immediate, stabilize, restart and prevention stages.",
        action_playbook_aggregate if action_playbook else "missing; HIAD action-to-playbook coverage audit has not run",
    ))

    accident_response_path = root / "research/hiad_accident_response_coverage_evaluation_2026_10_05.json"
    accident_response = _json(accident_response_path)
    accident_aggregate = (accident_response or {}).get("aggregate") or {}
    accident_source = (accident_response or {}).get("source") or {}
    accident_contract = (accident_response or {}).get("contract") or {}
    accident_hashes = accident_source.get("hashes") or {}
    accident_expected_hashes = {
        "action_evidence_sha256": root / "research/hiad_action_evidence.json",
        "response_stage_contract_sha256": root / "research/hiad_response_stage_contract.json",
        "action_playbook_coverage_sha256": root / "research/hiad_action_playbook_coverage.json",
        "playbook_catalog_sha256": root / "src/h2station/data/emergency_playbooks.json",
    }
    accident_hashes_match = bool(accident_hashes) and all(
        accident_hashes.get(key) == _sha256(path)
        for key, path in accident_expected_hashes.items()
    )
    accident_response_pass = bool(
        (accident_response or {}).get("status")
        == "completed_public_accident_response_coverage_evaluation"
        and (accident_response or {}).get("evidence_role")
        == "public_accident_grounded_interface_evaluation"
        and accident_aggregate.get("case_count") == 34
        and accident_aggregate.get("public_action_category_case_count") == 33
        and accident_aggregate.get("no_public_action_category_case_count") == 1
        and accident_aggregate.get("category_count") == 8
        and accident_aggregate.get("covered_category_count") == 8
        and accident_aggregate.get("uncovered_case_category_count") == 0
        and accident_aggregate.get("contract_pass") is True
        and accident_contract.get("raw_action_text_used") is False
        and accident_contract.get("effectiveness_claimed") is False
        and accident_contract.get("safety_claimed") is False
        and accident_contract.get("holdout_use") is False
        and accident_source.get("action_evidence_source_hash_matches") is True
        and accident_hashes_match
        and "does not judge source actions" in str((accident_response or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "hiad_accident_response_coverage_evaluation",
        "PASS" if accident_response_pass else ("FAIL" if accident_response else "PENDING"),
        "Public HIAD action categories are routed case-by-case to staged response plans with an explicit non-evaluative boundary.",
        str(accident_response_path.relative_to(root)),
        "34 cases, 33 cases with public action categories, 8/8 categories covered with zero uncovered case-category pairs, current input hashes, no raw action text or holdout use.",
        {
            "aggregate": accident_aggregate,
            "contract": accident_contract,
            "source_hashes_match": accident_hashes_match,
        } if accident_response else "missing; accident-response coverage evaluation has not run",
    ))

    hiad_machine_protocol_path = root / "research/hiad_machine_response_benchmark_protocol_2026_10_08.json"
    hiad_machine_result_path = root / "research/hiad_machine_response_benchmark_2026_10_08.json"
    hiad_machine_protocol = _json(hiad_machine_protocol_path)
    hiad_machine_result = _json(hiad_machine_result_path)
    hiad_machine_frozen = (hiad_machine_protocol or {}).get("frozen_inputs") or {}
    hiad_machine_aggregate = (hiad_machine_result or {}).get("aggregate") or {}
    hiad_machine_variants = hiad_machine_aggregate.get("variant_summary") or {}
    hiad_machine_paired = hiad_machine_aggregate.get("paired_machine_proxy_difference") or {}
    hiad_machine_result_protocol = (hiad_machine_result or {}).get("protocol") or {}
    hiad_machine_sources_match = all(
        (root / relative).is_file() and _sha256(root / relative) == hiad_machine_frozen.get(key)
        for relative, key in (
            ("data/public_validation/processed/hiad_hrs_cases.jsonl", "hiad_cases_sha256"),
            ("research/hiad_action_evidence.json", "action_evidence_sha256"),
            ("scripts/run_hiad_machine_response_benchmark.py", "runner_sha256"),
        )
    )
    hiad_machine_pass = bool(
        (hiad_machine_protocol or {}).get("status")
        == "frozen_before_cohort_model_response_collection"
        and ((hiad_machine_protocol or {}).get("outcome_history") or {}).get(
            "cohort_model_outputs_accessed_before_freeze"
        ) is False
        and ((hiad_machine_protocol or {}).get("outcome_history") or {}).get(
            "confirmatory_or_prospective_claim_permitted"
        ) is False
        and (hiad_machine_result or {}).get("status")
        == "COMPLETED_RETROSPECTIVE_MACHINE_BENCHMARK"
        and hiad_machine_result_protocol.get("sha256") == _sha256(hiad_machine_protocol_path)
        and hiad_machine_sources_match
        and hiad_machine_aggregate.get("case_count") == 34
        and hiad_machine_aggregate.get("response_count") == 68
        and (hiad_machine_variants.get("alarm-only") or {}).get("response_count") == 34
        and (hiad_machine_variants.get("saga-linked") or {}).get("response_count") == 34
        and (hiad_machine_variants.get("saga-linked") or {}).get("failed_call_count") == 0
        and (hiad_machine_variants.get("saga-linked") or {}).get(
            "unsupported_claim_response_count"
        ) == 3
        and hiad_machine_paired.get("case_count") == 34
        and "do not establish" in str((hiad_machine_result or {}).get("claim_boundary", ""))
    )
    gates.append(_gate(
        "hiad_retrospective_machine_response_benchmark_integrity",
        "PASS" if hiad_machine_pass else ("FAIL" if hiad_machine_result else "PENDING"),
        "The current direct SAGA path has a frozen, reproducible 34-case retrospective machine-proxy benchmark that retains provider failures and unsupported numeric claims.",
        f"{hiad_machine_protocol_path.relative_to(root)}; {hiad_machine_result_path.relative_to(root)}",
        "34 paired alarm/SAGA responses, matching frozen source hashes, no post-response scoring changes, retained unsupported-claim count and an explicit non-effectiveness boundary.",
        {
            "case_count": hiad_machine_aggregate.get("case_count"),
            "response_count": hiad_machine_aggregate.get("response_count"),
            "alarm_only": hiad_machine_variants.get("alarm-only"),
            "saga_linked": hiad_machine_variants.get("saga-linked"),
            "paired_machine_proxy_difference": hiad_machine_paired,
            "sources_match": hiad_machine_sources_match,
            "expert_effectiveness_claimed": False,
            "claim_boundary": (hiad_machine_result or {}).get("claim_boundary"),
        } if hiad_machine_result else "missing",
    ))

    hiad_guard_path = root / "research/hiad_machine_response_guard_recheck_2026_10_08.json"
    hiad_guard = _json(hiad_guard_path)
    hiad_guard_source = (hiad_guard or {}).get("source") or {}
    hiad_guard_runtime = (hiad_guard or {}).get("runtime") or {}
    hiad_guard_outcome = (hiad_guard or {}).get("outcome") or {}
    hiad_guard_rows = (hiad_guard or {}).get("responses") or []
    hiad_guard_pass = bool(
        (hiad_guard or {}).get("status") == "POST_OUTCOME_RUNTIME_SAFETY_RECHECK"
        and hiad_guard_source.get("retained_benchmark_sha256")
        == _sha256(hiad_machine_result_path)
        and hiad_guard_source.get("case_count") == 34
        and len(hiad_guard_rows) == 34
        and len({str(row.get("event_id")) for row in hiad_guard_rows}) == 34
        and hiad_guard_outcome.get("before_unsupported_claim_response_count") == 3
        and hiad_guard_outcome.get("after_unsupported_claim_response_count") == 0
        and hiad_guard_outcome.get("after_provider_failure_count") == 0
        and int(hiad_guard_outcome.get("guard_notice_response_count") or 0) > 0
        and all(not row.get("unsupported_value_unit_claims") for row in hiad_guard_rows)
        and len(str(hiad_guard_runtime.get("saga_commit") or "")) == 40
        and "not an independent holdout" in str((hiad_guard or {}).get("claim_boundary", ""))
    )
    gates.append(_gate(
        "hiad_direct_numeric_guard_recheck_integrity",
        "PASS" if hiad_guard_pass else ("FAIL" if hiad_guard else "PENDING"),
        "The direct SAGA API blocks input-unsupported value-unit claims in a retained post-outcome 34-case safety recheck.",
        str(hiad_guard_path.relative_to(root)),
        "Same consumed HIAD cohort, original 3/34 failure count retained, zero exposed unsupported claims after the guard, zero provider failures and an explicit non-holdout boundary.",
        {
            "source": hiad_guard_source,
            "runtime": hiad_guard_runtime,
            "outcome": hiad_guard_outcome,
            "claim_boundary": (hiad_guard or {}).get("claim_boundary"),
        } if hiad_guard else "missing",
    ))

    cip_endpoint_path = root / "research/cip_dispenser_endpoint_screen.json"
    cip_endpoint = _json(cip_endpoint_path)
    cip_aggregate = (cip_endpoint or {}).get("aggregate") or {}
    cip_source = (cip_endpoint or {}).get("source") or {}
    cip_endpoint_pass = bool(
        (cip_endpoint or {}).get("status") == "completed_endpoint_only_negative_diagnostic"
        and cip_source.get("doi") == "10.19799/j.cnki.2095-4239.2020.0049"
        and cip_aggregate.get("case_count") == 2
        and cip_aggregate.get("stop_reason_counts") == {"safety-temperature": 2}
        and all("endpoint_errors" in case for case in (cip_endpoint or {}).get("cases", []))
        and bool(cip_aggregate.get("claim_boundary"))
    )
    gates.append(_gate(
        "public_dispenser_endpoint_diagnostic",
        "PASS" if cip_endpoint_pass else ("FAIL" if cip_endpoint else "PENDING"),
        "Public 35/70 MPa dispenser endpoint tables are replayed as an explicit negative diagnostic without being promoted to full-loop validation.",
        str(cip_endpoint_path.relative_to(root)),
        "Two public endpoint cases, source DOI and download hashes, declared 85 degC stop model, retained endpoint errors and explicit claim boundary.",
        cip_aggregate if cip_endpoint else "missing; public endpoint diagnostic has not run",
    ))

    cip_live_path = root / "research/cip_2020_live_download_recheck_2026_10_05.json"
    cip_live = _json(cip_live_path)
    cip_live_source = (cip_live or {}).get("source") or {}
    cip_live_decision = (cip_live or {}).get("eligibility_decision") or {}
    cip_live_tables = (cip_live or {}).get("tables") or []
    cip_live_pass = bool(
        (cip_live or {}).get("schema_version") == 1
        and (cip_live or {}).get("status") == "PUBLIC_ENDPOINT_TABLES_RECHECKED"
        and cip_live_source.get("doi") == "10.19799/j.cnki.2095-4239.2020.0049"
        and len(cip_live_tables) == 4
        and [row.get("table") for row in cip_live_tables] == ["T1", "T2", "T3", "T4"]
        and all(row.get("http_status") == 200 for row in cip_live_tables)
        and all(row.get("sha256_matches_expected") is True for row in cip_live_tables)
        and all((row.get("inspection") or {}).get("rows") == 3 for row in cip_live_tables)
        and all((row.get("inspection") or {}).get("has_time_axis") is False for row in cip_live_tables)
        and cip_live_decision.get("full_loop_external_holdout_eligible") is False
        and (cip_live or {}).get("claim_boundary")
    )
    gates.append(_gate(
        "public_dispenser_table_download_integrity",
        "PASS" if cip_live_pass else ("FAIL" if cip_live else "PENDING"),
        "The four current public CIP dispenser table links are byte-checked and retained as endpoint-only evidence without promoting them to synchronized full-loop validation.",
        str(cip_live_path.relative_to(root)),
        "T1-T4 returned HTTP 200, matched recorded SHA-256 values, each contained three rows, and none exposed a sampled time axis; full-loop eligibility remains false.",
        {
            "tables": [row.get("table") for row in cip_live_tables],
            "sha256_matches": [row.get("sha256_matches_expected") for row in cip_live_tables],
            "full_loop_external_holdout_eligible": cip_live_decision.get("full_loop_external_holdout_eligible"),
        } if cip_live else "missing; live CIP table recheck has not run",
    ))

    green_hysland_path = root / "research/green_hysland_trailer_report_recheck_2026_10_05.json"
    green_hysland = _json(green_hysland_path)
    green_download = (green_hysland or {}).get("download") or {}
    green_trailer = (green_hysland or {}).get("tube_trailer_context") or {}
    green_hrs = (green_hysland or {}).get("hrs_provisional_boundary") or {}
    green_eligibility = (green_hysland or {}).get("eligibility_decision") or {}
    green_hysland_pass = bool(
        (green_hysland or {}).get("schema_version") == 1
        and (green_hysland or {}).get("status") == "PUBLIC_GREENHYSLAND_REPORT_RECHECKED"
        and green_download.get("http_status") == 200
        and len(str(green_download.get("sha256", ""))) == 64
        and green_download.get("pdf_pages", 0) >= 1
        and green_trailer.get("all_required_rows_present") is True
        and green_eligibility.get("component_boundary_context_eligible") is True
        and green_eligibility.get("full_loop_external_holdout_eligible") is False
        and green_hrs.get("populated_transaction_values") is False
        and (green_hysland or {}).get("claim_boundary")
    )
    gates.append(_gate(
        "green_hysland_trailer_context_integrity",
        "PASS" if green_hysland_pass else ("FAIL" if green_hysland else "PENDING"),
        "The live Green Hysland report provides traceable tube-trailer operating context while explicitly excluding its empty HRS provisional section from full-loop validation.",
        str(green_hysland_path.relative_to(root)),
        "HTTP 200 PDF with digest, required trailer KPI rows, component-context eligibility, and an explicit false full-loop flag.",
        {
            "pdf_sha256": green_download.get("sha256"),
            "required_trailer_rows": green_trailer.get("all_required_rows_present"),
            "hrs_provisional_populated": green_hrs.get("populated_transaction_values"),
            "full_loop_external_holdout_eligible": green_eligibility.get("full_loop_external_holdout_eligible"),
        } if green_hysland else "missing; Green Hysland report recheck has not run",
    ))

    mendeley_path = root / "research/hrs_mendeley_simulation_dataset_boundary_2026_10_05.json"
    mendeley = _json(mendeley_path)
    mendeley_source = (mendeley or {}).get("source") or {}
    mendeley_meta = (mendeley or {}).get("metadata_integrity") or {}
    mendeley_characterization = (mendeley or {}).get("dataset_characterization") or {}
    mendeley_eligibility = (mendeley or {}).get("eligibility_decision") or {}
    mendeley_pass = bool(
        (mendeley or {}).get("schema_version") == 1
        and (mendeley or {}).get("status") == "PUBLIC_MENDELEY_HRS_METADATA_RECHECKED"
        and mendeley_source.get("doi") == "10.17632/mnjs94yzfc.1"
        and mendeley_meta.get("http_status") == 200
        and mendeley_meta.get("abstract_present") is True
        and mendeley_meta.get("simulation_language_present") is True
        and mendeley_meta.get("cc_by_4_present") is True
        and mendeley_characterization.get("simulation_only") is True
        and mendeley_characterization.get("experimental_logger_archive") is False
        and mendeley_characterization.get("real_station_full_loop") is False
        and mendeley_eligibility.get("full_loop_external_holdout_eligible") is False
        and (mendeley or {}).get("claim_boundary")
    )
    gates.append(_gate(
        "mendeley_hrs_simulation_dataset_boundary_integrity",
        "PASS" if mendeley_pass else ("FAIL" if mendeley else "PENDING"),
        "The openly licensed Mendeley HRS dataset is retained as simulation provenance and explicitly excluded from independent full-loop validation.",
        str(mendeley_path.relative_to(root)),
        "DataCite metadata, DOI, CC BY 4.0, simulation-only characterization, and an explicit false full-loop eligibility decision.",
        {
            "doi": mendeley_source.get("doi"),
            "cc_by_4_present": mendeley_meta.get("cc_by_4_present"),
            "simulation_only": mendeley_characterization.get("simulation_only"),
            "full_loop_external_holdout_eligible": mendeley_eligibility.get("full_loop_external_holdout_eligible"),
        } if mendeley else "missing; Mendeley HRS metadata boundary recheck has not run",
    ))

    metrohyve_path = root / "research/metrohyve_gravimetric_hrs_calibration_boundary_2026_10_05.json"
    metrohyve = _json(metrohyve_path)
    metrohyve_source = (metrohyve or {}).get("source") or {}
    metrohyve_access = (metrohyve or {}).get("access_recheck") or {}
    metrohyve_scope = (metrohyve or {}).get("observed_scope") or {}
    metrohyve_eligibility = (metrohyve or {}).get("eligibility") or {}
    metrohyve_pass = bool(
        (metrohyve or {}).get("schema_version") == 1
        and (metrohyve or {}).get("status") == "PUBLIC_ARTICLE_COMPONENT_METROLOGY_RECHECKED"
        and metrohyve_source.get("doi") == "10.1016/j.flowmeasinst.2020.101743"
        and "CC BY-NC-ND 4.0" in str(metrohyve_source.get("license"))
        and metrohyve_access.get("crossref_metadata_http_status") == 200
        and metrohyve_access.get("elsevier_metadata_http_status") == 200
        and metrohyve_access.get("open_access_article") is True
        and metrohyve_access.get("raw_machine_readable_station_logger_found") is False
        and metrohyve_scope.get("real_hrs_field_tests") is True
        and metrohyve_scope.get("maximum_pressure_bar") == 875
        and metrohyve_eligibility.get("component_flow_metrology_eligible") is True
        and metrohyve_eligibility.get("full_loop_external_holdout_eligible") is False
        and (metrohyve or {}).get("goal_completion_permitted") is False
        and bool((metrohyve or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "metrohyve_gravimetric_hrs_metrology_boundary_integrity",
        "PASS" if metrohyve_pass else ("FAIL" if metrohyve else "PENDING"),
        "The open MetroHyVe HRS calibration paper provides independent flow-meter and uncertainty context without being misrepresented as a station-to-vehicle holdout.",
        str(metrohyve_path.relative_to(root)),
        "DOI/licence metadata, open-article access, real-HRS scope, 875-bar range, component-only eligibility and explicit full-loop exclusion.",
        {
            "doi": metrohyve_source.get("doi"),
            "real_hrs_field_tests": metrohyve_scope.get("real_hrs_field_tests"),
            "maximum_pressure_bar": metrohyve_scope.get("maximum_pressure_bar"),
            "component_flow_metrology_eligible": metrohyve_eligibility.get("component_flow_metrology_eligible"),
            "full_loop_external_holdout_eligible": metrohyve_eligibility.get("full_loop_external_holdout_eligible"),
        } if metrohyve else "missing; MetroHyVe boundary recheck has not run",
    ))

    hytf_path = root / "research/hytf_open_tank_trace_boundary_2026_10_05.json"
    hytf = _json(hytf_path)
    hytf_source = (hytf or {}).get("source") or {}
    hytf_experiment = (hytf or {}).get("experiment") or {}
    hytf_channels = hytf_experiment.get("channels") or {}
    hytf_access = (hytf or {}).get("access_observation") or {}
    hytf_eligibility = (hytf or {}).get("eligibility") or {}
    hytf_pass = bool(
        (hytf or {}).get("schema_version") == 1
        and (hytf or {}).get("status") == "PUBLIC_RAW_TANK_TRACE_BOUNDARY_RECHECKED"
        and hytf_source.get("repository_commit") == "4482486fa9ab02360af364f3d1dad5ea48eabaf8"
        and hytf_source.get("dataset_sha256") == "3f11f75afec75e71fa18893e0a351966467a436f569e8349065e06c1649673a0"
        and hytf_experiment.get("sample_count") == 2536
        and hytf_experiment.get("sample_period_s") == 0.1
        and len(hytf_channels.get("tank_thermocouples") or []) == 14
        and hytf_access.get("raw_machine_readable_trace_retrieved") is True
        and hytf_access.get("mass_flow_or_transferred_mass_trace") is False
        and hytf_access.get("full_loop_external_holdout_eligible") is False
        and hytf_eligibility.get("component_tank_screen_eligible_after_protocol_freeze") is True
        and hytf_eligibility.get("full_loop_external_holdout_eligible") is False
        and (hytf or {}).get("claim_boundary")
    )
    gates.append(_gate(
        "hytf_public_tank_trace_boundary_integrity",
        "PASS" if hytf_pass else ("FAIL" if hytf else "PENDING"),
        "The public HyTF raw tank trace is pinned as a component-level thermal boundary without being promoted to an HRS full-loop holdout.",
        str(hytf_path.relative_to(root)),
        "Pinned repository commit and file digest, 2,536 samples at 0.1 s, fourteen thermocouples, explicit missing mass-flow/station channels and false full-loop eligibility.",
        {
            "repository_commit": hytf_source.get("repository_commit"),
            "dataset_sha256": hytf_source.get("dataset_sha256"),
            "sample_count": hytf_experiment.get("sample_count"),
            "sample_period_s": hytf_experiment.get("sample_period_s"),
            "tank_thermocouple_count": len(hytf_channels.get("tank_thermocouples") or []),
            "component_tank_screen_eligible_after_protocol_freeze": hytf_eligibility.get("component_tank_screen_eligible_after_protocol_freeze"),
            "full_loop_external_holdout_eligible": hytf_eligibility.get("full_loop_external_holdout_eligible"),
        } if hytf else "missing; HyTF public tank trace boundary recheck has not run",
    ))

    multhyfuel_path = root / "research/multhyfuel_d24_public_experiment_recheck_2026_10_05.json"
    multhyfuel = _json(multhyfuel_path)
    multhyfuel_download = (multhyfuel or {}).get("download") or {}
    multhyfuel_measurements = (multhyfuel or {}).get("reported_measurements") or {}
    multhyfuel_anchors = (multhyfuel or {}).get("page_anchors") or {}
    multhyfuel_eligibility = (multhyfuel or {}).get("eligibility_decision") or {}
    multhyfuel_pass = bool(
        (multhyfuel or {}).get("schema_version") == 1
        and (multhyfuel or {}).get("status") == "PUBLIC_MULTHYFUEL_D24_EXPERIMENT_RECHECKED"
        and (multhyfuel or {}).get("evidence_role") == "public_dispenser_consequence_experiment"
        and multhyfuel_download.get("http_status") == 200
        and multhyfuel_download.get("content_type") == "application/pdf"
        and multhyfuel_download.get("sha256_matches_expected") is True
        and multhyfuel_download.get("pdf_pages", 0) >= 25
        and all(multhyfuel_anchors.values())
        and multhyfuel_measurements.get("jetfire_700bar_measured_flow_g_s") == 40.0
        and multhyfuel_measurements.get("jetfire_700bar_measured_flame_length_m_min") >= 5.0
        and multhyfuel_measurements.get("internal_700bar_0_2mm_flow_g_s") == 9.0
        and multhyfuel_measurements.get("internal_700bar_0_2mm_max_h2_percent") == 25.0
        and multhyfuel_eligibility.get("public_experiment_verified") is True
        and multhyfuel_eligibility.get("consequence_benchmark_eligible") is True
        and multhyfuel_eligibility.get("full_loop_station_vehicle_holdout_eligible") is False
        and multhyfuel_eligibility.get("saga_effectiveness_eligible") is False
        and bool((multhyfuel or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "multhyfuel_d24_public_experiment_integrity",
        "PASS" if multhyfuel_pass else ("FAIL" if multhyfuel else "PENDING"),
        "The public MultHyFuel D2.4 mock-up dispenser experiments provide traceable consequence benchmarks without being misrepresented as full-loop or SAGA validation.",
        str(multhyfuel_path.relative_to(root)),
        "HTTP 200 PDF digest, 25-page source, experimental setup/page anchors, measured jet-fire/internal-cloud values and explicit full-loop/SAGA exclusions.",
        {
            "pdf_sha256": multhyfuel_download.get("sha256"),
            "pdf_pages": multhyfuel_download.get("pdf_pages"),
            "jetfire_700bar_measured_flow_g_s": multhyfuel_measurements.get("jetfire_700bar_measured_flow_g_s"),
            "jetfire_700bar_flame_length_m_min": multhyfuel_measurements.get("jetfire_700bar_measured_flame_length_m_min"),
            "internal_700bar_0_2mm_flow_g_s": multhyfuel_measurements.get("internal_700bar_0_2mm_flow_g_s"),
            "consequence_benchmark_eligible": multhyfuel_eligibility.get("consequence_benchmark_eligible"),
            "full_loop_station_vehicle_holdout_eligible": multhyfuel_eligibility.get("full_loop_station_vehicle_holdout_eligible"),
            "saga_effectiveness_eligible": multhyfuel_eligibility.get("saga_effectiveness_eligible"),
        } if multhyfuel else "missing; MultHyFuel public experiment recheck has not run",
    ))

    accidental_ignition_path = root / "research/accidental_self_ignition_public_evidence_2026_10_04.json"
    accidental_ignition = _json(accidental_ignition_path)
    accidental_source = (accidental_ignition or {}).get("source") or {}
    accidental_archive = (accidental_ignition or {}).get("archive") or {}
    accidental_eligibility = (accidental_ignition or {}).get("eligibility") or {}
    accidental_files = (accidental_ignition or {}).get("files") or []
    accidental_ignition_pass = bool(
        (accidental_ignition or {}).get("status")
        == "public_accidental_release_ignition_evidence_captured"
        and (accidental_ignition or {}).get("evidence_role")
        == "public_accidental_release_ignition_experiment"
        and accidental_source.get("zenodo_doi") == "10.5281/zenodo.17913628"
        and accidental_source.get("article_doi") == "10.1016/j.elstat.2025.104222"
        and accidental_source.get("license") == "CC BY 4.0"
        and accidental_archive.get("sha256")
        and len(accidental_files) == 3
        and all(item.get("sha256") and item.get("numeric_rows", 0) > 0 for item in accidental_files)
        and accidental_eligibility.get("public_accident_or_experiment_evidence") is True
        and accidental_eligibility.get("consequence_and_ignition_grounding_eligible") is True
        and accidental_eligibility.get("full_loop_station_vehicle_holdout_eligible") is False
        and accidental_eligibility.get("numerical_release_model_validation_claimed") is False
        and bool((accidental_ignition or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "accidental_release_ignition_public_evidence",
        "PASS" if accidental_ignition_pass else ("FAIL" if accidental_ignition else "PENDING"),
        "An openly licensed controlled high-pressure hydrogen breach experiment is captured for accident-like consequence and ignition scenario grounding without being misrepresented as station validation.",
        str(accidental_ignition_path.relative_to(root)),
        "Zenodo and article DOI, CC BY rights, archive/file hashes, pressure plus paired ignition/no-ignition traces, and an explicit full-loop exclusion.",
        {
            "zenodo_doi": accidental_source.get("zenodo_doi"),
            "article_doi": accidental_source.get("article_doi"),
            "license": accidental_source.get("license"),
            "file_count": len(accidental_files),
            "archive_sha256": accidental_archive.get("sha256"),
            "eligibility": accidental_eligibility,
            "claim_boundary": (accidental_ignition or {}).get("claim_boundary"),
        } if accidental_ignition else "missing; public accidental-release evidence record has not been captured",
    ))

    thermal_protocol_path = root / "research/thermal_effects_ignited_release_protocol_2026_10_04.json"
    thermal_protocol = _json(thermal_protocol_path)
    thermal_source = (thermal_protocol or {}).get("source") or {}
    thermal_analysis = (thermal_protocol or {}).get("predeclared_analysis") or {}
    thermal_files = (thermal_protocol or {}).get("selected_files") or []
    expected_thermal_files = [f"Exp_{index:05d}.mat" for index in range(1, 9)]
    thermal_protocol_pass = bool(
        (thermal_protocol or {}).get("status") == "frozen_before_raw_outcome_access"
        and (thermal_protocol or {}).get("protocol_id") == "THERMAL-EFFECTS-IGNITED-2601"
        and thermal_source.get("doi") == "10.23642/usn.17695082.v1"
        and thermal_source.get("license") == "CC BY 4.0"
        and thermal_files == expected_thermal_files
        and (thermal_protocol or {}).get("selection_rule")
        and (thermal_protocol or {}).get("raw_outcomes_accessed_before_freeze") is False
        and thermal_analysis.get("primary_observables")
        and thermal_analysis.get("eligibility")
        and thermal_analysis.get("claim_boundary")
        and (thermal_protocol or {}).get("data_redistribution")
    )
    gates.append(_gate(
        "thermal_effects_public_protocol_integrity",
        "PASS" if thermal_protocol_pass else ("FAIL" if thermal_protocol else "PENDING"),
        "The independent public ignited-release thermal-effects archive is prospectively frozen as a consequence-only screen.",
        str(thermal_protocol_path.relative_to(root)),
        "DOI and CC BY rights, all eight public MAT experiments, predeclared observables/eligibility, no pre-freeze outcome access and an explicit exclusion from full-loop or legal-distance claims.",
        {
            "doi": thermal_source.get("doi"),
            "license": thermal_source.get("license"),
            "file_count": len(thermal_files),
            "selected_files": thermal_files,
            "raw_outcomes_accessed_before_freeze": (thermal_protocol or {}).get("raw_outcomes_accessed_before_freeze"),
            "claim_boundary": thermal_analysis.get("claim_boundary"),
        } if thermal_protocol else "missing; thermal-effects protocol has not been frozen",
    ))

    thermal_replay_path = root / "research/thermal_effects_archive_replay_2026_10_04.json"
    thermal_replay = _json(thermal_replay_path)
    thermal_cases = (thermal_replay or {}).get("cases") or []
    thermal_replay_pass = bool(
        (thermal_replay or {}).get("status") == "descriptive_public_archive_replay_complete"
        and (thermal_replay or {}).get("source_doi") == "10.23642/usn.17695082.v1"
        and (thermal_replay or {}).get("license") == "CC BY 4.0"
        and (thermal_replay or {}).get("case_count") == 8
        and len(thermal_cases) == 8
        and [case.get("file") for case in thermal_cases] == expected_thermal_files
        and all(
            case.get("bytes", 0) > 0
            and len(case.get("sha256", "")) == 64
            and case.get("active_release_window", {}).get("threshold_g_s") == 0.5
            for case in thermal_cases
        )
        and "descriptive" in ((thermal_replay or {}).get("claim_boundary") or "").lower()
    )
    gates.append(_gate(
        "thermal_effects_public_archive_replay",
        "PASS" if thermal_replay_pass else ("FAIL" if thermal_replay else "PENDING"),
        "All eight public ignited-release MAT files were parsed under one deterministic descriptive extraction rule.",
        str(thermal_replay_path.relative_to(root)),
        "Eight source files, non-empty SHA-256-linked artifacts, consistent mass-flow release-window rule and an explicit non-validation claim boundary.",
        {
            "case_count": len(thermal_cases),
            "files": [case.get("file") for case in thermal_cases],
            "release_window_threshold_g_s": (
                thermal_cases[0].get("active_release_window", {}).get("threshold_g_s")
                if thermal_cases else None
            ),
            "claim_boundary": (thermal_replay or {}).get("claim_boundary"),
        } if thermal_replay else "missing; thermal-effects archive replay has not been run",
    ))

    thermal_result_path = root / "research/thermal_effects_ignited_release_result_2026_10_05.json"
    thermal_result = _json(thermal_result_path)
    thermal_result_cases = (thermal_result or {}).get("cases") or []
    thermal_result_pass = bool(
        (thermal_result or {}).get("status") == "postfreeze_descriptive_consequence_replay_complete"
        and (thermal_result or {}).get("source", {}).get("doi") == "10.23642/usn.17695082.v1"
        and (thermal_result or {}).get("source", {}).get("license") == "CC BY 4.0"
        and (thermal_result or {}).get("case_count") == 8
        and len(thermal_result_cases) == 8
        and [case.get("file") for case in thermal_result_cases] == expected_thermal_files
        and not (thermal_result or {}).get("missing_files")
        and all(
            len(case.get("sha256", "")) == 64
            and not case.get("required_channel_missing")
            and case.get("timebase", {}).get("MFM", {}).get("monotonic_strict") is True
            for case in thermal_result_cases
        )
        and "not predictive" in ((thermal_result or {}).get("claim_boundary") or "").lower()
    )
    gates.append(_gate(
        "thermal_effects_postfreeze_integrity_replay",
        "PASS" if thermal_result_pass else ("FAIL" if thermal_result else "PENDING"),
        "The post-freeze thermal archive audit verifies every public case, time base, channel inventory and claim boundary without promoting it to predictive station validation.",
        str(thermal_result_path.relative_to(root)),
        "Eight SHA-256-linked cases, deterministic release-window rule, monotonic source time bases and explicit non-predictive/full-loop exclusions.",
        {
            "case_count": len(thermal_result_cases),
            "missing_files": (thermal_result or {}).get("missing_files"),
            "claim_boundary": (thermal_result or {}).get("claim_boundary"),
        } if thermal_result else "missing; post-freeze thermal audit has not been run",
    ))

    khk_public_path = root / "research/khk_hydrogen_station_public_reports_inventory_2026_10_04.json"
    khk_public = _json(khk_public_path)
    khk_source = (khk_public or {}).get("source_page") or {}
    khk_rights = (khk_public or {}).get("rights_and_mirroring") or {}
    khk_coverage = (khk_public or {}).get("coverage") or {}
    khk_eligibility = (khk_public or {}).get("eligibility") or {}
    khk_public_pass = bool(
        (khk_public or {}).get("status")
        == "public_khk_accident_report_inventory_captured"
        and khk_source.get("institution")
        == "High Pressure Gas Safety Institute of Japan (KHK)"
        and khk_source.get("url")
        == "https://www.khk.or.jp/hydrogen/accident_information.html"
        and khk_rights.get("landing_page_public") is True
        and khk_rights.get("raw_pdf_mirrored") is False
        and khk_rights.get("rights_status") == "public_report_citation_only"
        and khk_coverage.get("pdf_report_count") == 23
        and khk_coverage.get("incident_code_count") == 26
        and khk_coverage.get("precaution_report_count") == 8
        and len((khk_public or {}).get("accident_reports") or []) == 23
        and len((khk_public or {}).get("precaution_reports") or []) == 8
        and all(
            item.get("url") and item.get("incident_codes")
            for item in ((khk_public or {}).get("accident_reports") or [])
        )
        and all(
            item.get("url") and item.get("year")
            for item in ((khk_public or {}).get("precaution_reports") or [])
        )
        and khk_eligibility.get("public_actual_accident_evidence") is True
        and khk_eligibility.get("qualitative_scenario_grounding_eligible") is True
        and khk_eligibility.get("synchronized_process_trace_eligible") is False
        and khk_eligibility.get("full_loop_station_vehicle_holdout_eligible") is False
        and khk_eligibility.get("physics_model_validation_eligible") is False
        and bool((khk_public or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "khk_public_accident_report_inventory",
        "PASS" if khk_public_pass else ("FAIL" if khk_public else "PENDING"),
        "Public KHK hydrogen accident reports are inventoried for traceable qualitative scenario and response grounding without being misrepresented as numerical validation data.",
        str(khk_public_path.relative_to(root)),
        "23 linked PDF reports covering 26 incident codes, 8 precaution reports, public citation links, no PDF mirroring, and explicit exclusion from synchronized physics/full-loop claims.",
        {
            "source_page": khk_source,
            "coverage": khk_coverage,
            "rights_and_mirroring": khk_rights,
            "eligibility": khk_eligibility,
            "claim_boundary": (khk_public or {}).get("claim_boundary"),
        } if khk_public else "missing; KHK public report inventory has not been captured",
    ))

    khk_access_path = root / "research/khk_public_reports_access_verification_2026_10_04.json"
    khk_access = _json(khk_access_path)
    khk_access_records = (khk_access or {}).get("records") or []
    khk_access_pass = bool(
        (khk_access or {}).get("status") == "public_khk_accident_report_access_verified"
        and (khk_access or {}).get("report_count") == 23
        and (khk_access or {}).get("verified_report_count") == 23
        and len(khk_access_records) == 23
        and all(
            record.get("http_status") == 200
            and record.get("content_type", "").lower().startswith("application/pdf")
            and record.get("bytes", 0) > 0
            and record.get("pdf_magic") is True
            and len(record.get("sha256") or "") == 64
            and record.get("page_count", 0) > 0
            for record in khk_access_records
        )
        and "not redistributed" in ((khk_access or {}).get("rights_boundary") or "").lower()
        and bool((khk_access or {}).get("claim_boundary"))
    )
    gates.append(_gate(
        "khk_public_accident_report_access_verification",
        "PASS" if khk_access_pass else ("FAIL" if khk_access else "PENDING"),
        "All inventoried KHK accident-report links resolve to PDF files whose provenance is hash-locked without redistributing the reports.",
        str(khk_access_path.relative_to(root)),
        "23/23 public report URLs return PDF content with non-empty SHA-256 records and page counts; only metadata is committed.",
        {
            "report_count": (khk_access or {}).get("report_count"),
            "verified_report_count": (khk_access or {}).get("verified_report_count"),
            "page_counts": [record.get("page_count") for record in khk_access_records],
            "rights_boundary": (khk_access or {}).get("rights_boundary"),
            "claim_boundary": (khk_access or {}).get("claim_boundary"),
        } if khk_access else "missing; KHK public report access verification has not been run",
    ))

    precedent_routing_path = root / "research/runtime_public_accident_precedent_routing_2026_10_07.json"
    precedent_routing = _json(precedent_routing_path)
    precedent_source = (precedent_routing or {}).get("source") or {}
    precedent_aggregate = (precedent_routing or {}).get("aggregate") or {}
    precedent_source_paths = {
        "precedent_map_sha256": root / "research/khk_scenario_precedent_map_2026_10_04.json",
        "inventory_sha256": root / "research/khk_hydrogen_station_public_reports_inventory_2026_10_04.json",
        "runtime_resolver_sha256": root / "src/h2station/hazop/response.py",
        "runtime_manifest_sha256": root / "src/h2station/llm_grounding.py",
    }
    precedent_hashes_match = bool(precedent_routing) and all(
        precedent_source.get(key) == _sha256(path)
        for key, path in precedent_source_paths.items()
    )
    precedent_routing_pass = bool(
        (precedent_routing or {}).get("artifact_type")
        == "runtime_public_accident_precedent_routing_audit"
        and (precedent_routing or {}).get("status") == "PASS"
        and precedent_source.get("source_digest_matches") is True
        and precedent_hashes_match
        and precedent_aggregate.get("public_report_count") == 23
        and precedent_aggregate.get("mapped_response_family_count") == 8
        and precedent_aggregate.get("unmatched_response_family_count") == 0
        and precedent_aggregate.get("manifest_routing_failure_count") == 0
        and precedent_aggregate.get("prompt_projection_failure_count") == 0
        and precedent_aggregate.get("contract_pass") is True
        and (precedent_routing or {}).get("raw_report_text_loaded") is False
        and (precedent_routing or {}).get("effectiveness_claimed") is False
        and (precedent_routing or {}).get("frequency_claimed") is False
    )
    gates.append(_gate(
        "runtime_public_accident_precedent_routing",
        "PASS" if precedent_routing_pass else ("FAIL" if precedent_routing else "PENDING"),
        "Active response families receive integrity-checked, scenario-specific public KHK accident precedents in both the evidence manifest and compact LLM prompt.",
        str(precedent_routing_path.relative_to(root)),
        "23 citation-only reports, eight mapped response families, current source hashes and zero manifest/prompt routing failures; no raw report text or effectiveness/frequency claim.",
        {
            "aggregate": precedent_aggregate,
            "source_hashes_match": precedent_hashes_match,
            "raw_report_text_loaded": (precedent_routing or {}).get("raw_report_text_loaded"),
            "effectiveness_claimed": (precedent_routing or {}).get("effectiveness_claimed"),
            "claim_boundary": (precedent_routing or {}).get("claim_boundary"),
        } if precedent_routing else "missing; runtime accident-precedent routing audit has not run",
    ))

    preslhy_path = root / "research/preslhy_blowdown_external_validation.json"
    preslhy = _json(preslhy_path)
    preslhy_protocol_path = root / "research/preslhy_blowdown_validation_protocol.json"
    preslhy_protocol = _json(preslhy_protocol_path)
    preslhy_eligibility = (preslhy or {}).get("eligibility") or {}
    preslhy_aggregate = (preslhy or {}).get("aggregate") or {}
    preslhy_protocol_hash = (
        _sha256(preslhy_protocol_path) if preslhy_protocol_path.is_file() else None
    )
    preslhy_pass = bool(
        (preslhy_protocol or {}).get("status")
        == "frozen_before_raw_excel_outcome_access"
        and ((preslhy_protocol or {}).get("source") or {}).get(
            "outcomes_accessed_before_freeze"
        )
        is False
        and preslhy_eligibility.get("minimum_requirements_met") is True
        and preslhy_aggregate.get(
            "ambient_direct_aperture_blowdown_claim_supported"
        )
        is True
        and (preslhy or {}).get("protocol_sha256") == preslhy_protocol_hash
    )
    gates.append(_gate(
        "preslhy_blowdown_external_validation",
        "PASS" if preslhy_pass else ("FAIL" if preslhy else "PENDING"),
        "The source-depletion and direct-aperture release model meets its prospectively frozen screens on public PRESLHY ambient blowdown experiments.",
        f"{preslhy_path.relative_to(root)}; {preslhy_protocol_path.relative_to(root)}",
        ">=12 cases across >=3 nozzle and pressure groups, >=70% joint primary pass fraction, frozen implementation and retained failures.",
        {
            "eligibility": preslhy_eligibility,
            "aggregate": preslhy_aggregate,
            "claim_boundary": (preslhy_protocol or {}).get("claim_boundary"),
        } if preslhy else "missing; acquisition/validation has not completed",
    ))

    preslhy_partb_path = root / "research/preslhy_partb_ambient_validation.json"
    preslhy_partb = _json(preslhy_partb_path)
    preslhy_partb_protocol_path = root / "research/preslhy_partb_holdout_protocol.json"
    preslhy_partb_protocol = _json(preslhy_partb_protocol_path)
    preslhy_partb_eligibility = (preslhy_partb or {}).get("eligibility") or {}
    preslhy_partb_aggregate = (preslhy_partb or {}).get("aggregate") or {}
    preslhy_partb_protocol_hash = (
        _sha256(preslhy_partb_protocol_path)
        if preslhy_partb_protocol_path.is_file()
        else None
    )
    preslhy_partb_pass = bool(
        (preslhy_partb_protocol or {}).get("status")
        == "frozen_before_part_b_archive_download_and_numerical_outcome_access"
        and (preslhy_partb_protocol or {}).get("outcomes_accessed_before_freeze") is False
        and preslhy_partb_eligibility.get("minimum_requirements_met") is True
        and preslhy_partb_aggregate.get(
            "ambient_cryostat_part_b_claim_supported"
        ) is True
        and (preslhy_partb or {}).get("protocol_sha256") == preslhy_partb_protocol_hash
    )
    gates.append(_gate(
        "preslhy_partb_ambient_external_validation",
        "PASS" if preslhy_partb_pass else ("FAIL" if preslhy_partb else "PENDING"),
        "The frozen release model meets the independent ambient Cryostat Part-B pressure-decay screens.",
        f"{preslhy_partb_path.relative_to(root)}; {preslhy_partb_protocol_path.relative_to(root)}",
        "Five public ambient cases across two nozzle and two pressure groups, >=70% joint primary pass fraction, no post-freeze fitting.",
        {
            "eligibility": preslhy_partb_eligibility,
            "aggregate": preslhy_partb_aggregate,
            "archive_sha256": (preslhy_partb or {}).get("archive_sha256"),
            "claim_boundary": (preslhy_partb or {}).get("claim_boundary"),
            "protocol_hash_matches": (
                (preslhy_partb or {}).get("protocol_sha256")
                == preslhy_partb_protocol_hash
            ),
        } if preslhy_partb else "missing; Part-B archive evaluation has not completed",
    ))

    preslhy_partb_nonadiabatic_path = root / "research/preslhy_partb_nonadiabatic_diagnostic_2026_10_05.json"
    preslhy_partb_nonadiabatic = _json(preslhy_partb_nonadiabatic_path)
    preslhy_partb_nonadiabatic_result = (preslhy_partb_nonadiabatic or {}).get("diagnostic_result") or {}
    preslhy_partb_nonadiabatic_pass = bool(
        (preslhy_partb_nonadiabatic or {}).get("schema_version") == 1
        and (preslhy_partb_nonadiabatic or {}).get("status")
        == "POST_OUTCOME_DEVELOPMENT_DIAGNOSTIC_ONLY"
        and (preslhy_partb_nonadiabatic or {}).get("protocol", {}).get("outcomes_were_already_accessed") is True
        and (preslhy_partb_nonadiabatic or {}).get("protocol", {}).get("case_count") == 5
        and preslhy_partb_nonadiabatic_result.get("joint_primary_passes") == 3
        and (preslhy_partb_nonadiabatic or {}).get("baseline_frozen_result", {}).get("joint_primary_passes") == 3
        and (preslhy_partb_nonadiabatic or {}).get("interpretation", {}).get("claim_boundary")
    )
    gates.append(_gate(
        "preslhy_partb_nonadiabatic_diagnostic_integrity",
        "PASS" if preslhy_partb_nonadiabatic_pass else ("FAIL" if preslhy_partb_nonadiabatic else "PENDING"),
        "The revised non-adiabatic model is replayed on the consumed Part-B cases as a negative development diagnostic without replacing the frozen result.",
        str(preslhy_partb_nonadiabatic_path.relative_to(root)),
        "Five post-outcome cases, unchanged 3/5 joint result, explicit geometry limitation and non-validation claim boundary.",
        {
            "status": (preslhy_partb_nonadiabatic or {}).get("status"),
            "joint_primary_passes": preslhy_partb_nonadiabatic_result.get("joint_primary_passes"),
            "baseline_joint_primary_passes": (preslhy_partb_nonadiabatic or {}).get("baseline_frozen_result", {}).get("joint_primary_passes"),
            "claim_boundary": (preslhy_partb_nonadiabatic or {}).get("interpretation", {}).get("claim_boundary"),
        } if preslhy_partb_nonadiabatic else "missing; Part-B revised-model diagnostic has not been recorded",
    ))

    preslhy_partb_input_audit_path = root / "research/preslhy_partb_input_audit_2026_10_05.json"
    preslhy_partb_input_audit = _json(preslhy_partb_input_audit_path)
    preslhy_partb_input_checks = (preslhy_partb_input_audit or {}).get("checks") or {}
    preslhy_partb_input_audit_pass = bool(
        (preslhy_partb_input_audit or {}).get("schema_version") == 1
        and (preslhy_partb_input_audit or {}).get("status")
        == "completed_frozen_input_interpretation_audit"
        and (preslhy_partb_input_audit or {}).get("evidence_role")
        == "parser_and_unit_diagnostic_only"
        and preslhy_partb_input_audit.get("frozen_validation_result_unchanged") is True
        and preslhy_partb_input_checks.get("all_checks_pass") is True
        and (preslhy_partb_input_audit or {}).get("interpretation", {}).get("claim_boundary")
    )
    gates.append(_gate(
        "preslhy_partb_input_interpretation_audit",
        "PASS" if preslhy_partb_input_audit_pass else ("FAIL" if preslhy_partb_input_audit else "PENDING"),
        "The PRESLHY Part-B workbook labels, units, time base and release marker are independently checked without changing the frozen validation result.",
        str(preslhy_partb_input_audit_path.relative_to(root)),
        "Five Final workbooks, bar units, finite monotonic samples, nominal-pressure agreement and release-marker alignment.",
        {
            "checks": preslhy_partb_input_checks,
            "finding": (preslhy_partb_input_audit or {}).get("interpretation", {}).get("finding"),
            "claim_boundary": (preslhy_partb_input_audit or {}).get("interpretation", {}).get("claim_boundary"),
        } if preslhy_partb_input_audit else "missing; Part-B input interpretation audit has not been recorded",
    ))

    e5_result_path = root / "research/preslhy_e5_1_holdout_result.json"
    e5_result = _json(e5_result_path)
    e5_protocol_path = root / "research/preslhy_e5_1_holdout_protocol.json"
    e5_protocol = _json(e5_protocol_path)
    e5_primary = (e5_result or {}).get("primary_ambient") or {}
    e5_aggregate = e5_primary.get("aggregate") or {}
    e5_protocol_hash = (
        _sha256(e5_protocol_path) if e5_protocol_path.is_file() else None
    )
    e5_pass = bool(
        (e5_protocol or {}).get("status")
        == "fully_frozen_before_numerical_outcome_access"
        and (e5_protocol or {}).get("outcomes_accessed_before_freeze") is False
        and e5_aggregate.get("minimum_requirements_met") is True
        and e5_aggregate.get("claim_supported") is True
        and (e5_result or {}).get("protocol_sha256") == e5_protocol_hash
    )
    gates.append(_gate(
        "preslhy_revised_holdout_validation",
        "PASS" if e5_pass else ("FAIL" if e5_result else "PENDING"),
        "The revised non-adiabatic source-depletion model meets the prospectively frozen PRESLHY E5.1 holdout rule.",
        f"{e5_result_path.relative_to(root)}; {e5_protocol_path.relative_to(root)}",
        ">=4 primary ambient cases across >=2 nozzle and pressure groups, >=70% joint pass fraction, frozen implementation and retained failures.",
        {
            "aggregate": e5_aggregate,
            "primary_cases": len(e5_primary.get("cases") or []),
            "retained_failures": len((e5_result or {}).get("retained_failures") or []),
            "protocol_hash_matches": (
                (e5_result or {}).get("protocol_sha256") == e5_protocol_hash
            ),
            "claim_boundary": (e5_result or {}).get("claim_boundary"),
        } if e5_result else "missing; holdout evaluation has not completed",
    ))

    proust_result_path = root / "research/proust_release_holdout_result.json"
    proust_result = _json(proust_result_path)
    proust_protocol_path = root / "research/proust_release_holdout_protocol.json"
    proust_protocol = _json(proust_protocol_path)
    proust_data_path = root / "data/public_validation/derived/proust_90mpa_release.csv"
    proust_aggregate = (proust_result or {}).get("aggregate") or {}
    proust_protocol_hash = (
        _sha256(proust_protocol_path) if proust_protocol_path.is_file() else None
    )
    proust_data_hash = _sha256(proust_data_path) if proust_data_path.is_file() else None
    proust_pass = bool(
        (proust_protocol or {}).get("status")
        == "fully_frozen_before_numerical_figure_outcome_access"
        and (proust_protocol or {}).get(
            "numerical_figure_outcomes_accessed_before_freeze"
        ) is False
        and proust_aggregate.get("minimum_requirements_met") is True
        and proust_aggregate.get("claim_supported") is True
        and (proust_result or {}).get("protocol_sha256") == proust_protocol_hash
        and (proust_result or {}).get("data_sha256") == proust_data_hash
    )
    gates.append(_gate(
        "proust_independent_release_validation",
        "PASS" if proust_pass else ("FAIL" if proust_result else "PENDING"),
        "The fixed high-pressure aperture relation meets its prospectively frozen rule on the independent INERIS/CEA 90 MPa campaign.",
        f"{proust_result_path.relative_to(root)}; {proust_protocol_path.relative_to(root)}; {proust_data_path.relative_to(root)}",
        "All 1, 2 and 3 mm series eligible; >=2/3 jointly pass <=15% peak-normalized RMSE and <=20% median absolute percentage error.",
        {
            "aggregate": proust_aggregate,
            "protocol_hash_matches": (
                (proust_result or {}).get("protocol_sha256") == proust_protocol_hash
            ),
            "data_hash_matches": (
                (proust_result or {}).get("data_sha256") == proust_data_hash
            ),
            "claim_boundary": (proust_result or {}).get("claim_boundary"),
        } if proust_result else "missing; independent release evaluation has not completed",
    ))

    release_development_path = root / "research/release_network_development.json"
    release_development = _json(release_development_path)
    release_development_pass = bool(
        (release_development or {}).get("evidence_role")
        == "consumed_development_only"
        and (release_development or {}).get("eligible_as_confirmatory_validation")
        is False
        and (((release_development or {}).get("interpretation") or {}).get(
            "claim_supported"
        ))
        is False
        and all(
            ((release_development or {}).get("contamination_disclosure") or {}).get(key)
            is True
            for key in (
                "proust_outcomes_viewed_before_parameter_selection",
                "imamura_numeric_outcomes_viewed_before_analysis_formalization",
            )
        )
    )
    gates.append(_gate(
        "release_network_development_integrity",
        "PASS" if release_development_pass else "FAIL",
        "The post-outcome release-network diagnostic is retained as consumed development evidence and cannot be mistaken for validation.",
        str(release_development_path.relative_to(root)),
        "Proust and Imamura contamination disclosed; confirmatory eligibility and claim support both false.",
        {
            "evidence_role": (release_development or {}).get("evidence_role"),
            "eligible_as_confirmatory_validation": (release_development or {}).get(
                "eligible_as_confirmatory_validation"
            ),
            "interpretation": (release_development or {}).get("interpretation"),
        } if release_development else "missing",
    ))

    apparatus_protocol_path = root / "research/apparatus_resolved_release_protocol.json"
    apparatus_protocol = _json(apparatus_protocol_path)
    apparatus_secondary_path = root / "research/release_network_prospective_protocol.json"
    apparatus_secondary = _json(apparatus_secondary_path)
    apparatus_manifest_path = root / "research/apparatus_release_holdout_manifest.template.json"
    apparatus_manifest = _json(apparatus_manifest_path)
    apparatus_model_path = root / "src/h2station/release_network.py"
    apparatus_evaluator_path = root / "src/h2station/apparatus_release_validation.py"
    apparatus_runner_path = root / "scripts/run_apparatus_release_holdout.py"
    locked_model = (apparatus_protocol or {}).get("locked_model") or {}
    locked_evaluator = (apparatus_protocol or {}).get("locked_evaluator") or {}
    template_cases = (apparatus_manifest or {}).get("cases") or []
    apparatus_protocol_hash = (
        _sha256(apparatus_protocol_path) if apparatus_protocol_path.is_file() else None
    )
    apparatus_model_hash = (
        _sha256(apparatus_model_path) if apparatus_model_path.is_file() else None
    )
    apparatus_evaluator_hash = (
        _sha256(apparatus_evaluator_path) if apparatus_evaluator_path.is_file() else None
    )
    apparatus_runner_hash = (
        _sha256(apparatus_runner_path) if apparatus_runner_path.is_file() else None
    )
    apparatus_integrity_pass = bool(
        (apparatus_protocol or {}).get("status")
        == "PROSPECTIVE_PROTOCOL_SPECIFICATION_ONLY"
        and ((apparatus_protocol or {}).get("protocol_revision") or {}).get(
            "target_campaign_outcome_data_accessed"
        ) is False
        and str(locked_model.get("sha256", "")).lower() == apparatus_model_hash
        and str(locked_evaluator.get("sha256", "")).lower() == apparatus_evaluator_hash
        and str(locked_evaluator.get("runner_sha256", "")).lower()
        == apparatus_runner_hash
        and str((apparatus_secondary or {}).get("model_sha256", "")).lower()
        == apparatus_model_hash
        and str((apparatus_secondary or {}).get("evaluator_sha256", "")).lower()
        == apparatus_evaluator_hash
        and str((apparatus_secondary or {}).get("campaign_runner_sha256", "")).lower()
        == apparatus_runner_hash
        and str((apparatus_manifest or {}).get("protocol_sha256", "")).lower()
        == apparatus_protocol_hash
        and str((apparatus_manifest or {}).get("model_sha256", "")).lower()
        == apparatus_model_hash
        and str((apparatus_manifest or {}).get("evaluator_sha256", "")).lower()
        == apparatus_evaluator_hash
        and str((apparatus_manifest or {}).get("runner_sha256", "")).lower()
        == apparatus_runner_hash
        and len(template_cases) == 8
        and len({
            ((item.get("strata") or {}).get("source_pressure_group"))
            for item in template_cases
        }) >= 2
        and len({
            ((item.get("strata") or {}).get("geometry_group"))
            for item in template_cases
        }) >= 2
        and len({
            ((item.get("strata") or {}).get("valve_opening_group"))
            for item in template_cases
        }) >= 2
        and ((apparatus_protocol or {}).get("promotion_gate") or {}).get(
            "external_validation_status"
        ) == "NOT_ESTABLISHED"
    )
    gates.append(_gate(
        "apparatus_resolved_holdout_executor_integrity",
        "PASS" if apparatus_integrity_pass else "FAIL",
        "The prospective source-line-valve-terminal holdout path is hash-locked, privacy bounded and executable without being promoted to validation.",
        "; ".join(str(path.relative_to(root)) for path in (
            apparatus_protocol_path, apparatus_secondary_path, apparatus_manifest_path,
            apparatus_model_path, apparatus_evaluator_path, apparatus_runner_path,
        )),
        "Model, evaluator, runner and protocol hashes agree; eight-case stratification and no-fit/privacy rules are frozen; external validation remains explicitly not established.",
        {
            "protocol_sha256": apparatus_protocol_hash,
            "model_sha256": apparatus_model_hash,
            "evaluator_sha256": apparatus_evaluator_hash,
            "runner_sha256": apparatus_runner_hash,
            "template_case_count": len(template_cases),
            "target_campaign_outcome_data_accessed": (
                ((apparatus_protocol or {}).get("protocol_revision") or {}).get(
                    "target_campaign_outcome_data_accessed"
                )
            ),
            "external_validation_status": (
                ((apparatus_protocol or {}).get("promotion_gate") or {}).get(
                    "external_validation_status"
                )
            ),
            "claim_boundary": (apparatus_protocol or {}).get("claim_boundary"),
        } if apparatus_protocol else "missing",
    ))

    schefer_result_path = root / "research/schefer_2006_holdout_result.json"
    schefer_result = _json(schefer_result_path)
    schefer_protocol_path = root / "research/schefer_2006_holdout_protocol.json"
    schefer_protocol = _json(schefer_protocol_path)
    schefer_data_path = root / "data/public_validation/derived/schefer_2006_figure3b.csv"
    schefer_observed = (schefer_result or {}).get("result") or {}
    schefer_protocol_hash = (
        _sha256(schefer_protocol_path) if schefer_protocol_path.is_file() else None
    )
    schefer_data_hash = _sha256(schefer_data_path) if schefer_data_path.is_file() else None
    schefer_pass = bool(
        (schefer_protocol or {}).get("status")
        == "endpoints_and_code_frozen_before_numerical_curve_access_with_aggregate_duration_known"
        and ((schefer_protocol or {}).get("known_before_freeze") or {}).get(
            "numerical_curve_coordinates_accessed"
        ) is False
        and schefer_observed.get("joint_primary_screen_pass") is True
        and (schefer_result or {}).get("protocol_sha256") == schefer_protocol_hash
        and (schefer_result or {}).get("data_sha256") == schefer_data_hash
    )
    gates.append(_gate(
        "schefer_transient_release_validation",
        "PASS" if schefer_pass else ("FAIL" if schefer_result else "PENDING"),
        "The locked adiabatic vessel-discharge model meets all frozen transient mass-flow screens on the independent Sandia/SRI experiment.",
        f"{schefer_result_path.relative_to(root)}; {schefer_protocol_path.relative_to(root)}; {schefer_data_path.relative_to(root)}",
        "At least 15 points; <=15% peak-normalized RMSE, <=20% median absolute percentage error and <=20% half-peak-time error; all screens required.",
        {
            "result": schefer_observed,
            "protocol_hash_matches": (
                (schefer_result or {}).get("protocol_sha256") == schefer_protocol_hash
            ),
            "data_hash_matches": (
                (schefer_result or {}).get("data_sha256") == schefer_data_hash
            ),
            "prior_aggregate_duration_known": bool(
                ((schefer_protocol or {}).get("known_before_freeze") or {}).get(
                    "approximate_total_blowdown_duration_from_secondary_descriptions"
                )
            ),
            "claim_boundary": (schefer_protocol or {}).get("claim_boundary"),
        } if schefer_result else "missing; transient release holdout has not completed",
    ))

    schefer_2007_result_path = root / "research/schefer_2007_holdout_result.json"
    schefer_2007_result = _json(schefer_2007_result_path)
    schefer_2007_protocol_path = root / "research/schefer_2007_holdout_protocol.json"
    schefer_2007_protocol = _json(schefer_2007_protocol_path)
    schefer_2007_data_path = root / "data/public_validation/derived/schefer_2007_figure4.csv"
    schefer_2007_observed = (schefer_2007_result or {}).get("result") or {}
    schefer_2007_protocol_hash = (
        _sha256(schefer_2007_protocol_path) if schefer_2007_protocol_path.is_file() else None
    )
    schefer_2007_data_hash = (
        _sha256(schefer_2007_data_path) if schefer_2007_data_path.is_file() else None
    )
    schefer_2007_pass = bool(
        (schefer_2007_protocol or {}).get("status")
        == "endpoints_and_code_frozen_before_numerical_curve_access"
        and ((schefer_2007_protocol or {}).get("known_before_freeze") or {}).get(
            "numerical_curve_coordinates_accessed"
        ) is False
        and schefer_2007_observed.get("joint_primary_screen_pass") is True
        and (schefer_2007_result or {}).get("protocol_sha256")
        == schefer_2007_protocol_hash
        and (schefer_2007_result or {}).get("data_sha256") == schefer_2007_data_hash
    )
    gates.append(_gate(
        "schefer_2007_pressure_decay_validation",
        "PASS" if schefer_2007_pass else ("FAIL" if schefer_2007_result else "PENDING"),
        "The locked adiabatic vessel-discharge model meets all frozen pressure-decay screens on the independent Schefer et al. 2007 experiment.",
        f"{schefer_2007_result_path.relative_to(root)}; {schefer_2007_protocol_path.relative_to(root)}; {schefer_2007_data_path.relative_to(root)}",
        "At least 15 points; <=10% initial-pressure-normalized RMSE, <=15% median absolute percentage error and <=20% half-pressure-time error; all screens required.",
        {
            "result": schefer_2007_observed,
            "protocol_hash_matches": (
                (schefer_2007_result or {}).get("protocol_sha256")
                == schefer_2007_protocol_hash
            ),
            "data_hash_matches": (
                (schefer_2007_result or {}).get("data_sha256") == schefer_2007_data_hash
            ),
            "claim_boundary": (schefer_2007_protocol or {}).get("claim_boundary"),
        } if schefer_2007_result else "missing; pressure-decay holdout has not completed",
    ))

    grune_result_path = root / "research/grune_2014_holdout_result.json"
    grune_result = _json(grune_result_path)
    grune_protocol_path = root / "research/grune_2014_holdout_protocol.json"
    grune_protocol = _json(grune_protocol_path)
    grune_data_path = root / "data/public_validation/derived/grune_2014_figure2.csv"
    grune_access_path = root / "research/grune_2014_publisher_access_recheck_2026_10_06.json"
    grune_access = _json(grune_access_path)
    grune_eligibility = (grune_result or {}).get("eligibility") or {}
    grune_observed = (grune_result or {}).get("result") or {}
    grune_hashes_match = bool(
        grune_protocol_path.is_file()
        and grune_data_path.is_file()
        and (grune_result or {}).get("protocol_sha256") == _sha256(grune_protocol_path)
        and (grune_result or {}).get("data_sha256") == _sha256(grune_data_path)
    )
    grune_pass = bool(
        (grune_protocol or {}).get("status")
        == "endpoints_and_code_frozen_before_numerical_curve_access"
        and ((grune_protocol or {}).get("known_before_freeze") or {}).get(
            "numerical_curve_coordinates_accessed"
        ) is False
        and grune_hashes_match
        and grune_eligibility.get("minimum_requirements_met") is True
        and grune_observed.get("joint_primary_screen_pass") is True
        and (grune_access or {}).get("eligibility", {}).get("full_raw_holdout_eligible") is True
    )
    grune_status = (
        "PASS" if grune_pass else
        "PENDING" if grune_result and not grune_eligibility.get("minimum_requirements_met")
        else "FAIL" if grune_result else "PENDING"
    )
    gates.append(_gate(
        "grune_2014_pressure_decay_validation",
        grune_status,
        "The locked source model meets all pressure-decay screens on the independent KIT small-reservoir release.",
        f"{grune_result_path.relative_to(root)}; {grune_protocol_path.relative_to(root)}; {grune_data_path.relative_to(root)}; {grune_access_path.relative_to(root)}; research/grune_2014_archive_access_recheck_2026_10_05.json",
        "At least 15 points plus an observable half-pressure crossing; <=10% NRMSE, <=15% median error and <=20% half-time error.",
        {
            "eligibility": grune_eligibility,
            "result": grune_observed,
            "hashes_match": grune_hashes_match,
            "publisher_access_recheck": {
                "status": (grune_access or {}).get("status"),
                "raw_trace_found": ((grune_access or {}).get("access_result") or {}).get("machine_readable_pressure_time_trace_found"),
                "full_raw_holdout_eligible": ((grune_access or {}).get("eligibility") or {}).get("full_raw_holdout_eligible"),
            },
            "claim_boundary": (grune_result or {}).get("claim_boundary"),
        } if grune_result else "missing; numeric holdout has not completed",
    ))

    ekoto_result_path = root / "research/ekoto_2012_holdout_result.json"
    ekoto_result = _json(ekoto_result_path)
    ekoto_protocol_path = root / "research/ekoto_2012_holdout_protocol.json"
    ekoto_protocol = _json(ekoto_protocol_path)
    ekoto_data_path = root / "data/public_validation/derived/ekoto_2012_figure3.csv"
    ekoto_observed = (ekoto_result or {}).get("result") or {}
    ekoto_protocol_hash = _sha256(ekoto_protocol_path) if ekoto_protocol_path.is_file() else None
    ekoto_data_hash = _sha256(ekoto_data_path) if ekoto_data_path.is_file() else None
    ekoto_pass = bool(
        (ekoto_protocol or {}).get("status")
        == "endpoints_and_code_frozen_before_numerical_curve_access"
        and ((ekoto_protocol or {}).get("known_before_freeze") or {}).get(
            "numerical_curve_coordinates_accessed"
        ) is False
        and ekoto_observed.get("joint_primary_screen_pass") is True
        and (ekoto_result or {}).get("protocol_sha256") == ekoto_protocol_hash
        and (ekoto_result or {}).get("data_sha256") == ekoto_data_hash
    )
    gates.append(_gate(
        "ekoto_transient_release_validation",
        "PASS" if ekoto_pass else ("FAIL" if ekoto_result else "PENDING"),
        "The locked adiabatic vessel-discharge model meets all frozen transient mass-flow screens on the independent Ekoto et al. scaled release.",
        f"{ekoto_result_path.relative_to(root)}; {ekoto_protocol_path.relative_to(root)}; {ekoto_data_path.relative_to(root)}",
        "At least 15 points; <=15% peak-normalized RMSE, <=20% median absolute percentage error and <=20% half-peak-time error; all screens required.",
        {
            "result": ekoto_observed,
            "protocol_hash_matches": (
                (ekoto_result or {}).get("protocol_sha256") == ekoto_protocol_hash
            ),
            "data_hash_matches": (
                (ekoto_result or {}).get("data_sha256") == ekoto_data_hash
            ),
            "claim_boundary": (ekoto_protocol or {}).get("claim_boundary"),
        } if ekoto_result else "missing; Ekoto holdout has not completed",
    ))

    protocol_path = root / "research/hiad_study_protocol_manifest.json"
    protocol = _json(protocol_path)
    protocol_ok, protocol_mismatches = _protocol_integrity(root, protocol)
    gates.append(_gate(
        "hiad_protocol_integrity", "PASS" if protocol_ok else "FAIL",
        "The incident decision-support study protocol was hash-locked before outcomes.",
        str(protocol_path.relative_to(root)),
        "Every required protocol/code hash matches the current file.",
        {"mismatches": protocol_mismatches},
    ))

    machine_preflight_path = root / "research/hiad_casebook_machine_preflight_2026_10_05.json"
    machine_preflight = _json(machine_preflight_path)
    machine_preflight_pass = bool(
        (machine_preflight or {}).get("kind") == "machine_preflight_only"
        and (machine_preflight or {}).get("machine_preflight_pass") is True
        and (machine_preflight or {}).get("case_count") == 24
        and all(
            check.get("status") == "PASS"
            for check in (machine_preflight or {}).get("checks", [])
        )
        and len((machine_preflight or {}).get("claim_boundary", [])) >= 3
    )
    gates.append(_gate(
        "hiad_casebook_machine_preflight_integrity",
        "PASS" if machine_preflight_pass else "PENDING",
        "The prepared HIAD casebook passes machine-only structural checks while all human gates remain unresolved.",
        str(machine_preflight_path.relative_to(root)),
        "24 cases, required context/provenance fields, unique IDs, and explicit pending human-review markers.",
        machine_preflight or "missing",
    ))

    ethics_pass = bool(
        protocol_ok and (protocol or {}).get("ethics_status") in {
            "approved", "exempt", "not-required"
        }
        and (protocol or {}).get("ethics_determination_id")
        and (protocol or {}).get("reviewer_recruitment_permitted") is True
    )
    gates.append(_gate(
        "institutional_ethics_determination",
        "PASS" if ethics_pass else "PENDING",
        "The applicable institution has recorded the human-participant determination.",
        str(protocol_path.relative_to(root)),
        "Approved, exempt or not-required status, identifier and completed institutional fields.",
        {
            "status": (protocol or {}).get("ethics_status"),
            "determination_id": (protocol or {}).get("ethics_determination_id"),
            "unresolved_fields": (protocol or {}).get("unresolved_institution_fields"),
        },
    ))

    freeze_path = root / "data/public_validation/results/hiad_casebook_frozen/casebook_freeze_manifest.json"
    casebook_freeze = _json(freeze_path)
    freeze_hashes = (casebook_freeze or {}).get("file_sha256") or {}
    required_freeze_hashes = {
        "source_casebook", "submitted_approved_casebook",
        "approved_casebook_submitted.json", "approved_casebook_frozen.json",
        "casebook_change_log.csv",
    }
    casebook_pass = bool(
        (casebook_freeze or {}).get("case_count") == 24
        and (casebook_freeze or {}).get("all_frozen_cases_retained") is True
        and (casebook_freeze or {}).get("all_cases_approved") is True
        and required_freeze_hashes.issubset(freeze_hashes)
    )
    gates.append(_gate(
        "hiad_casebook_frozen", "PASS" if casebook_pass else "PENDING",
        "All 24 holdout incident vignettes passed coordinator leakage review and were frozen.",
        str(freeze_path.relative_to(root)),
        "24 retained and approved cases with source/submitted/frozen hashes.",
        casebook_freeze or "missing",
    ))

    public_evidence_path = root / "research/hiad_hrs_public_evidence.json"
    public_evidence = _json(public_evidence_path)
    public_evidence_pass = bool(
        (public_evidence or {}).get("aggregate", {}).get("case_count") == 34
        and (public_evidence or {}).get("selection", {}).get("coordinator_approval") is False
        and (public_evidence or {}).get("source", {}).get("sha256")
    )
    gates.append(_gate(
        "hiad_public_evidence_inventory",
        "PASS" if public_evidence_pass else "PENDING",
        "The public HIAD 2.2 HRS incident subset is hash-linked and reproducibly summarized without leaking blinded responses.",
        str(public_evidence_path.relative_to(root)),
        "34 public HRS rows, source digest, explicit selection rule and non-casebook claim boundary.",
        public_evidence or "missing",
    ))

    collection_path = root / "data/public_validation/results/hiad_decision/collection_manifest.json"
    collection = _json(collection_path)
    collection_pass = bool(
        (collection or {}).get("response_count")
        == (collection or {}).get("expected_response_count") == 168
        and (collection or {}).get("failed_calls_retained_for_blinded_scoring") is True
        and (collection or {}).get("casebook_freeze_manifest_sha256")
        and (collection or {}).get("protocol_manifest_sha256")
        and (collection or {}).get("protocol_collection_permitted") is True
    )
    gates.append(_gate(
        "hiad_holdout_collection", "PASS" if collection_pass else "PENDING",
        "All masked alarm/direct/RAG holdout responses were collected under the frozen protocol.",
        str(collection_path.relative_to(root)),
        "24 × (1 alarm + 3 direct + 3 RAG) = 168 retained responses with freeze linkage.",
        collection or "missing",
    ))

    analysis_path = root / "data/public_validation/results/hiad_decision/analysis/expert_review_analysis.json"
    analysis = _json(analysis_path)
    variants = (analysis or {}).get("variant_summary") or {}
    review_complete = bool(
        (analysis or {}).get("event_count") == 24
        and (analysis or {}).get("rater_count") == 3
        and {"alarm-only", "saga-linked", "saga-standards-rag"}.issubset(variants)
        and ((analysis or {}).get("reviewer_qualification_summary") or {}).get("reviewer_count") == 3
    )
    gates.append(_gate(
        "independent_expert_review_complete",
        "PASS" if review_complete else "PENDING",
        "Three qualified independent reviewers completed the locked 24-event evaluation.",
        str(analysis_path.relative_to(root)),
        "24 events, 3 raters, all three variants, qualification summary and lock hashes.",
        analysis or "missing",
    ))

    direct = ((analysis or {}).get("paired_composite_differences_vs_alarm") or {}).get("saga-linked") or {}
    direct_summary = variants.get("saga-linked") or {}
    alarm_summary = variants.get("alarm-only") or {}
    ci = direct.get("bootstrap_95_ci") or []
    effect_supported = bool(
        review_complete and len(ci) == 2 and ci[0] > 0
        and direct_summary.get("critical_omission_rate", 1.0)
        <= alarm_summary.get("critical_omission_rate", 0.0)
        and direct_summary.get("unsafe_advice_rate", 1.0)
        <= alarm_summary.get("unsafe_advice_rate", 0.0)
    )
    gates.append(_gate(
        "saga_effectiveness_and_safety_supported",
        "PASS" if effect_supported else "PENDING",
        "Direct SAGA improves expert-rated guidance without higher observed omission or unsafe-advice rates.",
        str(analysis_path.relative_to(root)),
        "Paired bootstrap CI lower bound >0 and omission/unsafe rates no higher than alarm-only.",
        {"direct_vs_alarm": direct, "alarm": alarm_summary, "direct": direct_summary},
    ))

    grounding_path = root / "research/llm_evidence_grounding_validation.json"
    grounding = _json(grounding_path)
    grounding_tank_diagnostic = (
        (grounding or {}).get("methytrucks_tank_diagnostic_boundary") or {}
    )
    grounding_release_validation = (
        (grounding or {}).get("cross_campaign_release_validation_boundary") or {}
    )
    grounding_pass = bool(
        (grounding or {}).get("status") == "software_contract_verified"
        and ((grounding or {}).get("tests") or {}).get("full_suite", {}).get("failed") == 0
        and any(
            "flow-boundary mismatches" in str(item)
            for item in (grounding or {}).get("verified_properties", [])
        )
        and any(
            "five-session MetHyTrucks HySaM" in str(item)
            for item in (grounding or {}).get("verified_properties", [])
        )
        and grounding_tank_diagnostic.get("case_count") == 5
        and grounding_tank_diagnostic.get("channel_dictionary_present") is False
        and grounding_tank_diagnostic.get("workbook_to_sink_crosswalk_present") is False
        and grounding_tank_diagnostic.get("prospective_holdout_eligible") is False
        and grounding_tank_diagnostic.get("full_loop_validation_eligible") is False
        and grounding_tank_diagnostic.get("claim_supported") is False
        and any(
            "cross-campaign release validation" in str(item)
            for item in (grounding or {}).get("verified_properties", [])
        )
        and grounding_release_validation.get("eligible_campaign_count") == 3
        and grounding_release_validation.get("supported_campaign_count") == 1
        and grounding_release_validation.get("failed_campaign_count") == 2
        and grounding_release_validation.get("ineligible_campaign_count") == 1
        and grounding_release_validation.get(
            "universal_release_validation_supported"
        ) is False
        and grounding_release_validation.get(
            "apparatus_resolved_holdout_received"
        ) is False
        and grounding_release_validation.get(
            "runtime_model_changed_after_outcomes"
        ) is False
    )
    gates.append(_gate(
        "llm_evidence_grounding_contract",
        "PASS" if grounding_pass else "PENDING",
        "Main and selected-sensor assistants receive traceable evidence with explicit calculation and uncertainty status.",
        str(grounding_path.relative_to(root)),
        "Manifest schema, normal/emergency distinction, contradiction guard, bounded tank evidence, mixed release-campaign outcomes and full regression suite.",
        grounding or "missing",
    ))

    hitrf_path = root / "research/nlr_hitrf_public_operational_reference_2026_10_06.json"
    hitrf = _json(hitrf_path)
    hitrf_source = (hitrf or {}).get("source") or {}
    hitrf_storage = (hitrf or {}).get("storage") or {}
    hitrf_stages = ((hitrf or {}).get("compression") or {}).get("stages") or []
    hitrf_thermal = (hitrf or {}).get("dispensing_and_thermal") or {}
    hitrf_reference_pass = bool(
        (hitrf or {}).get("artifact_type") == "public_facility_operational_reference"
        and (hitrf or {}).get("status") == "public_facility_operational_reference"
        and hitrf_source.get("url")
        and hitrf_source.get("raw_synchronized_logger_public") is False
        and all(key in hitrf_storage for key in ("low_pressure", "medium_pressure", "high_pressure"))
        and len(hitrf_stages) >= 3
        and hitrf_thermal.get("chiller_target_temperature_c") is not None
        and "claim_boundary" in ((hitrf or {}).get("runtime_use") or {})
    )
    gates.append(_gate(
        "public_hitrf_operational_reference_integrity",
        "PASS" if hitrf_reference_pass else ("PENDING" if hitrf else "FAIL"),
        "The public HITRF facility envelope is available to LLM grounding without being presented as raw full-loop validation.",
        str(hitrf_path.relative_to(root)),
        "Storage tiers, compression stages, thermal boundary and an explicit no-raw-logger claim boundary.",
        {
            "source_url": hitrf_source.get("url"),
            "raw_synchronized_logger_public": hitrf_source.get("raw_synchronized_logger_public"),
            "storage_tiers": sorted(hitrf_storage),
            "compression_stage_count": len(hitrf_stages),
            "chiller_target_temperature_c": hitrf_thermal.get("chiller_target_temperature_c"),
            "claim_boundary": ((hitrf or {}).get("runtime_use") or {}).get("claim_boundary"),
        } if hitrf else "missing",
    ))

    sensitivity_path = root / "research/hiad_design_sensitivity.json"
    sensitivity = _json(sensitivity_path)
    sensitivity_pass = bool(
        (sensitivity or {}).get("event_count") == 24
        and (sensitivity or {}).get("analysis_timing")
        == "before holdout response collection and expert rating"
        and (sensitivity or {}).get("simulations_per_effect", 0) >= 20_000
    )
    gates.append(_gate(
        "preoutcome_design_sensitivity", "PASS" if sensitivity_pass else "FAIL",
        "The fixed incident-study sample limitations were quantified before outcomes.",
        str(sensitivity_path.relative_to(root)),
        "24 events, >=20,000 simulations/effect and explicit pre-outcome timing.",
        sensitivity or "missing",
    ))

    format_path = root / "manuscript/ijhe_format_check.json"
    format_check = _json(format_path)
    format_pass = bool((format_check or {}).get("format_gate_passed"))
    gates.append(_gate(
        "ijhe_format_gate", "PASS" if format_pass else "FAIL",
        "The manuscript satisfies the explicit IJHE length/front-matter limits checked locally.",
        str(format_path.relative_to(root)),
        "All format checks true; this is not a scientific-readiness decision.",
        format_check or "missing",
    ))

    compile_path = root / "manuscript/ijhe_compile_status.json"
    compile_status = _json(compile_path)
    compile_pass = bool((compile_status or {}).get("success") is True)
    gates.append(_gate(
        "ijhe_latex_compilation", "PASS" if compile_pass else "PENDING",
        "The exact submitted LaTeX source compiles successfully.",
        str(compile_path.relative_to(root)),
        "Compiler success with source hash and no unresolved errors.",
        compile_status or "missing; built-in compiler previously unavailable on Windows",
    ))

    metadata_path = root / "manuscript/submission_metadata.json"
    metadata = _json(metadata_path)
    metadata_pass = bool(
        (metadata or {}).get("all_authors_confirmed") is True
        and (metadata or {}).get("institutional_emails_confirmed") is True
        and (metadata or {}).get("credit_roles_confirmed") is True
        and (metadata or {}).get("competing_interests_confirmed") is True
        and (metadata or {}).get("funding_confirmed") is True
        and (metadata or {}).get("ai_disclosure_confirmed") is True
    )
    gates.append(_gate(
        "submission_metadata_and_declarations",
        "PASS" if metadata_pass else "PENDING",
        "Every author, affiliation, institutional email and declaration is confirmed.",
        str(metadata_path.relative_to(root)),
        "All author/CRediT/conflict/funding/AI-disclosure confirmations true.",
        metadata or "missing",
    ))

    citation_path = root / "CITATION.cff"
    citation = citation_path.read_text(encoding="utf-8") if citation_path.is_file() else ""
    doi_pass = "10.5281/zenodo.23084421" in citation
    gates.append(_gate(
        "software_doi", "PASS" if doi_pass else "PENDING",
        "The reproducible software release has a persistent DOI.",
        str(citation_path.relative_to(root)),
        "Repository citation metadata contains the released Zenodo DOI.",
        "10.5281/zenodo.23084421" if doi_pass else "missing",
    ))

    by_id = {item["id"]: item for item in gates}
    bounded_required = (
        "tank_external_validation", "active_fill_correction_disclosed",
        "corrected_closed_loop_internal_evidence",
        "full_loop_negative_result_disclosed",
        "hyram_adapter_verification", "preslhy_blowdown_external_validation",
        "preslhy_partb_ambient_external_validation",
        "preslhy_revised_holdout_validation",
        "proust_independent_release_validation",
        "schefer_transient_release_validation",
        "schefer_2007_pressure_decay_validation",
        "grune_2014_pressure_decay_validation",
        "ekoto_transient_release_validation",
        "hiad_protocol_integrity",
        "external_hrs_intake_integrity_contract",
        "external_hrs_trace_quality_contract",
        "institutional_ethics_determination", "hiad_casebook_frozen",
        "hiad_holdout_collection", "independent_expert_review_complete",
        "preoutcome_design_sensitivity", "ijhe_format_gate",
        "ijhe_latex_compilation", "submission_metadata_and_declarations",
        "software_doi",
    )
    full_required = bounded_required + (
        "full_loop_external_validation", "station_consequence_geometry_validation",
        "saga_effectiveness_and_safety_supported",
    )
    bounded_ready = all(by_id[item]["status"] == "PASS" for item in bounded_required)
    full_ready = all(by_id[item]["status"] == "PASS" for item in full_required)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_journal": {
            "title": "International Journal of Hydrogen Energy",
            "issn": "0360-3199",
            "publisher_scope_url": (
                "https://shop.elsevier.com/journals/international-journal-of-hydrogen-energy/0360-3199"
            ),
            "guide_for_authors_url": (
                "https://www.elsevier.com/journals/international-journal-of-hydrogen-energy/0360-3199/guide-for-authors"
            ),
            "data_statement_guidance_url": (
                "https://www.elsevier.com/researcher/author/tools-and-resources/research-data/data-statement"
            ),
            "readiness_interpretation": (
                "A local gate is an evidence-readiness decision, not an acceptance or peer-review prediction."
            ),
        },
        "bounded_ijhe_submission_ready": bounded_ready,
        "full_user_objective_ready": full_ready,
        "goal_completion_permitted": full_ready,
        "gate_counts": {
            status: sum(item["status"] == status for item in gates)
            for status in ("PASS", "FAIL", "PENDING")
        },
        "blocking_bounded_submission_gates": [
            item for item in bounded_required if by_id[item]["status"] != "PASS"
        ],
        "blocking_full_objective_gates": [
            item for item in full_required if by_id[item]["status"] != "PASS"
        ],
        "gates": gates,
        "decision_rule": (
            "Only full_user_objective_ready=true permits goal completion. "
            "A bounded paper may report negative or limited physics honestly, but it "
            "does not satisfy the full validated-digital-twin objective."
        ),
    }


def _markdown(report: dict[str, object]) -> str:
    lines = [
        "# IJHE evidence-readiness audit", "",
        "Target journal: **International Journal of Hydrogen Energy** (ISSN 0360-3199). "
        "See the [publisher scope](https://shop.elsevier.com/journals/international-journal-of-hydrogen-energy/0360-3199), "
        "[Guide for Authors](https://www.elsevier.com/journals/international-journal-of-hydrogen-energy/0360-3199/guide-for-authors) "
        "and [Elsevier data-statement guidance](https://www.elsevier.com/researcher/author/tools-and-resources/research-data/data-statement).",
        "The local result is an evidence-readiness gate, not a guarantee of editorial acceptance.", "",
        f"- Bounded IJHE submission ready: **{report['bounded_ijhe_submission_ready']}**",
        f"- Full user objective ready: **{report['full_user_objective_ready']}**",
        f"- Goal completion permitted: **{report['goal_completion_permitted']}**", "",
        "| Gate | Status | Claim | Evidence |",
        "|---|---|---|---|",
    ]
    for gate in report["gates"]:
        lines.append(
            f"| `{gate['id']}` | **{gate['status']}** | {gate['claim']} | "
            f"`{gate['evidence']}` |"
        )
    lines.extend([
        "", "## Blocking bounded-submission gates", "",
        *[f"- `{item}`" for item in report["blocking_bounded_submission_gates"]],
        "", "## Blocking full-objective gates", "",
        *[f"- `{item}`" for item in report["blocking_full_objective_gates"]],
        "", report["decision_rule"],
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--json-output", type=Path,
        default=Path("manuscript/ijhe_readiness_audit.json"),
    )
    parser.add_argument(
        "--report-output", type=Path,
        default=Path("manuscript/IJHE_READINESS_AUDIT.md"),
    )
    parser.add_argument(
        "--require-ready", choices=("none", "bounded", "full"), default="none",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    report = audit(root)
    json_output = args.json_output if args.json_output.is_absolute() else root / args.json_output
    report_output = args.report_output if args.report_output.is_absolute() else root / args.report_output
    json_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    report_output.write_text(_markdown(report), encoding="utf-8", newline="\n")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.require_ready == "bounded" and not report["bounded_ijhe_submission_ready"]:
        return 2
    if args.require_ready == "full" and not report["full_user_objective_ready"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
