from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "freeze_hiad_approved_casebook.py"
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_hiad_approved_casebook import CONFIRMATION, _validate  # noqa: E402


def _source() -> dict:
    return {
        "source": "HIAD 2.2",
        "split": "holdout",
        "development_count": 1,
        "holdout_count": 1,
        "cases": [{
            "event_id": "401",
            "quality": "3",
            "stratum": "unignited-release",
            "input_context": {
                "title": "Hydrogen release",
                "description": "Hydrogen was detected beside the dispenser.",
                "initiating_system": "Hydrogen system",
                "physical_effect": "Unignited Hydrogen Release",
                "consequence_nature": "Leak no ignition",
                "sub_application": "Hydrogen dispenser",
                "supply_chain_stage": "Hydrogen transfer",
                "operational_condition": "NORMAL",
            },
            "reference_emergency_action": "The station was shut down.",
            "reference_lesson_learnt": "Inspect the hose.",
            "reference_corrective_measures": "Replace the hose.",
            "references": ["public record"],
            "narrative_action_leakage_review": "PENDING",
            "expert_vignette_approved": "NO",
        }],
    }


def _approved(decision: str = "KEEP", notes: str = "") -> dict:
    data = json.loads(json.dumps(_source()))
    data["coordinator_review_metadata"] = {
        "coordinator_code": "C1",
        "all_frozen_cases_retained": True,
    }
    case = data["cases"][0]
    case["narrative_action_leakage_review"] = "PASS"
    case["expert_vignette_approved"] = "YES"
    case["coordinator_review"] = {
        "coordinator_code": "C1",
        "decision": decision,
        "notes": notes,
        "confirmation": CONFIRMATION,
    }
    return data


def test_valid_keep_casebook_passes_freeze_validation():
    changes = _validate(_source(), _approved())
    assert changes[0]["decision"] == "KEEP"
    assert changes[0]["residual_advisory_tier"] == "LOW"


def test_freeze_rejects_missing_frozen_case():
    approved = _approved()
    approved["cases"] = []
    with pytest.raises(SystemExit, match="non-empty cases list"):
        _validate(_source(), approved)


def test_freeze_rejects_change_to_noneditable_model_field():
    approved = _approved()
    approved["cases"][0]["input_context"]["operational_condition"] = "ABNORMAL"
    with pytest.raises(SystemExit, match="changed non-editable model field"):
        _validate(_source(), approved)


def test_freeze_requires_rationale_for_residual_advisory_flag():
    source = _source()
    source["cases"][0]["input_context"]["description"] = "The station was shut down."
    approved = _approved()
    approved["cases"][0]["input_context"]["description"] = "The station was shut down."
    with pytest.raises(SystemExit, match="coordinator rationale is required"):
        _validate(source, approved)


def test_rewrite_must_change_editable_model_text():
    with pytest.raises(SystemExit, match="REWRITE but model text is unchanged"):
        _validate(_source(), _approved(decision="REWRITE"))


def test_cli_writes_frozen_casebook_change_log_and_hash_manifest(tmp_path: Path):
    source_path = tmp_path / "source.json"
    approved_path = tmp_path / "approved.json"
    source_path.write_text(json.dumps(_source()), encoding="utf-8")
    approved_path.write_text(json.dumps(_approved()), encoding="utf-8")
    output = tmp_path / "frozen"

    subprocess.run([
        sys.executable, str(SCRIPT),
        "--source", str(source_path),
        "--approved", str(approved_path),
        "--output", str(output),
    ], check=True, capture_output=True, text=True)

    manifest = json.loads((output / "casebook_freeze_manifest.json").read_text())
    assert manifest["case_count"] == 1
    assert manifest["all_frozen_cases_retained"] is True
    assert manifest["all_cases_approved"] is True
    assert manifest["decision_counts"] == {"KEEP": 1, "REWRITE": 0}
    assert "approved_casebook_submitted.json" in manifest["file_sha256"]
    assert "approved_casebook_frozen.json" in manifest["file_sha256"]
    assert (
        manifest["file_sha256"]["submitted_approved_casebook"]
        == manifest["file_sha256"]["approved_casebook_submitted.json"]
    )
    assert (output / "approved_casebook_submitted.json").is_file()
    assert (output / "casebook_change_log.csv").is_file()
