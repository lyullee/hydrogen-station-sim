import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _record():
    return json.loads(
        (ROOT / "research/korean_trailer_meter_experiment_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )


def test_component_experiment_is_not_promoted_to_full_loop_holdout():
    record = _record()
    assert record["decision"] == "KOREAN_COMPONENT_EXPERIMENT_DATA_REQUEST_LEAD"
    assert record["full_loop_holdout_eligible"] is False
    assert record["gate_impact"] == "independent_full_loop_gate_remains_open"
    assert record["observed_experiment"]["raw_time_series"] is False
    assert record["observed_experiment"]["full_station_controller_vehicle_channels"] is False


def test_reported_component_measurement_metadata_is_preserved():
    record = _record()
    observed = record["observed_experiment"]
    assert observed["sampling"] == "1 Hz data acquisition is reported"
    assert observed["calibration_flow_range_kg_min"] == [0.0, 5.17]
    assert observed["reported_model_average_errors_percent"] == {
        "model_1": 19.84,
        "model_2": 5.38,
        "model_3": 2.10,
    }
    assert set(observed["channels"]) >= {"pressure", "temperature", "Coriolis mass flow"}


def test_data_request_requires_reproducibility_and_reuse_metadata():
    record = _record()
    requested = set(record["requested_package"])
    assert "de-identified 1 Hz pressure-temperature-mass-flow rows" in requested
    assert "written permission for derived metrics and journal publication" in requested
    assert "valve/controller state and stop/fault markers" in requested
