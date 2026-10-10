import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_esst_supplements_are_retained_as_summary_only_benchmark():
    protocol = json.loads(
        (ROOT / "research/esst_2020_dispenser_full_loop_protocol_2026_10_11.json")
        .read_text(encoding="utf-8")
    )
    result = json.loads(
        (ROOT / "research/esst_2020_dispenser_full_loop_result_2026_10_11.json")
        .read_text(encoding="utf-8")
    )

    assert protocol["status"] == "FROZEN_BEFORE_RAW_OUTCOME_ACCESS"
    assert result["status"] == "SCREENED_INELIGIBLE_SUMMARY_ONLY"
    assert result["intake"]["archive_count"] == 4
    assert result["eligibility"]["public_real_refueling_context"] is True
    assert result["eligibility"]["time_resolved_machine_readable_trace"] is False
    assert result["eligibility"]["full_loop_external_validation_eligible"] is False
    assert result["decision"]["full_loop_gate_effect"] == "none"

