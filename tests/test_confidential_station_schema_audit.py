import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/confidential_station_schema_audit_2026_10.json"


def test_confidential_schema_audit_is_deidentified_and_claim_bounded():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    serialized = json.dumps(result, ensure_ascii=False)
    assert result["artifact_type"] == "confidential_station_schema_audit"
    assert result["source_identifiers_published"] is False
    assert result["raw_rows_persisted"] is False
    assert result["exact_source_dates_published"] is False
    assert result["source_bundle_count"] == 2
    assert result["signal_inventory"]["tagged_channel_counts"]["pressure"] > 0
    assert result["eligibility"]["station_side_schema_intake_supported"] is True
    assert result["eligibility"]["full_station_vehicle_validation"] is False
    assert result["eligibility"]["full_loop_holdout_eligible"] is False
    assert "코하이젠" not in serialized
    assert "화성" not in serialized
    assert "LocalTimeCol" not in serialized
    assert "2025 04" not in serialized
