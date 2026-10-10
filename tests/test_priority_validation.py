from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_priority_validation import DEFAULT_CHECKS, priority_status  # noqa: E402


def test_priority_status_exposes_p0_before_lower_tracks() -> None:
    status = priority_status()

    assert status["readiness"]["full_user_objective_ready"] is False
    assert status["data_volume_is_primary_blocker"] is False
    assert status["execution_tracks"][0]["priority"] == "P0"
    assert status["execution_tracks"][0]["parallel_track"] == "full_loop_intake_and_scoring"


def test_default_checks_are_focused_and_parallelizable() -> None:
    assert len(DEFAULT_CHECKS) == 3
    assert {check.priority for check in DEFAULT_CHECKS} == {"P0", "P1"}
    assert all("pytest" in check.command for check in DEFAULT_CHECKS)
    assert all("test_" in " ".join(check.command) for check in DEFAULT_CHECKS)
