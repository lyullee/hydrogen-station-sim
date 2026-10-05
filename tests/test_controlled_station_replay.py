from __future__ import annotations

import json
from pathlib import Path

from h2station.controlled_station_replay import (
    TraceMapping,
    apply_recharge_hysteresis,
    fit_station_boundary,
    fit_station_boundary_profile,
    read_boundary_profile,
    summarize_lifecycle_counters,
    synchronize_station_traces,
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
            authorized_boundary_roles=("station_pressure", "station_temperature"),
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


def test_nonpositive_pressure_sentinels_are_excluded_from_calibration(tmp_path: Path):
    trace = tmp_path / "pressure_sentinel.csv"
    trace.write_text(
        "time,pressure\n"
        "0,-0.020289\n"
        "1,40.0\n"
        "2,40.5\n",
        encoding="utf-8",
    )
    summary = fit_station_boundary(
        trace,
        TraceMapping(
            time_column="time",
            pressure_columns=(("storage", "pressure"),),
        ),
        stride=1,
    )
    assert summary.pressure_min_pa == 40.0e6
    assert "nonpositive_pressure_excluded" in summary.quality_warnings


def test_synchronized_replay_reports_excluded_pressure_sentinels(tmp_path: Path):
    pressure_trace = tmp_path / "pressure.csv"
    pressure_trace.write_text(
        "time,pressure\n"
        "0,-0.020289\n"
        "1,40.0\n"
        "2,40.5\n",
        encoding="utf-8",
    )
    equipment_trace = tmp_path / "equipment.csv"
    equipment_trace.write_text(
        "time,temperature\n"
        "0,20.0\n"
        "1,20.5\n"
        "2,21.0\n",
        encoding="utf-8",
    )
    pressure = TraceMapping(
        time_column="time",
        pressure_columns=(("station", "pressure"),),
        time_is_absolute=True,
    )
    equipment = TraceMapping(
        time_column="time",
        temperature_columns=(("diagnostic", "temperature"),),
        time_is_absolute=True,
    )
    alignment = synchronize_station_traces(
        pressure_trace,
        pressure,
        equipment_trace,
        equipment,
        max_match_gap_s=1.0,
    ).alignment
    assert alignment.synchronized_rows == 2
    assert "nonpositive_pressure_excluded" in alignment.quality_warnings


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
            authorized_boundary_roles=("station_pressure", "station_temperature"),
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
            authorized_boundary_roles=("station_pressure", "station_temperature"),
        ),
    )
    assert profile.time_s == (0.0, 1.0, 2.0)
    assert profile.pressure_pa == (40.0e6, 41.0e6, 42.0e6)
    assert profile.reference_scenario_kwargs()["supply_pressure_profile_pa"][0] == (0.0, 40.0e6)


def test_equipment_temperature_requires_explicit_boundary_attestation():
    try:
        TraceMapping(
            time_column="time",
            temperature_columns=(("compressor", "temp"),),
            temperature_boundary_role="compressor",
        )
    except ValueError as exc:
        assert "authorized_boundary_roles" in str(exc)
    else:
        raise AssertionError("unattested equipment temperatures must remain diagnostic")


def test_lifecycle_summary_is_aggregate_and_does_not_imply_operating_hours(tmp_path: Path):
    trace = tmp_path / "lifecycle.csv"
    trace.write_text(
        "time,hp,mp,temp\n"
        "0,10,20,25\n"
        "1,10,21,26\n"
        "2,11,21,27\n"
        "3,11,20,28\n",
        encoding="utf-8",
    )
    summary = summarize_lifecycle_counters(
        trace,
        TraceMapping(
            time_column="time",
            lifecycle_columns=(("high_bank_cycles", "hp"), ("medium_bank_cycles", "mp")),
        ),
        stride=1,
    )
    public = summary.to_public_dict()
    assert public["raw_rows_persisted"] is False
    assert "lifecycle.csv" not in json.dumps(public)
    assert public["counters"]["high_bank_cycles"]["positive_increment_count"] == 1
    assert public["counters"]["medium_bank_cycles"]["negative_increment_count"] == 1
    assert "operating-hour" in public["claim_boundary"]


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


