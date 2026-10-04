from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit_elvhys_auxiliary_replay import run


ROOT = Path(__file__).resolve().parents[1]


def test_elvhys_pressure_peaking_subset_is_reproducible_and_bounded(tmp_path):
    if not (ROOT / "data/public_validation/raw/elvhys_4_2").is_dir():
        pytest.skip("ELVHYS raw subset is intentionally not mirrored in Git")
    result = run(
        ROOT / "data/public_validation/raw/elvhys_4_2",
        tmp_path / "elvhys_auxiliary_replay.json",
    )
    assert result["status"] == "completed_post_access_auxiliary_replay"
    assert result["evidence_role"] == "public_consequence_auxiliary_provenance_and_replay"
    assert len(result["cases"]) == 3
    assert len(result["file_manifest"]) == 6
    assert all(case["pressure_time"]["monotonic_strict"] for case in result["cases"])
    assert all(case["flow_time"]["monotonic_strict"] for case in result["cases"])
    assert result["claims"]["provenance_integrity_pass"] is True
    assert result["claims"]["predictive_model_validation_permitted"] is False
    assert result["claims"]["full_loop_station_vehicle_validation_permitted"] is False


def test_committed_elvhys_replay_has_same_claim_boundary():
    result = json.loads((ROOT / "research/elvhys_auxiliary_replay.json").read_text(encoding="utf-8"))
    assert result["selection"]["outcomes_accessed_before_freeze"] is True
    assert result["claims"]["predictive_model_validation_permitted"] is False
    assert result["claims"]["full_loop_station_vehicle_validation_permitted"] is False
