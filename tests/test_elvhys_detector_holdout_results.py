from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_both_prospective_elvhys_intake_failures_are_retained():
    v1 = _json("research/elvhys_detector_holdout_result_2026_10_07.json")
    v2 = _json("research/elvhys_detector_holdout_result_v2_2026_10_07.json")

    assert v1["status"] == "FAIL"
    assert v1["retained_failure"] is True
    assert v1["primary_contract_pass"] is False
    assert v1["protocol"]["sha256"] == _sha256(v1["protocol"]["path"])

    assert v2["status"] == "FAIL"
    assert v2["retained_failure"] is True
    assert v2["primary_contract_pass"] is False
    assert v2["protocol"]["outcomes_accessed_before_freeze"] is False
    assert v2["protocol"]["sha256"] == _sha256(v2["protocol"]["path"])
    assert v2["execution"]["failure_encountered_at_test_id"] == 44


def test_post_failure_diagnostic_keeps_the_failed_case_in_the_cohort():
    diagnostic = _json(
        "research/elvhys_detector_intake_diagnostic_2026_10_08.json"
    )
    aggregate = diagnostic["aggregate"]
    cases = diagnostic["cases"]

    assert diagnostic["outcome_informed"] is True
    assert diagnostic["eligible_as_confirmatory_validation"] is False
    assert aggregate["selected_case_count"] == 15
    assert aggregate["baseline_eligible_case_count"] == 14
    assert aggregate["baseline_ineligible_case_count"] == 1
    assert aggregate["failed_case_ids"] == [44]
    assert aggregate["case_exclusion_permitted"] is False
    assert len(cases) == 15
    failed = [case for case in cases if not case["case_baseline_eligible"]]
    assert [case["test_id"] for case in failed] == [44]
    assert failed[0]["available_pre_guard_rows"] == 0
