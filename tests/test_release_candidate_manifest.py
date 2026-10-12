"""Guard the reproducible release-candidate boundary."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_candidate_manifest_matches_repository_and_readiness_ledger() -> None:
    manifest = json.loads(
        (ROOT / "research/release_candidate_manifest_2026_10_12.json").read_text(
            encoding="utf-8"
        )
    )
    audit = json.loads(
        (ROOT / "research/ijhe_readiness_audit.json").read_text(encoding="utf-8")
    )
    source_commit = manifest["validated_source_commit"]
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"],
        cwd=ROOT,
        capture_output=True,
    )

    assert ancestry.returncode == 0
    assert manifest["readiness"]["bounded_ijhe_submission_ready"] is False
    assert manifest["readiness"]["full_user_objective_ready"] is False
    assert manifest["readiness"]["goal_completion_permitted"] is False
    assert manifest["readiness"]["overall_gates"] == {
        "PASS": audit["gate_counts"]["PASS"],
        "FAIL": audit["gate_counts"]["FAIL"],
        "PENDING": audit["gate_counts"]["PENDING"],
        "total": sum(audit["gate_counts"].values()),
    }
    assert len(manifest["known_blockers"]) >= 8
    focus = json.loads(
        (ROOT / manifest["software_evidence"]["local_priority_focus_artifact"]).read_text(
            encoding="utf-8"
        )
    )
    assert focus["status"] == "PASS"
    assert focus["software_checks"]["status"] == "PASS"
    assert focus["readiness_status"] == "BLOCKED"

