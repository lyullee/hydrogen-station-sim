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
