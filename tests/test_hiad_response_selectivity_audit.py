from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_hiad_response_selectivity import audit  # noqa: E402


def _row(event_id: str, mentioned: list[str], expected: list[str], answer: str) -> dict:
    matched = sorted(set(mentioned).intersection(expected))
    return {
        "event_id": event_id,
        "mentioned_categories": mentioned,
        "expected_categories": expected,
        "matched_expected_categories": matched,
        "stage_coverage": 0.8,
        "answer": answer,
    }


def test_selectivity_audit_balances_recall_with_non_reference_action_burden():
    expected = ["shutdown", "monitoring"]
    benchmark = {"responses": [{
        **_row("1", ["monitoring"], expected, "Check alarm."),
        "variant": "alarm-only",
    }]}
    guard = {"responses": [
        _row("1", ["shutdown", "monitoring", "repair"], expected,
             "Stop, monitor, inspect and repair."),
    ]}
    result = audit(benchmark, guard, seed=7, replicates=100)
    assert result["cohort"]["reference_evaluable_event_count"] == 1
    assert result["variant_summary"]["saga_linked_guarded"]["reference_recall"] == 1.0
    assert result["variant_summary"]["saga_linked_guarded"][
        "reference_precision"
    ] == 2 / 3
    assert result["variant_summary"]["saga_linked_guarded"][
        "non_reference_category_count"
    ] == 1.0
    assert "does not establish" in result["claim_boundary"]


def test_retained_selectivity_artifact_is_bounded_and_reproducible():
    retained = json.loads(
        (ROOT / "research/hiad_response_selectivity_audit_2026_10_08.json")
        .read_text(encoding="utf-8")
    )
    assert retained["status"] == "COMPLETED_POST_OUTCOME_ROBUSTNESS_AUDIT"
    assert retained["source"]["new_provider_calls"] == 0
    assert retained["source"]["outcomes_known_before_analysis"] is True
    assert retained["cohort"]["retained_event_count"] == 34
    assert retained["cohort"]["reference_evaluable_event_count"] == 33
    assert retained["paired_differences_saga_minus_alarm_only"][
        "reference_f1"
    ]["mean_paired_difference"] > 0
    assert retained["variant_summary"]["saga_linked_guarded"][
        "non_reference_category_count"
    ] > retained["variant_summary"]["alarm_only"][
        "non_reference_category_count"
    ]
