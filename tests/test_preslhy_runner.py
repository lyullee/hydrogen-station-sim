from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from scripts import run_preslhy_blowdown_validation as runner


def test_eligible_model_failure_is_retained_as_failed_case(monkeypatch):
    trace = SimpleNamespace(
        case_id="negative-case",
        nozzle_diameter_mm=2.0,
        initial_pressure_pa=15.0e6,
        source_package="PRE3P1A_KIT_D2_300K_DATA.zip",
        source_member="negative-case.xlsx",
        initial_temperature_k=293.15,
        temperature_substituted=False,
        ambient_pressure_substituted=True,
        pressure_unit_interpretation="explicit_absolute",
    )

    def fail(_trace):
        raise RuntimeError("integration failed")

    monkeypatch.setattr(runner, "evaluate_preslhy_trace", fail)
    record = runner._evaluate_or_retain_failure(trace)

    assert record["joint_primary_screen_pass"] is False
    assert record["pressure_screen_pass"] is False
    assert record["half_time_screen_pass"] is False
    assert record["pressure_group"] == "high"
    assert record["evaluation_error"] == "RuntimeError: integration failed"


def test_freeze_integrity_detects_model_byte_change_before_data_access(tmp_path):
    model = tmp_path / "model.py"
    model.write_text("frozen\n", encoding="utf-8")
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    protocol = {
        "frozen_model": {
            "git_commit": "frozen-commit",
            "files_sha256": {"model.py": digest},
        }
    }

    matched = runner._freeze_integrity(tmp_path, protocol)
    assert matched["matches_frozen_model"] is True
    assert matched["mismatches"] == []

    model.write_text("changed after outcome access\n", encoding="utf-8")
    changed = runner._freeze_integrity(tmp_path, protocol)
    assert changed["matches_frozen_model"] is False
    assert changed["mismatches"][0]["path"] == "model.py"


def test_direct_source_checkout_entry_point_fails_closed_without_pythonpath():
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "scripts/run_preslhy_blowdown_validation.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "does not match the prospectively frozen PRESLHY implementation" in (
        completed.stdout + completed.stderr
    )
