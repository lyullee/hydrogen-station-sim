from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_schefer_public_boundary_is_diagnostic_only() -> None:
    record = json.loads(
        (
            ROOT
            / "research/schefer_2007_public_apparatus_boundary_2026_10_12.json"
        ).read_text(encoding="utf-8")
    )
    assert record["evidence_role"] == "post_outcome_boundary_diagnostic_only"
    assert record["eligibility_decision"] == "BOUNDARY_DIAGNOSTIC_ONLY_NO_GATE_PROMOTION"
    boundary = record["apparatus_boundary"]
    assert boundary["storage_tubes_used_for_blowdown"] == 2
    assert boundary["storage_tube_volume_l_each"] == 617
    assert boundary["exit_diameter_mm"] == 5.08
    assert boundary["valve_opening_profile_publicly_resolved"] is False
    assert boundary["upstream_line_volume_publicly_resolved"] is False
    assert boundary["common_clock_raw_pressure_temperature_mass_flow_file_found"] is False
    assert record["numeric_holdout_added"] is False
    assert record["runtime_model_changed"] is False
