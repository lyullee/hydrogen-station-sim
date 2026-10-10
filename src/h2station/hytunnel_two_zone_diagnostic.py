"""A claim-bounded two-zone development model for the HyTunnel enclosure.

The frozen HyTunnel holdout deliberately uses a zero-dimensional well-mixed
balance.  This module is a separate post-outcome development diagnostic.  It
adds one physically declared transport state: a source-to-vent zone followed
by a bulk zone.  The zone length is taken from the published experiment
geometry (source 5 m from the ventilation wall in a 40 ft container); no
case-specific fitting, sensor selection, time shifting or threshold changes
are performed.

The model is intentionally not wired into the production runtime or the
frozen readiness gate.  The public MAT files do not contain an authoritative
sensor-coordinate crosswalk, so the result is a mean-concentration transport
diagnostic only.  It cannot support detector-placement, plume-shape or HRS
consequence-distance claims.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Iterable

import numpy as np

from .hytunnel_carpark_validation import (
    AMBIENT_PRESSURE_PA,
    AMBIENT_TEMPERATURE_K,
    CONTAINER_VOLUME_M3,
    DISPERSION_CASES,
    HyTunnelTrace,
    _duration_above,
    _hydrogen_density_ambient,
    _metrics,
    _series_on_time,
    load_hytunnel_mat,
)


@dataclass(frozen=True, slots=True)
class TwoZoneInputs:
    """Geometry-derived parameters for the development transport model."""

    container_volume_m3: float = CONTAINER_VOLUME_M3
    enclosure_length_m: float = 12.192  # 40 ft ISO container
    source_to_vent_wall_m: float = 5.0
    cross_section_area_m2: float = 2.4384 * 2.5908

    def __post_init__(self) -> None:
        for name in (
            "container_volume_m3",
            "enclosure_length_m",
            "source_to_vent_wall_m",
            "cross_section_area_m2",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be positive and finite")
        if self.source_to_vent_wall_m >= self.enclosure_length_m:
            raise ValueError("source_to_vent_wall_m must be shorter than enclosure_length_m")

    @property
    def source_zone_fraction(self) -> float:
        return self.source_to_vent_wall_m / self.enclosure_length_m

    @property
    def source_zone_volume_m3(self) -> float:
        return self.container_volume_m3 * self.source_zone_fraction

    @property
    def bulk_zone_volume_m3(self) -> float:
        return self.container_volume_m3 - self.source_zone_volume_m3

    def as_dict(self) -> dict[str, float]:
        return {
            "container_volume_m3": self.container_volume_m3,
            "enclosure_length_m": self.enclosure_length_m,
            "source_to_vent_wall_m": self.source_to_vent_wall_m,
            "cross_section_area_m2": self.cross_section_area_m2,
            "source_zone_fraction": self.source_zone_fraction,
            "source_zone_volume_m3": self.source_zone_volume_m3,
            "bulk_zone_volume_m3": self.bulk_zone_volume_m3,
        }


@dataclass(frozen=True, slots=True)
class TwoZoneCaseResult:
    experiment: int
    points: int
    measured_peak_volpct: float
    predicted_peak_volpct: float
    nrmse_percent_peak_measured: float
    median_absolute_percentage_error_percent: float
    peak_relative_error_percent: float
    spearman_rho: float
    measured_flammable_duration_s: float
    predicted_flammable_duration_s: float
    joint_primary_screen_pass: bool


def _aligned_inputs(trace: HyTunnelTrace) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Apply the frozen time-support rule without changing its thresholds."""

    time = np.asarray(trace.sensor_time_s, dtype=float)
    concentration = np.asarray(trace.concentration_volpct, dtype=float)
    valid_time = np.isfinite(time) & (time >= trace.release_start_s)
    if np.count_nonzero(valid_time) < 30:
        raise ValueError("fewer than 30 post-release concentration samples")
    time = time[valid_time]
    concentration = concentration[valid_time]
    measured_mean = np.nanmean(concentration, axis=1)
    flow = _series_on_time(trace.mass_flow_g_s, trace.mass_flow_time_s, time, "MFM.mfr")
    ventilation = _series_on_time(
        trace.ventilation_m3_h, trace.ventilation_time_s, time, "Vent.vfr"
    )
    synchronized = np.isfinite(measured_mean) & np.isfinite(flow) & np.isfinite(ventilation)
    time = time[synchronized]
    measured_mean = measured_mean[synchronized]
    flow = flow[synchronized]
    ventilation = ventilation[synchronized]
    if time.size < 30:
        raise ValueError("fewer than 30 samples on the common concentration, flow and ventilation support")
    return time, measured_mean, np.maximum(flow, 0.0) / 1000.0, np.maximum(ventilation, 0.0) / 3600.0


