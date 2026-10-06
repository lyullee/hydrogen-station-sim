import json
from pathlib import Path

from scripts.audit_private_media_intake import audit


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/confidential_private_media_intake_assessment_2026_10.json"


def test_private_media_artifact_is_privacy_bounded_and_not_validation():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    serialized = json.dumps(result, ensure_ascii=False)
    assert result["artifact_type"] == "confidential_private_media_intake_assessment"
    assert result["source_identifiers_published"] is False
    assert result["raw_media_persisted"] is False
    assert result["exact_source_dates_published"] is False
    assert result["media_inventory"]["video_count"] > 0
    assert result["content_assessment"]["machine_readable_trace_present"] is False
    assert result["content_assessment"]["ocr_or_frame_values_used_for_calibration"] is False
    assert result["eligibility"]["full_loop_holdout_eligible"] is False
    assert "FTPData" not in serialized
    assert "20261002" not in serialized


def test_media_audit_counts_files_without_exposing_names(tmp_path):
    (tmp_path / "one.jpg").write_bytes(b"image")
    (tmp_path / "two.mp4").write_bytes(b"video")
    (tmp_path / "notes.txt").write_text("private", encoding="utf-8")
    result = audit(tmp_path)
    assert result["file_count"] == 3
    assert result["media_inventory"]["image_count"] == 1
    assert result["media_inventory"]["video_count"] == 1
    assert result["media_inventory"]["non_media_count"] == 1
    assert "one.jpg" not in json.dumps(result)
    assert "two.mp4" not in json.dumps(result)
