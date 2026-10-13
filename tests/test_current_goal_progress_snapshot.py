from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_current_progress_snapshot_matches_authoritative_readiness_audit() -> None:
    audit = json.loads(
        (ROOT / "manuscript/ijhe_readiness_audit.json").read_text(encoding="utf-8")
    )
    snapshot = json.loads(
        (ROOT / "research/goal_progress_snapshot_2026_10_14.json").read_text(
            encoding="utf-8"
        )
    )

    counts = audit["gate_counts"]
    assert snapshot["gate_counts"] == {
        "PASS": counts["PASS"],
        "FAIL": counts["FAIL"],
        "PENDING": counts["PENDING"],
        "TOTAL": sum(counts.values()),
    }
    assert snapshot["bounded_ijhe_submission_ready"] is audit[
        "bounded_ijhe_submission_ready"
    ]
    assert snapshot["full_user_objective_ready"] is audit["full_user_objective_ready"]
    assert snapshot["goal_completion_permitted"] is audit["goal_completion_permitted"]
    assert snapshot["blocking_bounded_submission_gates"] == audit[
        "blocking_bounded_submission_gates"
    ]
    assert snapshot["blocking_full_objective_gates"] == audit[
        "blocking_full_objective_gates"
    ]
