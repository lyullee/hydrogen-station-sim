"""Post-outcome non-adiabatic sensitivity diagnostic for Schefer (2007).

The locked Schefer holdout remains in :mod:`schefer_2007_validation` and is
never changed by this module.  The public apparatus summary does not resolve
the vessel wall, line inventory, or valve-opening profile, so this diagnostic
reports a declared parameter envelope rather than selecting a fitted model.
Its output is useful for deciding whether a future, untouched release should
include wall heat transfer; it cannot promote the existing holdout claim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import pi
from pathlib import Path

import numpy as np

from .preslhy_nonadiabatic import DischaVesselParameters, simulate_nonadiabatic_blowdown
from .preslhy_validation import PreslhyTrace
from .schefer_2007_validation import Schefer2007PressureTrace


@dataclass(frozen=True, slots=True)
class ScheferNonadiabaticDiagnosticParameters:
    """One declared physical sensitivity point, never a fitted runtime value."""

    wall_heat_capacity_j_k: float
    external_heat_transfer_w_m2_k: float
    equivalent_internal_diameter_m: float = 1.0
    wall_specific_heat_j_kg_k: float = 500.0
    discharge_coefficient: float = 1.0

    @property
    def wall_mass_kg(self) -> float:
        return self.wall_heat_capacity_j_k / self.wall_specific_heat_j_kg_k

    @property
    def equivalent_internal_height_m(self) -> float:
        # The source reports total volume but not the tank aspect ratio.  A
        # one-metre equivalent diameter is an explicit geometry proxy used
        # only to expose sensitivity, not to assert the apparatus geometry.
        return 1.234 / (pi * self.equivalent_internal_diameter_m**2 / 4.0)


@dataclass(frozen=True, slots=True)
class ScheferNonadiabaticDiagnosticMetrics:
    wall_heat_capacity_j_k: float
    external_heat_transfer_w_m2_k: float
    pressure_nrmse_percent_initial_measured: float
    median_absolute_percentage_error_percent: float
    half_pressure_time_relative_error_percent: float
    nrmse_screen_pass: bool
    median_ape_screen_pass: bool
    half_pressure_time_screen_pass: bool
    joint_primary_screen_pass: bool


def _as_preslhy_trace(trace: Schefer2007PressureTrace) -> PreslhyTrace:
    """Adapt the figure digitization without changing its values."""

    return PreslhyTrace(
        case_id="schefer-2007-fig4-post-outcome-diagnostic",
        source_package="HyRAM+ digitized Figure 4",
        source_member="schefer-2007-fig4.csv",
        nozzle_diameter_mm=5.08,
        time_s=trace.time_s,
        pressure_bar_abs=trace.measured_pressure_psi * 0.06894757293168,
        initial_temperature_k=290.0,
        ambient_pressure_pa=101_325.0,
        pressure_unit_interpretation="psi_absolute_digitized_to_bar_absolute",
        temperature_substituted=True,
        ambient_pressure_substituted=True,
    )


def _declining_crossing_time(time_s: np.ndarray, values: np.ndarray, target: float) -> float:
    reached = np.flatnonzero(values <= target)
    if not reached.size:
        return float("nan")
    index = int(reached[0])
    if index == 0:
        return float(time_s[0])
    t0, t1 = float(time_s[index - 1]), float(time_s[index])
    v0, v1 = float(values[index - 1]), float(values[index])
    if v1 == v0:
        return t1
    return t0 + (target - v0) * (t1 - t0) / (v1 - v0)


def evaluate_sensitivity_point(
    trace: Schefer2007PressureTrace,
    parameters: ScheferNonadiabaticDiagnosticParameters,
) -> ScheferNonadiabaticDiagnosticMetrics:
    """Evaluate one declared sensitivity point against the already-public trace."""

    source = _as_preslhy_trace(trace)
    model_parameters = DischaVesselParameters(
        internal_volume_m3=1.234,
        internal_diameter_m=parameters.equivalent_internal_diameter_m,
        internal_height_m=parameters.equivalent_internal_height_m,
        wall_mass_kg=parameters.wall_mass_kg,
        wall_specific_heat_j_kg_k=parameters.wall_specific_heat_j_kg_k,
        external_heat_transfer_w_m2_k=parameters.external_heat_transfer_w_m2_k,
        ambient_temperature_k=290.0,
        discharge_coefficient=parameters.discharge_coefficient,
    )
    simulated = simulate_nonadiabatic_blowdown(source, trace.time_s, parameters=model_parameters)
    measured = trace.measured_pressure_psi
    predicted = simulated.pressure_pa / 6_894.757293168
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
    return ScheferNonadiabaticDiagnosticMetrics(
        wall_heat_capacity_j_k=parameters.wall_heat_capacity_j_k,
        external_heat_transfer_w_m2_k=parameters.external_heat_transfer_w_m2_k,
        pressure_nrmse_percent_initial_measured=nrmse,
        median_absolute_percentage_error_percent=median_ape,
        half_pressure_time_relative_error_percent=half_error,
        nrmse_screen_pass=nrmse_pass,
        median_ape_screen_pass=median_pass,
        half_pressure_time_screen_pass=half_pass,
        joint_primary_screen_pass=nrmse_pass and median_pass and half_pass,
    )


def evaluate_declared_sensitivity_envelope(
    trace: Schefer2007PressureTrace,
    *,
    wall_heat_capacities_j_k: tuple[float, ...] = (1.0e5, 5.0e5, 1.0e6, 5.0e6),
    external_heat_transfer_coefficients_w_m2_k: tuple[float, ...] = (2.0, 6.0, 12.0, 25.0),
) -> list[ScheferNonadiabaticDiagnosticMetrics]:
    """Return the full declared grid; no point is chosen or promoted."""

    return [
        evaluate_sensitivity_point(
            trace,
            ScheferNonadiabaticDiagnosticParameters(capacity, coefficient),
        )
        for capacity in wall_heat_capacities_j_k
        for coefficient in external_heat_transfer_coefficients_w_m2_k
    ]


def write_diagnostic_json(path: str | Path, metrics: list[ScheferNonadiabaticDiagnosticMetrics]) -> None:
    """Write a claim-bounded, reproducible diagnostic artifact."""

    import json

    payload = {
        "schema_version": 1,
        "status": "post_outcome_sensitivity_diagnostic_only",
        "model_changed": False,
        "runtime_promotion": False,
        "holdout_gate_promotion": False,
        "apparatus_boundary": {
            "total_vessel_volume_m3": 1.234,
            "published_restriction_diameter_mm": 5.08,
            "wall_geometry_and_line_inventory_resolved": False,
        },
        "metrics": [asdict(item) for item in metrics],
        "claim_boundary": (
            "The grid exposes sensitivity to declared wall heat-transfer assumptions. "
            "It is post-outcome because the digitized pressure trace was already used "
            "by the frozen holdout, and it cannot establish an independent validation claim."
        ),
    }
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


__all__ = [
    "ScheferNonadiabaticDiagnosticMetrics",
    "ScheferNonadiabaticDiagnosticParameters",
    "evaluate_declared_sensitivity_envelope",
    "evaluate_sensitivity_point",
    "write_diagnostic_json",
]
