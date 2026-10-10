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


def build_snapshot(audit: dict[str, Any]) -> dict[str, Any]:
    counts = audit.get("gate_counts") or {}
    passed = int(counts.get("PASS", 0))
    failed = int(counts.get("FAIL", 0))
    pending = int(counts.get("PENDING", 0))
    total = passed + failed + pending
    closure = (passed / total * 100.0) if total else 0.0
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metric_definition": "PASS gates divided by PASS+FAIL+PENDING gates; not a publication-readiness probability",
        "gate_counts": {"PASS": passed, "FAIL": failed, "PENDING": pending, "TOTAL": total},
        "gate_closure_percent": round(closure, 1),
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
                "obtain an independent time-resolved measured pressure trace for the pending Grune holdout",
                "obtain a synchronized station-to-vehicle trace with vehicle-side and ESD/control channels",
                "complete blinded expert and prospective SAGA safety-effectiveness evaluation",
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit_json.read_text(encoding="utf-8"))
    snapshot = build_snapshot(audit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
