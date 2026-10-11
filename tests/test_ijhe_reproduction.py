from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reproduce_ijhe import FOCUSED_TESTS, _decision_snapshot  # noqa: E402


def test_reproduction_route_declares_the_paper_integrity_suite():
    assert "tests/test_ijhe_readiness_audit.py" in FOCUSED_TESTS
    assert "tests/test_ijhe_compile_artifact.py" in FOCUSED_TESTS
    assert "tests/test_ijhe_manuscript_format.py" in FOCUSED_TESTS


def test_decision_snapshot_excludes_generated_timestamp():
    first = {
        "bounded_ijhe_submission_ready": False,
        "full_user_objective_ready": False,
        "goal_completion_permitted": False,
        "gate_counts": {"PASS": 1, "FAIL": 2},
        "blocking_bounded_submission_gates": ["example"],
        "generated_at": "one",
    }
    second = dict(first, generated_at="two")
    assert _decision_snapshot(first) == _decision_snapshot(second)
