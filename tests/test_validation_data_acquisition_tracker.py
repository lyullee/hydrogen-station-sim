from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_validation_data_acquisition_tracker import audit  # noqa: E402


def test_external_data_tracker_is_complete_and_non_evidentiary():
    report = audit(ROOT / "research/validation_data_acquisition_tracker.json")
    assert report["status"] == "PASS"
    # Keep this count explicit so an added request lead is visible in review.
    assert report["candidate_count"] == 33
    assert report["request_draft_count"] >= 22
    assert "not evidence" in report["claim_boundary"].lower()


def test_new_thermal_transfer_requests_require_blind_splits_when_possible():
    import json

    tracker = json.loads(
        (ROOT / "research/validation_data_acquisition_tracker.json")
        .read_text(encoding="utf-8")
    )
    candidates = {row["id"]: row for row in tracker["candidates"]}
    for candidate_id in (
        "wan_2026_type_iii_iv_aspect_ratio",
        "ferry_250bar_type_iv_2026",
    ):
        candidate = candidates[candidate_id]
        assert "blind" in candidate["status"]
        assert "blind" in candidate["minimum_acceptance"].lower()
        assert "blind" in candidate["claim_boundary"].lower()
        assert (ROOT / candidate["draft"]).is_file()


def test_priority_refresh_targets_the_largest_validation_blockers_first():
    import json

    priority = json.loads(
        (ROOT / "research/validation_data_priority_refresh_2026_10_08.json")
        .read_text(encoding="utf-8")
    )
    ranked = priority["ranked_candidates"]
    assert [row["rank"] for row in ranked] == list(range(1, len(ranked) + 1))
    assert ranked[0]["id"] == "hyfill_hd_hrs_experiments_2026"
    assert ranked[1]["id"] == "wan_2026_type_iii_iv_aspect_ratio"
    assert "full_loop_external_validation" in ranked[0]["expected_gate_impact"]
    assert "dickens_typeiii_prospective_validation" in ranked[1][
        "expected_gate_impact"
    ]
    assert priority["contact_sent"] is False
    assert "not validation evidence" in priority["claim_boundary"].lower()
    for row in ranked:
        assert (ROOT / row["draft"]).is_file()
