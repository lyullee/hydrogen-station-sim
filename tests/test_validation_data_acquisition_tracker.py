from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_validation_data_acquisition_tracker import audit  # noqa: E402


def test_external_data_tracker_is_complete_and_non_evidentiary():
    report = audit(ROOT / "research/validation_data_acquisition_tracker.json")
    assert report["status"] == "PASS"
    # Keep this count explicit so an added request lead is visible in review.
    assert report["candidate_count"] == 30
    assert report["request_draft_count"] >= 22
    assert "not evidence" in report["claim_boundary"].lower()
