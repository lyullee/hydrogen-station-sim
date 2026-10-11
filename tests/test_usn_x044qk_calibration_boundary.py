import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/usn_x044qk_calibration_boundary_recheck_2026_10_12.json"


def test_x044qk_calibration_boundary_fails_closed_without_promoting_a_gate():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["status"] == "CALIBRATION_STILL_INSUFFICIENT_FOR_NUMERICAL_REPLAY"
    assert record["source"]["dataset_license"] == "CC0 1.0"
    instrument = record["publisher_reported_measurement_boundary"]
    assert instrument["reported_sensor_range_bar_g"] == [0, 250]
    assert instrument["reported_sensor_uncertainty"] == "±0.5% FSO (±1.25 bar)"
    raw = record["raw_archive_observation"]
    assert raw["raw_unit"] == "V"
    assert raw["experiment_specific_voltage_to_pressure_transfer"] == (
        "not published in the public README, dataset metadata, or reviewed article text"
    )
    decision = record["decision"]
    assert decision["numeric_model_replay"] is False
    assert decision["runtime_parameter_changed"] is False
    assert decision["validation_gate_promoted"] is False
