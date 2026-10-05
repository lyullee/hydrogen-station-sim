from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_capacity_geometry_no_volume_fit_is_retained_as_negative_diagnostic():
    path = ROOT / (
        "research/h2protocol_capacity_geometry_no_volume_fit_diagnostic_2026_10_06.json"
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["status"] == "exploratory_no_volume_fit_diagnostic_only"
    assert report["evidence_role"] == "negative_model_development_evidence"
    assert report["geometry_rule"]["effective_volume_multiplier"] == 1.0
    assert report["aggregate"]["case_count"] == 36
    assert report["aggregate"]["screening_pass_count"] == 6
    assert report["interpretation"]["decision"] == "retain_production_defaults"
    assert report["source"]["temporary_harness_used"] is True
    assert "fresh holdout" in report["claim_boundary"]
