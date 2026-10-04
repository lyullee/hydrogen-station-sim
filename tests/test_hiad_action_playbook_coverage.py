from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_hiad_action_playbook_coverage import audit  # noqa: E402


def test_public_hiad_action_categories_have_traceable_five_stage_plans():
    report = audit(ROOT)
    aggregate = report["aggregate"]
    assert aggregate["category_count"] == 8
    assert aggregate["covered_category_count"] == 8
    assert aggregate["case_count"] == 34
    assert aggregate["covered_case_count"] == 34
    assert aggregate["contract_pass"] is True
    assert aggregate["missing_plan_ids"] == []
    assert aggregate["incomplete_plan_ids"] == []
    assert "does not judge incident actions" in report["claim_boundary"]
