from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research" / "preslhy_e5_1_holdout_result.json"
PROTOCOL = ROOT / "research" / "preslhy_e5_1_holdout_protocol.json"
NOISE_DIAGNOSTIC = ROOT / "research" / "preslhy_e5_measurement_noise_diagnostic_2026_10_05.json"


def test_archived_e5_result_retains_ineligible_negative_decision():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    aggregate = result["primary_ambient"]["aggregate"]

    assert aggregate["cases"] == 3
    assert aggregate["joint_primary_passes"] == 2
    assert aggregate["joint_primary_pass_fraction"] == 2 / 3
    assert aggregate["minimum_requirements_met"] is False
    assert aggregate["claim_supported"] is False
    assert len(result["retained_failures"]) == 3


def test_archived_e5_result_is_linked_to_frozen_protocol():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    digest = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()

    assert result["protocol_sha256"] == digest
    assert protocol["status"] == "fully_frozen_before_numerical_outcome_access"
    assert protocol["outcomes_accessed_before_freeze"] is False


def test_noise_diagnostic_cannot_replace_the_frozen_negative_result():
    diagnostic = json.loads(NOISE_DIAGNOSTIC.read_text(encoding="utf-8"))
    assert diagnostic["status"] == "OUTCOME_INFORMED_MEASUREMENT_NOISE_DIAGNOSTIC_NOT_VALIDATION"
    assert diagnostic["method"]["primary_result_replaced"] is False
    assert diagnostic["method"]["outcome_access_before_diagnostic"] is True
    assert len(diagnostic["cases"]) == 3
    assert all(case["filtered_diagnostic_joint_screen_pass"] for case in diagnostic["cases"])
    assert "cannot close" in diagnostic["interpretation"]["limitation"]
