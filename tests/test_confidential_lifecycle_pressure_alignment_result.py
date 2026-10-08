from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / (
    "research/confidential_station_lifecycle_pressure_alignment_holdout_"
    "2026_10_09.json"
)
PROTOCOL = ROOT / (
    "research/confidential_station_lifecycle_pressure_alignment_protocol_"
    "2026_10_08.json"
)


def test_lifecycle_pressure_alignment_retains_frozen_negative_holdout() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["runner_git_commit"] == "7af51ce"
    assert result["files"] == {
        "pressure_files_read": 12,
        "counter_files_read": 12,
        "exact_duplicate_files_excluded": 1,
    }
    assert result["rows"]["pressure_rows_read"] == 29_361_281
    assert result["rows"]["counter_rows_read"] == 26_839_420
    assert result["counter_quality"]["negative_chronological_steps"] == 2
    assert result["calibration"]["combined"]["counter_event_recall"] == 0.170591
    holdout = result["holdout"]["combined"]
    assert holdout["counter_event_recall"] == 0.196032
    assert holdout["pressure_event_precision"] == 0.902716
    assert holdout["absolute_time_offset_s"]["median"] == 26.0
    assert result["eligibility"]["counter_monotonicity_met"] is False
    assert result["screens"]["holdout_counter_recall_met"] is False
    assert result["screens"]["recall_stability_met"] is False
    decision = result["decision"]
    assert decision["pressure_completion_counter_alignment_supported"] is False
    assert decision["recharge_event_detector_corroborated"] is False
    for key in (
        "runtime_parameter_application",
        "default_model_parameters_changed",
        "vehicle_fill_validation",
        "full_loop_holdout_eligible",
        "independent_external_validation",
    ):
        assert decision[key] is False
    assert result["protocol"]["protocol_sha256"] == hashlib.sha256(
        PROTOCOL.read_bytes()
    ).hexdigest()


def test_lifecycle_pressure_alignment_result_has_no_private_source_surface() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert all(value is False for value in result["privacy"].values())
    serialized = json.dumps(result, ensure_ascii=False)
    assert re.search(r"[A-Za-z]:\\\\", serialized) is None
    assert "source_path" not in result
    assert "source_filename" not in result
    assert "absolute_timestamp" not in result
