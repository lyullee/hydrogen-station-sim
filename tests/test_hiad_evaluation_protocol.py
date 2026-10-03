from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_hiad_decision_evaluation as evaluation  # noqa: E402
from run_hiad_decision_evaluation import _response_payload  # noqa: E402


def _case() -> dict:
    return {
        "event_id": "401",
        "title": "Hose release",
        "description": "Hydrogen was released during filling.",
        "initiating_system": "Dispenser",
        "physical_effect": "Release",
        "consequence_nature": "Leak",
        "sub_application": "Road vehicle",
        "supply_chain_stage": "Distribution",
        "operational_condition": "Fuelling",
    }


def test_direct_and_standards_rag_variants_use_separate_saga_contracts():
    direct = _response_payload("saga-linked", _case(), "groq")
    rag = _response_payload("saga-standards-rag", _case(), "groq")

    assert direct["request_kind"] == "user_query"
    assert "context" in direct and "mode" not in direct
    assert rag["mode"] == "rag"
    assert rag["knowledge_mode"] == "standards"
    assert "Hose release" in rag["message"]
    json.dumps(rag)


def test_failed_provider_call_is_retained_in_blinded_scoring(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    case = {
        **_case(),
        "quality": "complete",
        "emergency_action": "Isolate the dispenser.",
        "lesson_learnt": "Verify hose integrity.",
        "corrective_measures": "Replace the hose.",
        "references": [],
    }
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text(json.dumps(case) + "\n", encoding="utf-8")
    approved_context = evaluation._context(case)["historical_observation"]
    approved_context["description"] = "Leakage-reviewed observation."
    approved_path = tmp_path / "approved.json"
    approved_path.write_text(json.dumps({"cases": [{
        "event_id": "401",
        "quality": "complete",
        "stratum": "unignited-release",
        "input_context": approved_context,
        "reference_emergency_action": case["emergency_action"],
        "reference_lesson_learnt": case["lesson_learnt"],
        "reference_corrective_measures": case["corrective_measures"],
        "references": [],
        "narrative_action_leakage_review": "PASS",
        "expert_vignette_approved": "YES",
    }]}), encoding="utf-8")
    output = tmp_path / "result"

    observed_payloads = []

    def fail(_url, payload, _timeout):
        observed_payloads.append(payload)
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(evaluation, "_post", fail)
    monkeypatch.setattr(sys, "argv", [
        "run_hiad_decision_evaluation.py",
        "--cases", str(cases_path),
        "--split", "development",
        "--approved-casebook", str(approved_path),
        "--saga-url", "http://example.invalid",
        "--repeats", "1",
        "--output", str(output),
    ])
    with pytest.raises(SystemExit, match="1 failed SAGA calls"):
        evaluation.main()

    with (output / "allocation_key.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    failed = next(row for row in rows if row["variant"] == "saga-linked")
    assert failed["call_failed"] == "True"
    assert failed["answer"].startswith("[PROVIDER CALL FAILED")
    manifest = json.loads((output / "collection_manifest.json").read_text())
    assert manifest["response_count"] == manifest["expected_response_count"] == 2
    assert manifest["failed_calls_retained_for_blinded_scoring"] is True
    assert (
        observed_payloads[0]["context"]["historical_observation"]["description"]
        == "Leakage-reviewed observation."
    )


def test_approved_vignette_replaces_every_model_visible_field():
    raw = _case()
    approved_context = {
        field: f"approved-{field}" for field in evaluation.CONTEXT_FIELDS
    }

    result = evaluation._apply_approved_vignette(
        raw, {"input_context": approved_context}
    )

    assert all(result[field] == approved_context[field] for field in approved_context)
    assert result["event_id"] == raw["event_id"]


def test_approved_vignette_requires_complete_model_context():
    incomplete = evaluation._context(_case())["historical_observation"]
    del incomplete["description"]

    with pytest.raises(SystemExit, match="missing input_context fields: description"):
        evaluation._apply_approved_vignette(
            _case(), {"input_context": incomplete}
        )


def test_collection_rejects_casebook_that_omits_frozen_split_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cases = []
    for event_id in ("401", "402"):
        cases.append({
            **_case(),
            "event_id": event_id,
            "quality": "complete",
            "emergency_action": "Isolate the dispenser.",
            "lesson_learnt": "Verify hose integrity.",
            "corrective_measures": "Replace the hose.",
            "references": [],
        })
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text(
        "".join(json.dumps(case) + "\n" for case in cases), encoding="utf-8"
    )
    approved_path = tmp_path / "approved.json"
    approved_path.write_text(json.dumps({"cases": []}), encoding="utf-8")

    monkeypatch.setattr(sys, "argv", [
        "run_hiad_decision_evaluation.py",
        "--cases", str(cases_path),
        "--split", "development",
        "--approved-casebook", str(approved_path),
        "--saga-url", "http://example.invalid",
        "--output", str(tmp_path / "result"),
    ])

    with pytest.raises(SystemExit, match="omitted frozen split IDs"):
        evaluation.main()


def test_holdout_collection_requires_casebook_freeze_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cases = []
    for event_id in ("401", "402"):
        cases.append({
            **_case(),
            "event_id": event_id,
            "quality": "complete",
            "emergency_action": "Isolate the dispenser.",
            "lesson_learnt": "Verify hose integrity.",
            "corrective_measures": "Replace the hose.",
            "references": [],
        })
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text(
        "".join(json.dumps(case) + "\n" for case in cases), encoding="utf-8"
    )
    holdout_case = evaluation._split(cases)["holdout"][0]
    approved_path = tmp_path / "approved.json"
    approved_path.write_text(json.dumps({"cases": [{
        "event_id": holdout_case["event_id"],
        "input_context": evaluation._context(holdout_case)["historical_observation"],
        "narrative_action_leakage_review": "PASS",
        "expert_vignette_approved": "YES",
    }]}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "run_hiad_decision_evaluation.py",
        "--cases", str(cases_path),
        "--split", "holdout",
        "--approved-casebook", str(approved_path),
        "--saga-url", "http://example.invalid",
        "--output", str(tmp_path / "result"),
    ])

    with pytest.raises(SystemExit, match="casebook-freeze-manifest is required"):
        evaluation.main()
