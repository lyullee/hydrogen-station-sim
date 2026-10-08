from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_hrs_source_reconciliation_2026_10_09.json"


def test_local_hrs_reconciliation_is_privacy_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert all(value is False for value in record["privacy"].values())
    assert record["local_search"]["measured_hrs_source_file_count"] == 33
    assert record["local_search"]["measured_hrs_deduplicated_rows"] == 56_854_143


def test_local_hrs_reconciliation_covers_station_equipment_roles() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    collections = {item["id"]: item for item in record["measured_collections"]}
    assert collections["station_pressure_meter_bundle"]["file_count"] == 12
    assert collections["bank_lifecycle_thermal_bundle"]["file_count"] == 13
    wide = collections["wide_compressor_equipment_bundle"]
    assert wide["file_count"] == 8
    assert wide["row_count"] == 653_442
    assert wide["median_sample_period_s"] == 1.0
    assert wide["maximum_gap_s"] == 3.0


def test_local_hrs_reconciliation_keeps_full_loop_gate_closed() -> None:
    coverage = json.loads(ARTIFACT.read_text(encoding="utf-8"))["coverage_assessment"]
    assert coverage["local_station_data_is_sparse"] is False
    assert coverage["station_side_dynamic_evidence_is_substantial"] is True
    assert coverage["vehicle_side_full_loop_validation_ready"] is False
    assert coverage["full_loop_external_holdout_count"] == 0
    assert coverage["missing_for_full_loop"]
