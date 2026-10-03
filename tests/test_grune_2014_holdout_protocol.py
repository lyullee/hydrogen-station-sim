from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "grune_2014_holdout_protocol.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_grune_protocol_freezes_code_and_discloses_prior_knowledge():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == "endpoints_and_code_frozen_before_numerical_curve_access"
    known = protocol["known_before_freeze"]
    assert known["numerical_curve_coordinates_accessed"] is False
    assert known["target_model_predictions_computed"] is False
    assert "not fully blinded" in known["blinding_limit"]
    assert protocol["locked_model"]["sha256"] == _sha256(
        ROOT / protocol["locked_model"]["path"]
    )
    assert protocol["locked_runner"]["sha256"] == _sha256(
        ROOT / protocol["locked_runner"]["path"]
    )


def test_grune_protocol_requires_all_three_screens_and_retains_failures():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert set(protocol["primary_endpoints"]) == {
        "pressure_nrmse_percent_initial_measured",
        "median_absolute_percentage_error_percent",
        "half_pressure_time_relative_error_percent",
    }
    assert protocol["aggregate_decision"]["claim_supported"] == (
        "all three primary endpoint screens pass"
    )
    assert protocol["aggregate_decision"]["retain_numerical_and_runtime_failures"] is True
