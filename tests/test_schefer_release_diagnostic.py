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


def test_release_model_grid_is_claim_bounded_and_does_not_promote_a_fit():
    record = json.loads(
        (
            ROOT
            / "research/release_model_posthoc_sensitivity_2026_10_10.json"
        ).read_text(encoding="utf-8")
    )
    assert record["evidence_role"] == "posthoc_development_diagnostic_only"
    assert record["status"] == "completed_without_modifying_frozen_results"
    assert record["method"]["outcome_fitting"] is False
    assert record["method"]["frozen_primary_results_rewritten"] is False
    assert len(record["cases"]) == 3
    assert all(
        case["any_grid_point_joint_screen_pass"] is False
        for case in record["cases"]
    )
    assert "independent validation claim" in record["claim_boundary"]
