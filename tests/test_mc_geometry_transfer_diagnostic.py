from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mc_geometry_transfer_diagnostic_cannot_promote_a_rule():
    report = json.loads(
        (ROOT / "research/mc_geometry_transfer_diagnostic_2026_10_08.json")
        .read_text(encoding="utf-8")
    )

    assert report["evidence_role"] == "post_outcome_development_diagnostic_only"
    assert report["post_outcome"] is True
    assert report["parameter_fitting"] is False
    assert report["runtime_geometry_changed"] is False
    assert report["geometry_rule_selection_prohibited"] is True
    assert len(report["runs"]) == 3
    assert all(run["case_count"] == 8 for run in report["runs"])
    assert report["runs"][0]["geometry_rule"] == (
        "frozen_tables_method_effective_volume"
    )
    assert report["outcome_derived_identifiability"][
        "use_for_parameter_selection_prohibited"
    ] is True
