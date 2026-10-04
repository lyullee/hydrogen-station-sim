from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_hiad_accident_response_coverage import evaluate  # noqa: E402


def test_public_hiad_accident_actions_route_to_staged_plans_without_effectiveness_claim():
    report = evaluate(ROOT)
    aggregate = report["aggregate"]
    assert report["status"] == "completed_public_accident_response_coverage_evaluation"
    assert report["evidence_role"] == "public_accident_grounded_interface_evaluation"
    assert aggregate["case_count"] == 34
    assert aggregate["public_action_category_case_count"] == 33
    assert aggregate["no_public_action_category_case_count"] == 1
    assert aggregate["category_count"] == 8
    assert aggregate["covered_category_count"] == 8
    assert aggregate["uncovered_case_category_count"] == 0
    assert aggregate["contract_pass"] is True
    assert report["contract"]["raw_action_text_used"] is False
    assert report["contract"]["effectiveness_claimed"] is False
    assert report["contract"]["safety_claimed"] is False
    assert report["contract"]["holdout_use"] is False
    assert "does not judge source actions" in report["claim_boundary"]


def test_each_action_category_has_declared_minimum_stages_and_hashes():
    report = evaluate(ROOT)
    expected_keys = {
        "category", "public_case_count", "assessed_case_count", "covered_case_count",
        "uncovered_case_count", "required_stages", "coverage_fraction",
        "category_present_in_source_taxonomy",
    }
    assert all(set(row) == expected_keys for row in report["categories"])
    assert all(row["required_stages"] for row in report["categories"])
    assert all(row["covered_case_count"] == row["assessed_case_count"] for row in report["categories"])
    assert report["source"]["action_evidence_source_hash_matches"] is True
    assert all(len(value) == 64 for value in report["source"]["hashes"].values())
