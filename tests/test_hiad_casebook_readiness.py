from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_hiad_casebook_readiness import audit  # noqa: E402


def test_unapproved_casebook_blocks_collection():
    casebook = {
        "holdout_count": 2,
        "cases": [
            {"event_id": "1", "expert_vignette_approved": "NO", "narrative_action_leakage_review": "PENDING"},
            {"event_id": "2", "expert_vignette_approved": "NO", "narrative_action_leakage_review": "PENDING"},
        ],
    }
    prescreen = {"case_count": 2, "advisory_only": True}
    protocol = {"ethics_status": "pending", "holdout_response_collection_permitted": False}
    result = audit(casebook, prescreen, protocol)
    assert result["aggregate"]["unresolved_case_count"] == 2
    assert result["collection_allowed"] is False


def test_collection_requires_ethics_and_all_approvals():
    casebook = {
        "holdout_count": 1,
        "cases": [{"event_id": "1", "expert_vignette_approved": "YES", "narrative_action_leakage_review": "PASS"}],
    }
    prescreen = {"case_count": 1, "advisory_only": True}
    protocol = {"ethics_status": "approved", "ethics_determination_id": "IRB-1", "holdout_response_collection_permitted": True}
    result = audit(casebook, prescreen, protocol)
    assert result["collection_allowed"] is True
