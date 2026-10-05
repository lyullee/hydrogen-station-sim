from __future__ import annotations

import json
from pathlib import Path

from h2station.controlled_station_replay import (
    TraceMapping,
    apply_recharge_hysteresis,
    fit_station_boundary,
    read_boundary_profile,
)
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario


def test_private_mapping_produces_deidentified_aggregate(tmp_path: Path):
    trace = tmp_path / "private_trace.csv"
    trace.write_text(
        "time,pressure,temp,flow,state\n"
        "0,40,20,0,0\n"
        "1,40.2,20.1,0.1,1\n"
        "2,40.4,20.2,0.2,1\n"
        "3,40.1,20.2,0,0\n",
        encoding="utf-8",
    )
    summary = fit_station_boundary(
        trace,
        TraceMapping(
            time_column="time",
            pressure_columns=(("storage", "pressure"),),
            temperature_columns=(("storage_temperature", "temp"),),
            flow_column="flow",
            state_columns=(("esd", "state"),),
        ),
        stride=1,
    )
    public = summary.to_public_dict()
    assert public["raw_rows_persisted"] is False
    assert public["source_identifiers_published"] is False
    assert "private_trace.csv" not in json.dumps(public)
    assert public["channel_roles"] == [
        "station_pressure", "station_temperature", "mass_flow", "discrete_state"
    ]
    assert summary.recommended_recharge_restart_margin_pa is not None


def test_hysteresis_never_reduces_operator_margin(tmp_path: Path):
    trace = tmp_path / "trace.csv"
    trace.write_text(
        "time,pressure\n0,40\n1,40.1\n2,40.2\n",
        encoding="utf-8",
    )
    summary = fit_station_boundary(
        trace,
        TraceMapping(time_column="time", pressure_columns=(("storage", "pressure"),)),
        stride=1,
    )
    assert apply_recharge_hysteresis(2.0e6, summary) >= 2.0e6


def test_time_column_index_supports_corrupted_export_header(tmp_path: Path):
    trace = tmp_path / "index_time.csv"
    trace.write_text(
        "unreadable_time,pressure,temp,state\n"
        "0,40,20,0\n"
        "1,40.1,21,1\n",
        encoding="utf-8",
    )
    summary = fit_station_boundary(
        trace,
        TraceMapping(
            time_column_index=0,
            pressure_columns=(("storage", "pressure"),),
            temperature_columns=(("storage_temperature", "temp"),),
            state_columns=(("esd", "state"),),
        ),
        stride=1,
    )
    assert summary.median_sample_period_s == 1.0
    assert summary.temperature_median_deg_c == 20.5
    assert summary.state_transition_count == 1


def test_boundary_profile_normalizes_newest_first_trace_in_memory(tmp_path: Path):
    trace = tmp_path / "reverse.csv"
    trace.write_text(
        "time,pressure,temp\n"
        "2,42,22\n"
        "1,41,21\n"
        "0,40,20\n",
        encoding="utf-8",
    )
    profile = read_boundary_profile(
        trace,
        TraceMapping(
            time_column="time",
            pressure_columns=(("storage", "pressure"),),
            temperature_columns=(("storage_temperature", "temp"),),
        ),
    )
    assert profile.time_s == (0.0, 1.0, 2.0)
    assert profile.pressure_pa == (40.0e6, 41.0e6, 42.0e6)
    assert profile.reference_scenario_kwargs()["supply_pressure_profile_pa"][0] == (0.0, 40.0e6)


def test_station_calibration_margin_is_explicitly_injected():
    built = build_reference_scenario(
        ReferenceScenario(
            station_dispatch_pressure_margin_pa=1.4e6,
            station_recharge_hysteresis_pa=1.8e6,
        ),
        UnavailableHyRAMBackend(),
    )
    assert built.station.supervisor.parameters.minimum_dispatch_pressure_margin_pa == 1.4e6
    assert built.station.supervisor.parameters.recharge_pressure_hysteresis_pa == 1.8e6
