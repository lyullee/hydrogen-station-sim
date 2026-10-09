from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mc_boundary_diagnostic_is_bounded_and_keeps_release_gate_closed():
    record = json.loads(
        (ROOT / "research/partial_station_mc_boundary_diagnostic_2026_10_09.json")
        .read_text(encoding="utf-8")
    )

    assert record["evidence_role"] == "development_diagnostic_only"
    assert record["post_outcome"] is True
    assert record["production_runtime_changed"] is False
    assert record["frozen_holdout_effect"] == (
        "none; the previously frozen 0/8 external result remains unchanged"
    )
    assert record["source"]["case_count"] == 8
    assert all(run["screening_pass_count"] == 0 for run in record["runs"])
    assert record["runs"][0]["aggregate"]["simulation_coverage_fraction"] < 1.0
    assert record["runs"][1]["aggregate"]["simulation_coverage_fraction"] == 1.0
    assert "not" in record["claim_boundary"]
