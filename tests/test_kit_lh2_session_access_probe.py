from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "research/kit_lh2_session_access_probe_2026_10_11.json"


def test_kit_session_probe_preserves_no_outcome_access_claim() -> None:
    payload = json.loads(PROBE.read_text(encoding="utf-8"))
    assert payload["session_probe"]["stream_status"] == 200
    assert payload["session_probe"]["full_archive_downloaded"] is False
    assert payload["boundary"]["numeric_signal_values_opened"] is False
    assert payload["boundary"]["video_outcomes_opened"] is False
    assert payload["decision"]["stage1_integrity_verified"] is False
    assert payload["decision"]["stage2_eligible"] is False
