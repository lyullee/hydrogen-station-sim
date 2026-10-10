from __future__ import annotations

from scripts.write_goal_progress_snapshot import build_snapshot


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
