from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/kit_lh2_consequence_intake_protocol_2026_10_08.json"


def test_kit_lh2_stage1_is_frozen_before_archive_or_outcome_access() -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert payload["status"] == "stage1_inventory_protocol_frozen_before_archive_download"
    assert payload["source"]["doi"] == "10.35097/1483"
    assert payload["source"]["archive_version"] == 1
    assert payload["source"]["publisher_reported_md5"] == "0e4ac934ecb973c6f07212e8a80707c9"
    assert payload["source"]["license"] == "CC BY-SA 4.0"
    assert payload["source"]["numerical_signal_files_downloaded_before_freeze"] is False
    assert payload["source"]["numerical_signal_files_opened_before_freeze"] is False
    assert payload["source"]["video_outcomes_opened_before_freeze"] is False
    assert payload["source"]["repository_duplicate_search"]["prior_numeric_result_found"] is False


def test_kit_lh2_stage1_prohibits_outcome_access_before_second_freeze() -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    prohibited = " ".join(payload["stage1_prohibited_operations"])
    assert "signal values" in prohibited
    assert "videos" in prohibited
    assert "fit" in prohibited
    assert len(payload["stage2_freeze_requirements"]) >= 6
    assert "eligibility only" in payload["claim_boundary"]
