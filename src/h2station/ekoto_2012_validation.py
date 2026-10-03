"""Prospective evaluator for the Ekoto et al. (2012) release-flow holdout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .schefer_2006_validation import (
    ScheferBlowdownInputs,
    _declining_crossing_time,
    simulate_adiabatic_blowdown_flow,
)


@dataclass(frozen=True, slots=True)
class EkotoFlowTrace:
    time_s: np.ndarray
    measured_mass_flow_kg_s: np.ndarray


@dataclass(frozen=True, slots=True)
class EkotoHoldoutResult:
    points: int
    measured_peak_mass_flow_kg_s: float
    predicted_peak_mass_flow_kg_s: float
    mass_flow_nrmse_percent_peak_measured: float
    median_absolute_percentage_error_percent: float
    experimental_half_peak_time_s: float
    predicted_half_peak_time_s: float
    half_peak_time_relative_error_percent: float
    nrmse_screen_pass: bool
    median_ape_screen_pass: bool
    half_peak_time_screen_pass: bool
    joint_primary_screen_pass: bool


EKOTO_INPUTS = ScheferBlowdownInputs(
    initial_pressure_pa_abs=13.45e6,
    initial_temperature_k=297.0,
    tank_volume_m3=0.00363,
    restriction_diameter_m=0.00356,
    discharge_coefficient=0.75,
    ambient_pressure_pa=101_325.0,
)


def load_ekoto_flow_csv(path: str | Path) -> EkotoFlowTrace:
    data = np.genfromtxt(
        path,
        delimiter=",",
        names=True,
        skip_header=2,
        dtype=float,
        encoding="utf-8",
    )
    names = set(data.dtype.names or ())
    if not {"x3", "y3"}.issubset(names):
        raise ValueError("Ekoto digitization must contain x3/y3 columns")
    time_s = np.atleast_1d(np.asarray(data["x3"], dtype=float))
    flow = np.atleast_1d(np.asarray(data["y3"], dtype=float))
    valid = np.isfinite(time_s) & np.isfinite(flow) & (flow >= 0.0)
    time_s, flow = time_s[valid], flow[valid]
    order = np.argsort(time_s, kind="stable")
    time_s, flow = time_s[order], flow[order]
    unique = np.concatenate(([True], np.diff(time_s) > 0.0))
    time_s, flow = time_s[unique], flow[unique]
    if len(time_s) < 15:
        raise ValueError("Ekoto holdout requires at least 15 unique points")
    if time_s[0] < 0.0 or np.any(np.diff(time_s) <= 0.0):
        raise ValueError("Ekoto time must be non-negative and strictly increasing")
    if float(np.max(flow)) <= 0.0:
        raise ValueError("Ekoto mass-flow trace has no positive value")
    return EkotoFlowTrace(time_s=time_s, measured_mass_flow_kg_s=flow)


def predict_ekoto_mass_flow(time_s: np.ndarray) -> np.ndarray:
    return simulate_adiabatic_blowdown_flow(time_s, inputs=EKOTO_INPUTS) / 1000.0


def evaluate_ekoto_holdout(trace: EkotoFlowTrace) -> EkotoHoldoutResult:
    predicted = predict_ekoto_mass_flow(trace.time_s)
    measured = trace.measured_mass_flow_kg_s
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
    return EkotoHoldoutResult(
        points=len(measured),
        measured_peak_mass_flow_kg_s=peak,
        predicted_peak_mass_flow_kg_s=float(np.max(predicted)),
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
