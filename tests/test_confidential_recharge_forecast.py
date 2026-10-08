from __future__ import annotations

from pathlib import Path

import pytest

from h2station.confidential_recharge_forecast import (
    RechargeForecastRules,
    validate_recharge_pressure_forecast,
)
from h2station.controlled_station_replay import TraceMapping


def _mapping() -> TraceMapping:
    return TraceMapping(
        time_column="time",
        pressure_columns=(
            ("medium_storage_pressure", "medium_secret"),
            ("high_storage_pressure", "high_secret"),
        ),
        state_columns=(("compressor_load", "load_secret"),),
    )


def _write_trace(path: Path, *, offset: float = 0.0) -> None:
    rows = ["time,medium_secret,high_secret,load_secret"]
    medium = 55.0 + offset
    high = 82.0 + offset
    for second in range(800):
        cycle = second // 80
        local = second % 80
        active = local < 60
        if active:
            if cycle % 2 == 0:
                medium += 0.020
                high += 0.002
            else:
                medium += 0.002
                high += 0.030
        rows.append(f"{second},{medium:.6f},{high:.6f},{1 if active else 0}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _relaxed_rules() -> RechargeForecastRules:
    return RechargeForecastRules(
        minimum_matching_files=2,
        minimum_calibration_cases=6,
        minimum_holdout_cases=2,
        minimum_holdout_cases_per_bank=1,
        maximum_holdout_median_absolute_error_mpa=0.10,
        maximum_holdout_p90_absolute_error_mpa=0.10,
        minimum_mae_improvement_over_persistence_fraction=0.80,
        minimum_positive_direction_fraction=0.90,
        maximum_gain_relative_shift=0.10,
    )


def test_forecast_uses_chronological_holdout_and_exports_only_aggregates(tmp_path: Path):
    _write_trace(tmp_path / "private_a.csv")
    _write_trace(tmp_path / "private_b.csv", offset=0.1)
    result = validate_recharge_pressure_forecast(
        tmp_path,
        _mapping(),
        compressor_state_role="compressor_load",
        active_state_values=("1",),
        bank_by_pressure_role={
            "medium_storage_pressure": "medium",
            "high_storage_pressure": "high",
        },
        pressure_semantics_attested=True,
        state_semantics_attested=True,
        rules=_relaxed_rules(),
    )
    assert result["decision"]["short_horizon_station_pressure_forecast_supported"] is True
    assert result["calibration"]["case_count"] >= 6
    assert result["holdout"]["case_count"] >= 2
    assert result["holdout"]["combined"]["median_absolute_error_mpa"] <= 0.10
    serialized = str(result)
    assert "private_a" not in serialized
    assert "medium_secret" not in serialized
    assert result["raw_rows_persisted"] is False
    assert result["decision"]["runtime_parameter_application"] is False


def test_forecast_rejects_missing_attestation(tmp_path: Path):
    _write_trace(tmp_path / "trace.csv")
    with pytest.raises(ValueError, match="pressure semantics"):
        validate_recharge_pressure_forecast(
            tmp_path,
            _mapping(),
            compressor_state_role="compressor_load",
            active_state_values=("1",),
            bank_by_pressure_role={
                "medium_storage_pressure": "medium",
                "high_storage_pressure": "high",
            },
            pressure_semantics_attested=False,
            state_semantics_attested=True,
            rules=_relaxed_rules(),
        )


def test_forecast_requires_both_bank_roles(tmp_path: Path):
    _write_trace(tmp_path / "trace.csv")
    with pytest.raises(ValueError, match="exactly one medium and one high"):
        validate_recharge_pressure_forecast(
            tmp_path,
            _mapping(),
            compressor_state_role="compressor_load",
            active_state_values=("1",),
            bank_by_pressure_role={"medium_storage_pressure": "medium"},
            pressure_semantics_attested=True,
            state_semantics_attested=True,
            rules=_relaxed_rules(),
        )
