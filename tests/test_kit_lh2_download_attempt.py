from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT = ROOT / "research/kit_lh2_download_attempt_2026_10_11.json"


def test_kit_download_attempt_cannot_be_promoted_from_partial_stream() -> None:
    payload = json.loads(ATTEMPT.read_text(encoding="utf-8"))
    attempt = payload["attempt"]
    boundary = payload["protocol_boundary"]
    assert attempt["bytes_received_before_disconnect"] < payload["source"]["archive_bytes_reported"]
    assert attempt["partial_md5"] != payload["source"]["archive_md5_reported"]
    assert boundary["numeric_signal_values_opened"] is False
    assert boundary["video_outcomes_opened"] is False
    assert boundary["stage1_integrity_verified"] is False
    assert boundary["stage2_eligible"] is False
    resume = payload["range_route_probe"]["resume_probe_after_cooldown"]
    assert resume["status"] == 206
    assert resume["bytes_received"] == 1048576
    assert resume["numeric_signal_values_opened"] is False
    assert resume["video_outcomes_opened"] is False
