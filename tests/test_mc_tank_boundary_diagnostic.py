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
    assert record["schema_version"] == 2
    assert record["evidence_role"] == "development_diagnostic_only"
    assert record["post_outcome"] is True
    assert record["parameter_fitting"] is False
    assert record["boundary_semantics"] == {
        "temperature_channel": "Tinlet_G",
        "pressure_channel": "Pinlet",
        "pairing_rule": (
            "Evaluate inlet hydrogen enthalpy from the co-located inlet "
            "temperature/pressure pair. Storage-source pressure channels "
            "875PT1 and 875PT3 are not nozzle-inlet pressure."
        ),
        "production_runtime_changed": False,
    }
    assert record["aggregate"]["case_count"] == 8
    assert "station controller" in record["claim_boundary"]
    assert record["aggregate"]["pressure_rmse_mpa_mean"] < 5.0
    assert record["aggregate"]["temperature_rmse_c_mean"] < 10.0
    assert record["aggregate"]["joint_screening_pass_count"] == 0
    assert all(
        case["inlet_enthalpy_pressure_basis"] == "pressure_mpa"
        and case["observed_pressure_source"] == "Pinlet"
        for case in record["cases"]
    )
