from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_submission_readiness_summary_matches_authoritative_decision():
    audit = json.loads((ROOT / "manuscript" / "ijhe_readiness_audit.json").read_text(encoding="utf-8"))
    summary = (ROOT / "manuscript" / "submission_readiness.md").read_text(encoding="utf-8")

    assert "Bounded IJHE submission ready | **False**" in summary
    assert "Full validated-digital-twin objective ready | **False**" in summary
    assert "Goal completion permitted | **False**" in summary
    counts = audit["gate_counts"]
    assert f"{counts['PASS']} PASS · {counts['FAIL']} FAIL · {counts['PENDING']} PENDING" in summary

    for gate_id in audit["blocking_bounded_submission_gates"]:
        assert f"`{gate_id}`" in summary
    for gate_id in audit["blocking_full_objective_gates"]:
        assert f"`{gate_id}`" in summary

    assert "Only `full_user_objective_ready=true`" in summary
    assert "scientific validity" in summary
    assert "acceptance by IJHE" in summary
