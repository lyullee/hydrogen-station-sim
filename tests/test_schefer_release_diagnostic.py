import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_schefer_diagnostic_preserves_negative_holdout_results():
    record = json.loads(
        (
            ROOT
            / "research/schefer_release_postaccess_residual_diagnostic_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["evidence_role"] == "post_access_exploratory_diagnostic"
    assert record["schefer_2006_transient_mass_flow"]["result"]["joint_primary_screen_pass"] is False
    assert record["schefer_2007_pressure_decay"]["result"]["joint_primary_screen_pass"] is False
    assert record["schefer_2006_transient_mass_flow"]["gate_impact"].endswith("remains_failed")
    assert record["schefer_2007_pressure_decay"]["gate_impact"].endswith("remains_failed")
