from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "schefer_2006_holdout_protocol.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_schefer_protocol_locks_evaluator_runner_and_honest_access_state():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == (
        "endpoints_and_code_frozen_before_numerical_curve_access_with_aggregate_duration_known"
    )
    assert protocol["known_before_freeze"]["numerical_curve_coordinates_accessed"] is False
    assert protocol["known_before_freeze"]["target_model_predictions_computed"] is False
    assert "about 100 s" in protocol["known_before_freeze"][
        "approximate_total_blowdown_duration_from_secondary_descriptions"
    ]
    assert _sha256(ROOT / protocol["locked_model"]["path"]) == protocol["locked_model"]["sha256"]
    assert _sha256(ROOT / protocol["locked_runner"]["path"]) == protocol["locked_runner"]["sha256"]


def test_schefer_protocol_requires_all_three_screens():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["eligibility"]["minimum_unique_points"] == 15
    assert protocol["primary_endpoints"]["mass_flow_nrmse_percent_peak_measured"]["maximum"] == 15.0
    assert protocol["primary_endpoints"]["median_absolute_percentage_error_percent"]["maximum"] == 20.0
    assert protocol["primary_endpoints"]["half_peak_time_relative_error_percent"]["maximum"] == 20.0
    assert protocol["aggregate_decision"]["claim_supported"] == "all three primary endpoint screens pass"
