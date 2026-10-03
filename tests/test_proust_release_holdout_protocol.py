from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "proust_release_holdout_protocol.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_proust_protocol_precedes_numerical_figure_access_and_locks_code():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == "fully_frozen_before_numerical_figure_outcome_access"
    assert protocol["numerical_figure_outcomes_accessed_before_freeze"] is False
    assert protocol["source"]["numerical_curve_values_seen_before_freeze"] is False
    assert protocol["access_audit"]["numerical_graph_coordinates_accessed"] is False
    assert protocol["access_audit"]["model_predictions_for_this_campaign_computed"] is False
    assert _sha256(ROOT / protocol["locked_model"]["path"]) == protocol["locked_model"]["sha256"]
    for item in protocol["locked_implementation"].values():
        assert _sha256(ROOT / item["path"]) == item["sha256"]


def test_proust_protocol_prohibits_temperature_substitution_and_requires_three_groups():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["eligibility"]["minimum_primary_series"] == 3
    assert protocol["eligibility"]["minimum_nozzle_diameter_groups"] == 3
    assert "Do not substitute ambient temperature" in protocol["digitization"][
        "missing_temperature_policy"
    ]
    assert protocol["locked_model"]["discharge_coefficient"] == 0.8
