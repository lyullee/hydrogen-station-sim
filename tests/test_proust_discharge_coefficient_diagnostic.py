import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/proust_discharge_coefficient_sensitivity_2026_10_06.json"


def test_proust_coefficient_diagnostic_remains_post_outcome_and_unapplied():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "proust_discharge_coefficient_sensitivity_diagnostic"
    assert record["evidence_role"] == "post_outcome_diagnostic_only"
    assert record["parameter_fitting"] is False
    assert record["production_model_parameter_changed"] is False
    effective = record["effective_coefficient_by_diameter"]
    assert [row["nozzle_diameter_mm"] for row in effective] == [1.0, 2.0, 3.0]
    assert effective[0]["effective_cd_median"] > 1.0
    assert effective[1]["effective_cd_median"] < 0.8
    assert effective[2]["effective_cd_median"] < 0.8
    assert len(record["sensitivity_grid"]) == 11
