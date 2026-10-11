from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load() -> dict:
    return json.loads(
        (ROOT / "research/preslhy_partb_boundary_diagnostic_2026_10_11.json")
        .read_text(encoding="utf-8")
    )


def test_boundary_diagnostic_is_explicitly_post_outcome_and_non_runtime() -> None:
    report = _load()
    assert report["status"] == "POST_OUTCOME_DIAGNOSTIC_ONLY"
    assert report["model_boundary"]["runtime_parameter_application"] is False
    assert report["model_boundary"]["primary_gate_effect"] == "none"
    assert "cannot replace" in report["claim_boundary"]


def test_boundary_diagnostic_retains_the_frozen_negative_result() -> None:
    report = _load()
    assert len(report["cases"]) == 5
    assert sum(case["joint_primary_screen_pass"] for case in report["cases"]) == 3
    two_mm = [case for case in report["cases"] if case["nozzle_diameter_mm"] == 2.0]
    four_mm = [case for case in report["cases"] if case["nozzle_diameter_mm"] == 4.0]
    assert len(two_mm) == 2
    assert all(not case["joint_primary_screen_pass"] for case in two_mm)
    assert all(case["joint_primary_screen_pass"] for case in four_mm)
    assert all(case["source_file_sha256"] for case in report["cases"])
