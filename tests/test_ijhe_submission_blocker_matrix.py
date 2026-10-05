import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_current_blocker_matrix_tracks_the_readiness_audit():
    audit = json.loads((ROOT / "manuscript/ijhe_readiness_audit.json").read_text(encoding="utf-8"))
    matrix = json.loads(
        (ROOT / "research/ijhe_submission_blocker_matrix_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert matrix["gate_counts"] == audit["gate_counts"]
    assert matrix["reproducibility"]["public_full_loop_search_candidate_count"] == 14
    assert matrix["reproducibility"]["public_operational_benchmark_candidate_count"] == 16
    assert matrix["decision"]["goal_completion_permitted"] is False
    assert matrix["decision"]["full_user_objective_ready"] is False
    ids = {item["id"] for item in matrix["blocking_matrix"]}
    assert {"full_loop_external_validation", "saga_human_effectiveness", "submission_declarations"} <= ids