def test_profile_calibration_can_be_fitted_from_a_calibration_slice_only(tmp_path: Path):
    trace = tmp_path / "boundary_profile.csv"
    trace.write_text("time,pressure\n0,40\n1,40.5\n2,41.0\n", encoding="utf-8")
    profile = read_boundary_profile(
        trace,
        TraceMapping(time_column="time", pressure_columns=(("bank", "pressure"),)),
    )
    summary = fit_station_boundary_profile(profile)
    assert summary.sampled_rows == 3
    assert summary.duration_s == 2.0
    assert summary.recommended_recharge_restart_margin_pa is not None
    assert summary.channel_roles == ("station_pressure",)


def test_synchronization_requires_real_overlap_and_keeps_states_discrete(tmp_path: Path):
    pressure = tmp_path / "pressure.csv"
    equipment = tmp_path / "equipment.csv"
    pressure.write_text(
        "time,pressure\n"
        "2026-01-01T00:00:00Z,40\n"
        "2026-01-01T00:00:01Z,41\n"
        "2026-01-01T00:00:02Z,42\n",
        encoding="utf-8",
    )
    equipment.write_text(
        "time,temp,state\n"
        "2026-01-01T00:00:00Z,20,OFF\n"
        "2026-01-01T00:00:01Z,21,ON\n"
        "2026-01-01T00:00:02Z,22,ON\n",
        encoding="utf-8",
    )
    profile = synchronize_station_traces(
        pressure,
        TraceMapping(
            time_column="time",
            pressure_columns=(("bank", "pressure"),),
            time_format="%Y-%m-%dT%H:%M:%SZ",
        ),
        equipment,
        TraceMapping(
            time_column="time",
            temperature_columns=(("compressor", "temp"),),
            state_columns=(("load", "state"),),
            temperature_boundary_role="compressor",
            authorized_boundary_roles=("compressor",),
            time_format="%Y-%m-%dT%H:%M:%SZ",
        ),
        max_match_gap_s=0.1,
    )
    assert profile.boundary.pressure_pa == (40.0e6, 41.0e6, 42.0e6)
    assert profile.boundary.temperature_k == (293.15, 294.15, 295.15)
    assert profile.state_values == (("load", ("OFF", "ON", "ON")),)
    public = profile.alignment.to_public_dict()
    assert public["raw_rows_persisted"] is False
    assert public["source_identifiers_published"] is False

    diagnostic_only = synchronize_station_traces(
        pressure,
        TraceMapping(
            time_column="time",
            pressure_columns=(("bank", "pressure"),),
            time_format="%Y-%m-%dT%H:%M:%SZ",
        ),
        equipment,
        TraceMapping(
            time_column="time",
            temperature_columns=(("compressor", "temp"),),
            state_columns=(("load", "state"),),
            time_format="%Y-%m-%dT%H:%M:%SZ",
        ),
        max_match_gap_s=0.1,
    )
    assert diagnostic_only.boundary.temperature_k == ()


def test_synchronization_rejects_nonoverlapping_campaigns(tmp_path: Path):
    pressure = tmp_path / "pressure.csv"
    equipment = tmp_path / "equipment.csv"
    pressure.write_text(
        "time,pressure\n2026-01-01T00:00:00Z,40\n2026-01-01T00:00:01Z,41\n",
        encoding="utf-8",
    )
    equipment.write_text(
        "time,temp\n2026-01-02T00:00:00Z,20\n2026-01-02T00:00:01Z,21\n",
        encoding="utf-8",
    )
    try:
        synchronize_station_traces(
            pressure,
            TraceMapping(
                time_column="time",
                pressure_columns=(("bank", "pressure"),),
                time_format="%Y-%m-%dT%H:%M:%SZ",
            ),
            equipment,
            TraceMapping(
                time_column="time",
                temperature_columns=(("compressor", "temp"),),
                time_format="%Y-%m-%dT%H:%M:%SZ",
            ),
        )
    except ValueError as exc:
        assert "do not overlap" in str(exc)
    else:
        raise AssertionError("non-overlapping logger campaigns must not be aligned")
