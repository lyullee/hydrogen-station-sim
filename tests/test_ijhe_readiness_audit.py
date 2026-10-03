from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_ijhe_readiness import audit  # noqa: E402


def test_current_evidence_audit_passes_verified_components_and_blocks_completion():
    report = audit(ROOT)
    gates = {item["id"]: item for item in report["gates"]}

    assert gates["tank_external_validation"]["status"] == "PASS"
    assert gates["hyram_adapter_verification"]["status"] == "PASS"
    assert gates["preoutcome_design_sensitivity"]["status"] == "PASS"
    assert gates["full_loop_external_validation"]["status"] == "FAIL"
    assert gates["institutional_ethics_determination"]["status"] == "PENDING"
    assert gates["independent_expert_review_complete"]["status"] == "PENDING"
    assert report["bounded_ijhe_submission_ready"] is False
    assert report["full_user_objective_ready"] is False
    assert report["goal_completion_permitted"] is False


def test_full_objective_gate_is_stricter_than_bounded_submission_gate():
    report = audit(ROOT)
    bounded = set(report["blocking_bounded_submission_gates"])
    full = set(report["blocking_full_objective_gates"])
    assert bounded < full
    assert "full_loop_external_validation" in full - bounded
    assert "station_consequence_geometry_validation" in full - bounded
    assert "saga_effectiveness_and_safety_supported" in full - bounded
