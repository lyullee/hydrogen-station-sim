from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_station_rescan_2026_10_09.json"


def test_local_rescan_is_privacy_bounded_and_reconciled() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "local_confidential_station_data_rescan"
    assert all(value is False for value in record["privacy"].values())
    assert record["inventory"]["csv_files"] == 33
    assert record["inventory"]["deduplicated_data_rows"] == 56_854_143
    assert record["reconciliation"]["core_inventory_matches_prior_artifact"] is True
    assert record["reconciliation"]["drift_detected"] is False


def test_local_rescan_keeps_vehicle_and_runtime_claims_gated() -> None:
    decision = json.loads(ARTIFACT.read_text(encoding="utf-8"))["decision"]
    assert decision["local_station_data_is_sparse"] is False
    assert decision["station_side_dynamic_validation_ready"] is True
    assert decision["vehicle_side_full_loop_validation_ready"] is False
    assert decision["runtime_defaults_changed"] is False
