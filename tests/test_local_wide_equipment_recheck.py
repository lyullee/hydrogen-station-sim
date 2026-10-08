"""Regression checks for the privacy-bounded wide equipment-log screen."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_wide_equipment_recheck_2026_10_09.json"


def test_wide_equipment_recheck_is_privacy_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "local_wide_equipment_recheck"
    assert all(value is False for value in record["privacy"].values())
    rendered = ARTIFACT.read_text(encoding="utf-8")
    assert "COMP." not in rendered
    assert "2025-04" not in rendered


def test_wide_equipment_recheck_captures_station_side_dynamics() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    inventory = record["inventory"]
    quality = record["quality_screen"]
    assert inventory["file_count"] == 8
    assert inventory["row_count"] == 653442
    assert inventory["schema_width"] == 64
    assert inventory["median_sample_period_s"] == 1.0
    assert inventory["maximum_gap_s"] == 3.0
    assert quality["pressure_roles_fully_finite"] == 2
    assert quality["temperature_roles_fully_finite"] == 3
    assert quality["compressor_load_transition_count"] == 261


def test_wide_equipment_recheck_preserves_full_loop_boundary() -> None:
    coverage = json.loads(ARTIFACT.read_text(encoding="utf-8"))["coverage_assessment"]
    assert coverage["local_equipment_boundary_data_is_substantial"] is True
    assert coverage["station_side_external_validation_ready"] is False
    assert coverage["vehicle_side_full_loop_validation_ready"] is False
    assert coverage["quantitative_consequence_validation_ready"] is False
