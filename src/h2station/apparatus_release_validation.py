"""Prospective, no-fit evaluator for apparatus-resolved release campaigns.

The evaluator is deliberately separate from the production digital twin.  It
accepts one synchronized SI-unit trace, initializes the frozen release network
from the first measured boundary sample, and scores the complete trace without
time shifting, cropping, dynamic time warping, or parameter fitting.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .preslhy_nonadiabatic import _CoolPropHydrogen
from .release_network import ReleaseNetworkInputs, simulate_release_network


REQUIRED_COLUMNS = (
    "time_s",
    "source_pressure_pa_abs",
    "source_temperature_k",
    "line_pressure_pa_abs",
    "line_temperature_k",
    "terminal_mass_flow_kg_s",
    "valve_position_fraction",
    "source_mass_kg",
    "ambient_pressure_pa",
    "ambient_temperature_k",
)


@dataclass(frozen=True, slots=True)
class ApparatusReleaseTrace:
    time_s: np.ndarray
    source_pressure_pa_abs: np.ndarray
    source_temperature_k: np.ndarray
    line_pressure_pa_abs: np.ndarray
    line_temperature_k: np.ndarray
    terminal_mass_flow_kg_s: np.ndarray
    valve_position_fraction: np.ndarray
    source_mass_kg: np.ndarray
    ambient_pressure_pa: np.ndarray
    ambient_temperature_k: np.ndarray


@dataclass(frozen=True, slots=True)
class ApparatusReleaseCaseResult:
    observed_valve_location: str
    points: int
    duration_s: float
    sampling_hz_median: float
    maximum_timestamp_jitter_s: float
    source_pressure_nrmse_percent_initial: float
    terminal_mass_flow_nrmse_percent_peak_measured: float
    terminal_mass_flow_median_absolute_percentage_error_percent: float
    half_peak_time_relative_error_percent: float
    line_pressure_nrmse_percent_peak_measured: float
    line_temperature_rmse_k: float
    source_mass_nrmse_percent_initial: float
    valve_position_rmse_fraction: float
    mass_closure_max_relative_error: float
    energy_closure_max_relative_error: float
    measured_peak_mass_flow_kg_s: float
    predicted_peak_mass_flow_kg_s: float
    experimental_half_peak_time_s: float | None
    predicted_half_peak_time_s: float | None
    quality_gate_pass: bool
    primary_endpoint_pass: bool
    numerical_conservation_pass: bool
    joint_case_pass: bool
    gate_details: dict[str, bool]


def load_apparatus_release_csv(path: str | Path) -> ApparatusReleaseTrace:
    """Load a synchronized trace with explicit SI-unit column names."""

    data = np.genfromtxt(path, delimiter=",", names=True, dtype=float, encoding="utf-8")
    names = tuple(data.dtype.names or ())
    missing = [name for name in REQUIRED_COLUMNS if name not in names]
    if missing:
        raise ValueError(f"apparatus release trace missing columns: {', '.join(missing)}")
    columns = {
        name: np.atleast_1d(np.asarray(data[name], dtype=float))
        for name in REQUIRED_COLUMNS
    }
    lengths = {len(values) for values in columns.values()}
    if len(lengths) != 1:
        raise ValueError("apparatus release columns must have equal length")
    if not lengths or next(iter(lengths)) < 2:
        raise ValueError("apparatus release trace requires at least two rows")
    if any(np.any(~np.isfinite(values)) for values in columns.values()):
        raise ValueError("apparatus release trace contains non-finite values")
    time_s = columns["time_s"]
    if np.any(np.diff(time_s) <= 0.0):
        raise ValueError("apparatus release timestamps must be strictly increasing")
    if np.any(columns["terminal_mass_flow_kg_s"] < 0.0):
        raise ValueError("terminal mass flow cannot be negative")
    if np.any(columns["source_mass_kg"] <= 0.0):
        raise ValueError("source mass must be positive")
    valve = columns["valve_position_fraction"]
    if np.any((valve < 0.0) | (valve > 1.0)):
        raise ValueError("valve position must remain within [0, 1]")
    for name in (
        "source_pressure_pa_abs", "source_temperature_k",
        "line_pressure_pa_abs", "line_temperature_k",
        "ambient_pressure_pa", "ambient_temperature_k",
    ):
        if np.any(columns[name] <= 0.0):
            raise ValueError(f"{name} must be positive")
    return ApparatusReleaseTrace(**columns)


def _declining_crossing_time(
    time_s: np.ndarray, values: np.ndarray, target: float,
) -> float | None:
    peak_index = int(np.argmax(values))
    reached = np.flatnonzero(values[peak_index:] <= target)
    if not reached.size:
        return None
    index = peak_index + int(reached[0])
    if index == peak_index:
        return float(time_s[index])
    before, after = float(values[index - 1]), float(values[index])
    t_before, t_after = float(time_s[index - 1]), float(time_s[index])
    if after == before:
        return t_after
    return t_before + (target - before) * (t_after - t_before) / (after - before)


def _nrmse(predicted: np.ndarray, measured: np.ndarray, scale: float) -> float:
    if scale <= 0.0 or not np.isfinite(scale):
        return float("inf")
    return float(np.sqrt(np.mean((predicted - measured) ** 2)) / scale * 100.0)


def _model_inputs(
    trace: ApparatusReleaseTrace,
    model_parameters: Mapping[str, Any],
) -> ReleaseNetworkInputs:
    parameters = dict(model_parameters)
    parameters.pop("observed_valve_location", None)
    prohibited = {
        "source_pressure_pa_abs", "source_temperature_k",
        "line_initial_pressure_pa_abs", "line_initial_temperature_k",
        "ambient_pressure_pa", "ambient_temperature_k",
    }
    overlap = prohibited.intersection(parameters)
    if overlap:
        raise ValueError(
            "initial and ambient boundary states must come from the first synchronized "
            f"sample, not model_parameters: {', '.join(sorted(overlap))}"
        )
    return ReleaseNetworkInputs(
        **parameters,
        source_pressure_pa_abs=float(trace.source_pressure_pa_abs[0]),
        source_temperature_k=float(trace.source_temperature_k[0]),
        line_initial_pressure_pa_abs=float(trace.line_pressure_pa_abs[0]),
        line_initial_temperature_k=float(trace.line_temperature_k[0]),
        ambient_pressure_pa=float(trace.ambient_pressure_pa[0]),
        ambient_temperature_k=float(trace.ambient_temperature_k[0]),
    )


def _observed_valve_location(model_parameters: Mapping[str, Any]) -> str:
    """Return which prescribed valve command the single logger trace represents."""

    location = str(model_parameters.get("observed_valve_location", "upstream")).strip().lower()
    if location not in {"upstream", "terminal"}:
        raise ValueError("observed_valve_location must be 'upstream' or 'terminal'")
    return location


def evaluate_apparatus_release_case(
    trace: ApparatusReleaseTrace,
    *,
    model_parameters: Mapping[str, Any],
    thresholds: Mapping[str, float] | None = None,
) -> ApparatusReleaseCaseResult:
    """Run and score one untouched case with the prospectively frozen rules."""

    limits = {
        "minimum_points": 200.0,
        "minimum_sampling_hz": 20.0,
        "maximum_timestamp_jitter_s": 0.002,
        "maximum_ambient_pressure_relative_range": 0.01,
        "maximum_ambient_temperature_range_k": 2.0,
        "source_pressure_nrmse_percent_initial_max": 10.0,
        "terminal_mass_flow_nrmse_percent_peak_max": 15.0,
        "terminal_mass_flow_median_ape_percent_max": 20.0,
        "half_peak_time_relative_error_percent_max": 20.0,
        "valve_position_rmse_fraction_max": 0.05,
        "initial_source_mass_relative_error_max": 0.05,
        "mass_closure_relative_error_max": 0.002,
        "energy_closure_relative_error_max": 0.002,
    }
    if thresholds:
        unknown = set(thresholds).difference(limits)
        if unknown:
            raise ValueError(f"unknown scoring thresholds: {', '.join(sorted(unknown))}")
        limits.update({key: float(value) for key, value in thresholds.items()})

    elapsed = trace.time_s - float(trace.time_s[0])
    intervals = np.diff(elapsed)
    median_interval = float(np.median(intervals))
    sampling_hz = 1.0 / median_interval
    timestamp_jitter = float(np.max(np.abs(intervals - median_interval)))
    inputs = _model_inputs(trace, model_parameters)
    observed_valve_location = _observed_valve_location(model_parameters)
    predicted = simulate_release_network(elapsed, inputs=inputs)

    measured_peak = float(np.max(trace.terminal_mass_flow_kg_s))
    predicted_peak = float(np.max(predicted.terminal_mass_flow_kg_s))
    source_pressure_nrmse = _nrmse(
        predicted.source_pressure_pa_abs,
        trace.source_pressure_pa_abs,
        float(trace.source_pressure_pa_abs[0]),
    )
    flow_nrmse = _nrmse(
        predicted.terminal_mass_flow_kg_s,
        trace.terminal_mass_flow_kg_s,
        measured_peak,
    )
    relative_mask = trace.terminal_mass_flow_kg_s >= 0.1 * measured_peak
    if measured_peak > 0.0 and np.any(relative_mask):
        flow_mape = float(
            np.median(
                np.abs(
                    predicted.terminal_mass_flow_kg_s[relative_mask]
                    - trace.terminal_mass_flow_kg_s[relative_mask]
                ) / trace.terminal_mass_flow_kg_s[relative_mask]
            ) * 100.0
        )
    else:
        flow_mape = float("inf")
    measured_half = _declining_crossing_time(
        elapsed, trace.terminal_mass_flow_kg_s, 0.5 * measured_peak,
    )
    predicted_half = _declining_crossing_time(
        elapsed, predicted.terminal_mass_flow_kg_s, 0.5 * measured_peak,
    )
    if measured_half is None or measured_half <= 0.0 or predicted_half is None:
        half_error = float("inf")
    else:
        half_error = abs(predicted_half - measured_half) / measured_half * 100.0

    line_pressure_scale = float(np.max(trace.line_pressure_pa_abs))
    line_pressure_nrmse = _nrmse(
        predicted.line_pressure_pa_abs, trace.line_pressure_pa_abs, line_pressure_scale,
    )
    line_temperature_rmse = float(
        np.sqrt(np.mean((predicted.line_temperature_k - trace.line_temperature_k) ** 2))
    )
    source_mass_nrmse = _nrmse(
        predicted.source_mass_kg, trace.source_mass_kg, float(trace.source_mass_kg[0]),
    )
    predicted_valve_position = (
        predicted.terminal_valve_opening_fraction
        if observed_valve_location == "terminal"
        else predicted.upstream_valve_opening_fraction
    )
    valve_rmse = float(np.sqrt(np.mean(
        (predicted_valve_position - trace.valve_position_fraction) ** 2
    )))
    initial_mass_scale = float(predicted.source_mass_kg[0] + predicted.line_mass_kg[0])
    mass_closure = float(np.max(np.abs(predicted.mass_balance_residual_kg))) / max(
        initial_mass_scale, 1.0e-12,
    )
    eos = _CoolPropHydrogen()
    source_initial = eos.storage_from_pt(
        inputs.source_pressure_pa_abs, inputs.source_temperature_k,
    )
    line_initial = eos.storage_from_pt(
        inputs.line_initial_pressure_pa_abs, inputs.line_initial_temperature_k,
    )
    source_wall_temperature = (
        inputs.source_wall_temperature_k
        if inputs.source_wall_temperature_k is not None
        else inputs.source_temperature_k
    )
    line_wall_temperature = (
        inputs.line_wall_temperature_k
        if inputs.line_wall_temperature_k is not None
        else inputs.line_initial_temperature_k
    )
    initial_stored_energy = (
        float(source_initial.rhomass() * inputs.source_volume_m3 * source_initial.umass())
        + float(line_initial.rhomass() * inputs.line_volume_m3 * line_initial.umass())
        + inputs.source_wall_capacity_j_k * source_wall_temperature
        + inputs.line_wall_capacity_j_k * line_wall_temperature
    )
    energy_closure = float(np.max(np.abs(predicted.energy_balance_residual_j))) / max(
        abs(initial_stored_energy), 1.0,
    )
    initial_source_mass_error = abs(
        float(predicted.source_mass_kg[0]) - float(trace.source_mass_kg[0])
    ) / float(trace.source_mass_kg[0])
    ambient_pressure_range = float(np.ptp(trace.ambient_pressure_pa)) / float(
        np.mean(trace.ambient_pressure_pa)
    )
    ambient_temperature_range = float(np.ptp(trace.ambient_temperature_k))

    gates = {
        "minimum_points": len(elapsed) >= int(limits["minimum_points"]),
        "minimum_sampling_frequency": sampling_hz >= limits["minimum_sampling_hz"],
        "timestamp_jitter": timestamp_jitter <= limits["maximum_timestamp_jitter_s"],
        "ambient_pressure_constant_boundary": ambient_pressure_range
        <= limits["maximum_ambient_pressure_relative_range"],
        "ambient_temperature_constant_boundary": ambient_temperature_range
        <= limits["maximum_ambient_temperature_range_k"],
        "positive_measured_release": measured_peak > 0.0,
        "measured_half_peak_observed": measured_half is not None,
        "initial_source_mass_consistency": initial_source_mass_error
        <= limits["initial_source_mass_relative_error_max"],
        "valve_law_consistency": valve_rmse
        <= limits["valve_position_rmse_fraction_max"],
        "source_pressure_endpoint": source_pressure_nrmse
        <= limits["source_pressure_nrmse_percent_initial_max"],
        "terminal_flow_nrmse_endpoint": flow_nrmse
        <= limits["terminal_mass_flow_nrmse_percent_peak_max"],
        "terminal_flow_mape_endpoint": flow_mape
        <= limits["terminal_mass_flow_median_ape_percent_max"],
        "half_peak_time_endpoint": half_error
        <= limits["half_peak_time_relative_error_percent_max"],
        "mass_conservation": mass_closure
        <= limits["mass_closure_relative_error_max"],
        "energy_conservation": energy_closure
        <= limits["energy_closure_relative_error_max"],
    }
    quality_keys = {
        "minimum_points", "minimum_sampling_frequency", "timestamp_jitter",
        "ambient_pressure_constant_boundary", "ambient_temperature_constant_boundary",
        "positive_measured_release", "measured_half_peak_observed",
        "initial_source_mass_consistency", "valve_law_consistency",
    }
    primary_keys = {
        "source_pressure_endpoint", "terminal_flow_nrmse_endpoint",
        "terminal_flow_mape_endpoint", "half_peak_time_endpoint",
    }
    conservation_keys = {"mass_conservation", "energy_conservation"}
    quality_pass = all(gates[key] for key in quality_keys)
    primary_pass = all(gates[key] for key in primary_keys)
    conservation_pass = all(gates[key] for key in conservation_keys)
    return ApparatusReleaseCaseResult(
        observed_valve_location=observed_valve_location,
        points=len(elapsed),
        duration_s=float(elapsed[-1]),
        sampling_hz_median=sampling_hz,
        maximum_timestamp_jitter_s=timestamp_jitter,
        source_pressure_nrmse_percent_initial=source_pressure_nrmse,
        terminal_mass_flow_nrmse_percent_peak_measured=flow_nrmse,
        terminal_mass_flow_median_absolute_percentage_error_percent=flow_mape,
        half_peak_time_relative_error_percent=half_error,
        line_pressure_nrmse_percent_peak_measured=line_pressure_nrmse,
        line_temperature_rmse_k=line_temperature_rmse,
        source_mass_nrmse_percent_initial=source_mass_nrmse,
        valve_position_rmse_fraction=valve_rmse,
        mass_closure_max_relative_error=mass_closure,
        energy_closure_max_relative_error=energy_closure,
        measured_peak_mass_flow_kg_s=measured_peak,
        predicted_peak_mass_flow_kg_s=predicted_peak,
        experimental_half_peak_time_s=measured_half,
        predicted_half_peak_time_s=predicted_half,
        quality_gate_pass=quality_pass,
        primary_endpoint_pass=primary_pass,
        numerical_conservation_pass=conservation_pass,
        joint_case_pass=quality_pass and primary_pass and conservation_pass,
        gate_details=gates,
    )


__all__ = [
    "ApparatusReleaseCaseResult",
    "ApparatusReleaseTrace",
    "REQUIRED_COLUMNS",
    "evaluate_apparatus_release_case",
    "load_apparatus_release_csv",
]
