from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "preslhy_e5_1_holdout_protocol.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_e5_protocol_precedes_archive_access_and_locks_model():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["outcomes_accessed_before_freeze"] is False
    assert protocol["source"]["numerical_archive_accessed_before_freeze"] is False
    module = ROOT / protocol["locked_model"]["module"]
    assert _sha256(module) == protocol["locked_model"]["sha256"]
    assert protocol["locked_model"]["parameter_changes_after_freeze"].startswith(
        "prohibited"
    )
    locked = protocol["locked_evaluation_implementation"]
    for key in ("adapter", "runner", "acquisition"):
        item = locked[key]
        assert _sha256(ROOT / item["path"]) == item["sha256"]
    amendment = protocol["amendments"][0]
    assert amendment["archive_structure_accessed"] is True
    assert amendment["numerical_pressure_values_accessed"] is False
    assert amendment["model_outcomes_computed"] is False


def test_e5_protocol_has_eligibility_screens_and_negative_policy():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    eligibility = protocol["eligibility"]
    assert eligibility["minimum_primary_cases"] >= 4
    assert eligibility["minimum_nozzle_diameter_groups"] >= 2
    assert eligibility["minimum_initial_pressure_groups"] >= 2
    endpoints = protocol["primary_endpoints"]
    assert endpoints["pressure_nrmse_percent_initial_absolute_pressure"][
        "case_screen_max"
    ] == 10.0
    assert endpoints[
        "time_to_50_percent_initial_gauge_pressure_relative_error_percent"
    ]["case_screen_max"] == 20.0
    aggregate = protocol["aggregate_decision"]
    assert aggregate["minimum_joint_primary_screen_pass_fraction"] == 0.7
    assert "prohibits" in aggregate["negative_result_policy"]


def test_e5_protocol_keeps_ignition_data_in_primary_trace():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert "complete" in protocol["ignition_policy"]["primary_trace_window"]
    assert "post-ignition" in protocol["ignition_policy"]["primary_trace_window"]
