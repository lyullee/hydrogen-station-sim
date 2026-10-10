from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_calibrated_confirmation_is_explicitly_non_promotional_evidence():
    record = json.loads(
        (
            ROOT
            / "research/closed_loop_calibrated_confirmatory_diagnostic_2026_10_10.json"
        ).read_text(encoding="utf-8")
    )

    assert record["artifact_type"] == (
        "post_outcome_closed_loop_calibrated_confirmatory_diagnostic"
    )
    assert record["evidence_role"] == "model-development diagnostic only"
    assert record["post_outcome"] is True
    assert record["parameter_fitting"] is False
    assert record["production_default_changed"] is False
    assert record["validation_gate_effect"] == "none"
    assert record["diagnostic_aggregate"]["case_count"] == 11
    assert record["diagnostic_aggregate"]["screening_pass_count"] == 1
    assert "not a new independent holdout" in record["claim_boundary"]

