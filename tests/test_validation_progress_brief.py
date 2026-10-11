from __future__ import annotations

import json
from pathlib import Path

from scripts.build_validation_progress_brief import build_brief


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_validation_progress_brief_keeps_bounded_claims_and_negative_holdout() -> None:
    report = build_brief(
        _load("research/data_coverage_summary_2026_10_10.json"),
        _load("research/ijhe_readiness_audit.json"),
        _load("research/local_candidate_full_loop_screen_2026_10_09.json"),
    )

    assert "56,854,143개 행" in report
    assert "0 / 8 통과" in report
    assert "새 full-loop 측정 코호트: **확인되지 않음**" in report
    assert "The synchronized station-to-vehicle data gap is documented as a paper limitation and is no longer a required goal gate." in report
    assert "SAGA" in report


def test_validation_progress_brief_uses_latest_audit_counts() -> None:
    report = build_brief(
        {
            "readiness": {
                "ijhe_gate_counts": {"PASS": 127, "FAIL": 10, "PENDING": 7},
                "bounded_submission_ready": False,
            },
            "validated_or_actionable_now": [],
            "minimum_next_input": {},
        },
        {
            "gate_counts": {"PASS": 128, "FAIL": 10, "PENDING": 7},
            "bounded_ijhe_submission_ready": False,
            "gates": [
                {"id": "full_loop_external_validation", "status": "FAIL"},
                {"id": "institutional_ethics_determination", "status": "PENDING"},
                {"id": "physics", "status": "PASS"},
            ],
        },
        {"coverage_assessment": {"new_full_loop_measured_cohort_found": False}},
    )

    assert "IJHE 내부 게이트: **PASS 128 / FAIL 10 / PENDING 7**" in report
    assert "개정 주 목표 보조 지표: **1 PASS / 0 FAIL / 0 PENDING = 100.0%**" in report
