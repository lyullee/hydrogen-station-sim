"""Create an external draft protocol for a controlled HRS full-loop evaluation.

The command reads the receipt, never the de-identified trace itself.  It copies
only the trace digest and the evidence scope into an external draft template.
The authorised custodian must complete operating-boundary and acceptance fields,
freeze it before looking at numerical outcomes, and then set
``frozen_before_outcomes`` to true.  The evaluator rejects this draft as-is.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
_SCOPES = frozenset({
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


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("receipt must be a JSON object")
    return payload


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def draft_protocol(receipt_path: Path) -> dict[str, Any]:
    """Build a non-executable draft from a controlled-export receipt only."""

    receipt_path = _outside_repository(receipt_path, field="controlled receipt")
    receipt = _json(receipt_path)
    trace_sha256 = receipt.get("trace_sha256")
    scope = receipt.get("evaluation_scope")
    if not isinstance(trace_sha256, str) or len(trace_sha256) != 64:
        raise ValueError("receipt has no usable trace_sha256")
    if scope not in _SCOPES:
        raise ValueError("receipt evaluation_scope is unsupported")
    if not receipt.get("station_to_vehicle_trace_ready"):
        raise ValueError("receipt has not passed the station-to-vehicle trace screen")
    if scope == "cascade_resolved_station_to_vehicle" and not receipt.get("full_loop_trace_ready"):
        raise ValueError("cascade-resolved receipt is not full-loop ready")
    if scope == "station_to_vehicle_selected_bank_only" and receipt.get("cascade_dispatch_evaluable"):
        raise ValueError("cascade-resolved receipt must use cascade-resolved scope")

    full = scope == "cascade_resolved_station_to_vehicle"
    criteria: dict[str, Any] = {
        "pressure_rmse_mpa_max": None,
        "temperature_rmse_c_max": None,
        "mass_flow_rmse_g_s_max": None,
        "selected_source_pressure_rmse_mpa_max": None,
        "delivered_temperature_rmse_c_max": None,
    }
    if full:
        criteria.update({
            "cascade_bank_pressure_rmse_mpa_max": None,
            "dispatch_accuracy_min": None,
            "compressor_state_accuracy_min": None,
        })

    return {
        "schema_version": 1,
        "artifact_type": "controlled_hrs_frozen_evaluation_protocol",
        "protocol_status": "DRAFT_COMPLETE_AND_FREEZE_BEFORE_OUTCOMES",
        "frozen_before_outcomes": False,
        "model_commit": _git_commit(),
        "expected_trace_sha256": trace_sha256,
        "evaluation_scope": scope,
        "freeze_requirements": [
            "Complete every null field using authorised, pre-outcome operating records.",
            "Do not inspect outcome metrics or alter the trace after this protocol is frozen.",
            "Record the decision outside this JSON, then set frozen_before_outcomes to true.",
            "Run the evaluator from the same clean source commit recorded in model_commit.",
        ],
        "ambient_temperature_c": None,
        "vehicle": {
            "initial_state_policy": "trace_first_sample",
            "internal_volume_m3": None,
            "nominal_working_pressure_mpa": None,
        },
        "control": {
            "target_pressure_mpa": None,
            "pressure_ramp_rate_mpa_min": None,
            "delivery_temperature_c": None,
            "maximum_gas_temperature_c": None,
            "maximum_mass_flow_g_s": None,
            "control_period_s": None,
        },
        "station": {
            "pressure_observable": "not_evaluated",
            "initial_bank_pressure_mpa": {
                "low": None,
                "medium": None,
                "high": None,
            },
        },
        "process": {
            "recharge_enabled": None,
            "recharge_auto_stop": None,
            "trailer_pressure_mpa": None,
            "trailer_temperature_c": None,
            "trailer_capacity_kg": None,
        },
        "state_semantics": {
            "cascade_selected_bank": {
                "low": ["REPLACE_WITH_ATTESTED_LOW_STATE"],
                "medium": ["REPLACE_WITH_ATTESTED_MEDIUM_STATE"],
                "high": ["REPLACE_WITH_ATTESTED_HIGH_STATE"],
            },
            "compressor_active_values": ["REPLACE_WITH_ATTESTED_ACTIVE_STATE"],
        },
        "acceptance_criteria": criteria,
        "claim_boundary": (
            "This protocol supports a bounded, controlled model comparison. It does not "
            "permit safety certification, disclosure of raw data, or claims about "
            "unmeasured phenomena."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = _outside_repository(args.output, field="controlled protocol draft")
    if output.exists():
        raise FileExistsError("controlled protocol draft must not already exist")
    output.parent.mkdir(parents=True, exist_ok=True)
    protocol = draft_protocol(args.receipt)
    output.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "evaluation_scope": protocol["evaluation_scope"],
        "executable": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
