"""Prospective validation helpers for the Proust et al. 90 MPa releases.

The published campaign reports a 25 L Type-IV source, a 10 m by 10 mm supply
line and 1--3 mm terminal orifices.  This module evaluates only the local
real-gas discharge relation at digitized measured source states.  It does not
claim to reproduce the vessel-wall transient, supply-line inventory or flame.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from pathlib import Path

import numpy as np

from .preslhy_nonadiabatic import _CoolPropHydrogen


@dataclass(frozen=True, slots=True)
class ProustReleasePoint:
    case_id: str
    nozzle_diameter_mm: float
    source_pressure_pa_abs: float
    source_temperature_k: float
    measured_mass_flow_kg_s: float
    digitization_uncertainty_kg_s: float
    source_figure: str
    point_index: int


@dataclass(frozen=True, slots=True)
class ProustSeriesResult:
    case_id: str
    nozzle_diameter_mm: float
    points: int
    pressure_min_mpa_abs: float
    pressure_max_mpa_abs: float
    measured_peak_mass_flow_g_s: float
    predicted_peak_mass_flow_g_s: float
    mass_flow_nrmse_percent_peak_measured: float
    median_absolute_percentage_error_percent: float
    digitization_interval_coverage_fraction: float
    nrmse_screen_pass: bool
    median_ape_screen_pass: bool
    joint_primary_screen_pass: bool


def load_digitized_points(path: str | Path) -> list[ProustReleasePoint]:
    """Load the prospectively specified long-form digitization CSV."""

    data = np.genfromtxt(path, delimiter=",", names=True, dtype=None, encoding="utf-8")
    if data.shape == ():
        rows = [data]
    else:
        rows = list(data)
    required = {
        "case_id", "nozzle_diameter_mm", "source_pressure_mpa_abs",
        "source_temperature_k", "measured_mass_flow_g_s",
        "digitization_uncertainty_g_s", "source_figure", "point_index",
    }
    names = set(data.dtype.names or ())
    missing = required - names
    if missing:
        raise ValueError(f"digitization CSV missing columns: {sorted(missing)}")
    points: list[ProustReleasePoint] = []
    for row in rows:
        point = ProustReleasePoint(
            case_id=str(row["case_id"]),
            nozzle_diameter_mm=float(row["nozzle_diameter_mm"]),
            source_pressure_pa_abs=float(row["source_pressure_mpa_abs"]) * 1.0e6,
            source_temperature_k=float(row["source_temperature_k"]),
            measured_mass_flow_kg_s=float(row["measured_mass_flow_g_s"]) / 1000.0,
            digitization_uncertainty_kg_s=(
                float(row["digitization_uncertainty_g_s"]) / 1000.0
            ),
            source_figure=str(row["source_figure"]),
            point_index=int(row["point_index"]),
        )
        _validate_point(point)
        points.append(point)
    if len({(p.case_id, p.point_index) for p in points}) != len(points):
        raise ValueError("duplicate case_id/point_index rows")
    return points


def _validate_point(point: ProustReleasePoint) -> None:
    values = (
        point.nozzle_diameter_mm,
        point.source_pressure_pa_abs,
        point.source_temperature_k,
        point.measured_mass_flow_kg_s,
        point.digitization_uncertainty_kg_s,
    )
    if not all(np.isfinite(values)):
        raise ValueError("all numerical values must be finite")
    if not 1.0 <= point.nozzle_diameter_mm <= 3.0:
        raise ValueError("nozzle diameter outside the published 1--3 mm domain")
    if not 2.0e6 <= point.source_pressure_pa_abs <= 95.0e6:
        raise ValueError("source pressure outside the frozen 2--95 MPa window")
    if not 220.0 <= point.source_temperature_k <= 330.0:
        raise ValueError("source temperature outside the frozen measured window")
    if point.measured_mass_flow_kg_s <= 0.0:
        raise ValueError("measured mass flow must be positive")
    if point.digitization_uncertainty_kg_s < 0.0:
        raise ValueError("digitization uncertainty cannot be negative")


def predict_mass_flow_kg_s(
    point: ProustReleasePoint,
    *,
    discharge_coefficient: float = 0.8,
    downstream_pressure_pa: float = 101_325.0,
) -> float:
    """Evaluate the already-developed real-gas isentropic aperture model."""

    eos = _CoolPropHydrogen()
    area = pi * (point.nozzle_diameter_mm / 1000.0) ** 2 / 4.0
    flux = eos.isentropic_mass_flux(
        point.source_pressure_pa_abs,
        point.source_temperature_k,
        downstream_pressure_pa,
    )
    return discharge_coefficient * area * flux


def evaluate_series(
    points: list[ProustReleasePoint],
    *,
    discharge_coefficient: float = 0.8,
) -> ProustSeriesResult:
    """Apply frozen series-level screens without point or case fitting."""

    if len(points) < 8:
        raise ValueError("a primary series requires at least eight digitized states")
    case_ids = {point.case_id for point in points}
    diameters = {point.nozzle_diameter_mm for point in points}
    if len(case_ids) != 1 or len(diameters) != 1:
        raise ValueError("each evaluated series must contain one case and diameter")
    ordered = sorted(points, key=lambda point: point.source_pressure_pa_abs)
    measured = np.asarray([p.measured_mass_flow_kg_s for p in ordered])
    predicted = np.asarray([
        predict_mass_flow_kg_s(p, discharge_coefficient=discharge_coefficient)
        for p in ordered
    ])
    peak = float(np.max(measured))
    nrmse = float(np.sqrt(np.mean((predicted - measured) ** 2)) / peak * 100.0)
    relative_mask = measured >= 0.1 * peak
    median_ape = float(np.median(
        np.abs(predicted[relative_mask] - measured[relative_mask])
        / measured[relative_mask]
    ) * 100.0)
    lower = measured - np.asarray([p.digitization_uncertainty_kg_s for p in ordered])
    upper = measured + np.asarray([p.digitization_uncertainty_kg_s for p in ordered])
    coverage = float(np.mean((predicted >= lower) & (predicted <= upper)))
    nrmse_pass = nrmse <= 15.0
    median_pass = median_ape <= 20.0
    return ProustSeriesResult(
        case_id=next(iter(case_ids)),
        nozzle_diameter_mm=next(iter(diameters)),
        points=len(points),
        pressure_min_mpa_abs=min(p.source_pressure_pa_abs for p in points) / 1.0e6,
        pressure_max_mpa_abs=max(p.source_pressure_pa_abs for p in points) / 1.0e6,
        measured_peak_mass_flow_g_s=peak * 1000.0,
        predicted_peak_mass_flow_g_s=float(np.max(predicted)) * 1000.0,
        mass_flow_nrmse_percent_peak_measured=nrmse,
        median_absolute_percentage_error_percent=median_ape,
        digitization_interval_coverage_fraction=coverage,
        nrmse_screen_pass=nrmse_pass,
        median_ape_screen_pass=median_pass,
        joint_primary_screen_pass=nrmse_pass and median_pass,
    )

