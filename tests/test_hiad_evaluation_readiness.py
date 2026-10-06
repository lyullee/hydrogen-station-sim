from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from scripts.audit_hiad_evaluation_readiness import audit
from scripts.freeze_hiad_study_protocol import REQUIRED_FILES


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _protocol_with_locked_files(root: Path) -> dict:
    hashes = {}
    for relative in REQUIRED_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("locked protocol material", encoding="utf-8")
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "protocol_id": "HIAD-SAGA-2601",
        "protocol_frozen_before_holdout_collection": True,
        "required_file_sha256": hashes,
        "ethics_status": "exempt",
        "ethics_determination_id": "E1",
        "reviewer_recruitment_permitted": True,
        "holdout_response_collection_permitted": True,
        "unresolved_institution_fields": {},
    }


def _write_valid_freeze(root: Path, casebook: dict) -> None:
    source = root / "data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json"
    freeze_dir = root / "data/public_validation/results/hiad_casebook_frozen"
    freeze_dir.mkdir(parents=True, exist_ok=True)
    submitted = freeze_dir / "approved_casebook_submitted.json"
    frozen = freeze_dir / "approved_casebook_frozen.json"
    change_log = freeze_dir / "casebook_change_log.csv"
    submitted.write_text(json.dumps(casebook), encoding="utf-8")
    frozen.write_text(json.dumps(casebook), encoding="utf-8")
    change_log.write_text("event_id,decision\n1,KEEP\n", encoding="utf-8")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    _write(freeze_dir / "casebook_freeze_manifest.json", {
        "case_count": len(casebook["cases"]),
        "all_frozen_cases_retained": True,
        "all_cases_approved": True,
        "file_sha256": {
            "source_casebook": digest(source),
            "submitted_approved_casebook": digest(submitted),
            "approved_casebook_submitted.json": digest(submitted),
            "approved_casebook_frozen.json": digest(frozen),
            "casebook_change_log.csv": digest(change_log),
        },
    })


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
    casebook = {
        "cases": [{"event_id": "1", "narrative_action_leakage_review": "PASS", "expert_vignette_approved": "YES"}]
    }
    _write(tmp_path / "data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json", casebook)
    _write(tmp_path / "data/public_validation/results/hiad_coordinator_prescreen/prescreen_manifest.json", {
        "advisory_only": True, "human_review_required_for_every_case": True, "case_count": 1,
    })
    _write(
        tmp_path / "research/hiad_study_protocol_manifest.json",
        _protocol_with_locked_files(tmp_path),
    )
    _write_valid_freeze(tmp_path, casebook)
    report = audit(tmp_path)
    assert report["readiness"]["ready_for_holdout_collection"] is True
    assert report["readiness"]["ready_for_independent_review"] is False
    assert report["readiness"]["independent_review_complete"] is False


def test_stale_protocol_cannot_enable_holdout_collection(tmp_path: Path):
    _write(tmp_path / "data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json", {
        "cases": [{"event_id": "1", "narrative_action_leakage_review": "PASS", "expert_vignette_approved": "YES"}]
    })
    _write(tmp_path / "data/public_validation/results/hiad_coordinator_prescreen/prescreen_manifest.json", {
        "advisory_only": True, "human_review_required_for_every_case": True, "case_count": 1,
    })
    protocol = _protocol_with_locked_files(tmp_path)
    _write(tmp_path / "research/hiad_study_protocol_manifest.json", protocol)
    (tmp_path / "scripts/run_hiad_decision_evaluation.py").write_text(
        "changed after freeze", encoding="utf-8"
    )
    _write(tmp_path / "data/public_validation/results/hiad_casebook_frozen/casebook_freeze_manifest.json", {
        "case_count": 1, "all_frozen_cases_retained": True, "all_cases_approved": True,
    })

    report = audit(tmp_path)

    assert report["protocol"]["integrity_passed"] is False
    assert report["readiness"]["ethics_and_collection_permitted"] is False
    assert report["readiness"]["ready_for_holdout_collection"] is False
