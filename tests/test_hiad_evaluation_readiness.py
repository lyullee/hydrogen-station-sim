from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.audit_hiad_evaluation_readiness import audit


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_advisory_prescreen_never_implies_casebook_approval(tmp_path: Path):
    casebook = {
        "cases": [
            {
                "event_id": "1",
                "narrative_action_leakage_review": "PENDING",
                "expert_vignette_approved": "NO",
            }
        ]
    }
    _write(tmp_path / "data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json", casebook)
    _write(tmp_path / "data/public_validation/results/hiad_coordinator_prescreen/prescreen_manifest.json", {
        "advisory_only": True,
        "human_review_required_for_every_case": True,
        "case_count": 1,
    })
    _write(tmp_path / "research/hiad_study_protocol_manifest.json", {
        "protocol_id": "TEST",
        "ethics_status": "pending",
        "ethics_determination_id": None,
        "reviewer_recruitment_permitted": False,
        "holdout_response_collection_permitted": False,
    })
    review = tmp_path / "data/public_validation/results/hiad_coordinator_prescreen/coordinator_review.csv"
    review.parent.mkdir(parents=True, exist_ok=True)
    with review.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "event_id", "coordinator_leakage_decision",
            "rewrite_required_yes_no", "coordinator_notes",
        ])
        writer.writeheader()
        writer.writerow({"event_id": "1", "coordinator_leakage_decision": "", "rewrite_required_yes_no": "", "coordinator_notes": ""})

    report = audit(tmp_path)
    assert report["coordinator_prescreen"]["advisory_only_and_human_review_required"] is True
    assert report["coordinator_prescreen"]["review_complete"] is False
    assert report["readiness"]["casebook_frozen"] is False
    assert report["readiness"]["ready_for_holdout_collection"] is False
    assert report["readiness"]["independent_review_complete"] is False


def test_complete_downstream_artifacts_are_required_for_review_ready(tmp_path: Path):
    _write(tmp_path / "data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json", {
        "cases": [{"event_id": "1", "narrative_action_leakage_review": "PASS", "expert_vignette_approved": "YES"}]
    })
    _write(tmp_path / "data/public_validation/results/hiad_coordinator_prescreen/prescreen_manifest.json", {
        "advisory_only": True, "human_review_required_for_every_case": True, "case_count": 1,
    })
    _write(tmp_path / "research/hiad_study_protocol_manifest.json", {
        "protocol_id": "TEST", "ethics_status": "exempt", "ethics_determination_id": "E1",
        "reviewer_recruitment_permitted": True, "holdout_response_collection_permitted": True,
    })
    _write(tmp_path / "data/public_validation/results/hiad_casebook_frozen/casebook_freeze_manifest.json", {
        "case_count": 1, "all_frozen_cases_retained": True, "all_cases_approved": True,
    })
    report = audit(tmp_path)
    assert report["readiness"]["ready_for_holdout_collection"] is True
    assert report["readiness"]["ready_for_independent_review"] is False
    assert report["readiness"]["independent_review_complete"] is False
