from __future__ import annotations

import json
from pathlib import Path

from scripts.write_goal_progress_snapshot import build_snapshot


ROOT = Path(__file__).resolve().parents[1]


def test_progress_snapshot_is_a_gate_closure_metric() -> None:
    snapshot = build_snapshot(
        {
            "gate_counts": {"PASS": 127, "FAIL": 10, "PENDING": 7},
            "bounded_ijhe_submission_ready": False,
            "full_user_objective_ready": False,
            "goal_completion_permitted": False,
            "blocking_bounded_submission_gates": ["full_loop_external_validation"],
            "blocking_full_objective_gates": ["grune_2014_pressure_decay_validation"],
        }
    )
    assert snapshot["gate_counts"] == {"PASS": 127, "FAIL": 10, "PENDING": 7, "TOTAL": 144}
    assert snapshot["gate_closure_percent"] == 88.2
    assert snapshot["full_user_objective_ready"] is False
    assert "validated_full_station_to_vehicle_digital_twin" in snapshot["interpretation"]["do_not_claim"]
    scope = snapshot["interpretation"]["scope_amendment_2026_10_11"]
    assert "synchronized station-to-vehicle raw logger validation" in scope["excluded_from_primary_goal"]
    assert snapshot["interpretation"]["priority_status_2026_10_11"]["independent_component_holdout"] == "retained_public_type_iv_split_ready"
    assert snapshot["primary_scope_progress_2026_10_11"]["gate_closure_percent"] == 88.2


def test_committed_full_regression_evidence_is_reflected_in_progress_snapshot() -> None:
    regression = json.loads(
        (ROOT / "research/full_regression_test_run_2026_10_11.json").read_text(
            encoding="utf-8"
        )
    )
    snapshot = json.loads(
        (ROOT / "research/goal_progress_snapshot_2026_10_11.json").read_text(
            encoding="utf-8"
        )
    )
    reflected = snapshot["interpretation"]["latest_access_evidence"]["full_regression"]
    for key in ("status", "tests_passed", "tests_failed", "warnings", "source_commit"):
        assert reflected[key] == regression[key]
    assert reflected["evidence"] == "research/full_regression_test_run_2026_10_11.json"


def test_regeneration_preserves_curated_evidence_block() -> None:
    prior = {
        "interpretation": {
            "latest_access_evidence": {
                "full_regression": {"tests_passed": 1446},
                "geometry_diagnostic": {"runtime_default_changed": False},
            }
        }
    }
    snapshot = build_snapshot(
        {"gate_counts": {"PASS": 1, "FAIL": 0, "PENDING": 0}},
        prior,
    )
    assert snapshot["interpretation"]["latest_access_evidence"] == prior["interpretation"]["latest_access_evidence"]
