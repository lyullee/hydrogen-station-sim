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


def test_machine_preflight_rejects_approval_marker_or_missing_context():
    case = _case()
    case["expert_vignette_approved"] = "YES"
    case["input_context"]["description"] = ""
    report = preflight({"split": "holdout", "holdout_count": 1, "cases": [case]})
    statuses = {check["id"]: check["status"] for check in report["checks"]}
    assert report["machine_preflight_pass"] is False
    assert statuses["human_gates_remain_unresolved"] == "FAIL"
    assert statuses["required_context_fields_nonempty"] == "FAIL"
