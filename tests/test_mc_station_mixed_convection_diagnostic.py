from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_mc_station_mixed_convection_diagnostic import (  # noqa: E402
    EQUIVALENT_CYLINDER_ASPECT_RATIO,
    equivalent_geometry,
)


def test_equivalent_geometry_preserves_declared_tank_volume():
    volume_m3 = 0.122
    diameter_m, length_m = equivalent_geometry(volume_m3)
    reconstructed = (
        math.pi * diameter_m**2 * length_m / 4.0
        + math.pi * diameter_m**3 / 6.0
    )
    assert reconstructed == pytest.approx(volume_m3, rel=1.0e-12)
    assert length_m / diameter_m == pytest.approx(
        EQUIVALENT_CYLINDER_ASPECT_RATIO
    )


def test_committed_station_diagnostic_retains_negative_result_and_claim_boundary():
    report = json.loads(
        (ROOT / "research/mc_station_mixed_convection_diagnostic_2026_10_08.json")
        .read_text(encoding="utf-8")
    )
    assert report["post_outcome"] is True
    assert report["source_worktree_dirty"] is True
    assert report["parameter_fitting"] is False
    assert report["geometry_selection_prohibited"] is True
    assert report["historical_frozen_validation_unchanged"] is True
    assert "cannot revise the frozen 0/8" in report["claim_boundary"]

    runs = report["runs"]
    assert [row["thermal_model"] for row in runs] == [
        "constant_ua",
        "mixed_convection",
        "mixed_convection",
        "mixed_convection",
    ]
    assert [row["nozzle_diameter_mm"] for row in runs] == [None, 3.0, 5.0, 7.0]
    assert all(row["aggregate"]["case_count"] == 8 for row in runs)
    assert all(
        row["aggregate"]["joint_screening_pass_count"] == 0 for row in runs
    )

    baseline = runs[0]["aggregate"]
    for mixed in runs[1:]:
        aggregate = mixed["aggregate"]
        assert aggregate["temperature_safety_stop_count"] < baseline[
            "temperature_safety_stop_count"
        ]
        assert aggregate["pressure_rmse_mpa_mean"] < baseline[
            "pressure_rmse_mpa_mean"
        ]
        assert aggregate["temperature_rmse_c_mean"] < baseline[
            "temperature_rmse_c_mean"
        ]
        assert aggregate["soc_rmse_percentage_points_mean"] < baseline[
            "soc_rmse_percentage_points_mean"
        ]
