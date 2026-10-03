from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "schefer_2007_holdout_protocol.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_schefer_2007_protocol_locks_code_before_curve_access():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == "endpoints_and_code_frozen_before_numerical_curve_access"
    assert protocol["known_before_freeze"]["numerical_curve_coordinates_accessed"] is False
    assert protocol["known_before_freeze"]["target_model_predictions_computed"] is False
    assert _sha256(ROOT / protocol["locked_model"]["path"]) == protocol["locked_model"]["sha256"]
    assert _sha256(ROOT / protocol["locked_runner"]["path"]) == protocol["locked_runner"]["sha256"]


def test_schefer_2007_protocol_requires_all_screens():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    endpoints = protocol["primary_endpoints"]
    assert protocol["eligibility"]["minimum_unique_points"] == 15
    assert endpoints["pressure_nrmse_percent_initial_measured"]["maximum"] == 10.0
    assert endpoints["median_absolute_percentage_error_percent"]["maximum"] == 15.0
    assert endpoints["half_pressure_time_relative_error_percent"]["maximum"] == 20.0
    assert protocol["aggregate_decision"]["claim_supported"] == "all three primary endpoint screens pass"
