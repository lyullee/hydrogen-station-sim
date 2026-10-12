"""Write a reproducible progress snapshot from the IJHE readiness audit.

The percentage in this report is a gate-closure metric (PASS gates divided by
all gates).  It is intentionally kept separate from scientific readiness: a
negative or pending validation result must not be converted into a PASS just
to make the percentage look better.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_snapshot(
    audit: dict[str, Any],
    prior_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    counts = audit.get("gate_counts") or {}
    passed = int(counts.get("PASS", 0))
    failed = int(counts.get("FAIL", 0))
    pending = int(counts.get("PENDING", 0))
    total = passed + failed + pending
    closure = (passed / total * 100.0) if total else 0.0
    excluded_from_primary_scope = {
        "full_loop_external_validation",
        "institutional_ethics_determination",
        "hiad_casebook_frozen",
        "hiad_holdout_collection",
        "independent_expert_review_complete",
        "saga_effectiveness_and_safety_supported",
        # This is a public-catalogue access-boundary record, not a numerical
        # validation result.  Keep it in the overall ledger for provenance,
        # but do not let a metadata/access check inflate the science-scope
        # closure metric.
        "public_nbsdc_lh2_station_intake_integrity",
    }
    gate_rows = audit.get("gates") or []
    scoped_rows = [
        row for row in gate_rows
        if row.get("id") not in excluded_from_primary_scope
    ]
    if scoped_rows:
        scoped_counts = {
            status: sum(row.get("status") == status for row in scoped_rows)
            for status in ("PASS", "FAIL", "PENDING")
        }
    else:
        scoped_counts = {"PASS": passed, "FAIL": failed, "PENDING": pending}
    scoped_total = sum(scoped_counts.values())
    scoped_closure = (scoped_counts["PASS"] / scoped_total * 100.0) if scoped_total else 0.0
    snapshot = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metric_definition": "PASS gates divided by PASS+FAIL+PENDING gates; not a publication-readiness probability",
        "gate_counts": {"PASS": passed, "FAIL": failed, "PENDING": pending, "TOTAL": total},
        "gate_closure_percent": round(closure, 1),
        "primary_scope_progress_2026_10_11": {
            "metric_definition": "Scope-adjusted gate closure after removing the declared station-to-vehicle full-loop, optional SAGA human-evaluation lanes and non-validation public access-boundary checks; this is not a scientific improvement claim.",
            "gate_counts": {**scoped_counts, "TOTAL": scoped_total},
            "gate_closure_percent": round(scoped_closure, 1),
            "excluded_gate_ids": sorted(excluded_from_primary_scope),
        },
        "bounded_ijhe_submission_ready": bool(audit.get("bounded_ijhe_submission_ready")),
        "full_user_objective_ready": bool(audit.get("full_user_objective_ready")),
        "goal_completion_permitted": bool(audit.get("goal_completion_permitted")),
        "blocking_bounded_submission_gates": list(audit.get("blocking_bounded_submission_gates") or []),
        "blocking_full_objective_gates": list(audit.get("blocking_full_objective_gates") or []),
        "interpretation": {
            "current_state": "implementation_and_evidence_gates_partially_closed",
            "do_not_claim": [
                "validated_full_station_to_vehicle_digital_twin",
                "publication_acceptance_or_probability",
            ],
            "next_high_impact_actions": [
                (
                    "obtain a stable KIT LH2 custodian/session transfer or retry after the RADAR rate limit cools, "
                    "then verify the publisher MD5 before metadata-only inventory"
                ),
                "obtain an independent time-resolved measured pressure trace for the pending Grune holdout",
                (
                    "keep the blinded expert and prospective SAGA safety-effectiveness study optional; "
                    "start it only if the manuscript claims improved human safety decisions"
                ),
            ],
            "scope_amendment_2026_10_11": {
                "in_scope": [
                    "station-side HRS process and safety digital-twin behavior",
                    "public Type-IV tank thermodynamics with a frozen independent holdout",
                    "release, dispersion, consequence and risk-model component validation",
                    "SAGA direct-answer response generation with explicit evidence boundaries",
                ],
                "excluded_from_primary_goal": [
                    "synchronized station-to-vehicle raw logger validation",
                    "vehicle-side controller/ESD channel validation",
                ],
                "paper_limitation": (
                    "No openly reusable synchronized station-to-vehicle trace was identified; "
                    "the paper will state this as a boundary and will not claim full-loop field validation."
                ),
                "legacy_full_scope_metric": (
                    "full_user_objective_ready and its open full-loop gate remain in the audit only for "
                    "traceability; they are not a required claim in the amended primary scope."
                ),
            },
            "priority_status_2026_10_11": {
                "independent_component_holdout": "retained_public_type_iv_split_ready",
                "station_to_vehicle_raw_data": "removed_from_primary_goal_after_public_search",
                "ethics_and_expert_review": (
                    "optional_for_physics_validation; required only for a claim that SAGA improves "
                    "human safety guidance"
                ),
            },
        },
    }
    # The audit is the authoritative source for gate state, while the
    # snapshot also carries manually curated provenance details (full
    # regression records, post-access diagnostic boundaries and hashes).  Keep
    # that evidence block across regeneration so refreshing the audit cannot
    # silently delete the paper's reproducibility trail.
    prior_evidence = (
        ((prior_snapshot or {}).get("interpretation") or {})
        .get("latest_access_evidence")
    )
    if isinstance(prior_evidence, dict) and prior_evidence:
        snapshot["interpretation"]["latest_access_evidence"] = prior_evidence
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit_json.read_text(encoding="utf-8"))
    prior_snapshot: dict[str, Any] | None = None
    if args.output.is_file():
        try:
            candidate = json.loads(args.output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            candidate = None
        if isinstance(candidate, dict):
            prior_snapshot = candidate
    snapshot = build_snapshot(audit, prior_snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Use an explicit LF newline so regeneration does not create a repository-wide
    # CRLF diff on Windows; only evidence or gate changes should appear in review.
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
