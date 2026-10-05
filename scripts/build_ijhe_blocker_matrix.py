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
    operational_search_path = root / "research/public_operational_benchmark_recheck_2026_10_05.json"
    audit = load_json(audit_path)
    hiad = load_json(hiad_path)
    tracker = load_json(tracker_path)
    search = load_json(search_path)
    operational_search = load_json(operational_search_path)

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
            "llm_grounding": {
                "gate": gate("llm_evidence_grounding_contract")["status"],
                "evidence": "research/llm_evidence_grounding_validation.json",
                "claim_boundary": "Software evidence/contradiction contract only; no operator-effectiveness or safety claim.",
            },
            "public_incident_traceability": {
                "gate": gate("khk_public_accident_report_access_verification")["status"],
                "evidence": [
                    "research/khk_hydrogen_station_public_reports_inventory_2026_10_04.json",
                    "research/hiad_accident_response_coverage_evaluation_2026_10_05.json",
                ],
                "claim_boundary": "Qualitative scenario and response grounding; HIAD action-category routing is structural only, with no frequency, calibrated probability, response-effectiveness or safety claim.",
            },
            "confined_space_consequence_measurements": {
                "gate": gate("grune_ventilation_measurement_inventory")["status"],
                "evidence": "research/grune_ventilation_dataset_inventory_2026_10_05.json",
                "claim_boundary": "Hash-verified CC BY 4.0 concentration/ventilation measurements only; no model comparison, outdoor separation-distance claim or full-loop validation claim.",
            },
            "real_station_candidate": {
                "status": "ACCESS_REQUEST_ONLY",
                "evidence": [
                    "research/nbsdc_hrss_operational_access_verification_2026_10_04.json",
                    "research/nbsdc_winter_olympics_access_recheck_2026_10_05.json",
                ],
                "claim_boundary": "NBSDC HRS descriptions and file inventories are verified; raw workbooks remain application-controlled and cannot be used as validation evidence yet.",
            },
        },
        "blocking_matrix": [
            {
                "id": "full_loop_external_validation",
                "status": gate("full_loop_external_validation")["status"],
                "why_blocked": "The frozen external station-loop holdout has 0/8 engineering-screen passes, and the public search found no new eligible synchronized station/controller/vehicle raw set.",
                "evidence": [
                    "data/public_validation/results/closed_loop_external_holdout/validation.json",
                    "research/mc_default_source_boundary_identifiability_2026_10_04.json",
                    "research/public_full_loop_search_recheck_2026_10_04.json",
                    "research/public_operational_benchmark_recheck_2026_10_05.json",
                    "research/nbsdc_hrss_operational_access_verification_2026_10_04.json",
                    "research/nbsdc_winter_olympics_access_recheck_2026_10_05.json",
                ],
                "unblock_criterion": "Obtain a clean, rights-cleared, pre-access frozen external dataset with synchronized station pressure/temperature/mass-flow, protocol/controller, dispenser/nozzle, and vehicle/receptacle channels; resolve the source-boundary/topology ambiguity; then score >=8 cases with >=80% screen pass fraction.",
                "next_action": "Submit the prepared NBSDC Pucheng request and other custodian requests through an approved institutional channel; require source pressure/temperature, bank topology and valve-state metadata; do not treat request approval or metadata as validation.",
            },
            {
                "id": "consequence_model_external_validation",
                "status": "FAIL_OR_PENDING",
                "why_blocked": "Several release/blowdown datasets are useful component tests, but the retained joint screens do not meet the predeclared threshold or lack an observable decay feature.",
                "evidence": [
                    "manuscript/ijhe_readiness_audit.json",
                    "research/preslhy_blowdown_validation.json",
                    "research/proust_independent_release_validation.json",
                    "research/schefer_transient_release_validation.json",
                    "research/grune_2014_pressure_decay_validation.json",
                ],
                "unblock_criterion": "Either improve the declared model against a pre-access untouched component holdout without post-outcome tuning, or narrow the manuscript claim to the observed component-test scope.",
                "next_action": "Keep all failures and confidence intervals in the manuscript; do not convert a partial component screen into a station consequence claim.",
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
            "operational_benchmark_recheck_sha256": sha256(operational_search_path),
            "candidate_route_count": len(tracker.get("candidates") or []),
            "public_full_loop_search_candidate_count": candidate_count(search),
            "public_operational_benchmark_candidate_count": candidate_count(operational_search),
        },
        "claim_policy": [
            "Never present a request, metadata page, or public station inventory as raw validation evidence.",
            "Keep component-test failures and model limitations visible in the paper and supplement.",
            "Do not mark the user goal complete until full_loop_external_validation and saga_effectiveness_and_safety_supported are supported and all pending human/submission gates are closed.",
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
    parser.add_argument("--json-output", type=Path, default=Path("research/ijhe_submission_blocker_matrix_2026_10_04.json"))
    parser.add_argument("--report-output", type=Path, default=Path("research/IJHE_SUBMISSION_BLOCKER_MATRIX_2026_10_04.md"))
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
