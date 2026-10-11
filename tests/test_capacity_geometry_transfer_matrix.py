from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_capacity_geometry_matrix_preserves_claim_boundary():
    report = json.loads(
        (ROOT / "research/capacity_geometry_transfer_matrix_2026_10_12.json")
        .read_text(encoding="utf-8")
    )
    assert report["evidence_role"] == "post_outcome_development_synthesis_only"
    assert report["outcomes_accessed_before_synthesis"] is True
    assert report["parameter_fitting"] is False
    assert report["runtime_geometry_changed"] is False
    assert len(report["datasets"]) == 2
    assert any("universal production rule" in item for item in report["findings"])
    assert "cannot establish station" in report["claim_boundary"]


def test_capacity_geometry_matrix_retains_both_negative_and_positive_transfer_evidence():
    report = json.loads(
        (ROOT / "research/capacity_geometry_transfer_matrix_2026_10_12.json")
        .read_text(encoding="utf-8")
    )
    mc = report["datasets"][0]["variants"]
    nrel = report["datasets"][1]["variants"]
    assert any(item["joint_pass_count"] == 0 for item in mc)
    assert any(item["joint_pass_count"] == 4 for item in mc)
    assert any(item["joint_pass_count"] == 7 for item in nrel)
    assert any(item["joint_pass_count"] == 0 for item in nrel)
