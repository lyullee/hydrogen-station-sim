"""Deterministic bounded uncertainty propagation for consequence screening."""

from __future__ import annotations

from dataclasses import replace
import math
from statistics import mean
from typing import Any, Callable, Mapping

import numpy as np

from .live import HyRAMDynamicReleaseRequest


OUTPUTS = (
    "mass_flow_override_kg_s",
    "sampled_effect_radius_m",
    "maximum_heat_flux_w_m2",
    "maximum_overpressure_pa",
    "flammable_plume_streamline_distance_m",
    "risk_score_0_100",
)


def _scaled_flow(base: HyRAMDynamicReleaseRequest, *, pressure: float,
                 temperature: float, diameter: float, coefficient: float) -> float:
    """Scale the declared point flow with the choked-flow leading terms."""

    pressure_ratio = max(pressure - base.ambient_pressure_pa, 0.0) / max(
        base.source_pressure_pa - base.ambient_pressure_pa, 1.0
    )
    return max(0.0, base.mass_flow_override_kg_s * pressure_ratio *
               math.sqrt(base.source_temperature_k / temperature) *
               (diameter / base.orifice_diameter_m) ** 2 *
               (coefficient / base.discharge_coefficient))


def consequence_uncertainty_screen(
    evaluator: Callable[[HyRAMDynamicReleaseRequest], Mapping[str, Any]],
    request: HyRAMDynamicReleaseRequest,
    *,
    sample_count: int = 24,
    pressure_relative: float = 0.03,
    temperature_k: float = 3.0,
    diameter_relative: float = 0.10,
    discharge_coefficient_relative: float = 0.12,
    seed: int = 731,
) -> dict[str, Any]:
    """Propagate declared bounded inputs through the consequence evaluator.

    The samples are a reproducible sensitivity ensemble.  Their percentiles
    are not confidence intervals and do not establish a safety distance.
    """

    if not 8 <= sample_count <= 128:
        raise ValueError("sample_count must be between 8 and 128")
    bounds = {
        "source_pressure_pa": pressure_relative,
        "source_temperature_k": temperature_k,
        "orifice_diameter_m": diameter_relative,
        "discharge_coefficient": discharge_coefficient_relative,
    }
    if any(not math.isfinite(float(value)) or value < 0 for value in bounds.values()):
        raise ValueError("uncertainty bounds must be finite and non-negative")

    rng = np.random.default_rng(seed)
    unit = (np.arange(sample_count, dtype=float) + 0.5) / sample_count
    columns = []
    for _ in range(4):
        values = 2.0 * unit - 1.0
        rng.shuffle(values)
        columns.append(values.copy())

    records: list[dict[str, float]] = []
    inputs: list[dict[str, float]] = []
    for index in range(sample_count):
        pressure = request.source_pressure_pa * (1 + pressure_relative * columns[0][index])
        temperature = max(1.0, request.source_temperature_k + temperature_k * columns[1][index])
        diameter = request.orifice_diameter_m * (1 + diameter_relative * columns[2][index])
        coefficient = request.discharge_coefficient * (
            1 + discharge_coefficient_relative * columns[3][index]
        )
        flow = _scaled_flow(request, pressure=pressure, temperature=temperature,
                            diameter=diameter, coefficient=coefficient)
        sampled = replace(
            request,
            source_pressure_pa=pressure,
            source_temperature_k=temperature,
            orifice_diameter_m=diameter,
            discharge_coefficient=coefficient,
            mass_flow_override_kg_s=flow,
        )
        raw = dict(evaluator(sampled))
        records.append({key: float(raw[key]) for key in OUTPUTS
                        if raw.get(key) is not None and
                        math.isfinite(float(raw[key]))})
        inputs.append({
            "source_pressure_pa": pressure,
            "source_temperature_k": temperature,
            "orifice_diameter_m": diameter,
            "discharge_coefficient": coefficient,
        })

    percentiles: dict[str, dict[str, float | int]] = {}
    for key in OUTPUTS:
        values = [row[key] for row in records if key in row]
        if values:
            p05, p50, p95 = np.percentile(values, [5, 50, 95])
            percentiles[key] = {"p05": float(p05), "p50": float(p50),
                                "p95": float(p95), "sample_count": len(values)}

    target = "sampled_effect_radius_m" if "sampled_effect_radius_m" in percentiles else (
        "maximum_heat_flux_w_m2" if "maximum_heat_flux_w_m2" in percentiles else None
    )
    sensitivity: list[dict[str, float | str]] = []
    if target:
        y = np.asarray([row.get(target, math.nan) for row in records], dtype=float)
        valid = np.isfinite(y)
        for key in bounds:
            x = np.asarray([row[key] for row in inputs], dtype=float)
            coefficient = float(np.corrcoef(x[valid], y[valid])[0, 1]) if valid.sum() > 2 else 0.0
            if not math.isfinite(coefficient):
                coefficient = 0.0
            sensitivity.append({"input": key, "target": target,
                                "pearson_linear_correlation": coefficient,
                                "absolute_importance": abs(coefficient)})
        sensitivity.sort(key=lambda row: float(row["absolute_importance"]), reverse=True)

    return {
        "status": "BOUNDED_SENSITIVITY_CALCULATED",
        "method": "deterministic_stratified_parameter_screen",
        "seed": seed,
        "sample_count": sample_count,
        "declared_bounds": bounds,
        "percentiles": percentiles,
        "sensitivity_ranking": sensitivity,
        "successful_output_fraction": mean(
            len(row) > 0 for row in records
        ),
        "claim_limit": (
            "P05/P50/P95 are percentiles of the declared sensitivity ensemble, "
            "not statistical confidence intervals, validated evacuation radii, "
            "or site-specific safety distances."
        ),
    }
