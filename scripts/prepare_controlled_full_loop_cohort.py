"""Prepare a pre-outcome cohort protocol from controlled export receipts.

Only receipt metadata is read.  Numerical evaluation results are neither read
nor accepted by this command, so the complete case set and aggregate decision
rule can be frozen before any case outcome is inspected.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SCOPES = frozenset({
    "station_to_vehicle_selected_bank_only",
    "cascade_resolved_station_to_vehicle",
})


def _outside_repository(path: Path, *, field: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{field} must be outside the repository worktree")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def prepare(receipt_paths: Iterable[Path]) -> dict[str, Any]:
    receipts = [
        _read_json(_outside_repository(path, field="controlled receipt"))
        for path in receipt_paths
    ]
    if not receipts:
        raise ValueError("at least one controlled receipt is required")
    scopes = {receipt.get("evaluation_scope") for receipt in receipts}
    if len(scopes) != 1 or next(iter(scopes)) not in SCOPES:
        raise ValueError("all receipts must use the same supported evaluation_scope")
    scope = next(iter(scopes))
    trace_hashes: list[str] = []
    for index, receipt in enumerate(receipts, start=1):
        digest = receipt.get("trace_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"receipt {index} has no usable trace_sha256")
        if not receipt.get("station_to_vehicle_trace_ready"):
            raise ValueError(f"receipt {index} is not station-to-vehicle ready")
        if scope == "cascade_resolved_station_to_vehicle":
            if not receipt.get("full_loop_trace_ready") or not receipt.get("cascade_dispatch_evaluable"):
                raise ValueError(f"receipt {index} is not cascade-resolved full-loop ready")
        elif receipt.get("cascade_dispatch_evaluable"):
            raise ValueError(f"receipt {index} has a cascade scope mismatch")
        trace_hashes.append(digest.lower())
    if len(set(trace_hashes)) != len(trace_hashes):
        raise ValueError("the cohort contains a duplicate controlled trace")

    criteria: dict[str, Any] = {
        "pressure_rmse_mpa_max": None,
        "temperature_rmse_c_max": None,
        "mass_flow_rmse_g_s_max": None,
        "selected_source_pressure_rmse_mpa_max": None,
        "delivered_temperature_rmse_c_max": None,
    }
    if scope == "cascade_resolved_station_to_vehicle":
        criteria.update({
            "cascade_bank_pressure_rmse_mpa_max": None,
            "dispatch_accuracy_min": None,
            "compressor_state_accuracy_min": None,
        })

    return {
        "schema_version": 1,
        "artifact_type": "controlled_hrs_frozen_cohort_protocol",
        "protocol_status": "DRAFT_COMPLETE_AND_FREEZE_BEFORE_CASE_OUTCOMES",
        "frozen_before_case_outcomes": False,
        "model_commit": _git_commit(),
        "evaluation_scope": scope,
        "expected_trace_sha256": sorted(trace_hashes),
        "cohort_acceptance": {
            "minimum_case_count": 8,
            "minimum_case_pass_fraction": 0.8,
        },
        "evidence_design": {
            "independent_holdout": None,
            "model_developers_blinded_to_case_outcomes_before_freeze": None,
            "rights_cleared_for_controlled_evaluation": None,
        },
        "individual_acceptance_criteria": criteria,
        "freeze_requirements": [
            "Retain every expected trace in the final registry, including failed evaluations.",
            "Set every individual and cohort threshold before reading case outcomes.",
            "Set frozen_before_case_outcomes true only after the controlled freeze is recorded.",
            "Do not add, remove, replace, or duplicate a trace after freeze.",
        ],
        "claim_boundary": (
            "A frozen cohort protocol prevents selective case reporting. It does not "
            "by itself validate the model, certify safety, or authorize raw-data disclosure."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipts", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = _outside_repository(args.output, field="controlled cohort protocol")
    if output.exists():
        raise FileExistsError("controlled cohort protocol output must not already exist")
    protocol = prepare(args.receipts)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "case_count": len(protocol["expected_trace_sha256"]),
        "ready_to_freeze": len(protocol["expected_trace_sha256"]) >= 8,
        "evaluation_scope": protocol["evaluation_scope"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
