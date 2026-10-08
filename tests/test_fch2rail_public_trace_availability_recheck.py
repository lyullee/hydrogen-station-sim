"""Regression checks for the FCH2RAIL/DLR public trace recheck."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/fch2rail_public_trace_availability_recheck_2026_10_09.json"


def test_fch2rail_recheck_is_privacy_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert all(value is False for value in record["privacy"].values())


def test_fch2rail_recheck_distinguishes_reports_from_raw_traces() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    scope = record["reported_measurement_scope"]
    inventory = record["official_file_link_inventory"]
    assert scope["station_measurements_reported"] is True
    assert scope["vehicle_measurements_reported"] is True
    assert scope["raw_synchronized_station_vehicle_trace_public"] is False
    assert inventory["raw_trace_download_verified"] is False


def test_fch2rail_recheck_preserves_full_loop_gate() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["gate_impact"]["full_loop_external_validation_gate"] == "remains_open"
    assert record["gate_impact"]["goal_completion_permitted"] is False
    assert record["eligibility_decision"]["independent_full_loop_validation"].startswith(
        "ineligible"
    )
