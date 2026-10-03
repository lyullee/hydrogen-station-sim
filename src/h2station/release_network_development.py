"""Development-only diagnostics for series restrictions in hydrogen releases.

This module deliberately contains no validation decision.  The Proust data used
to select the equivalent restriction and the Imamura values used to inspect its
transfer had already been viewed, so every result produced here is consumed
development evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt
from typing import Iterable

import numpy as np

from .preslhy_nonadiabatic import _CoolPropHydrogen


@dataclass(frozen=True, slots=True)
class ReleaseObservation:
    series_id: str
    diameter_mm: float
    source_pressure_pa_abs: float
    source_temperature_k: float
    measured_mass_flow_kg_s: float


@dataclass(frozen=True, slots=True)
class DevelopmentSeriesMetrics:
    series_id: str
    diameter_mm: float
    points: int
    measured_peak_g_s: float
    predicted_peak_g_s: float
    nrmse_percent_peak_measured: float
    median_absolute_percentage_error_percent: float
    within_reference_screen: bool


def aperture_area_m2(diameter_mm: float) -> float:
    if diameter_mm <= 0.0:
        raise ValueError("diameter must be positive")
    return pi * (diameter_mm / 1000.0) ** 2 / 4.0


def series_effective_conductance_m2(
    *,
    nozzle_diameter_mm: float,
    nozzle_discharge_coefficient: float,
    supply_diameter_mm: float,
    supply_discharge_coefficient: float,
) -> float:
    """Combine two choked restrictions using a diagnostic conductance rule.

    The relation is an engineering development approximation, not a substitute
    for a resolved valve/pipe control volume.
    """

    if nozzle_discharge_coefficient <= 0.0 or supply_discharge_coefficient <= 0.0:
        raise ValueError("discharge coefficients must be positive")
    nozzle = nozzle_discharge_coefficient * aperture_area_m2(nozzle_diameter_mm)
    supply = supply_discharge_coefficient * aperture_area_m2(supply_diameter_mm)
    return 1.0 / sqrt(1.0 / nozzle**2 + 1.0 / supply**2)


def predict_observations(
    observations: Iterable[ReleaseObservation],
    *,
    nozzle_discharge_coefficient: float,
    supply_diameter_mm: float | None = None,
    supply_discharge_coefficient: float = 0.8,
    downstream_pressure_pa: float = 101_325.0,
) -> np.ndarray:
    eos = _CoolPropHydrogen()
    predictions: list[float] = []
    for point in observations:
        if supply_diameter_mm is None:
            conductance = (
                nozzle_discharge_coefficient * aperture_area_m2(point.diameter_mm)
            )
        else:
            conductance = series_effective_conductance_m2(
                nozzle_diameter_mm=point.diameter_mm,
                nozzle_discharge_coefficient=nozzle_discharge_coefficient,
                supply_diameter_mm=supply_diameter_mm,
                supply_discharge_coefficient=supply_discharge_coefficient,
            )
        flux = eos.isentropic_mass_flux(
            point.source_pressure_pa_abs,
            point.source_temperature_k,
            downstream_pressure_pa,
        )
        predictions.append(conductance * flux)
    return np.asarray(predictions, dtype=float)


def evaluate_development_series(
    observations: Iterable[ReleaseObservation],
    predicted_mass_flow_kg_s: Iterable[float],
    *,
    nrmse_reference_percent: float = 15.0,
    median_ape_reference_percent: float = 20.0,
) -> DevelopmentSeriesMetrics:
    points = list(observations)
    predicted = np.asarray(list(predicted_mass_flow_kg_s), dtype=float)
    if not points or predicted.size != len(points):
        raise ValueError("observations and predictions must be non-empty and aligned")
    series_ids = {point.series_id for point in points}
    diameters = {point.diameter_mm for point in points}
    if len(series_ids) != 1 or len(diameters) != 1:
        raise ValueError("one series and one diameter are required")
    measured = np.asarray([point.measured_mass_flow_kg_s for point in points])
    if np.any(measured <= 0.0) or np.any(predicted < 0.0):
        raise ValueError("mass-flow values must be physical")
    peak = float(np.max(measured))
    nrmse = float(np.sqrt(np.mean((predicted - measured) ** 2)) / peak * 100.0)
    mask = measured >= 0.1 * peak
    median_ape = float(
        np.median(np.abs(predicted[mask] - measured[mask]) / measured[mask]) * 100.0
    )
    return DevelopmentSeriesMetrics(
        series_id=next(iter(series_ids)),
        diameter_mm=next(iter(diameters)),
        points=len(points),
        measured_peak_g_s=peak * 1000.0,
        predicted_peak_g_s=float(np.max(predicted)) * 1000.0,
        nrmse_percent_peak_measured=nrmse,
        median_absolute_percentage_error_percent=median_ape,
        within_reference_screen=(
            nrmse <= nrmse_reference_percent
            and median_ape <= median_ape_reference_percent
        ),
    )
