"""Prospective evaluator for the Schefer et al. (2007) pressure holdout.

This module is intentionally separate from the 2006 mass-flow evaluator.  It
uses the same pre-existing, well-mixed adiabatic real-gas vessel balance but
tests transfer to a different vessel, pressure and restriction using a pressure
trace that was not numerically inspected while this evaluator was written.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from .preslhy_nonadiabatic import _CoolPropHydrogen


@dataclass(frozen=True, slots=True)
class Schefer2007Inputs:
    initial_pressure_pa_abs: float = 43.1e6
    initial_temperature_k: float = 290.0
    tank_volume_m3: float = 1.234
    restriction_diameter_m: float = 0.00508
    discharge_coefficient: float = 1.0
    ambient_pressure_pa: float = 101_325.0


@dataclass(frozen=True, slots=True)
class Schefer2007PressureTrace:
    time_s: np.ndarray
    measured_pressure_psi: np.ndarray


@dataclass(frozen=True, slots=True)
class Schefer2007HoldoutResult:
    points: int
    measured_initial_pressure_psi: float
    predicted_initial_pressure_psi: float
    pressure_nrmse_percent_initial_measured: float
    median_absolute_percentage_error_percent: float
    experimental_half_pressure_time_s: float
    predicted_half_pressure_time_s: float
    half_pressure_time_relative_error_percent: float
    nrmse_screen_pass: bool
    median_ape_screen_pass: bool
    half_pressure_time_screen_pass: bool
    joint_primary_screen_pass: bool


def load_schefer_2007_pressure_csv(path: str | Path) -> Schefer2007PressureTrace:
    """Read the two digitized Figure 4 curve segments without extrapolation."""

    data = np.genfromtxt(
        path,
        delimiter=",",
        names=True,
        skip_header=2,
        dtype=float,
        encoding="utf-8",
    )
    names = set(data.dtype.names or ())
    if not {"x1", "y1", "x2", "y2"}.issubset(names):
        raise ValueError("Schefer 2007 digitization must contain x1/y1/x2/y2 columns")
    time_s = np.concatenate(
        (np.atleast_1d(np.asarray(data["x1"], dtype=float)),
         np.atleast_1d(np.asarray(data["x2"], dtype=float)))
    )
    pressure_psi = np.concatenate(
        (np.atleast_1d(np.asarray(data["y1"], dtype=float)),
         np.atleast_1d(np.asarray(data["y2"], dtype=float)))
    )
    valid = np.isfinite(time_s) & np.isfinite(pressure_psi) & (pressure_psi > 0.0)
    time_s, pressure_psi = time_s[valid], pressure_psi[valid]
    order = np.argsort(time_s, kind="stable")
    time_s, pressure_psi = time_s[order], pressure_psi[order]
    unique = np.concatenate(([True], np.diff(time_s) > 0.0))
    time_s, pressure_psi = time_s[unique], pressure_psi[unique]
    if len(time_s) < 15:
        raise ValueError("Schefer 2007 holdout requires at least 15 unique points")
    if time_s[0] < 0.0 or np.any(np.diff(time_s) <= 0.0):
        raise ValueError("Schefer 2007 time must be non-negative and strictly increasing")
    return Schefer2007PressureTrace(time_s=time_s, measured_pressure_psi=pressure_psi)


def simulate_adiabatic_blowdown_pressure(
    evaluation_time_s: np.ndarray,
    *,
    inputs: Schefer2007Inputs | None = None,
) -> np.ndarray:
    """Return absolute vessel pressure in psi at requested times."""

    requested = np.asarray(evaluation_time_s, dtype=float)
    if len(requested) < 2 or requested[0] < 0.0 or np.any(np.diff(requested) <= 0.0):
        raise ValueError("evaluation times must be non-negative and strictly increasing")
    p = inputs or Schefer2007Inputs()
    eos = _CoolPropHydrogen()
    state = eos.storage_from_pt(p.initial_pressure_pa_abs, p.initial_temperature_k)
    initial_mass = state.rhomass() * p.tank_volume_m3
    initial_energy = initial_mass * state.umass()
    minimum_mass = max(initial_mass * 1.0e-9, 1.0e-10)
    area = pi * p.restriction_diameter_m**2 / 4.0

    def quantities(vector: np.ndarray):
        mass = max(float(vector[0]), minimum_mass)
        gas = eos.storage_from_rho_u(mass / p.tank_volume_m3, float(vector[1]) / mass)
        if gas.p() <= p.ambient_pressure_pa * (1.0 + 1.0e-7):
            flow = 0.0
        else:
            flow = (
                p.discharge_coefficient
                * area
                * eos.isentropic_mass_flux(gas.p(), gas.T(), p.ambient_pressure_pa)
            )
        return gas, flow

    def derivative(_time: float, vector: np.ndarray) -> np.ndarray:
        gas, flow = quantities(vector)
        flow = min(flow, max(float(vector[0]), 0.0) / 1.0e-3)
        return np.asarray((-flow, -flow * gas.hmass()), dtype=float)

    solution = solve_ivp(
        derivative,
        (0.0, float(requested[-1])),
        np.asarray((initial_mass, initial_energy), dtype=float),
        method="LSODA",
        rtol=2.0e-7,
        atol=(1.0e-10, 1.0e-2),
        max_step=max(0.01, min(0.25, float(requested[-1]) / 1000.0)),
    )
    if not solution.success:
        raise RuntimeError(f"Schefer 2007 integration failed: {solution.message}")
    node_pressure_pa = np.asarray(
        [quantities(solution.y[:, index])[0].p() for index in range(solution.y.shape[1])]
    )
    return np.interp(requested, solution.t, node_pressure_pa) / 6_894.757293168


def _declining_crossing_time(time_s: np.ndarray, values: np.ndarray, target: float) -> float:
    reached = np.flatnonzero(values <= target)
    if not reached.size:
        return float("nan")
    index = int(reached[0])
    if index == 0:
        return float(time_s[0])
    v0, v1 = float(values[index - 1]), float(values[index])
    t0, t1 = float(time_s[index - 1]), float(time_s[index])
    if v1 == v0:
        return t1
    return t0 + (target - v0) * (t1 - t0) / (v1 - v0)


def evaluate_schefer_2007_holdout(
    trace: Schefer2007PressureTrace,
) -> Schefer2007HoldoutResult:
    predicted = simulate_adiabatic_blowdown_pressure(trace.time_s)
    measured = trace.measured_pressure_psi
    initial = float(np.max(measured))
    nrmse = float(np.sqrt(np.mean((predicted - measured) ** 2)) / initial * 100.0)
    relative_mask = measured >= 0.1 * initial
    median_ape = float(
        np.median(np.abs(predicted[relative_mask] - measured[relative_mask]) / measured[relative_mask])
        * 100.0
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
    return Schefer2007HoldoutResult(
        points=len(measured),
        measured_initial_pressure_psi=initial,
        predicted_initial_pressure_psi=float(predicted[0]),
        pressure_nrmse_percent_initial_measured=nrmse,
        median_absolute_percentage_error_percent=median_ape,
        experimental_half_pressure_time_s=experimental_half,
        predicted_half_pressure_time_s=predicted_half,
        half_pressure_time_relative_error_percent=half_error,
        nrmse_screen_pass=nrmse_pass,
        median_ape_screen_pass=median_pass,
        half_pressure_time_screen_pass=half_pass,
        joint_primary_screen_pass=nrmse_pass and median_pass and half_pass,
    )
