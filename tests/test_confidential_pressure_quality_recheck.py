import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research" / "confidential_pressure_quality_recheck_2026_10_06.json"


def test_pressure_quality_recheck_is_deidentified_and_bounded():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["raw_rows_persisted"] is False
    assert record["source_identifiers_published"] is False
    assert record["exact_source_dates_published"] is False
    assert record["recheck"]["nonpositive_pressure_excluded_before_aggregation"] is True
    assert record["recheck"]["calibration_profile_replaced"] is False
    assert record["runtime_behavior"]["measured_boundary_calibration_default"] is False
    serialized = json.dumps(record, ensure_ascii=False)
    assert "C:\\Users" not in serialized
    assert "코하이젠" not in serialized
