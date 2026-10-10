from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_priority_focus import _select_checks  # noqa: E402


def test_focus_selects_highest_priority_software_checks_first() -> None:
    assert {check.priority for check in _select_checks("P0")} == {"P0"}
    assert {check.priority for check in _select_checks("P1")} == {"P1"}
    assert {check.priority for check in _select_checks("critical")} == {"P0", "P1"}
    assert len(_select_checks("all")) > len(_select_checks("P0"))
