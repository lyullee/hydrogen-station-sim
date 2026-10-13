from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research" / "preslhy_blowdown_external_validation.json"
PROTOCOL = ROOT / "research" / "preslhy_blowdown_validation_protocol.json"
FREEZE_AUDIT = (
    ROOT / "research" / "preslhy_blowdown_freeze_integrity_audit_2026_10_13.json"
)


def test_archived_preslhy_result_is_demoted_to_post_outcome_diagnostic():
    result = json.loads(RESULT.read_text(encoding="utf-8"))

    assert result["decision"]["status"] == "POST_OUTCOME_DIAGNOSTIC_ONLY"
    assert result["decision"]["claim_supported"] is False
    assert result["freeze_integrity"]["prospective_claim_permitted"] is False
    assert result["eligibility"]["eligible_cases"] == 22
    assert result["eligibility"]["excluded_workbooks"] == 0
    assert result["eligibility"]["minimum_requirements_met"] is True
    assert result["aggregate"]["joint_primary_pass_fraction"] == 8 / 11
    assert result["aggregate"]["post_outcome_numerical_rule_met"] is True
    assert result["aggregate"][
        "ambient_direct_aperture_blowdown_claim_supported"
    ] is False
    assert result["aggregate"]["claim_threshold"] == 0.7
    assert result["failure_accounting"]["evaluation_error_count"] == 0
    assert result["failure_accounting"]["decision_uses_all_eligible_cases"] is True
    assert sum(case["joint_primary_screen_pass"] for case in result["cases"]) == 16
    failed_errors = [case for case in result["cases"] if case.get("evaluation_error")]
    assert len(failed_errors) == 0


def test_original_frozen_preslhy_failure_remains_controlling():
    audit = json.loads(FREEZE_AUDIT.read_text(encoding="utf-8"))
    primary = audit["primary_frozen_result"]

    assert audit["status"] == (
        "PRIMARY_FROZEN_RESULT_RETAINED_POST_OUTCOME_RERUN_DEMOTED"
    )
    assert primary["joint_primary_passes"] == 11
    assert primary["aggregate"]["joint_primary_pass_fraction"] == 0.5
    assert primary["aggregate"]["claim_threshold"] == 0.7
    assert primary["claim_supported"] is False
    assert audit["integrity_findings"]["model_changed_after_outcome_access"] is True
    assert audit["runtime_parameter_application"] is False


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
