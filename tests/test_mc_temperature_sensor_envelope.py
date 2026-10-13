from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.run_mc_temperature_sensor_envelope_diagnostic import (
    sensor_envelope_metrics,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/mc_temperature_sensor_envelope_2026_10_14.json"


def test_sensor_envelope_metric_is_zero_inside_and_distance_outside() -> None:
    sensors = np.asarray([[10.0, 20.0, 30.0], [12.0, 22.0, 32.0]])
    result = sensor_envelope_metrics(
        np.asarray([11.0, 25.0, 28.0]), sensors
    )
    assert result["sample_count"] == 3
    assert result["sensor_channel_count"] == 2
    assert result["inside_envelope_fraction"] == pytest.approx(1.0 / 3.0)
    assert result["envelope_mae_c"] == pytest.approx(5.0 / 3.0)
    assert result["envelope_rmse_c"] == pytest.approx(np.sqrt(13.0 / 3.0))


def test_committed_sensor_envelope_result_preserves_claim_boundary() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["artifact_type"] == "mc_temperature_sensor_envelope_diagnostic"
    assert result["post_outcome"] is True
    assert result["external_validation"] is False
    assert result["prospective_validation"] is False
    assert result["observation_operator_selection_performed"] is False
    assert result["runtime_parameter_changed"] is False
    assert result["validation_gate_changed"] is False
    assert result["promotion_to_validation_prohibited"] is True
    assert result["raw_experimental_rows_persisted"] is False
    assert len(result["cases"]) == 8
    assert all(
        case["training_case_count"] == 7
        and case["held_out_case_used_for_geometry_fit"] is False
        for case in result["cases"]
    )
