from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_mc_soc_boundary_diagnostic import run  # noqa: E402


def test_mc_soc_boundary_is_consistent_with_observed_eos_boundary() -> None:
    report = run()
    aggregate = report["aggregate"]
    assert report["case_count"] == 8
    assert aggregate["soc_definition_screen_pass_count"] == 8
    assert aggregate["soc_definition_rmse_percentage_points_max"] < 0.5
    assert aggregate["soc_definition_final_abs_error_percentage_points_max"] < 0.5
    assert 0.9 < aggregate["inferred_volume_ratio_median"] < 1.1
    assert report["runtime_parameter_updated"] is False
