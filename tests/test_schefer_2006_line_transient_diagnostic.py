from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_line_transient_diagnostic_is_explicitly_non_validating():
    artifact = json.loads(
        (ROOT / "research/schefer_2006_line_transient_diagnostic_2026_10_09.json")
        .read_text(encoding="utf-8")
    )
    assert artifact["post_outcome_diagnostic"] is True
    assert artifact["frozen_result_unchanged"] is True
    assert artifact["runtime_parameter_updated"] is False
    assert artifact["validation_gate_effect"] == "none"
    assert artifact["claim_supported"] is False
    assert set(artifact["instrument_boundary_views"]) == {"source_flow", "outlet_flow"}
    sensitivity = artifact["post_outcome_valve_time_constant_sensitivity"]
    assert [item["source_valve_time_constant_s"] for item in sensitivity] == [
        0.0,
        0.5,
        1.0,
        2.0,
        4.0,
    ]
    assert all(
        "mass_flow_nrmse_percent_peak_measured" in item["source_flow"]
        for item in sensitivity
    )
