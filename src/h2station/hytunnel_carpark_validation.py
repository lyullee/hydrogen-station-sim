"""Validation helpers for the HyTunnel-CS ventilated-car-park experiments.

The public archive contains actual-hydrogen concentration, mass-flow,
ventilation, tank-pressure and tank-temperature time series.  Two deliberately
bounded models are evaluated without outcome fitting:

* a spatially lumped, well-mixed hydrogen mass balance compared with the mean
  of the available concentration heads; and
* a local 0.5 mm real-gas aperture relation evaluated from measured upstream
  pressure and temperature during the five eligible blowdown experiments.

Neither model resolves the measured plume geometry, the 3.86 m discharge-line
transient, detector dynamics or a complete hydrogen-refuelling-station loop.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat
from scipy.stats import spearmanr

from .preslhy_nonadiabatic import _CoolPropHydrogen


CONTAINER_VOLUME_M3 = 60.8
AMBIENT_PRESSURE_PA = 101_325.0
AMBIENT_TEMPERATURE_K = 293.15
BLOWDOWN_NOZZLE_DIAMETER_M = 0.0005
BLOWDOWN_DISCHARGE_COEFFICIENT = 0.8
DISPERSION_CASES = tuple(range(4, 17)) + tuple(range(19, 24))
BLOWDOWN_CASES = tuple(range(19, 24))


@dataclass(frozen=True, slots=True)
class HyTunnelTrace:
    experiment: int
    sensor_time_s: np.ndarray
    concentration_volpct: np.ndarray
    mass_flow_time_s: np.ndarray
    mass_flow_g_s: np.ndarray
    release_start_s: float
    ventilation_time_s: np.ndarray
    ventilation_m3_h: np.ndarray
    tank_time_s: np.ndarray | None = None
    tank_pressure_bar: np.ndarray | None = None
    tank_temperature_c: np.ndarray | None = None


@dataclass(frozen=True, slots=True)
class DispersionCaseResult:
    experiment: int
    points: int
    sensor_count: int
    measured_peak_volpct: float
    predicted_peak_volpct: float
    nrmse_percent_peak_measured: float
    median_absolute_percentage_error_percent: float
    peak_relative_error_percent: float
    spearman_rho: float
    measured_flammable_duration_s: float
    predicted_flammable_duration_s: float
    joint_primary_screen_pass: bool


@dataclass(frozen=True, slots=True)
class MassFlowCaseResult:
    experiment: int
    points: int
    measured_peak_g_s: float
    predicted_peak_g_s: float
    nrmse_percent_peak_measured: float
    median_absolute_percentage_error_percent: float
    peak_relative_error_percent: float
    spearman_rho: float
    joint_primary_screen_pass: bool


def _field(container: Any, name: str) -> Any:
    if isinstance(container, dict):
        if name in container:
            return container[name]
    if hasattr(container, name):
        return getattr(container, name)
    if isinstance(container, np.ndarray) and container.dtype.names and name in container.dtype.names:
        return container[name]
    raise KeyError(name)


def _vector(value: Any, name: str) -> np.ndarray:
    result = np.asarray(value, dtype=float).squeeze()
    if result.ndim == 0:
        result = result.reshape(1)
    if result.ndim != 1:
        result = result.reshape(-1)
    if result.size == 0:
        raise ValueError(f"{name} is empty")
    return result


def _time_sensor_matrix(value: Any, time_count: int) -> np.ndarray:
    result = np.asarray(value, dtype=float).squeeze()
    if result.ndim == 1:
        if result.size != time_count:
            raise ValueError("S.conc has no axis matching S.time")
        return result.reshape(time_count, 1)
    matching = [axis for axis, size in enumerate(result.shape) if size == time_count]
    if not matching:
        raise ValueError("S.conc has no axis matching S.time")
    time_axis = matching[0]
    moved = np.moveaxis(result, time_axis, 0)
    return moved.reshape(time_count, -1)


def _series_on_time(value: Any, source_time: np.ndarray, target_time: np.ndarray, name: str) -> np.ndarray:
    vector = _vector(value, name)
    if vector.size == 1:
        return np.full(target_time.shape, float(vector[0]))
    if vector.size != source_time.size:
        raise ValueError(f"{name} length does not match its documented time base")
    valid = np.isfinite(source_time) & np.isfinite(vector)
    if np.count_nonzero(valid) < 2:
        raise ValueError(f"{name} has fewer than two finite synchronized samples")
    ordered = np.argsort(source_time[valid], kind="stable")
    x = source_time[valid][ordered]
    y = vector[valid][ordered]
    unique = np.concatenate(([True], np.diff(x) > 0.0))
    return np.interp(target_time, x[unique], y[unique])


def load_hytunnel_mat(path: str | Path) -> HyTunnelTrace:
    path = Path(path)
    payload = loadmat(path, squeeze_me=True, struct_as_record=False)
    experiment_match = "".join(character for character in path.stem if character.isdigit())
    if not experiment_match:
        raise ValueError("experiment number is missing from the MAT filename")
    experiment = int(experiment_match)
    sensor = payload["S"]
    mfm = payload["MFM"]
    vent = payload["Vent"]
    sensor_time = _vector(_field(sensor, "time"), "S.time")
    concentration = _time_sensor_matrix(_field(sensor, "conc"), sensor_time.size)
    mass_flow_time = _vector(_field(mfm, "time"), "MFM.time")
    mass_flow = _vector(_field(mfm, "mfr"), "MFM.mfr")
    release_start = float(np.asarray(_field(mfm, "t0"), dtype=float).squeeze())
    ventilation_time = _vector(_field(vent, "time"), "Vent.time")
    ventilation = _vector(_field(vent, "vfr"), "Vent.vfr")

    tank_time = tank_pressure = tank_temperature = None
    if "Tank" in payload:
        tank = payload["Tank"]
        tank_time = _vector(_field(tank, "time"), "Tank.time")
        tank_pressure = _vector(_field(tank, "p"), "Tank.p")
        tank_temperature = _vector(_field(tank, "T"), "Tank.T")
    return HyTunnelTrace(
        experiment=experiment,
        sensor_time_s=sensor_time,
        concentration_volpct=concentration,
        mass_flow_time_s=mass_flow_time,
        mass_flow_g_s=mass_flow,
        release_start_s=release_start,
        ventilation_time_s=ventilation_time,
        ventilation_m3_h=ventilation,
        tank_time_s=tank_time,
        tank_pressure_bar=tank_pressure,
        tank_temperature_c=tank_temperature,
    )


def _hydrogen_density_ambient() -> float:
    eos = _CoolPropHydrogen()
    return float(eos.storage_from_pt(AMBIENT_PRESSURE_PA, AMBIENT_TEMPERATURE_K).rhomass())


def simulate_well_mixed_concentration(trace: HyTunnelTrace) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    time = np.asarray(trace.sensor_time_s, dtype=float)
    concentration = np.asarray(trace.concentration_volpct, dtype=float)
    valid_time = np.isfinite(time) & (time >= trace.release_start_s)
    if np.count_nonzero(valid_time) < 30:
        raise ValueError("fewer than 30 post-release concentration samples")
    time = time[valid_time]
    concentration = concentration[valid_time]
    measured_mean = np.nanmean(concentration, axis=1)
    if np.count_nonzero(np.isfinite(measured_mean)) < 30:
        raise ValueError("fewer than 30 finite sensor-array means")
    flow = _series_on_time(
        trace.mass_flow_g_s, trace.mass_flow_time_s, time, "MFM.mfr"
    )
    ventilation = _series_on_time(
        trace.ventilation_m3_h,
        trace.ventilation_time_s,
        time,
        "Vent.vfr",
    )
    flow = np.maximum(flow, 0.0) / 1000.0
    ventilation = np.maximum(ventilation, 0.0) / 3600.0
    density = _hydrogen_density_ambient()
    predicted_fraction = np.empty_like(time)
    predicted_fraction[0] = max(float(measured_mean[0]) / 100.0, 0.0)
    for index in range(1, len(time)):
        dt = float(time[index] - time[index - 1])
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("S.time must be finite and strictly increasing after t0")
        source_rate = flow[index - 1] / density / CONTAINER_VOLUME_M3
        removal_rate = ventilation[index - 1] / CONTAINER_VOLUME_M3
        if removal_rate > 0.0:
            equilibrium = source_rate / removal_rate
            predicted_fraction[index] = equilibrium + (
                predicted_fraction[index - 1] - equilibrium
            ) * math.exp(-removal_rate * dt)
        else:
            predicted_fraction[index] = predicted_fraction[index - 1] + source_rate * dt
        predicted_fraction[index] = float(np.clip(predicted_fraction[index], 0.0, 1.0))
    return time, measured_mean, predicted_fraction * 100.0


def _duration_above(time: np.ndarray, values: np.ndarray, threshold: float) -> float:
    if len(time) < 2:
        return 0.0
    return float(np.sum(np.diff(time) * (values[:-1] >= threshold)))


def _metrics(measured: np.ndarray, predicted: np.ndarray) -> tuple[float, float, float, float]:
    valid = np.isfinite(measured) & np.isfinite(predicted)
    measured = measured[valid]
    predicted = predicted[valid]
    if len(measured) < 30:
        raise ValueError("fewer than 30 finite paired samples")
    peak = float(np.max(measured))
    if peak <= 0.0:
        raise ValueError("measured response has no positive peak")
    nrmse = float(np.sqrt(np.mean((predicted - measured) ** 2)) / peak * 100.0)
    mask = measured >= max(0.1 * peak, 1.0e-9)
    median_ape = float(np.median(np.abs(predicted[mask] - measured[mask]) / measured[mask]) * 100.0)
    peak_error = abs(float(np.max(predicted)) - peak) / peak * 100.0
    rho = float(spearmanr(measured, predicted, nan_policy="omit").statistic)
    return nrmse, median_ape, peak_error, rho


def evaluate_dispersion_case(trace: HyTunnelTrace) -> DispersionCaseResult:
    time, measured, predicted = simulate_well_mixed_concentration(trace)
    nrmse, median_ape, peak_error, rho = _metrics(measured, predicted)
    passed = nrmse <= 40.0 and median_ape <= 50.0 and peak_error <= 50.0 and rho >= 0.6
    return DispersionCaseResult(
        experiment=trace.experiment,
        points=len(time),
        sensor_count=trace.concentration_volpct.shape[1],
        measured_peak_volpct=float(np.nanmax(measured)),
        predicted_peak_volpct=float(np.nanmax(predicted)),
        nrmse_percent_peak_measured=nrmse,
        median_absolute_percentage_error_percent=median_ape,
        peak_relative_error_percent=peak_error,
        spearman_rho=rho,
        measured_flammable_duration_s=_duration_above(time, measured, 4.0),
        predicted_flammable_duration_s=_duration_above(time, predicted, 4.0),
        joint_primary_screen_pass=passed,
    )


def evaluate_mass_flow_case(trace: HyTunnelTrace) -> MassFlowCaseResult:
    if trace.experiment not in BLOWDOWN_CASES:
        raise ValueError("mass-flow validation is restricted to Exp19-23")
    if trace.tank_time_s is None or trace.tank_pressure_bar is None or trace.tank_temperature_c is None:
        raise ValueError("Tank.p, Tank.T and Tank.time are required")
    time = np.asarray(trace.mass_flow_time_s, dtype=float)
    measured = np.asarray(trace.mass_flow_g_s, dtype=float)
    if measured.size != time.size:
        raise ValueError("MFM.mfr length does not match MFM.time")
    pressure = _series_on_time(trace.tank_pressure_bar, trace.tank_time_s, time, "Tank.p")
    temperature = _series_on_time(trace.tank_temperature_c, trace.tank_time_s, time, "Tank.T")
    finite = (
        np.isfinite(time) & np.isfinite(measured) & np.isfinite(pressure)
        & np.isfinite(temperature) & (time >= trace.release_start_s)
    )
    peak = float(np.nanmax(measured[finite])) if np.any(finite) else 0.0
    finite &= measured >= 0.1 * peak
    finite &= pressure * 1.0e5 > AMBIENT_PRESSURE_PA * 1.01
    if np.count_nonzero(finite) < 30:
        raise ValueError("fewer than 30 eligible blowdown mass-flow samples")
    measured = measured[finite]
    pressure = pressure[finite]
    temperature = temperature[finite] + 273.15
    eos = _CoolPropHydrogen()
    area = math.pi * BLOWDOWN_NOZZLE_DIAMETER_M**2 / 4.0
    predicted = np.asarray([
        BLOWDOWN_DISCHARGE_COEFFICIENT * area
        * eos.isentropic_mass_flux(p_bar * 1.0e5, temp_k, AMBIENT_PRESSURE_PA)
        * 1000.0
        for p_bar, temp_k in zip(pressure, temperature, strict=True)
    ])
    nrmse, median_ape, peak_error, rho = _metrics(measured, predicted)
    passed = nrmse <= 20.0 and median_ape <= 25.0 and peak_error <= 20.0 and rho >= 0.95
    return MassFlowCaseResult(
        experiment=trace.experiment,
        points=len(measured),
        measured_peak_g_s=float(np.max(measured)),
        predicted_peak_g_s=float(np.max(predicted)),
        nrmse_percent_peak_measured=nrmse,
        median_absolute_percentage_error_percent=median_ape,
        peak_relative_error_percent=peak_error,
        spearman_rho=rho,
        joint_primary_screen_pass=passed,
    )


def evaluate_directory(directory: Path) -> dict[str, object]:
    files = {int("".join(c for c in path.stem if c.isdigit())): path for path in directory.glob("Exp*.mat")}
    dispersion_results: list[DispersionCaseResult] = []
    mass_flow_results: list[MassFlowCaseResult] = []
    failures: list[dict[str, object]] = []
    for experiment in DISPERSION_CASES:
        path = files.get(experiment)
        if path is None:
            failures.append({"experiment": experiment, "stage": "dispersion", "reason": "missing file"})
            if experiment in BLOWDOWN_CASES:
                failures.append({"experiment": experiment, "stage": "mass_flow", "reason": "missing file"})
            continue
        try:
            trace = load_hytunnel_mat(path)
        except Exception as exc:  # preserve every data/schema/runtime failure
            failures.append({"experiment": experiment, "stage": "load", "reason": f"{type(exc).__name__}: {exc}"})
            continue
        try:
            dispersion_results.append(evaluate_dispersion_case(trace))
        except Exception as exc:  # one failed endpoint must not erase the other
            failures.append({"experiment": experiment, "stage": "dispersion", "reason": f"{type(exc).__name__}: {exc}"})
        if experiment in BLOWDOWN_CASES:
            try:
                mass_flow_results.append(evaluate_mass_flow_case(trace))
            except Exception as exc:
                failures.append({"experiment": experiment, "stage": "mass_flow", "reason": f"{type(exc).__name__}: {exc}"})

    dispersion_passes = sum(item.joint_primary_screen_pass for item in dispersion_results)
    mass_flow_passes = sum(item.joint_primary_screen_pass for item in mass_flow_results)
    dispersion_joint = len(dispersion_results) == len(DISPERSION_CASES) and dispersion_passes / len(DISPERSION_CASES) >= 0.70
    mass_flow_joint = len(mass_flow_results) == len(BLOWDOWN_CASES) and mass_flow_passes >= 4
    return {
        "dispersion": {
            "cases": [asdict(item) for item in dispersion_results],
            "eligible_case_count": len(dispersion_results),
            "pass_count": dispersion_passes,
            "pass_fraction_of_declared_cases": dispersion_passes / len(DISPERSION_CASES),
            "joint_screen_pass": dispersion_joint,
        },
        "mass_flow": {
            "cases": [asdict(item) for item in mass_flow_results],
            "eligible_case_count": len(mass_flow_results),
            "pass_count": mass_flow_passes,
            "pass_fraction_of_declared_cases": mass_flow_passes / len(BLOWDOWN_CASES),
            "joint_screen_pass": mass_flow_joint,
        },
        "failures": failures,
    }


__all__ = [
    "BLOWDOWN_CASES",
    "DISPERSION_CASES",
    "HyTunnelTrace",
    "evaluate_directory",
    "evaluate_dispersion_case",
    "evaluate_mass_flow_case",
    "load_hytunnel_mat",
    "simulate_well_mixed_concentration",
]
