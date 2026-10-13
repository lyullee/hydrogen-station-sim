from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _record() -> dict[str, object]:
    return json.loads(
        (
            ROOT
            / "research/usn_frozen_spatial_candidate_transfer_2026_10_13.json"
        ).read_text(encoding="utf-8")
    )


def test_transfer_keeps_post_access_boundary_and_fixed_candidate() -> None:
    record = _record()
    candidate = record["candidate"]
    classification = record["evidence_classification"]

    assert record["artifact_type"] == (
        "post_access_usn_frozen_spatial_candidate_transfer"
    )
    assert record["source"]["test_gas"] == "actual hydrogen"
    assert record["source"]["archive_count"] == 22
    assert candidate["parameters"] == {
        "upward_vertical_weight": 0.3,
        "downward_vertical_penalty": 0.1,
        "vertical_denominator_weight": 0.2,
        "denominator_power": 1.0,
        "horizontal_distance_power": 1.25,
        "denominator_offset": 0.25,
    }
    assert candidate["parameter_tuning_in_this_evaluation"] is False
    assert candidate["dataset_included_in_parameter_search"] is False
    assert classification == {
        "outcomes_accessed_before_candidate_freeze": True,
        "human_outcome_independence": False,
        "independent_holdout": False,
        "prospective_validation": False,
        "transfer_diagnostic_only": True,
        "readiness_gate_effect": False,
        "runtime_parameter_application": False,
    }


def test_transfer_uses_explicit_axis_mapping_and_retains_all_screens() -> None:
    record = _record()
    aggregate = record["result"]["aggregate"]

    assert record["coordinate_transform"]["mapping"] == (
        "candidate(x,y,z) = dataset(x,z,y)"
    )
    assert aggregate["experiment_count"] == 22
    assert set(aggregate["screens"]) == {
        "median_spearman_at_least_0_5",
        "spearman_at_least_0_4_fraction_at_least_0_6",
        "mean_top5_recall_at_least_0_6",
        "nearest_in_response_quartile_fraction_at_least_0_7",
    }
    assert aggregate["joint_pass"] == all(aggregate["screens"].values())


def test_transfer_candidate_is_absent_from_runtime_imports() -> None:
    for relative in ("src/h2station/api.py", "src/h2station/hazop/runtime.py"):
        assert "prospective_spatial_rank" not in (ROOT / relative).read_text(
            encoding="utf-8"
        )
