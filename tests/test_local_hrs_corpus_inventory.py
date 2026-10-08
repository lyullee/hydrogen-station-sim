"""Regression checks for the privacy-bounded local HRS corpus inventory."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_hrs_corpus_inventory_2026_10_09.json"


def test_inventory_is_privacy_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert all(value is False for value in record["privacy"].values())


def test_inventory_records_abundant_station_and_public_component_data() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    collections = {item["id"]: item for item in record["collections"]}
    station = collections["controlled_station_telemetry"]
    public = collections["local_public_machine_readable_corpus"]
    assert station["file_count"] == 33
    assert station["deduplicated_rows"] == 56_854_143
    assert public["file_count"] == 255
    assert public["examples"]["open_tank_or_refueling_experiments"]["sample_rows_in_workbooks"] == 9_480


def test_inventory_keeps_full_loop_boundary_closed() -> None:
    coverage = json.loads(ARTIFACT.read_text(encoding="utf-8"))["coverage_assessment"]
    assert coverage["local_station_data_is_sparse"] is False
    assert coverage["public_component_evidence_is_substantial"] is True
    assert coverage["vehicle_side_full_loop_validation_ready"] is False
    assert coverage["full_loop_external_holdout_count"] == 0
