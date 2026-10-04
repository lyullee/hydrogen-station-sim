from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("h5py")

from scripts.audit_thermal_effects_ignited_release import EXPECTED, run


ROOT = Path(__file__).resolve().parents[1]


def test_committed_thermal_effect_record_keeps_all_cases_and_claim_boundary():
    result = json.loads(
        (ROOT / "research/thermal_effects_ignited_release_result_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["status"] == "postfreeze_descriptive_consequence_replay_complete"
    assert result["case_count"] == len(EXPECTED) == 8
    assert [case["file"] for case in result["cases"]] == EXPECTED
    assert all(len(case["sha256"]) == 64 for case in result["cases"])
    assert all(not case["required_channel_missing"] for case in result["cases"] if case["file"] != "Exp_00003.mat")
    assert result["cases"][2]["required_channel_missing"] == {}
    assert "not predictive" in result["claim_boundary"]
    assert "full-loop" in result["claim_boundary"]


def test_thermal_runner_replays_local_external_archive_when_available(tmp_path):
    raw = ROOT / "tmp/thermal_probe"
    if not raw.is_dir() or not all((raw / name).is_file() for name in EXPECTED):
        pytest.skip("The external USN MAT archive is intentionally not mirrored in Git")
    result = run(raw, tmp_path / "thermal.json")
    assert result["status"] == "postfreeze_descriptive_consequence_replay_complete"
    assert result["case_count"] == 8
    assert all(case["timebase"]["MFM"]["monotonic_strict"] for case in result["cases"])
    assert all(case["release_window"]["sample_count"] > 0 for case in result["cases"])