def _advance_two_zone(
    source_fraction: float,
    bulk_fraction: float,
    source_rate_fraction_s: float,
    ventilation_m3_s: float,
    dt_s: float,
    *,
    inputs: TwoZoneInputs,
) -> tuple[float, float]:
    """Advance the coupled source/bulk balances exactly for constant inputs."""

    if dt_s <= 0.0 or not math.isfinite(dt_s):
        raise ValueError("dt_s must be positive and finite")
    if ventilation_m3_s <= 0.0:
        # No forced exchange: release accumulates in the source zone.
        return source_fraction + source_rate_fraction_s * dt_s, bulk_fraction
    source_volume = inputs.source_zone_volume_m3
    bulk_volume = inputs.bulk_zone_volume_m3
    source_rate = ventilation_m3_s / source_volume
    bulk_rate = ventilation_m3_s / bulk_volume
    source_equilibrium = source_rate_fraction_s / source_rate
    exp_source = math.exp(-source_rate * dt_s)
    exp_bulk = math.exp(-bulk_rate * dt_s)
    source_delta = source_fraction - source_equilibrium
    next_source = source_equilibrium + source_delta * exp_source
    if abs(source_rate - bulk_rate) <= 1.0e-12 * max(source_rate, bulk_rate):
        convolution = bulk_rate * dt_s * exp_bulk
    else:
        convolution = bulk_rate * (exp_source - exp_bulk) / (bulk_rate - source_rate)
    next_bulk = (
        bulk_fraction * exp_bulk
        + source_equilibrium * (1.0 - exp_bulk)
        + source_delta * convolution
    )
    return max(next_source, 0.0), max(next_bulk, 0.0)


def simulate_two_zone_concentration(
    trace: HyTunnelTrace,
    *,
    inputs: TwoZoneInputs | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return time, measured mean, predicted mean, source-zone and bulk fractions."""

    inputs = inputs or TwoZoneInputs()
    time, measured, flow_m3_s, ventilation_m3_s = _aligned_inputs(trace)
    density = _hydrogen_density_ambient()
    source = max(float(measured[0]) / 100.0, 0.0)
    bulk = source
    source_values = np.empty_like(time)
    bulk_values = np.empty_like(time)
    predicted = np.empty_like(time)
    source_values[0] = source
    bulk_values[0] = bulk
    predicted[0] = source * inputs.source_zone_fraction + bulk * (1.0 - inputs.source_zone_fraction)
    for index in range(1, len(time)):
        dt = float(time[index] - time[index - 1])
        source_rate = flow_m3_s[index - 1] / density / inputs.source_zone_volume_m3
        source, bulk = _advance_two_zone(
            source,
            bulk,
            source_rate,
            float(ventilation_m3_s[index - 1]),
            dt,
            inputs=inputs,
        )
        source = float(np.clip(source, 0.0, 1.0))
        bulk = float(np.clip(bulk, 0.0, 1.0))
        source_values[index] = source
        bulk_values[index] = bulk
        predicted[index] = source * inputs.source_zone_fraction + bulk * (1.0 - inputs.source_zone_fraction)
    return time, measured, predicted * 100.0, source_values * 100.0, bulk_values * 100.0


def evaluate_two_zone_case(
    trace: HyTunnelTrace,
    *,
    inputs: TwoZoneInputs | None = None,
) -> TwoZoneCaseResult:
    time, measured, predicted, _source, _bulk = simulate_two_zone_concentration(
        trace, inputs=inputs
    )
    nrmse, median_ape, peak_error, rho = _metrics(measured, predicted)
    passed = nrmse <= 40.0 and median_ape <= 50.0 and peak_error <= 50.0 and rho >= 0.6
    return TwoZoneCaseResult(
        experiment=trace.experiment,
        points=len(time),
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


def evaluate_directory(
    directory: Path,
    *,
    experiments: Iterable[int] = DISPERSION_CASES,
    inputs: TwoZoneInputs | None = None,
) -> dict[str, object]:
    experiment_list = tuple(int(experiment) for experiment in experiments)
    files = {
        int("".join(character for character in path.stem if character.isdigit())): path
        for path in directory.glob("Exp*.mat")
    }
    results: list[TwoZoneCaseResult] = []
    failures: list[dict[str, object]] = []
    for experiment in experiment_list:
        path = files.get(int(experiment))
        if path is None:
            failures.append({"experiment": int(experiment), "reason": "missing file"})
            continue
        try:
            results.append(evaluate_two_zone_case(load_hytunnel_mat(path), inputs=inputs))
        except Exception as exc:  # preserve every case-level failure
            failures.append(
                {"experiment": int(experiment), "reason": f"{type(exc).__name__}: {exc}"}
            )
    pass_count = sum(item.joint_primary_screen_pass for item in results)
    return {
        "model": "geometry_declared_two_zone_source_to_vent_transport",
        "inputs": (inputs or TwoZoneInputs()).as_dict(),
        "cases": [asdict(item) for item in results],
        "eligible_case_count": len(results),
        "pass_count": pass_count,
        "pass_fraction_of_declared_cases": pass_count / len(experiment_list)
        if experiment_list
        else 0.0,
        "failures": failures,
    }


__all__ = [
    "TwoZoneInputs",
    "TwoZoneCaseResult",
    "simulate_two_zone_concentration",
    "evaluate_two_zone_case",
    "evaluate_directory",
]
