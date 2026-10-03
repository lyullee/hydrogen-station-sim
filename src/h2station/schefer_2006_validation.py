"""Frozen evaluator for the Schefer et al. (2006) blowdown-flow holdout.

The evaluator is intentionally independent of the real-time station runtime.  It
uses the already-developed HEOS hydrogen helper and a well-mixed adiabatic tank
balance.  The published 3.175 mm manifold restriction is treated as the
controlling aperture; the downstream 7.94 mm by 7.6 m tube is outside the model
claim and is retained as a documented limitation.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from .preslhy_nonadiabatic import _CoolPropHydrogen


@dataclass(frozen=True, slots=True)
class ScheferBlowdownInputs:
    initial_pressure_pa_abs: float = 15.513e6
    initial_temperature_k: float = 315.15
    tank_volume_m3: float = 0.098
    restriction_diameter_m: float = 0.003175
    discharge_coefficient: float = 1.0
    ambient_pressure_pa: float = 101_325.0


@dataclass(frozen=True, slots=True)
class ScheferFlowTrace:
    time_s: np.ndarray
    measured_mass_flow_g_s: np.ndarray


@dataclass(frozen=True, slots=True)
class ScheferHoldoutResult:
    points: int
    measured_peak_mass_flow_g_s: float
    predicted_peak_mass_flow_g_s: float
    mass_flow_nrmse_percent_peak_measured: float
    median_absolute_percentage_error_percent: float
    experimental_half_peak_time_s: float
    predicted_half_peak_time_s: float
    half_peak_time_relative_error_percent: float
    nrmse_screen_pass: bool
    median_ape_screen_pass: bool
    half_peak_time_screen_pass: bool
    joint_primary_screen_pass: bool


def load_schefer_flow_csv(path: str | Path) -> ScheferFlowTrace:
    """Read the GPL-licensed HyRAM+ digitization of publisher Figure 3b."""

    data = np.genfromtxt(
        path,
        delimiter=",",
        names=True,
        skip_header=2,
        dtype=float,
        encoding="utf-8",
    )
    names = set(data.dtype.names or ())
    if not {"x1", "y1"}.issubset(names):
        raise ValueError("Schefer digitization must contain x1/y1 columns")
    time_s = np.atleast_1d(np.asarray(data["x1"], dtype=float))
    flow_g_s = np.atleast_1d(np.asarray(data["y1"], dtype=float))
    valid = np.isfinite(time_s) & np.isfinite(flow_g_s) & (flow_g_s >= 0.0)
    time_s, flow_g_s = time_s[valid], flow_g_s[valid]
    order = np.argsort(time_s, kind="stable")
    time_s, flow_g_s = time_s[order], flow_g_s[order]
    unique = np.concatenate(([True], np.diff(time_s) > 0.0))
    time_s, flow_g_s = time_s[unique], flow_g_s[unique]
    if len(time_s) < 15:
        raise ValueError("Schefer holdout requires at least 15 unique points")
    if time_s[0] < 0.0 or np.any(np.diff(time_s) <= 0.0):
        raise ValueError("Schefer time must be non-negative and strictly increasing")
    if float(np.max(flow_g_s)) <= 0.0:
        raise ValueError("Schefer mass-flow trace has no positive value")
    return ScheferFlowTrace(time_s=time_s, measured_mass_flow_g_s=flow_g_s)


def simulate_adiabatic_blowdown_flow(
    evaluation_time_s: np.ndarray,
    *,
    inputs: ScheferBlowdownInputs | None = None,
) -> np.ndarray:
    """Return aperture mass flow at requested times without outcome fitting."""

    requested = np.asarray(evaluation_time_s, dtype=float)
    if len(requested) < 2 or requested[0] < 0.0 or np.any(np.diff(requested) <= 0.0):
        raise ValueError("evaluation times must be non-negative and strictly increasing")
    p = inputs or ScheferBlowdownInputs()
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
        max_step=max(0.002, min(0.05, float(requested[-1]) / 1000.0)),
    )
    if not solution.success:
        raise RuntimeError(f"Schefer blowdown integration failed: {solution.message}")
    node_flow = np.asarray(
        [quantities(solution.y[:, index])[1] for index in range(solution.y.shape[1])]
    )
    return np.interp(requested, solution.t, node_flow) * 1000.0


def _declining_crossing_time(time_s: np.ndarray, values: np.ndarray, target: float) -> float:
    peak_index = int(np.argmax(values))
    tail = values[peak_index:]
    reached = np.flatnonzero(tail <= target)
    if not reached.size:
        return float("nan")
    index = peak_index + int(reached[0])
    if index == peak_index:
        return float(time_s[index])
    v0, v1 = float(values[index - 1]), float(values[index])
    t0, t1 = float(time_s[index - 1]), float(time_s[index])
    if v1 == v0:
        return t1
    return t0 + (target - v0) * (t1 - t0) / (v1 - v0)


def evaluate_schefer_holdout(trace: ScheferFlowTrace) -> ScheferHoldoutResult:
    predicted = simulate_adiabatic_blowdown_flow(trace.time_s)
    measured = trace.measured_mass_flow_g_s
    peak = float(np.max(measured))
    nrmse = float(np.sqrt(np.mean((predicted - measured) ** 2)) / peak * 100.0)
    relative_mask = measured >= 0.1 * peak
    median_ape = float(
        np.median(np.abs(predicted[relative_mask] - measured[relative_mask]) / measured[relative_mask])
        * 100.0
    )
    half_target = 0.5 * peak
    experimental_half = _declining_crossing_time(trace.time_s, measured, half_target)
    predicted_half = _declining_crossing_time(trace.time_s, predicted, half_target)
    if np.isfinite(experimental_half) and experimental_half > 0.0 and np.isfinite(predicted_half):
        half_error = abs(predicted_half - experimental_half) / experimental_half * 100.0
    else:
        half_error = float("inf")
    nrmse_pass = nrmse <= 15.0
    median_pass = median_ape <= 20.0
    half_pass = half_error <= 20.0
    return ScheferHoldoutResult(
        points=len(measured),
        measured_peak_mass_flow_g_s=peak,
        predicted_peak_mass_flow_g_s=float(np.max(predicted)),
        mass_flow_nrmse_percent_peak_measured=nrmse,
        median_absolute_percentage_error_percent=median_ape,
        experimental_half_peak_time_s=experimental_half,
        predicted_half_peak_time_s=predicted_half,
        half_peak_time_relative_error_percent=half_error,
        nrmse_screen_pass=nrmse_pass,
        median_ape_screen_pass=median_pass,
        half_peak_time_screen_pass=half_pass,
        joint_primary_screen_pass=nrmse_pass and median_pass and half_pass,
    )
