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
