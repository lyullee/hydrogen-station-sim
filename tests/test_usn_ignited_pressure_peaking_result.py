import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ignited_pressure_peaking_holdout_passes_frozen_primary_rule():
    result = json.loads(
        (ROOT / "research/usn_17934047_ignited_pressure_peaking_result_2026_10_08.json").read_text(
            encoding="utf-8"
        )
    )
    aggregate = result["aggregate"]
    assert result["status"] == "completed_prospective_protocol_execution"
    assert aggregate["eligible_case_count"] == 27
    assert aggregate["excluded_case_count"] == 0
    assert aggregate["primary_pass_count"] == 27
    assert aggregate["primary_pass_fraction"] == 1.0
    assert aggregate["confirmatory_rule_met"] is True
    assert aggregate["peak_overpressure_mae_kpa"] < 0.7


def test_ignited_pressure_peaking_result_preserves_scope_and_raw_boundary():
    result = json.loads(
        (ROOT / "research/usn_17934047_ignited_pressure_peaking_result_2026_10_08.json").read_text(
            encoding="utf-8"
        )
    )
    assert [item["case"] for item in result["cases"]] == list(range(2, 29))
    assert max(item["peak_overpressure_abs_error_kpa"] for item in result["cases"]) <= 2.0
    assert result["source"]["raw_files_committed"] is False
    assert "does not validate" in result["claim_boundary"].lower()
