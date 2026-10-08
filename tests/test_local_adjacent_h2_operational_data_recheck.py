import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_adjacent_h2_operational_data_recheck_2026_10_09.json"


def test_adjacent_inventory_is_privacy_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert all(value is False for value in record["privacy"].values())


def test_adjacent_inventory_is_large_but_not_full_loop() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    inventory = record["inventory"]
    assert inventory["telemetry_rows"] == 2_410_985
    assert inventory["telemetry_signal_key_count"] == 273
    coverage = record["coverage_assessment"]
    assert coverage["local_hydrogen_operational_data_is_abundant"] is True
    assert coverage["station_to_vehicle_full_loop_ready"] is False
