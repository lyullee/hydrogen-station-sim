"""Keep current user-facing readiness numbers aligned with the audit ledger."""

from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _counts() -> tuple[str, str]:
    audit = json.loads(
        (ROOT / "research/ijhe_readiness_audit.json").read_text(encoding="utf-8")
    )
    counts = audit["gate_counts"]
    overall = f"{counts['PASS']} PASS"
    overall += f", {counts['FAIL']} FAIL and {counts['PENDING']} PENDING"
    primary = json.loads(
        (ROOT / "research/validation_gap_triage_current.json").read_text(
            encoding="utf-8"
        )
    )["primary_scope"]
    scoped = f"{primary['pass']} PASS"
    scoped += f", {primary['fail']} FAIL and {primary['pending']} PENDING"
    return overall, scoped


def test_current_docs_use_authoritative_readiness_snapshot() -> None:
    overall, scoped = _counts()
    report = re.sub(
        r"\s+",
        " ",
        (ROOT / "docs/TECHNICAL_REPORT.md").read_text(encoding="utf-8"),
    )
    manual = re.sub(
        r"\s+",
        " ",
        (ROOT / "docs/USER_MANUAL.md").read_text(encoding="utf-8"),
    )

    assert overall in report
    assert scoped in report
    assert overall.replace(", ", " · ").replace(" and ", " · ") in manual
    assert scoped.replace(", ", " · ").replace(" and ", " · ") in manual
    assert "bounded IJHE submission readiness" in report
    assert "full user objective" in report


def test_live_manuscript_status_uses_current_regression_and_scope_counts() -> None:
    audit = json.loads(
        (ROOT / "research/ijhe_readiness_audit.json").read_text(encoding="utf-8")
    )
    regression = json.loads(
        (ROOT / "research/full_regression_test_run_2026_10_14.json").read_text(
            encoding="utf-8"
        )
    )
    primary = json.loads(
        (ROOT / "research/validation_gap_triage_current.json").read_text(
            encoding="utf-8"
        )
    )["primary_scope"]
    manuscript = re.sub(
        r"\s+",
        " ",
        (ROOT / "manuscript/submission_readiness.md").read_text(encoding="utf-8"),
    )
    scope_lock = re.sub(
        r"\s+",
        " ",
        (ROOT / "research/PAPER_OBJECTIVE_SCOPE_LOCK_2026_10_12.md").read_text(
            encoding="utf-8"
        ),
    )

    assert (
        f"{regression['tests_passed']:,} tests with 0 failures and 0 skips"
        in manuscript
    )
    assert (
        f"{primary['pass']} PASS · {primary['fail']} FAIL · "
        f"{primary['pending']} PENDING"
        in manuscript
    )
    assert f"{primary['closure_percent']:.1f}% (primary)" in scope_lock
    assert (
        f"{audit['gate_counts']['PASS'] / sum(audit['gate_counts'].values()) * 100:.1f}%"
        in scope_lock
    )


def test_promotional_snapshot_uses_current_integrity_counts() -> None:
    audit = json.loads(
        (ROOT / "research/ijhe_readiness_audit.json").read_text(encoding="utf-8")
    )
    regression = json.loads(
        (ROOT / "research/full_regression_test_run_2026_10_14.json").read_text(
            encoding="utf-8"
        )
    )
    primary = json.loads(
        (ROOT / "research/validation_gap_triage_current.json").read_text(
            encoding="utf-8"
        )
    )["primary_scope"]
    promotion = (ROOT / "docs/PROMOTIONAL_ACCURACY_SNAPSHOT_2026_10_12.md").read_text(
        encoding="utf-8"
    )

    assert f"{regression['tests_passed']:,} passed / 0 failed / 0 skipped" in promotion
    assert f"{primary['pass']} PASS / {primary['total']} = {primary['closure_percent']:.1f}%" in promotion
    counts = audit["gate_counts"]
    overall = sum(counts.values())
    assert (
        f"{counts['PASS']} PASS / {overall} = "
        f"{counts['PASS'] / overall * 100:.1f}%"
    ) in promotion
