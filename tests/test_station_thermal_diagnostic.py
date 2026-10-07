from __future__ import annotations

import json
from pathlib import Path

import pytest

from h2station.controlled_station_replay import TraceMapping
from h2station.station_thermal_diagnostic import (
    summarize_station_thermal_dynamics,
    validate_station_thermal_temporal_stability,
)


def _mapping() -> TraceMapping:
    return TraceMapping(
        time_column="secret_time",
        temperature_columns=(
            ("compressor_temperature", "secret_comp"),
            ("cooler_inlet_temperature", "secret_in"),
            ("cooler_outlet_temperature", "secret_out"),
        ),
        state_columns=(("cooling_run", "secret_state"),),
    )


def _trace(path: Path, rows: int = 40) -> None:
    values = ["secret_time,secret_comp,secret_in,secret_out,secret_state"]
    for index in range(rows):
        active = 1 if index % 4 in {1, 2} else 0
        inlet = -20.0 if active else 5.0
        outlet = -30.0 if active else 4.0
        values.append(f"{index},{30 + (index % 10) * 0.01},{inlet},{outlet},{active}")
    path.write_text("\n".join(values) + "\n", encoding="utf-8")


def _kwargs() -> dict[str, object]:
    return {
        "cooling_state_role": "cooling_run",
        "cooling_active_state_values": ("1",),
        "component_by_temperature_role": {
            "compressor_temperature": "compressor",
            "cooler_inlet_temperature": "cooler_inlet",
            "cooler_outlet_temperature": "cooler_outlet",
        },
        "temperature_semantics_attested": True,
        "state_semantics_attested": True,
    }


def test_thermal_summary_is_deidentified_and_conditioned_on_state(tmp_path: Path):
    trace = tmp_path / "private.csv"
    _trace(trace)

    public = summarize_station_thermal_dynamics(trace, _mapping(), **_kwargs()).to_public_dict()

    assert public["cooling_active_duty_cycle"] == pytest.approx(20 / 39)
    assert public["cooler_temperature_drop_active_degC"]["median"] == pytest.approx(10.0)
    assert public["cooler_temperature_drop_inactive_degC"]["median"] == pytest.approx(1.0)
    rendered = json.dumps(public)
    assert "secret_comp" not in rendered
    assert "private.csv" not in rendered


def test_thermal_summary_requires_both_attestations(tmp_path: Path):
    trace = tmp_path / "trace.csv"
    _trace(trace)
    kwargs = _kwargs()
    kwargs["temperature_semantics_attested"] = False
    with pytest.raises(ValueError, match="temperature role/unit"):
        summarize_station_thermal_dynamics(trace, _mapping(), **kwargs)
    kwargs = _kwargs()
    kwargs["state_semantics_attested"] = False
    with pytest.raises(ValueError, match="cooling-state semantics"):
        summarize_station_thermal_dynamics(trace, _mapping(), **kwargs)


def test_temporal_stability_uses_suffix_without_exporting_rows(tmp_path: Path):
    trace = tmp_path / "trace.csv"
    _trace(trace, rows=200)

    result = validate_station_thermal_temporal_stability(
        trace,
        _mapping(),
        calibration_fraction=0.70,
        minimum_holdout_rows=50,
        **_kwargs(),
    )

    assert result.minimum_holdout_rows_met is True
    assert all(result.component_medians_inside_calibration_p05_p95.values())
    assert result.cooler_active_drop_median_inside_calibration_p05_p95 is True
    assert result.stability_supported is True
    assert result.to_public_dict()["claim_boundary"].startswith("Within-record")
