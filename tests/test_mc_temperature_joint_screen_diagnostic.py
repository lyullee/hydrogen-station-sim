from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_mc_temperature_joint_screen_diagnostic import (  # noqa: E402
    TEMPERATURE_OBSERVATIONS,
    _operator_screen,
)


def test_operator_screen_requires_all_frozen_channels():
    boundary = {
        "pressure_rmse_mpa": 4.9,
        "soc_final_error_percentage_points": -4.9,
    }
    passing_temperature = {
        "temperature_rmse_c": 9.9,
    }
    failing_temperature = {
        "temperature_rmse_c": 10.1,
    }

    assert _operator_screen(passing_temperature, boundary) is True
    assert _operator_screen(failing_temperature, boundary) is False
    assert _operator_screen(passing_temperature, {**boundary, "pressure_rmse_mpa": 5.1}) is False
    assert _operator_screen(passing_temperature, {**boundary, "soc_final_error_percentage_points": -5.1}) is False


def test_joint_diagnostic_is_explicitly_non_promotional():
    report = json.loads(
        (ROOT / "research" / "mc_temperature_joint_screen_diagnostic_2026_10_11.json")
        .read_text(encoding="utf-8")
    )

    assert report["evidence_role"] == "post_outcome_semantic_diagnostic_only"
    assert report["parameter_fitting"] is False
    assert report["runtime_parameters_changed"] is False
    assert report["operator_selection_performed"] is False
    assert report["promotion_to_validation_prohibited"] is True
    assert set(report["candidate_observation_operators"]) == set(TEMPERATURE_OBSERVATIONS)
    assert all(
        report["aggregate"][name]["joint_screening_pass_count"] == 0
        for name in TEMPERATURE_OBSERVATIONS
    )
