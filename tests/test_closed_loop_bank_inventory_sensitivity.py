from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_bank_inventory_sensitivity_is_reproducible_and_claim_bounded() -> None:
    record = json.loads(
        (ROOT / "research/closed_loop_bank_inventory_sensitivity_2026_10_08.json")
        .read_text(encoding="utf-8")
    )

    assert record["status"] == "POST_OUTCOME_DIAGNOSTIC_ONLY"
    assert record["source_worktree_dirty"] is False
    assert record["design"]["parameter_search"] is False
    assert record["design"]["outcomes_previously_inspected"] is True
    assert record["production_default_changed"] is False
    assert record["validation_gate_effect"] == "none"
    assert record["baseline"]["aggregate"]["screening_pass_count"] == 2
    assert record["alternative"]["aggregate"]["screening_pass_count"] == 6

    result = ROOT / record["alternative"]["artifact"]
    assert hashlib.sha256(result.read_bytes()).hexdigest() == record["alternative"]["sha256"]
    result_payload = json.loads(result.read_text(encoding="utf-8"))
    assert result_payload["source_worktree_dirty"] is False
    assert result_payload["source_commit"] == record["source_commit"]
    assert result_payload["bank_internal_volume_m3"] == [5.0, 5.0, 5.0]

    # None of the paired mean changes is confirmatory on only 11 inspected cases.
    for metric in record["paired_change_alternative_minus_baseline"].values():
        lower, upper = metric["bootstrap_95_ci"]
        assert lower <= 0.0 <= upper
