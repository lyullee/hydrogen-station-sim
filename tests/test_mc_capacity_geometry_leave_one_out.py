from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/mc_capacity_geometry_leave_one_out_2026_10_14.json"


def test_mc_capacity_geometry_cross_validation_keeps_folds_disjoint() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["artifact_type"] == "mc_capacity_geometry_leave_one_case_out"
    assert result["post_outcome"] is True
    assert result["external_validation"] is False
    assert result["prospective_validation"] is False
    assert result["runtime_parameter_changed"] is False
    assert result["validation_gate_changed"] is False
    assert result["method"]["held_out_outcomes_excluded_from_fit"] is True
    assert len(result["folds"]) == 8
    for fold in result["folds"]:
        assert fold["training_case_count"] == 7
        assert fold["held_out_case_id"] not in fold["training_case_ids"]
        assert fold["held_out_volume_ratio_used_for_training"] is False


def test_mc_capacity_geometry_cross_validation_quantifies_remaining_limit() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    aggregate = result["aggregate"]
    comparison = result["baseline_comparison"]
    assert aggregate["joint_screening_pass_count"] == 4
    assert aggregate["fold_count"] == 8
    assert aggregate["pressure_rmse_mpa_mean"] < 2.0
    assert aggregate["soc_final_abs_error_percentage_points_mean"] < 3.1
    assert comparison["baseline_joint_screening_pass_count"] == 0
    assert comparison["pressure_rmse_reduction_percent"] > 50.0
    assert comparison["soc_final_abs_error_reduction_percent"] > 60.0
    assert comparison["temperature_rmse_reduction_percent"] < 0.0
    assert "temperature" in result["interpretation"].lower()
