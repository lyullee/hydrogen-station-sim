"""Regression tests for simulation-only response action execution."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_hiad_virtual_action_execution import build_audit  # noqa: E402


def test_public_response_templates_execute_and_confirm_in_virtual_runtime():
    report = build_audit()
    runtime = report["runtime"]
    assert runtime["family_count"] == 9
    assert runtime["family_pass_count"] == 9
    assert runtime["action_count"] > runtime["family_count"]
    assert runtime["all_family_sequences_passed"] is True
    assert runtime["failure_feedback_guard"]["status"] == "passed"
    assert all(row["status"] == "passed" for row in report["family_results"].values())


def test_virtual_action_audit_is_explicitly_not_field_effectiveness():
    report = build_audit()
    boundary = " ".join(report["claim_boundary"])
    assert "operator benefit" in boundary
    assert "field safety" in boundary
    assert report["excluded_response_only_families"] == ["structural_damage"]


def test_committed_artifact_matches_current_bounded_result():
    path = ROOT / "research/hiad_virtual_action_execution_2026_10_10.json"
    if not path.exists():
        return
    artifact = json.loads(path.read_text(encoding="utf-8"))
    assert artifact["runtime"]["all_family_sequences_passed"] is True
    assert artifact["runtime"]["failure_feedback_guard"]["status"] == "passed"
