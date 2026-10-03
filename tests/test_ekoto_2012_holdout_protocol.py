from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "ekoto_2012_holdout_protocol.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_ekoto_protocol_locks_code_before_curve_access():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == "endpoints_and_code_frozen_before_numerical_curve_access"
    assert protocol["known_before_freeze"]["numerical_curve_coordinates_accessed"] is False
    assert protocol["known_before_freeze"]["target_model_predictions_computed"] is False
    assert _sha256(ROOT / protocol["locked_model"]["path"]) == protocol["locked_model"]["sha256"]
    assert _sha256(ROOT / protocol["locked_runner"]["path"]) == protocol["locked_runner"]["sha256"]


def test_ekoto_protocol_requires_all_three_screens():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    endpoints = protocol["primary_endpoints"]
    assert protocol["eligibility"]["minimum_unique_points"] == 15
    assert endpoints["mass_flow_nrmse_percent_peak_measured"]["maximum"] == 15.0
    assert endpoints["median_absolute_percentage_error_percent"]["maximum"] == 20.0
    assert endpoints["half_peak_time_relative_error_percent"]["maximum"] == 20.0
    assert protocol["aggregate_decision"]["claim_supported"] == "all three primary endpoint screens pass"
