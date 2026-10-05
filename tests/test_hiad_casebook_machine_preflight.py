import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from preflight_hiad_casebook import preflight  # noqa: E402


def _case(event_id="1"):
    return {
        "event_id": event_id,
        "quality": "2",
        "stratum": "near-miss",
        "input_context": {
            "title": "Compressor event",
            "description": "Observed loss of performance.",
            "physical_effect": "No Hydrogen Release",
            "consequence_nature": "Near miss",
            "sub_application": "HRS",
            "supply_chain_stage": "Hydrogen compression",
            "operational_condition": "NORMAL",
        },
        "references": ["public record"],
        "narrative_action_leakage_review": "PENDING",
        "expert_vignette_approved": "NO",
    }


def test_machine_preflight_passes_without_approving_cases():
    report = preflight({"split": "holdout", "holdout_count": 24, "cases": [_case(str(i)) for i in range(24)]})
    assert report["machine_preflight_pass"] is True
    assert all(check["status"] == "PASS" for check in report["checks"])
    assert report["claim_boundary"]
    assert report["leakage_advisory"]["tier_counts"]["LOW"] == 24
    assert report["leakage_advisory"]["cases_with_forbidden_model_input_keys"] == []


def test_machine_preflight_rejects_approval_marker_or_missing_context():
    case = _case()
    case["expert_vignette_approved"] = "YES"
    case["input_context"]["description"] = ""
    report = preflight({"split": "holdout", "holdout_count": 1, "cases": [case]})
    statuses = {check["id"]: check["status"] for check in report["checks"]}
    assert report["machine_preflight_pass"] is False
    assert statuses["human_gates_remain_unresolved"] == "FAIL"
    assert statuses["required_context_fields_nonempty"] == "FAIL"


def test_machine_preflight_flags_reserved_outcome_fields_without_approving_case():
    case = _case()
    case["input_context"]["response"] = "The system was shut down."
    report = preflight({"split": "holdout", "holdout_count": 24, "cases": [case] * 24})
    statuses = {check["id"]: check["status"] for check in report["checks"]}
    assert report["machine_preflight_pass"] is False
    assert statuses["model_visible_context_has_no_reserved_outcome_fields"] == "FAIL"
    assert report["leakage_advisory"]["cases_with_forbidden_model_input_keys"] == ["1"] * 24
    assert report["leakage_advisory"]["tier_counts"]["HIGH"] == 24
