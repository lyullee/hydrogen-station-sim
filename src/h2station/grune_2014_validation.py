"""Prospective evaluator for the Grune et al. (2014) pressure trace.

The evaluator is fixed before numerical access to the published Figure 2
measured coordinates.  It reuses the pre-existing adiabatic real-gas source
balance without case fitting.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .schefer_2007_validation import (
    Schefer2007Inputs,
    _declining_crossing_time,
    simulate_adiabatic_blowdown_pressure,
)


@dataclass(frozen=True, slots=True)
class Grune2014Inputs:
    initial_pressure_pa_abs: float = 20.0e6
    initial_temperature_k: float = 293.15
    tank_volume_m3: float = 0.00037
    restriction_diameter_m: float = 0.004
    discharge_coefficient: float = 0.8
    ambient_pressure_pa: float = 101_325.0


@dataclass(frozen=True, slots=True)
class Grune2014Trace:
    time_s: np.ndarray
    measured_pressure_bar_abs: np.ndarray


@dataclass(frozen=True, slots=True)
class Grune2014HoldoutResult:
    points: int
    measured_initial_pressure_bar_abs: float
    predicted_initial_pressure_bar_abs: float
    pressure_nrmse_percent_initial_measured: float
    median_absolute_percentage_error_percent: float
    experimental_half_pressure_time_s: float
    predicted_half_pressure_time_s: float
    half_pressure_time_relative_error_percent: float
    nrmse_screen_pass: bool
    median_ape_screen_pass: bool
    half_pressure_time_screen_pass: bool
    joint_primary_screen_pass: bool


def load_grune_2014_pressure_csv(path: str | Path) -> Grune2014Trace:
    data = np.genfromtxt(path, delimiter=",", names=True, dtype=float, encoding="utf-8")
    names = set(data.dtype.names or ())
    if not {"time_s", "measured_pressure_bar_abs"}.issubset(names):
        raise ValueError("Grune 2014 CSV must contain time_s and measured_pressure_bar_abs")
    time_s = np.atleast_1d(np.asarray(data["time_s"], dtype=float))
    pressure = np.atleast_1d(np.asarray(data["measured_pressure_bar_abs"], dtype=float))
    valid = np.isfinite(time_s) & np.isfinite(pressure) & (pressure > 0.0)
    time_s, pressure = time_s[valid], pressure[valid]
    order = np.argsort(time_s, kind="stable")
    time_s, pressure = time_s[order], pressure[order]
    unique = np.concatenate(([True], np.diff(time_s) > 0.0))
    time_s, pressure = time_s[unique], pressure[unique]
    if len(time_s) < 15:
        raise ValueError("Grune 2014 holdout requires at least 15 unique points")
    if time_s[0] < 0.0 or np.any(np.diff(time_s) <= 0.0):
        raise ValueError("time must be non-negative and strictly increasing")
    return Grune2014Trace(time_s, pressure)


def _as_schefer_inputs(inputs: Grune2014Inputs) -> Schefer2007Inputs:
    return Schefer2007Inputs(
        initial_pressure_pa_abs=inputs.initial_pressure_pa_abs,
        initial_temperature_k=inputs.initial_temperature_k,
        tank_volume_m3=inputs.tank_volume_m3,
        restriction_diameter_m=inputs.restriction_diameter_m,
        discharge_coefficient=inputs.discharge_coefficient,
        ambient_pressure_pa=inputs.ambient_pressure_pa,
    )


def predict_pressure_bar_abs(
    time_s: np.ndarray,
    *,
    inputs: Grune2014Inputs | None = None,
) -> np.ndarray:
    psi = simulate_adiabatic_blowdown_pressure(
        np.asarray(time_s, dtype=float), inputs=_as_schefer_inputs(inputs or Grune2014Inputs())
    )
    return psi * 6_894.757293168 / 1.0e5


def evaluate_grune_2014_holdout(
    trace: Grune2014Trace,
    *,
    inputs: Grune2014Inputs | None = None,
) -> Grune2014HoldoutResult:
    predicted = predict_pressure_bar_abs(trace.time_s, inputs=inputs)
    measured = trace.measured_pressure_bar_abs
    initial = float(np.max(measured))
    nrmse = float(np.sqrt(np.mean((predicted - measured) ** 2)) / initial * 100.0)
    mask = measured >= 0.1 * initial
    median_ape = float(
        np.median(np.abs(predicted[mask] - measured[mask]) / measured[mask]) * 100.0
    )
    target = 0.5 * initial
    experimental_half = _declining_crossing_time(trace.time_s, measured, target)
    predicted_half = _declining_crossing_time(trace.time_s, predicted, target)
    if np.isfinite(experimental_half) and experimental_half > 0.0 and np.isfinite(predicted_half):
        half_error = abs(predicted_half - experimental_half) / experimental_half * 100.0
    else:
        half_error = float("inf")
    nrmse_pass = nrmse <= 10.0
    median_pass = median_ape <= 15.0
    half_pass = half_error <= 20.0
    return Grune2014HoldoutResult(
        points=len(measured),
        measured_initial_pressure_bar_abs=initial,
        predicted_initial_pressure_bar_abs=float(predicted[0]),
        pressure_nrmse_percent_initial_measured=nrmse,
        median_absolute_percentage_error_percent=median_ape,
        experimental_half_pressure_time_s=float(experimental_half),
        predicted_half_pressure_time_s=float(predicted_half),
        half_pressure_time_relative_error_percent=float(half_error),
        nrmse_screen_pass=nrmse_pass,
        median_ape_screen_pass=median_pass,
        half_pressure_time_screen_pass=half_pass,
        joint_primary_screen_pass=nrmse_pass and median_pass and half_pass,
    )


__all__ = [
    "Grune2014HoldoutResult",
    "Grune2014Inputs",
    "Grune2014Trace",
    "evaluate_grune_2014_holdout",
    "load_grune_2014_pressure_csv",
    "predict_pressure_bar_abs",
]
