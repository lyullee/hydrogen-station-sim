import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "h2safe_indoor_release_protocol_2026_10_07.json"
RESULT = ROOT / "research" / "h2safe_indoor_release_intake_2026_10_07.json"
REPORT = ROOT / "research" / "H2SAFE_INDOOR_SURROGATE_INTAKE_2026_10_07.md"


def test_h2safe_protocol_is_frozen_before_source_inspection():
    record = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert record["status"] == "PROTOCOL_FROZEN_NOT_EXECUTED"
    assert record["dataset"]["doi"] == "10.7799/17118570"
    assert record["runtime_and_claim_boundary"]["allowed_runtime_use"].startswith("Evidence")
    assert any(
        "hydrogen concentration equivalence" in value
        for value in record["runtime_and_claim_boundary"]["prohibited_inferences"]
    )


def test_h2safe_intake_preserves_scope_and_refuses_threshold_calibration():
    record = json.loads(RESULT.read_text(encoding="utf-8"))
    assert record["status"] == "completed_bounded_full_scale_indoor_surrogate_intake"
    assert record["source"]["doi"] == "10.7799/17118570"
    assert record["source"]["raw_rows_committed"] is False
    assert record["intake"]["case_count"] == 5
    assert record["intake"]["lab_sensor_coordinate_counts"] == {"Lab-1": 24, "Lab-2": 37}
    assert all(record["intake"]["readme_required_sections_present"].values())
    assert all(case["unmapped_sensor_columns"] == [] for case in record["intake"]["cases"])
    assert record["eligibility"]["numerical_hydrogen_alarm_or_trip_threshold_calibration"] is False
    assert record["eligibility"]["full_loop_station_vehicle_validation"] is False
    assert record["runtime_parameter_updated"] is False


def test_h2safe_report_keeps_the_surrogate_and_runtime_limits_visible():
    report = REPORT.read_text(encoding="utf-8")
    assert "helium as a nonflammable hydrogen surrogate" in report
    assert "is **not** used to" in report
    assert "station-to-vehicle filling loop" in report
