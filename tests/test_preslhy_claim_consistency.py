from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_preslhy_primary_and_diagnostic_claims_cannot_be_conflated():
    freeze_audit = _json(
        "research/preslhy_blowdown_freeze_integrity_audit_2026_10_13.json"
    )
    diagnostic = _json("research/preslhy_blowdown_external_validation.json")
    readiness = _json("research/ijhe_readiness_audit.json")

    primary = freeze_audit["primary_frozen_result"]
    assert primary["joint_primary_passes"] == 11
    assert primary["aggregate"]["joint_primary_pass_fraction"] == 0.5
    assert primary["claim_supported"] is False
    assert primary["decision"] == "FAIL"

    assert "post-outcome development diagnostic" in diagnostic["evidence_type"]
    assert diagnostic["aggregate"]["joint_primary_pass_fraction"] == 16 / 22
    assert diagnostic["decision"]["claim_supported"] is False
    assert diagnostic["decision"]["status"] == "POST_OUTCOME_DIAGNOSTIC_ONLY"

    gate = next(
        item
        for item in readiness["gates"]
        if item["id"] == "preslhy_blowdown_external_validation"
    )
    assert gate["status"] == "FAIL"
    assert gate["observed"]["aggregate"]["joint_primary_pass_fraction"] == 0.5
    assert gate["observed"]["post_outcome_diagnostic"]["claim_supported"] is False


def test_public_claims_retain_the_original_negative_result():
    manuscript = (ROOT / "manuscript/ijhe_manuscript_draft.tex").read_text(
        encoding="utf-8"
    )
    validation = (ROOT / "docs/PUBLIC_VALIDATION.md").read_text(encoding="utf-8")
    promotion = (
        ROOT / "docs/PROMOTIONAL_ACCURACY_SNAPSHOT_2026_10_12.md"
    ).read_text(encoding="utf-8")

    assert "joint pass fraction of 50.0\\%" in manuscript
    assert "Eleven cases passed both primary screens: 50.0%" in validation
    assert "original frozen PRESLHY ambient\n   blowdown result remains a retained negative result (11/22; 50.0%)" in validation
    assert "최초 동결평가 **11/22, 50.0%**로 기준 미달" in promotion
    assert "**16/22, 72.7%**는 사후 진단" in promotion
