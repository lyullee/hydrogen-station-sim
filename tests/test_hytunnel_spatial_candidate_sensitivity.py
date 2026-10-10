from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/hytunnel_spatial_candidate_sensitivity_2026_10_11.json"


def test_spatial_candidate_is_explicitly_post_outcome_and_not_runtime_enabled():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["post_outcome_development_only"] is True
    assert record["decision"]["runtime_application"] is False
    assert record["decision"]["readiness_gate_effect"] == "none"
    assert record["baseline"]["joint_screen_pass"] is False
    assert record["candidate"]["joint_screen_pass"] is True
    assert record["selection"]["outcomes_seen_before_selection"] is True
