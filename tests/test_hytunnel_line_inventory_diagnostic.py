from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_line_inventory_diagnostic_is_explicitly_post_outcome_and_bounded():
    path = ROOT / "research/hytunnel_line_inventory_diagnostic_2026_10_11.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    boundary = payload["model_boundary"]
    assert payload["post_outcome_diagnostic"] is True
    assert boundary["runtime_parameter_application"] is False
    assert boundary["frozen_gate_effect"] == "none"
    assert boundary["line_length_m"] == 3.86
    assert boundary["line_inner_diameter_m"] == 0.003
    assert boundary["nozzle_inner_diameter_m"] == 0.0005
    assert boundary["source_volume_selection"].startswith("declared sensitivity")
    assert len(payload["cases"]) == 15
    assert "does not replace the frozen mass-flow holdout" in payload["claim_boundary"]


def test_line_inventory_cases_keep_source_and_nozzle_flow_separate():
    path = ROOT / "research/hytunnel_line_inventory_diagnostic_2026_10_11.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert all(
        "source_peak_mass_flow_g_s" in case["summary"]
        and "outlet_peak_mass_flow_g_s" in case["summary"]
        for case in payload["cases"]
    )
