"""Integrity checks for the disclosed release-model sensitivity diagnostic."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "research" / "release_model_posthoc_sensitivity.json"


def test_posthoc_diagnostic_is_not_a_validation_gate():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["evidence_role"] == "posthoc_development_diagnostic_only"
    assert report["status"] == "completed_without_modifying_frozen_results"
    assert report["method"]["outcome_fitting"] is False
    assert report["method"]["frozen_primary_results_rewritten"] is False
    assert len(report["cases"]) == 3
    assert all(case["any_grid_point_joint_screen_pass"] is False for case in report["cases"])


def test_posthoc_diagnostic_keeps_trace_paths_and_hashes():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    for case in report["cases"]:
        data_path = ROOT / case["data_path"]
        assert data_path.is_file()
        assert len(case["data_sha256"]) == 64
        assert len(case["rows"]) == len(report["method"]["grid"])
