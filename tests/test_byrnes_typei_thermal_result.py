from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_byrnes_typei_thermal_prospective import evaluate  # noqa: E402


RESULT = ROOT / "research/byrnes_typei_thermal_prospective_result_2026_10_08.json"


def test_retained_result_invalidates_duplicate_prior_outcome_access() -> None:
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    assert payload["status"] == "completed_invalidated_prospective_attempt"
    assert payload["decision"] == "PROTOCOL_INVALID_PRIOR_OUTCOME_ACCESS"
    assert payload["protocol"]["prior_outcome_access_discovered_after_freeze"] is True
    assert payload["eligibility"]["prior_outcome_access"] is True
    assert payload["protocol"]["selected_files_replaced"] is False
    assert payload["protocol"]["mapping_or_thresholds_changed_after_access"] is False
    assert payload["eligibility"]["resolved_case_count"] == 0
    assert len(payload["eligibility"]["frozen_mapping_failures"]) == 6
    assert payload["model_evaluation"]["executed"] is False
    assert payload["model_evaluation"]["case_specific_fitting_performed"] is False
    assert payload["gate_impact"]["eligible_case_count_contributed"] == 0


def test_local_replay_reproduces_intake_decision_when_quarantine_exists() -> None:
    source = ROOT / "tmp/hyddown-v0.50.0"
    if not source.is_dir():
        return
    replay = evaluate(source)
    committed = json.loads(RESULT.read_text(encoding="utf-8"))
    assert replay["decision"] == committed["decision"]
    assert replay["source"]["files"] == committed["source"]["files"]
    assert replay["eligibility"] == committed["eligibility"]
