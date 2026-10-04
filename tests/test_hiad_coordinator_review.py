from __future__ import annotations

import csv
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
    result = _screen(_case(), min_overlap_tokens=4)
    assert result["advisory_tier"] == "HIGH"
    assert result["longest_exact_overlap_tokens"] >= 7
    assert result["possible_completed_action_sentences"]


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
    with (output / "coordinator_review.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["coordinator_leakage_decision"] == ""
    html = (output / "coordinator_review.html").read_text(encoding="utf-8")
    assert "Automated flags cannot approve" in html
    assert "Coordinator-only reference" in html
    assert "downloadApprovedCasebook" in html
    assert "Every frozen case must be retained and reviewed" in html
    assert "approved_holdout_casebook.json" in html
    assert "expert_vignette_approved = 'YES'" in html

