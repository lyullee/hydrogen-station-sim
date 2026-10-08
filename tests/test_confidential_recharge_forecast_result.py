from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / (
    "research/confidential_station_recharge_pressure_forecast_holdout_"
    "2026_10_08.json"
)
PROTOCOL = ROOT / (
    "research/confidential_station_recharge_pressure_forecast_protocol_"
    "2026_10_08.json"
)


def test_recharge_forecast_retains_frozen_positive_holdout() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["runner_git_commit"] == "1415a2a"
    assert result["files_read"] == 8
    assert result["sampled_rows"] == 653_442
    assert result["calibration"]["case_count"] == 1_024
    assert result["holdout"]["case_count"] == 394
    combined = result["holdout"]["combined"]
    assert combined["median_absolute_error_mpa"] == 0.055
    assert combined["p90_absolute_error_mpa"] == 0.529255
    assert combined["mae_improvement_over_persistence_fraction"] == 0.718855
    assert all(result["eligibility"].values())
    assert all(result["screens"].values())
    decision = result["decision"]
    assert decision["short_horizon_station_pressure_forecast_supported"] is True
    assert decision["runtime_parameter_application"] is False
    assert decision["vehicle_fill_validation"] is False
    assert decision["full_loop_holdout_eligible"] is False
    assert result["protocol"]["protocol_sha256"] == hashlib.sha256(
        PROTOCOL.read_bytes()
    ).hexdigest()


def test_recharge_forecast_result_has_no_private_source_surface() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    for key in (
        "source_identifiers_published",
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "raw_rows_persisted",
        "absolute_timestamps_published",
        "calendar_dates_published",
        "tag_names_published",
        "manufacturer_or_model_published",
    ):
        assert result[key] is False
    assert re.search(r"[A-Za-z]:\\\\", json.dumps(result, ensure_ascii=False)) is None
