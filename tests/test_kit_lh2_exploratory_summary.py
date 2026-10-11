import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "research/kit_lh2_exploratory_summary_2026_10_11.json"


def test_kit_exploratory_summary_keeps_gate_boundary():
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert data["artifact_type"] == "kit_lh2_exploratory_component_summary"
    assert data["case_count"] == 4
    assert data["numeric_values_opened_after_protocol_freeze"] is True
    assert data["parameter_fitting_performed"] is False
    assert data["runtime_parameter_changes"] is False
    assert data["validation_gate_effect"] == "none"
    assert all("Flowmeter" in trial["sheets"] for trial in data["trials"])
    assert all("Radiometers" in trial["sheets"] for trial in data["trials"])
