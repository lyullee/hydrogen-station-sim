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

    external_loop_path = root / "data/public_validation/results/closed_loop_external_holdout/validation.json"
    external_loop = _json(external_loop_path)
    external_protocol_path = root / "research/mc_default_external_holdout_protocol.json"
    external_protocol = _json(external_protocol_path)
    external_search_path = root / "research/external_full_loop_data_search.json"
    external_search = _json(external_search_path)
    external_search_recheck_path = root / "research/public_full_loop_search_recheck_2026_10_04.json"
    external_search_recheck = _json(external_search_recheck_path)
    external_operational_recheck_path = root / "research/public_operational_benchmark_recheck_2026_10_05.json"
    external_operational_recheck = _json(external_operational_recheck_path)
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
    external_loop_pass = (
        protocol_integrity
        and (external_loop or {}).get("protocol_frozen_before_data_access") is True
        and aggregate.get("case_count", 0)
        >= protocol_screens.get("minimum_evaluable_cases", 8)
        and aggregate.get("screening_pass_fraction", 0.0)
        >= protocol_screens.get("minimum_joint_screen_pass_fraction", 0.80)
        and (external_loop or {}).get("source_worktree_dirty") is False
    )
    gates.append(_gate(
        "full_loop_external_validation",
        "PASS" if external_loop_pass else "FAIL",
        "The complete station controller/cascade/precooler loop meets frozen engineering screens on new external cases.",
        f"{external_loop_path.relative_to(root)}; {external_search_path.relative_to(root)}; "
        f"{external_search_recheck_path.relative_to(root)}; {external_operational_recheck_path.relative_to(root)}",
        "Hash-locked protocol and model, clean-source external holdout with >=8 cases and >=80% screen pass fraction.",
        {
            "protocol_integrity": protocol_integrity,
            "aggregate": aggregate,
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
            "operational_benchmark_recheck_2026_10_05": {
                "result": (external_operational_recheck or {}).get("result"),
                "gate_impact": (external_operational_recheck or {}).get("gate_impact"),
                "candidate_count": len((external_operational_recheck or {}).get("candidates") or []),
            },
        } if external_loop else "missing; current internal comparisons pass 0/8 and 0/11",
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
        f"{grune_result_path.relative_to(root)}; {grune_protocol_path.relative_to(root)}; {grune_data_path.relative_to(root)}; research/grune_2014_archive_access_recheck_2026_10_05.json",
        "At least 15 points plus an observable half-pressure crossing; <=10% NRMSE, <=15% median error and <=20% half-time error.",
        {
            "eligibility": grune_eligibility,
            "result": grune_observed,
            "hashes_match": grune_hashes_match,
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
    casebook_pass = bool(
        (casebook_freeze or {}).get("case_count") == 24
        and (casebook_freeze or {}).get("all_frozen_cases_retained") is True
        and (casebook_freeze or {}).get("all_cases_approved") is True
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
    grounding_pass = bool(
        (grounding or {}).get("status") == "software_contract_verified"
        and ((grounding or {}).get("tests") or {}).get("full_suite", {}).get("failed") == 0
        and any(
            "flow-boundary mismatches" in str(item)
            for item in (grounding or {}).get("verified_properties", [])
        )
    )
    gates.append(_gate(
        "llm_evidence_grounding_contract",
        "PASS" if grounding_pass else "PENDING",
        "Main and selected-sensor assistants receive traceable evidence with explicit calculation and uncertainty status.",
        str(grounding_path.relative_to(root)),
        "Manifest schema, normal/emergency distinction, contradiction guard and full regression suite.",
        grounding or "missing",
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
