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

    external_loop_path = root / "data/public_validation/results/closed_loop_external_holdout/validation.json"
    external_loop = _json(external_loop_path)
    external_protocol_path = root / "research/mc_default_external_holdout_protocol.json"
    external_protocol = _json(external_protocol_path)
    external_search_path = root / "research/external_full_loop_data_search.json"
    external_search = _json(external_search_path)
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
        f"{external_loop_path.relative_to(root)}; {external_search_path.relative_to(root)}",
        "Hash-locked protocol and model, clean-source external holdout with >=8 cases and >=80% screen pass fraction.",
        {
            "protocol_integrity": protocol_integrity,
            "aggregate": aggregate,
            "new_external_data_search": {
                "status": (external_search or {}).get("status"),
                "next_action": (external_search or {}).get("next_action"),
                "claim_limit": (external_search or {}).get("claim_limit"),
            },
        } if external_loop else "missing; current internal comparisons pass 0/8 and 0/11",
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
