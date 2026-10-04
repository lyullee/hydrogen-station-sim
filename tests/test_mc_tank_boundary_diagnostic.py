from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mc_tank_boundary_replay_is_explicitly_bounded_diagnostic():
    record = json.loads(
        (ROOT / "research/mc_tank_boundary_diagnostic_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["diagnostic_type"] == "MC Default measured-boundary vehicle-tank replay"
    assert record["evidence_role"] == "development_diagnostic_only"
    assert record["post_outcome"] is True
    assert record["parameter_fitting"] is False
    assert record["aggregate"]["case_count"] == 8
    assert "station controller" in record["claim_boundary"]
    assert record["aggregate"]["pressure_rmse_mpa_mean"] < 5.0
    assert record["aggregate"]["temperature_rmse_c_mean"] > 10.0
