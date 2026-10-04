from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_khk_local_casebook_playbook_coverage import STAGES, audit  # noqa: E402


def _catalog():
    return {
        "plans": [{"id": "gas_release", **{stage: [stage] for stage in STAGES}}]
    }


def test_local_casebook_contract_requires_mapping_and_all_stages():
    result = audit({"cases": [{"response_plan_candidates": ["gas_release"]}]}, _catalog())
    assert result["aggregate"]["contract_pass"] is True


def test_unknown_or_empty_candidate_fails_contract():
    result = audit({"cases": [
        {"response_plan_candidates": []},
        {"response_plan_candidates": ["missing"]},
    ]}, _catalog())
    assert result["aggregate"]["contract_pass"] is False
    assert result["aggregate"]["unmapped_case_count"] == 1
    assert result["aggregate"]["unknown_plan_reference_count"] == 1


def test_missing_stage_fails_contract():
    catalog = {"plans": [{"id": "gas_release", "recognition": ["ok"]}]}
    result = audit({"cases": [{"response_plan_candidates": ["gas_release"]}]}, catalog)
    assert result["aggregate"]["case_with_missing_stage_count"] == 1
    assert result["aggregate"]["contract_pass"] is False
