from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_fch2rail_ijhe_access_boundary_is_explicit_and_hash_locked():
    record = json.loads(
        (ROOT / "research/fch2rail_ijhe_measurement_access_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["source"]["doi"] == "10.1016/j.ijhydene.2025.04.040"
    assert record["source"]["pdf_sha256"] == (
        "462b57007a42e0a0b359d104d621c4e63f788dcd51b4fe6d995032261cd482b3"
    )
    boundary = record["observed_measurement_boundary"]
    assert boundary["vehicle_tank_pressure_and_temperature"] is True
    assert boundary["dispenser_pressure_temperature_mass_flow"] is True
    assert boundary["machine_readable_rows_publicly_linked"] is False
    assert record["eligibility"]["synchronized_raw_full_loop_holdout_eligible"] is False
    assert record["eligibility"]["goal_completion_permitted"] is False
