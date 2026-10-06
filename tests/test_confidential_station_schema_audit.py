import json
import csv
from pathlib import Path

from scripts.audit_confidential_station_schema import audit

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
    families = result["signal_inventory"]["privacy_bounded_channel_families"]
    assert families["compressor_pressure"] > 0
    assert families["compressor_temperature"] > 0
    assert families["flow_rate"] > 0
    assert result["eligibility"]["vehicle_side_channel_family_count"] == 0
    assert "코하이젠" not in serialized
    assert "화성" not in serialized
    assert "LocalTimeCol" not in serialized
    assert "2025 04" not in serialized


def test_schema_family_screen_catches_non_english_vehicle_aliases(tmp_path):
    sample = tmp_path / "sample.csv"
    with sample.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle).writerow(["시간", "차량탱크압력", "노즐온도", "밸브상태"])
    result = audit(tmp_path)
    families = result["signal_inventory"]["privacy_bounded_channel_families"]
    assert families["vehicle_side"] == 2
    assert result["eligibility"]["vehicle_side_channel_family_count"] == 2
