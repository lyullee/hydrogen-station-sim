"""Apparatus-resolved hydrogen release network for prospective development.

The frozen Schefer/Proust evaluators intentionally model a local aperture or a
well-mixed vessel.  This module is a separate development model that represents
the minimum additional state needed for an apparatus with a supply line:

* a source vessel and a line control volume,
* a finite valve opening law,
* upstream and terminal restrictions, and
* lumped gas/wall thermal states for both control volumes.

It is not wired into the production station runtime and carries no validation
claim.  A future holdout must freeze the geometry, valve law and scoring before
any numerical outcome is inspected.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi

import numpy as np
from scipy.integrate import solve_ivp

from .preslhy_nonadiabatic import _CoolPropHydrogen


@dataclass(frozen=True, slots=True)
class ReleaseNetworkInputs:
    """Geometry and initial conditions for a two-volume release network."""

    source_volume_m3: float
    source_pressure_pa_abs: float
    source_temperature_k: float
    line_volume_m3: float
    line_initial_pressure_pa_abs: float = 101_325.0
    line_initial_temperature_k: float = 293.15
    upstream_diameter_m: float = 0.003175
    upstream_discharge_coefficient: float = 1.0
    terminal_diameter_m: float = 0.00794
    terminal_discharge_coefficient: float = 1.0
    valve_opening_time_s: float = 0.05
    source_wall_mass_kg: float = 0.0
    line_wall_mass_kg: float = 0.0
    wall_specific_heat_j_kg_k: float = 500.0
    source_internal_area_m2: float = 0.0
    line_internal_area_m2: float = 0.0
    source_external_area_m2: float = 0.0
    line_external_area_m2: float = 0.0
    source_wall_temperature_k: float | None = None
    line_wall_temperature_k: float | None = None
    internal_heat_transfer_w_m2_k: float = 0.0
    external_heat_transfer_w_m2_k: float = 0.0
    ambient_temperature_k: float = 293.15
    ambient_pressure_pa: float = 101_325.0

    def __post_init__(self) -> None:
        positive = {
            "source_volume_m3": self.source_volume_m3,
            "source_pressure_pa_abs": self.source_pressure_pa_abs,
            "source_temperature_k": self.source_temperature_k,
            "line_volume_m3": self.line_volume_m3,
            "line_initial_pressure_pa_abs": self.line_initial_pressure_pa_abs,
            "line_initial_temperature_k": self.line_initial_temperature_k,
            "upstream_diameter_m": self.upstream_diameter_m,
            "terminal_diameter_m": self.terminal_diameter_m,
            "wall_specific_heat_j_kg_k": self.wall_specific_heat_j_kg_k,
            "ambient_temperature_k": self.ambient_temperature_k,
        }
        for name, value in positive.items():
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be positive and finite")
        nonnegative = {
            "upstream_discharge_coefficient": self.upstream_discharge_coefficient,
            "terminal_discharge_coefficient": self.terminal_discharge_coefficient,
            "valve_opening_time_s": self.valve_opening_time_s,
            "source_wall_mass_kg": self.source_wall_mass_kg,
            "line_wall_mass_kg": self.line_wall_mass_kg,
            "source_internal_area_m2": self.source_internal_area_m2,
            "line_internal_area_m2": self.line_internal_area_m2,
            "source_external_area_m2": self.source_external_area_m2,
            "line_external_area_m2": self.line_external_area_m2,
            "internal_heat_transfer_w_m2_k": self.internal_heat_transfer_w_m2_k,
            "external_heat_transfer_w_m2_k": self.external_heat_transfer_w_m2_k,
        }
        for name, value in nonnegative.items():
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be non-negative and finite")
        if self.upstream_discharge_coefficient > 1.0 or self.terminal_discharge_coefficient > 1.0:
            raise ValueError("discharge coefficients cannot exceed one")

    @property
    def upstream_area_m2(self) -> float:
        return pi * self.upstream_diameter_m**2 / 4.0

    @property
    def terminal_area_m2(self) -> float:
        return pi * self.terminal_diameter_m**2 / 4.0

    @property
    def source_wall_capacity_j_k(self) -> float:
        return self.source_wall_mass_kg * self.wall_specific_heat_j_kg_k

    @property
    def line_wall_capacity_j_k(self) -> float:
        return self.line_wall_mass_kg * self.wall_specific_heat_j_kg_k


@dataclass(frozen=True, slots=True)
class ReleaseNetworkResult:
    time_s: np.ndarray
    source_pressure_pa_abs: np.ndarray
    line_pressure_pa_abs: np.ndarray
    source_temperature_k: np.ndarray
    line_temperature_k: np.ndarray
    source_wall_temperature_k: np.ndarray
    line_wall_temperature_k: np.ndarray
    source_mass_kg: np.ndarray
    line_mass_kg: np.ndarray
    upstream_mass_flow_kg_s: np.ndarray
    terminal_mass_flow_kg_s: np.ndarray


def _opening_fraction(time_s: float, opening_time_s: float) -> float:
    if opening_time_s <= 0.0:
        return 1.0
    return float(np.clip(time_s / opening_time_s, 0.0, 1.0))


def _gas_snapshot(eos: _CoolPropHydrogen, mass: float, energy: float, volume: float):
    minimum_mass = max(mass, 1.0e-12)
    state = eos.storage_from_rho_u(minimum_mass / volume, energy / minimum_mass)
    return float(state.p()), float(state.T()), float(state.hmass()), state


def simulate_release_network(
    evaluation_time_s: np.ndarray,
    *,
    inputs: ReleaseNetworkInputs,
) -> ReleaseNetworkResult:
    """Simulate a source-to-line-to-ambient release at requested timestamps.

    The two restrictions are directional and the line is a finite control
    volume.  Mass and energy crossing each boundary are explicit, so a future
    validation can compare either boundary flow without reconstructing hidden
    inventory.  No parameter fitting or data-dependent time shift occurs here.
    """

    requested = np.asarray(evaluation_time_s, dtype=float)
    if requested.ndim != 1 or len(requested) < 2 or requested[0] < 0.0:
        raise ValueError("evaluation_time_s must contain at least two non-negative times")
    if np.any(~np.isfinite(requested)) or np.any(np.diff(requested) <= 0.0):
        raise ValueError("evaluation_time_s must be finite and strictly increasing")

    eos = _CoolPropHydrogen()
    source_initial = eos.storage_from_pt(inputs.source_pressure_pa_abs, inputs.source_temperature_k)
    source_mass = float(source_initial.rhomass() * inputs.source_volume_m3)
    source_energy = float(source_mass * source_initial.umass())
    line_initial = eos.storage_from_pt(
        inputs.line_initial_pressure_pa_abs, inputs.line_initial_temperature_k
    )
    line_mass = float(line_initial.rhomass() * inputs.line_volume_m3)
    line_energy = float(line_mass * line_initial.umass())
    source_wall_temperature = (
        inputs.source_wall_temperature_k
        if inputs.source_wall_temperature_k is not None
        else inputs.source_temperature_k
    )
    line_wall_temperature = (
        inputs.line_wall_temperature_k
        if inputs.line_wall_temperature_k is not None
        else inputs.line_initial_temperature_k
    )
    source_wall_capacity = inputs.source_wall_capacity_j_k
    line_wall_capacity = inputs.line_wall_capacity_j_k
    initial = np.asarray(
        [source_mass, source_energy, line_mass, line_energy,
         source_wall_temperature, line_wall_temperature],
        dtype=float,
    )
    minimum_source_mass = max(source_mass * 1.0e-10, 1.0e-12)
    minimum_line_mass = max(line_mass * 1.0e-10, 1.0e-12)

    def quantities(time_s: float, vector: np.ndarray):
        source_m = max(float(vector[0]), minimum_source_mass)
        source_u = float(vector[1])
        line_m = max(float(vector[2]), minimum_line_mass)
        line_u = float(vector[3])
        source_p, source_t, source_h, source_state = _gas_snapshot(
            eos, source_m, source_u, inputs.source_volume_m3
        )
        line_p, line_t, line_h, line_state = _gas_snapshot(
            eos, line_m, line_u, inputs.line_volume_m3
        )
        opening = _opening_fraction(time_s, inputs.valve_opening_time_s)
        if source_p <= line_p * (1.0 + 1.0e-9):
            upstream = 0.0
        else:
            upstream = (
                opening
                * inputs.upstream_discharge_coefficient
                * inputs.upstream_area_m2
                * eos.isentropic_mass_flux(source_p, source_t, line_p)
            )
        if line_p <= inputs.ambient_pressure_pa * (1.0 + 1.0e-9):
            terminal = 0.0
        else:
            terminal = (
                inputs.terminal_discharge_coefficient
                * inputs.terminal_area_m2
                * eos.isentropic_mass_flux(line_p, line_t, inputs.ambient_pressure_pa)
            )
        upstream = min(upstream, source_m / 1.0e-4)
        terminal = min(terminal, line_m / 1.0e-4)
        source_wall_q = inputs.internal_heat_transfer_w_m2_k * inputs.source_internal_area_m2 * (
            float(vector[4]) - source_t
        )
        line_wall_q = inputs.internal_heat_transfer_w_m2_k * inputs.line_internal_area_m2 * (
            float(vector[5]) - line_t
        )
        return source_p, source_t, source_h, line_p, line_t, line_h, upstream, terminal, source_wall_q, line_wall_q, source_state, line_state

    def derivative(time_s: float, vector: np.ndarray) -> np.ndarray:
        source_p, source_t, source_h, line_p, line_t, line_h, upstream, terminal, source_wall_q, line_wall_q, _source_state, _line_state = quantities(time_s, vector)
        source_external_q = inputs.external_heat_transfer_w_m2_k * inputs.source_external_area_m2 * (
            inputs.ambient_temperature_k - float(vector[4])
        )
        line_external_q = inputs.external_heat_transfer_w_m2_k * inputs.line_external_area_m2 * (
            inputs.ambient_temperature_k - float(vector[5])
        )
        source_wall_derivative = 0.0
        line_wall_derivative = 0.0
        if source_wall_capacity > 0.0:
            source_wall_derivative = (-source_wall_q + source_external_q) / source_wall_capacity
        if line_wall_capacity > 0.0:
            line_wall_derivative = (-line_wall_q + line_external_q) / line_wall_capacity
        return np.asarray(
            [
                -upstream,
                -upstream * source_h + source_wall_q,
                upstream - terminal,
                upstream * source_h - terminal * line_h + line_wall_q,
                source_wall_derivative,
                line_wall_derivative,
            ],
            dtype=float,
        )

    end_time = float(requested[-1])
    solution = solve_ivp(
        derivative,
        (0.0, end_time),
        initial,
        method="LSODA",
        rtol=2.0e-6,
        atol=(1.0e-11, 1.0e-2, 1.0e-11, 1.0e-2, 1.0e-7, 1.0e-7),
        max_step=max(1.0e-4, min(0.02, end_time / 2000.0)),
    )
    if not solution.success:
        raise RuntimeError(f"release-network integration failed: {solution.message}")

    snapshots = [quantities(float(t), solution.y[:, i]) for i, t in enumerate(solution.t)]
    source_p = np.asarray([item[0] for item in snapshots])
    source_t = np.asarray([item[1] for item in snapshots])
    line_p = np.asarray([item[3] for item in snapshots])
    line_t = np.asarray([item[4] for item in snapshots])
    upstream = np.asarray([item[6] for item in snapshots])
    terminal = np.asarray([item[7] for item in snapshots])
    return ReleaseNetworkResult(
        time_s=requested,
        source_pressure_pa_abs=np.interp(requested, solution.t, source_p),
        line_pressure_pa_abs=np.interp(requested, solution.t, line_p),
        source_temperature_k=np.interp(requested, solution.t, source_t),
        line_temperature_k=np.interp(requested, solution.t, line_t),
        source_wall_temperature_k=np.interp(requested, solution.t, solution.y[4]),
        line_wall_temperature_k=np.interp(requested, solution.t, solution.y[5]),
        source_mass_kg=np.interp(requested, solution.t, solution.y[0]),
        line_mass_kg=np.interp(requested, solution.t, solution.y[2]),
        upstream_mass_flow_kg_s=np.interp(requested, solution.t, upstream),
        terminal_mass_flow_kg_s=np.interp(requested, solution.t, terminal),
    )


__all__ = ["ReleaseNetworkInputs", "ReleaseNetworkResult", "simulate_release_network"]
