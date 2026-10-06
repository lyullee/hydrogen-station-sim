from __future__ import annotations

import json
from pathlib import Path

import pytest

from h2station.controlled_station_replay import TraceMapping
from h2station.station_dynamics_calibration import (
    summarize_recharge_dynamics,
    validate_recharge_dynamics_temporal_holdout,
)


def _mapping() -> TraceMapping:
    return TraceMapping(
        time_column="time",
        pressure_columns=(
            ("medium_storage_pressure", "medium"),
            ("high_storage_pressure", "high"),
        ),
        state_columns=(("compressor_load", "load"),),
    )


def test_recharge_dynamics_uses_attested_state_cycles_and_never_exports_columns(tmp_path: Path):
    trace = tmp_path / "private_trace.csv"
    trace.write_text(
        "time,medium,high,load\n"
        "0,60,85,IDLE\n"
        "10,60,85,ON\n"
        "20,61,86,ON\n"
        "30,62,87,ON\n"
        "40,62,87,IDLE\n"
        "50,62,87,IDLE\n"
        "60,62,87,ON\n"
        "70,63,88,ON\n",
        encoding="utf-8",
    )
    summary = summarize_recharge_dynamics(
        trace,
        _mapping(),
        compressor_state_role="compressor_load",
        active_state_values=("on",),
        bank_by_pressure_role={
            "medium_storage_pressure": "medium",
            "high_storage_pressure": "high",
        },
        pressure_semantics_attested=True,
        state_semantics_attested=True,
    )
    public = summary.to_public_dict()
    assert public["source_identifiers_published"] is False
    assert public["recommended_minimum_recharge_off_time_s"] == pytest.approx(20.0)
    assert public["state_transition_count"] == 3
    assert public["bank_profiles"][0]["bank"] == "medium"
    assert public["bank_profiles"][0]["positive_active_ramp_median_pa_s"] == pytest.approx(100_000.0)
    assert "medium,high,load" not in json.dumps(public)
    assert "private_trace.csv" not in json.dumps(public)


def test_recharge_dynamics_requires_explicit_custodian_attestations(tmp_path: Path):
    trace = tmp_path / "trace.csv"
    trace.write_text("time,medium,high,load\n0,60,85,IDLE\n1,61,86,ON\n", encoding="utf-8")
    with pytest.raises(ValueError, match="pressure semantics"):
        summarize_recharge_dynamics(
            trace, _mapping(), compressor_state_role="compressor_load",
            active_state_values=("ON",),
            bank_by_pressure_role={"medium_storage_pressure": "medium"},
            pressure_semantics_attested=False,
            state_semantics_attested=True,
        )
    with pytest.raises(ValueError, match="compressor-state semantics"):
        summarize_recharge_dynamics(
            trace, _mapping(), compressor_state_role="compressor_load",
            active_state_values=("ON",),
            bank_by_pressure_role={"medium_storage_pressure": "medium"},
            pressure_semantics_attested=True,
            state_semantics_attested=False,
        )


def test_temporal_holdout_checks_later_completed_off_windows(tmp_path: Path):
    trace = tmp_path / "trace.csv"
    rows = ["time,medium,high,load"]
    for index in range(20):
        state = "ON" if index % 2 == 0 else "IDLE"
        rows.append(f"{index * 10},{60 + index},{85 + index},{state}")
    trace.write_text("\n".join(rows) + "\n", encoding="utf-8")

    result = validate_recharge_dynamics_temporal_holdout(
        trace,
        _mapping(),
        compressor_state_role="compressor_load",
        active_state_values=("ON",),
        bank_by_pressure_role={
            "medium_storage_pressure": "medium",
            "high_storage_pressure": "high",
        },
        pressure_semantics_attested=True,
        state_semantics_attested=True,
        calibration_fraction=0.5,
    )

    assert result.calibration.recommended_minimum_recharge_off_time_s == pytest.approx(10.0)
    assert result.holdout_completed_off_to_on_intervals == 4
    assert result.holdout_minimum_off_to_on_s == pytest.approx(10.0)
    assert result.dwell_consistent is True
