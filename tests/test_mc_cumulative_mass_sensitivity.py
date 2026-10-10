from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mc_cumulative_mass_sensitivity_is_bounded_and_does_not_promote_gate():
    record = json.loads(
        (ROOT / "research/mc_cumulative_mass_sensitivity_2026_10_10.json")
        .read_text(encoding="utf-8")
    )
    assert record["artifact_type"] == "mc_cumulative_mass_boundary_sensitivity"
    assert record["evidence_role"] == "development_diagnostic_only"
    assert record["post_outcome"] is True
    assert record["parameter_fitting"] is False
    assert record["runtime_parameter_updated"] is False
    assert "no independent mass channel" in record["source_limitation"]
    assert "does not revise the frozen MC result" in record["claim_boundary"]
    assert record["aggregate"]["case_count"] == 8
    assert record["aggregate"]["joint_screening_pass_count"] == 0
    assert record["aggregate"]["pressure_rmse_mpa_mean"] < 5.0
    assert record["aggregate"]["temperature_rmse_c_mean"] < 10.0
    assert all(
        case["mass_boundary_mode"] == "cumulative_trapezoid_of_measured_mass_flow"
        for case in record["cases"]
    )
