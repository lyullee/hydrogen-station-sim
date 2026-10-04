import json
from pathlib import Path

from scripts.verify_hiad_2_2_source import build_verification


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/public_validation/raw/hiad_2_2/HIAD 2.2.xlsx"


def test_hiad_22_source_verification_is_hash_locked_and_non_approval():
    result = build_verification(SOURCE)
    assert result["source"]["sha256"] == (
        "295772b60a4afe5ef47a00bc314eed48b76c170be00c29952d60e50fedd6f55f"
    )
    assert result["source"]["event_cutoff"] == "2025-12-31"
    assert result["selection"]["case_count"] == 34
    assert result["selection"]["unique_event_ids"] is True
    assert result["selection"]["response_text_read"] is False
    assert result["selection"]["coordinator_approval"] is False
    assert result["workbook"]["sheet_dimensions"]["EVENTS"]["rows"] == 1143


def test_committed_hiad_source_verification_matches_local_source():
    record = json.loads(
        (ROOT / "research/hiad_2_2_source_verification_2026_10_04.json").read_text(
            encoding="utf-8"
        )
    )
    fresh = build_verification(SOURCE)
    assert record == fresh
