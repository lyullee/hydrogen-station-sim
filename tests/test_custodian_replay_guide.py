import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_custodian_replay_guide_is_non_claiming_and_executable():
    guide = (
        ROOT / "research/CUSTODIAN_REPLAY_EXECUTION_GUIDE_2026_10_14.md"
    ).read_text(encoding="utf-8")
    checklist = json.loads(
        (
            ROOT / "research/custodian_replay_checklist_2026_10_14.json"
        ).read_text(encoding="utf-8")
    )

    assert "원시 행" in guide
    assert "outcomes_accessed_before_freeze" in guide
    assert "inspect_privacy_safe_event.py" in guide
    assert "freeze_privacy_safe_full_loop.py" in guide
    assert "안전거리" in guide
    assert checklist["status"] == "READY_FOR_CUSTODIAN_EXECUTION"
    assert checklist["raw_rows_in_repository"] is False
    assert len(checklist["steps"]) == 5
    assert checklist["promotion_rule"]["all_required_steps"] is True
    assert checklist["promotion_rule"]["all_frozen_screens_pass"] is True
    assert checklist["promotion_rule"]["missing_or_changed_evidence"] == (
        "retain_pending_or_fail"
    )
