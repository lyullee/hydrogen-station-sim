from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/hiad_casebook_gate_recheck_2026_10_09.json"


def test_hiad_gate_recheck_is_machine_only_and_privacy_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["status"] == "machine_preflight_pass_human_gates_open"
    assert record["machine_preflight"]["pass"] is True
    assert record["machine_preflight"]["case_count"] == 24
    assert record["privacy"]["raw_case_rows_published"] is False
    assert record["privacy"]["event_identifiers_published"] is False
    assert record["human_gates"]["approved_casebook_freeze"] == "PENDING"
    assert record["human_gates"]["masked_holdout_response_collection"] == "NOT_PERMITTED"


def test_hiad_gate_recheck_does_not_claim_effectiveness() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    boundary = " ".join(record["claim_boundary"])
    assert "effectiveness" in boundary
    assert "publication readiness" in boundary
