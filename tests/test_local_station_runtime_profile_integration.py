from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_station_runtime_profile_integration_2026_10_09.json"


def test_local_station_runtime_profile_integration_is_explicit_and_bounded():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "local_station_runtime_profile_integration_audit"
    assert record["status"] == "completed_runtime_integration_audit"
    assert record["all_checks_passed"] is True
    assert record["checks"] == {
        "reference_defaults_preserved": True,
        "opt_in_profile_applied": True,
        "failed_dynamics_profile_not_attached": True,
        "simulations_completed": True,
        "privacy_boundary_preserved": True,
    }
    assert record["cases"]["reference_defaults"]["profile_id"] == "reference_defaults"
    assert record["cases"]["explicit_opt_in"]["profile_id"] == (
        "owner_measured_operational_envelope_v1"
    )
    assert record["cases"]["explicit_opt_in"]["sampled_rows"] == 10896
    assert record["cases"]["explicit_opt_in"]["recharge_restart_margin_pa"] == 540000.0
    assert all(
        row["station_recharge_dynamics_status"] == "disabled"
        for row in record["cases"].values()
    )
    assert all(
        "C:" not in json.dumps(row, ensure_ascii=False)
        and "\\\\" not in json.dumps(row, ensure_ascii=False)
        for row in record["cases"].values()
    )
