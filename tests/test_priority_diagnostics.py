from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_priority_diagnostics import (  # noqa: E402
    DEFAULT_DIAGNOSTICS,
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
