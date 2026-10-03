from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "preslhy_blowdown_validation_protocol.json"


def _protocol() -> dict:
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_preslhy_protocol_is_prospectively_frozen_and_hash_locked():
    protocol = _protocol()

    assert protocol["status"] == "frozen_before_raw_excel_outcome_access"
    assert protocol["source"]["outcomes_accessed_before_freeze"] is False
    assert protocol["frozen_model"]["worktree_dirty_at_freeze"] is False
    assert re.fullmatch(r"[0-9a-f]{40}", protocol["frozen_model"]["git_commit"])
    assert protocol["frozen_model"]["parameter_fitting_permitted"] is False
    assert protocol["frozen_model"]["case_specific_fitting_permitted"] is False
    assert protocol["frozen_model"]["discharge_coefficient"] == 0.8
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", digest)
        for digest in protocol["frozen_model"]["files_sha256"].values()
    )


def test_preslhy_protocol_keeps_claim_boundary_and_negative_results():
    protocol = _protocol()

    boundary = protocol["claim_boundary"].lower()
    assert "does not validate a vehicle-fueling loop" in boundary
    assert "site vent stack" in boundary
    assert "dispersion" in boundary
    assert protocol["aggregate_decision"]["retain_all_eligible_failures"] is True
    assert protocol["aggregate_decision"][
        "minimum_joint_primary_screen_pass_fraction"
    ] == 0.7
    assert protocol["aggregate_decision"]["bootstrap_replicates"] == 10_000
    assert protocol["eligibility"]["minimum_evaluable_cases"] >= 12
    assert protocol["time_alignment"]["evaluation_start_s"] == 0.1
    assert "no dynamic time warping" in protocol["time_alignment"][
        "prediction_mapping"
    ].lower()


def test_preslhy_primary_screens_are_fixed_before_outcome_access():
    protocol = _protocol()
    endpoints = protocol["primary_endpoints"]

    assert endpoints["pressure_nrmse_percent_initial_absolute_pressure"][
        "case_screen_max"
    ] == 10.0
    assert endpoints[
        "time_to_50_percent_initial_gauge_pressure_relative_error_percent"
    ]["case_screen_max"] == 20.0
    assert protocol["sensitivity_only_not_calibration"][
        "discharge_coefficient_values"
    ] == [0.7, 0.8, 0.9]
    assert "cannot replace" in protocol["sensitivity_only_not_calibration"][
        "claim_rule"
    ].lower()
