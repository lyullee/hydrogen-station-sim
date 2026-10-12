from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_ijhe_readiness import audit


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _decision_snapshot(report: dict) -> dict:
    return {
        "bounded_ijhe_submission_ready": report["bounded_ijhe_submission_ready"],
        "full_user_objective_ready": report["full_user_objective_ready"],
        "goal_completion_permitted": report["goal_completion_permitted"],
        "gate_counts": report["gate_counts"],
        "blocking_bounded_submission_gates": report["blocking_bounded_submission_gates"],
        "blocking_full_objective_gates": report["blocking_full_objective_gates"],
        "gates": [
            {"id": gate["id"], "status": gate["status"]}
            for gate in report["gates"]
        ],
    }


def test_research_and_manuscript_audits_share_the_same_readiness_decision():
    manuscript = _load("manuscript/ijhe_readiness_audit.json")
    research = _load("research/ijhe_readiness_audit.json")
    assert _decision_snapshot(research) == _decision_snapshot(manuscript)


def _without_generated_at(report: dict) -> dict:
    return {key: value for key, value in report.items() if key != "generated_at"}


def _canonicalize_paths(value):
    """Compare audit content independently of the host path separator."""

    if isinstance(value, dict):
        return {key: _canonicalize_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonicalize_paths(item) for item in value]
    if isinstance(value, str):
        return value.replace("\\", "/")
    return value


def test_committed_audit_is_fresh_against_the_current_source_tree():
    """Prevent a source-hash audit from silently going stale after edits."""

    committed = _load("manuscript/ijhe_readiness_audit.json")
    current = audit(ROOT)
    assert _canonicalize_paths(_without_generated_at(committed)) == (
        _canonicalize_paths(_without_generated_at(current))
    )
