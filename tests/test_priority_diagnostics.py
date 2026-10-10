from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_priority_diagnostics import (  # noqa: E402
    DEFAULT_DIAGNOSTICS,
    _readiness_status,
    _scientific_screen,
    select_diagnostics,
)


def test_priority_diagnostics_have_parallel_p0_and_p1_tracks() -> None:
    assert {item.priority for item in DEFAULT_DIAGNOSTICS} == {"P0", "P1"}
    assert select_diagnostics(DEFAULT_DIAGNOSTICS, "P0")
    assert select_diagnostics(DEFAULT_DIAGNOSTICS, "P1")
    assert {item.priority for item in select_diagnostics(DEFAULT_DIAGNOSTICS, "critical")} == {"P0", "P1"}
    assert len(select_diagnostics(DEFAULT_DIAGNOSTICS, "all")) == len(DEFAULT_DIAGNOSTICS)


def test_diagnostic_scripts_are_repository_relative() -> None:
    for item in DEFAULT_DIAGNOSTICS:
        assert item.script.startswith("scripts/")
        assert item.script.endswith(".py")
        assert item.output_argument is True


def test_scientific_screen_is_separate_from_process_completion() -> None:
    failed = _scientific_screen(
        {"case_count": 8, "joint_screening_pass_fraction": 0.0}
    )
    assert failed["status"] == "FAIL"
    passed = _scientific_screen(
        {
            "case_count": 8,
            "aggregate": {"soc_definition_screen_pass_count": 8},
        }
    )
    assert passed["status"] == "PASS"
    assert _scientific_screen(
        {"cases": [{"joint_primary_screen_pass": True}, {"joint_primary_screen_pass": False}]}
    )["status"] == "FAIL"
    assert _scientific_screen({"case_count": 8})["status"] == "NOT_REPORTED"
    nrel_negative = _scientific_screen(
        {"tank_count": 7, "screening_pass_count": 0, "screening_pass_fraction": 0.0}
    )
    assert nrel_negative["status"] == "FAIL"
    assert nrel_negative["case_count"] == 7


def test_readiness_status_does_not_promote_negative_or_missing_science() -> None:
    assert _readiness_status("PASS", "FAIL") == "BLOCKED"
    assert _readiness_status("PASS", "NOT_REPORTED") == "NOT_ASSESSED"
    assert _readiness_status("FAIL", "PASS") == "FAIL"
    assert _readiness_status("PASS", "PASS") == "PASS"
