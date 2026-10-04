from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research" / "preslhy_blowdown_external_validation.json"
PROTOCOL = ROOT / "research" / "preslhy_blowdown_validation_protocol.json"


def test_archived_preslhy_result_retains_the_frozen_primary_decision():
    result = json.loads(RESULT.read_text(encoding="utf-8"))

    assert result["decision"]["status"] == "PASS"
    assert result["decision"]["claim_supported"] is True
    assert result["eligibility"]["eligible_cases"] == 22
    assert result["eligibility"]["excluded_workbooks"] == 0
    assert result["eligibility"]["minimum_requirements_met"] is True
    assert result["aggregate"]["joint_primary_pass_fraction"] == 8 / 11
    assert result["aggregate"]["claim_threshold"] == 0.7
    assert result["failure_accounting"]["evaluation_error_count"] == 0
    assert result["failure_accounting"]["decision_uses_all_eligible_cases"] is True
    assert sum(case["joint_primary_screen_pass"] for case in result["cases"]) == 16
    failed_errors = [case for case in result["cases"] if case.get("evaluation_error")]
    assert len(failed_errors) == 0


def test_archived_preslhy_result_is_linked_to_current_frozen_protocol():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    digest = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()

    assert result["protocol_sha256"] == digest
    assert {item["name"] for item in result["packages"]} == {
        "PRE3P1A_KIT_D05_300K_DATA.zip",
        "PRE3P1A_KIT_D1_300K_DATA.zip",
        "PRE3P1A_KIT_D2_300K_DATA.zip",
        "PRE3P1A_KIT_D4_300K_DATA.zip",
    }
