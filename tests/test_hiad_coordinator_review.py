from __future__ import annotations

import csv
import copy
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_hiad_coordinator_review.py"
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_hiad_coordinator_review import _maximal_overlap_phrases, _screen  # noqa: E402


def _case() -> dict:
    return {
        "event_id": "401",
        "quality": "3",
        "stratum": "unignited-release",
        "input_context": {
            "title": "Detection of hydrogen release",
            "description": (
                "The safety equipment operated as designed and shut the station down. "
                "The small leak was then located in the hose."
            ),
        },
        "reference_emergency_action": (
            "All safety equipment operated as designed and shut the station down."
        ),
        "reference_lesson_learnt": "Hoses require periodic inspection.",
        "reference_corrective_measures": "Replace the damaged hose.",
    }


def test_exact_overlap_returns_maximal_phrase_without_subphrases():
    phrases = _maximal_overlap_phrases(
        "the system was safely shut down after detection",
        "operators confirmed the system was safely shut down after detection",
    )
    assert phrases == ["the system was safely shut down after detection"]


def test_prescreen_flags_completed_action_and_reference_overlap():
    source = _case()
    before = copy.deepcopy(source)
    result = _screen(source, min_overlap_tokens=4)
    assert result["advisory_tier"] == "HIGH"
    assert result["longest_exact_overlap_tokens"] >= 7
    assert result["possible_completed_action_sentences"]
    assert result["machine_removed_sentence_count"] == 1
    assert result["machine_suggested_description"] == (
        "The small leak was then located in the hose."
    )
    assert result["coordinator_leakage_decision"] == ""
    assert source == before


def test_exact_overlap_without_completed_action_is_retained_for_human_review():
    case = _case()
    case["input_context"]["description"] = "Hoses experience frequent pressure cycles."
    case["reference_lesson_learnt"] = "Hoses experience frequent pressure cycles."
    result = _screen(case, min_overlap_tokens=4)
    item = result["machine_sentence_review"][0]

    assert item["machine_suggestion"] == "RETAIN_WITH_REVIEW"
    assert item["exact_overlap_phrases"] == ["hoses experience frequent pressure cycles"]
    assert result["machine_suggested_description"] == (
        "Hoses experience frequent pressure cycles."
    )


def test_cli_writes_auditable_advisory_package(tmp_path: Path):
    casebook = tmp_path / "casebook.json"
    casebook.write_text(json.dumps({"cases": [_case()]}), encoding="utf-8")
    output = tmp_path / "review"

    subprocess.run(
        [sys.executable, str(SCRIPT), "--casebook", str(casebook), "--output", str(output)],
        check=True,
    )

    manifest = json.loads((output / "prescreen_manifest.json").read_text())
    assert manifest["advisory_only"] is True
    assert manifest["human_review_required_for_every_case"] is True
    assert manifest["case_count"] == 1
    assert manifest["machine_rewrite_suggestion"] == {
        "advisory_only": True,
        "source_casebook_modified": False,
        "cases_with_removed_action_sentences": 1,
        "sentences_suggested_for_removal": 1,
        "cases_without_machine_draft": 0,
    }
    with (output / "coordinator_review.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["coordinator_leakage_decision"] == ""
    assert rows[0]["machine_suggested_description"] == (
        "The small leak was then located in the hose."
    )
    assert rows[0]["machine_sentence_review_json"]
    html = (output / "coordinator_review.html").read_text(encoding="utf-8")
    assert "Automated flags cannot approve" in html
    assert "Coordinator-only reference" in html
    assert "downloadApprovedCasebook" in html
    assert "Every frozen case must be retained and reviewed" in html
    assert "approved_holdout_casebook.json" in html
    assert "expert_vignette_approved = 'YES'" in html
    assert "Machine-suggested description · human review required" in html
    assert "Copy suggestion to editable description" in html
    assert "section.querySelector('.review-confirm').checked = false" in html
    assert "Review progress:" in html
    assert "Next unresolved case" in html
    assert "Save local draft" in html
    assert "localStorage.setItem(storageKey" in html
    assert "restoreDraft();" in html
    assert "caseComplete(section)" in html
