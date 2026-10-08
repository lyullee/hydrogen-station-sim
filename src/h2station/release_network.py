"""Apparatus-resolved hydrogen release network for prospective development.

The frozen Schefer/Proust evaluators intentionally model a local aperture or a
well-mixed vessel.  This module is a separate development model that represents
the minimum additional state needed for an apparatus with a supply line:

* a source vessel and one or more physically declared line control volumes,
* independent finite upstream and terminal valve opening laws,
* upstream, inter-volume and terminal restrictions, and
* lumped gas/wall thermal states for every control volume.

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
    """Geometry and initial conditions for an apparatus-resolved release.

    ``line_segments`` represents physical line/manifold volumes separated by
    declared equivalent restrictions.  It is not a numerical mesh setting:
    increasing it without apparatus geometry changes the physical model.
    The default of one preserves the original source-plus-line model.
    """

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
    # Legacy names describe the upstream/source isolation valve.  They remain
    # stable for the frozen v1 data contract.
    valve_opening_time_s: float = 0.05
    valve_opening_shape_exponent: float = 1.0
    upstream_valve_initial_fraction: float = 0.0
    # A terminal fraction of one preserves the original always-open outlet.
    # Set this to zero with a finite opening time for a precharged line whose
    # release valve is located at the nozzle/end of the supply line.
    terminal_valve_initial_fraction: float = 1.0
    terminal_valve_opening_time_s: float = 0.0
    terminal_valve_opening_shape_exponent: float = 1.0
    line_segments: int = 1
    intersegment_diameter_m: float | None = None
    intersegment_discharge_coefficient: float = 1.0
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
            "valve_opening_shape_exponent": self.valve_opening_shape_exponent,
            "terminal_valve_opening_shape_exponent": (
                self.terminal_valve_opening_shape_exponent
            ),
        }
        for name, value in positive.items():
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be positive and finite")
        nonnegative = {
            "upstream_discharge_coefficient": self.upstream_discharge_coefficient,
            "terminal_discharge_coefficient": self.terminal_discharge_coefficient,
            "valve_opening_time_s": self.valve_opening_time_s,
            "upstream_valve_initial_fraction": self.upstream_valve_initial_fraction,
            "terminal_valve_initial_fraction": self.terminal_valve_initial_fraction,
            "terminal_valve_opening_time_s": self.terminal_valve_opening_time_s,
            "source_wall_mass_kg": self.source_wall_mass_kg,
            "line_wall_mass_kg": self.line_wall_mass_kg,
            "source_internal_area_m2": self.source_internal_area_m2,
            "line_internal_area_m2": self.line_internal_area_m2,
            "source_external_area_m2": self.source_external_area_m2,
            "line_external_area_m2": self.line_external_area_m2,
            "internal_heat_transfer_w_m2_k": self.internal_heat_transfer_w_m2_k,
            "external_heat_transfer_w_m2_k": self.external_heat_transfer_w_m2_k,
            "intersegment_discharge_coefficient": self.intersegment_discharge_coefficient,
        }
        for name, value in nonnegative.items():
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be non-negative and finite")
        if (
            self.upstream_discharge_coefficient > 1.0
            or self.terminal_discharge_coefficient > 1.0
            or self.intersegment_discharge_coefficient > 1.0
        ):
            raise ValueError("discharge coefficients cannot exceed one")
        if (
            self.upstream_valve_initial_fraction > 1.0
            or self.terminal_valve_initial_fraction > 1.0
        ):
            raise ValueError("initial valve fractions cannot exceed one")
        if isinstance(self.line_segments, bool) or not isinstance(self.line_segments, int):
            raise ValueError("line_segments must be an integer")
        if self.line_segments < 1:
            raise ValueError("line_segments must be at least one")
        if self.line_segments > 1:
            if (
                self.intersegment_diameter_m is None
                or not np.isfinite(self.intersegment_diameter_m)
                or self.intersegment_diameter_m <= 0.0
            ):
                raise ValueError(
                    "intersegment_diameter_m must be positive for multiple line segments"
                )
        elif self.intersegment_diameter_m is not None and (
            not np.isfinite(self.intersegment_diameter_m)
            or self.intersegment_diameter_m <= 0.0
        ):
            raise ValueError("intersegment_diameter_m must be positive when supplied")

    @property
    def upstream_area_m2(self) -> float:
        return pi * self.upstream_diameter_m**2 / 4.0

    @property
    def terminal_area_m2(self) -> float:
        return pi * self.terminal_diameter_m**2 / 4.0

    @property
    def intersegment_area_m2(self) -> float:
        diameter = self.intersegment_diameter_m or self.upstream_diameter_m
        return pi * diameter**2 / 4.0

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
    cumulative_terminal_release_kg: np.ndarray
    cumulative_terminal_enthalpy_j: np.ndarray
    cumulative_thermal_boundary_energy_j: np.ndarray
    mass_balance_residual_kg: np.ndarray
    energy_balance_residual_j: np.ndarray
    valve_opening_fraction: np.ndarray
    upstream_valve_opening_fraction: np.ndarray
    terminal_valve_opening_fraction: np.ndarray
    line_pressure_profile_pa_abs: np.ndarray
    line_temperature_profile_k: np.ndarray
    line_mass_profile_kg: np.ndarray
    intersegment_mass_flow_kg_s: np.ndarray


def _opening_fraction(
    time_s: float,
    opening_time_s: float,
    shape_exponent: float = 1.0,
    initial_fraction: float = 0.0,
) -> float:
    if opening_time_s <= 0.0:
        return 1.0
    travel = float(np.clip(time_s / opening_time_s, 0.0, 1.0))
    return initial_fraction + (1.0 - initial_fraction) * travel**shape_exponent


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

    The source valve and terminal restriction are directional.  Flow between
    declared line volumes may reverse when a downstream volume has the higher
    pressure.  Mass and energy crossing every boundary are explicit, so a
    future validation can compare boundary flow without reconstructing hidden
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
    segment_count = inputs.line_segments
    segment_volume = inputs.line_volume_m3 / segment_count
    line_mass_total = float(line_initial.rhomass() * inputs.line_volume_m3)
    line_mass = np.full(segment_count, line_mass_total / segment_count, dtype=float)
    line_energy = line_mass * float(line_initial.umass())
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
    line_wall_capacity = inputs.line_wall_capacity_j_k / segment_count
    # The final three entries are bookkeeping states.  They do not affect the
    # physical equations; they make source/line/terminal mass and open-system
    # energy closure directly auditable at each reported time.
    source_mass_index = 0
    source_energy_index = 1
    line_mass_slice = slice(2, 2 + segment_count)
    line_energy_slice = slice(2 + segment_count, 2 + 2 * segment_count)
    source_wall_index = 2 + 2 * segment_count
    line_wall_slice = slice(source_wall_index + 1, source_wall_index + 1 + segment_count)
    terminal_mass_index = line_wall_slice.stop
    terminal_enthalpy_index = terminal_mass_index + 1
    thermal_boundary_index = terminal_mass_index + 2
    initial = np.concatenate(
        (
            np.asarray([source_mass, source_energy]),
            line_mass,
            line_energy,
            np.asarray([source_wall_temperature]),
            np.full(segment_count, line_wall_temperature),
            np.zeros(3),
        )
    )
    initial_stored_energy = (
        source_energy
        + float(np.sum(line_energy))
        + source_wall_capacity * source_wall_temperature
        + line_wall_capacity * segment_count * line_wall_temperature
    )
    minimum_source_mass = max(source_mass * 1.0e-10, 1.0e-12)
    minimum_line_mass = max(line_mass_total * 1.0e-10 / segment_count, 1.0e-12)

    def quantities(time_s: float, vector: np.ndarray):
        source_m = max(float(vector[source_mass_index]), minimum_source_mass)
        source_u = float(vector[source_energy_index])
        line_m = np.maximum(vector[line_mass_slice], minimum_line_mass)
        line_u = vector[line_energy_slice]
        source_p, source_t, source_h, source_state = _gas_snapshot(
            eos, source_m, source_u, inputs.source_volume_m3
        )
        line_snapshots = [
            _gas_snapshot(eos, float(mass), float(energy), segment_volume)
            for mass, energy in zip(line_m, line_u, strict=True)
        ]
        line_p = np.asarray([item[0] for item in line_snapshots])
        line_t = np.asarray([item[1] for item in line_snapshots])
        line_h = np.asarray([item[2] for item in line_snapshots])
        upstream_opening = _opening_fraction(
            time_s,
            inputs.valve_opening_time_s,
            inputs.valve_opening_shape_exponent,
            inputs.upstream_valve_initial_fraction,
        )
        terminal_opening = _opening_fraction(
            time_s,
            inputs.terminal_valve_opening_time_s,
            inputs.terminal_valve_opening_shape_exponent,
            inputs.terminal_valve_initial_fraction,
        )
        if source_p <= line_p[0] * (1.0 + 1.0e-9):
            upstream = 0.0
        else:
            upstream = (
                upstream_opening
                * inputs.upstream_discharge_coefficient
                * inputs.upstream_area_m2
                * eos.isentropic_mass_flux(source_p, source_t, line_p[0])
            )
        interface_flows = np.zeros(max(0, segment_count - 1), dtype=float)
        for index in range(segment_count - 1):
            pressure_delta = line_p[index] - line_p[index + 1]
            if abs(pressure_delta) <= max(line_p[index], line_p[index + 1]) * 1.0e-9:
                continue
            if pressure_delta > 0.0:
                flux = eos.isentropic_mass_flux(
                    line_p[index], line_t[index], line_p[index + 1]
                )
                interface_flows[index] = (
                    inputs.intersegment_discharge_coefficient
                    * inputs.intersegment_area_m2
                    * flux
                )
            else:
                flux = eos.isentropic_mass_flux(
                    line_p[index + 1], line_t[index + 1], line_p[index]
                )
                interface_flows[index] = -(
                    inputs.intersegment_discharge_coefficient
                    * inputs.intersegment_area_m2
                    * flux
                )
        if line_p[-1] <= inputs.ambient_pressure_pa * (1.0 + 1.0e-9):
            terminal = 0.0
        else:
            terminal = (
                terminal_opening * inputs.terminal_discharge_coefficient
                * inputs.terminal_area_m2
                * eos.isentropic_mass_flux(
                    line_p[-1], line_t[-1], inputs.ambient_pressure_pa
                )
            )
        upstream = min(upstream, source_m / 1.0e-4)
        for index, flow in enumerate(interface_flows):
            donor = index if flow >= 0.0 else index + 1
            interface_flows[index] = np.sign(flow) * min(
                abs(flow), line_m[donor] / 1.0e-4
            )
        terminal = min(terminal, line_m[-1] / 1.0e-4)
        source_wall_q = inputs.internal_heat_transfer_w_m2_k * inputs.source_internal_area_m2 * (
            float(vector[source_wall_index]) - source_t
        )
        line_wall_q = (
            inputs.internal_heat_transfer_w_m2_k
            * (inputs.line_internal_area_m2 / segment_count)
            * (vector[line_wall_slice] - line_t)
        )
        return (
            source_p, source_t, source_h, line_p, line_t, line_h,
            upstream, interface_flows, terminal, upstream_opening, terminal_opening,
            source_wall_q, line_wall_q,
        )

    def derivative(time_s: float, vector: np.ndarray) -> np.ndarray:
        (
            _source_p, source_t, source_h, _line_p, _line_t, line_h,
            upstream, interface_flows, terminal, _upstream_opening, _terminal_opening,
            source_wall_q, line_wall_q,
        ) = quantities(time_s, vector)
        source_external_q = inputs.external_heat_transfer_w_m2_k * inputs.source_external_area_m2 * (
            inputs.ambient_temperature_k - float(vector[source_wall_index])
        )
        line_external_q = (
            inputs.external_heat_transfer_w_m2_k
            * (inputs.line_external_area_m2 / segment_count)
            * (inputs.ambient_temperature_k - vector[line_wall_slice])
        )
        source_wall_derivative = 0.0
        line_wall_derivative = np.zeros(segment_count)
        # A zero-capacity wall is a prescribed-temperature boundary in this
        # lumped model.  Its gas-to-wall heat term is therefore counted as an
        # external boundary exchange instead of a stored-wall contribution.
        thermal_boundary_q = 0.0
        if source_wall_capacity > 0.0:
            source_wall_derivative = (-source_wall_q + source_external_q) / source_wall_capacity
            thermal_boundary_q += source_external_q
        else:
            thermal_boundary_q += source_wall_q
        if line_wall_capacity > 0.0:
            line_wall_derivative = (-line_wall_q + line_external_q) / line_wall_capacity
            thermal_boundary_q += float(np.sum(line_external_q))
        else:
            thermal_boundary_q += float(np.sum(line_wall_q))

        line_mass_rate = np.zeros(segment_count)
        line_energy_rate = np.asarray(line_wall_q, dtype=float).copy()
        line_mass_rate[0] += upstream
        line_energy_rate[0] += upstream * source_h
        for index, flow in enumerate(interface_flows):
            donor_enthalpy = line_h[index] if flow >= 0.0 else line_h[index + 1]
            line_mass_rate[index] -= flow
            line_mass_rate[index + 1] += flow
            enthalpy_flow = flow * donor_enthalpy
            line_energy_rate[index] -= enthalpy_flow
            line_energy_rate[index + 1] += enthalpy_flow
        line_mass_rate[-1] -= terminal
        line_energy_rate[-1] -= terminal * line_h[-1]

        derivative_vector = np.zeros_like(vector)
        derivative_vector[source_mass_index] = -upstream
        derivative_vector[source_energy_index] = -upstream * source_h + source_wall_q
        derivative_vector[line_mass_slice] = line_mass_rate
        derivative_vector[line_energy_slice] = line_energy_rate
        derivative_vector[source_wall_index] = source_wall_derivative
        derivative_vector[line_wall_slice] = line_wall_derivative
        derivative_vector[terminal_mass_index] = terminal
        derivative_vector[terminal_enthalpy_index] = terminal * line_h[-1]
        derivative_vector[thermal_boundary_index] = thermal_boundary_q
        return derivative_vector

    end_time = float(requested[-1])
    solution = solve_ivp(
        derivative,
        (0.0, end_time),
        initial,
        method="LSODA",
        rtol=2.0e-6,
        atol=np.concatenate(
            (
                np.asarray([1.0e-11, 1.0e-2]),
                np.full(segment_count, 1.0e-11),
                np.full(segment_count, 1.0e-2),
                np.full(segment_count + 1, 1.0e-7),
                np.asarray([1.0e-11, 1.0e-2, 1.0e-2]),
            )
        ),
        max_step=max(1.0e-4, min(0.02, end_time / 2000.0)),
    )
    if not solution.success:
        raise RuntimeError(f"release-network integration failed: {solution.message}")

    snapshots = [quantities(float(t), solution.y[:, i]) for i, t in enumerate(solution.t)]
    source_p = np.asarray([item[0] for item in snapshots])
    source_t = np.asarray([item[1] for item in snapshots])
    line_p = np.vstack([item[3] for item in snapshots])
    line_t = np.vstack([item[4] for item in snapshots])
    upstream = np.asarray([item[6] for item in snapshots])
    interface_flows = np.vstack([item[7] for item in snapshots]) if segment_count > 1 else np.empty((len(snapshots), 0))
    terminal = np.asarray([item[8] for item in snapshots])
    cumulative_terminal_release = np.interp(
        requested, solution.t, solution.y[terminal_mass_index]
    )
    cumulative_terminal_enthalpy = np.interp(
        requested, solution.t, solution.y[terminal_enthalpy_index]
    )
    cumulative_thermal_boundary = np.interp(
        requested, solution.t, solution.y[thermal_boundary_index]
    )
    stored_energy = (
        solution.y[source_energy_index]
        + np.sum(solution.y[line_energy_slice], axis=0)
        + source_wall_capacity * solution.y[source_wall_index]
        + line_wall_capacity * np.sum(solution.y[line_wall_slice], axis=0)
    )
    mass_residual = (
        solution.y[source_mass_index]
        + np.sum(solution.y[line_mass_slice], axis=0)
        + solution.y[terminal_mass_index]
        - (source_mass + line_mass_total)
    )
    energy_residual = (
        stored_energy
        + solution.y[terminal_enthalpy_index]
        - solution.y[thermal_boundary_index]
        - initial_stored_energy
    )
    line_pressure_profile = np.column_stack(
        [np.interp(requested, solution.t, line_p[:, index]) for index in range(segment_count)]
    )
    line_temperature_profile = np.column_stack(
        [np.interp(requested, solution.t, line_t[:, index]) for index in range(segment_count)]
    )
    line_mass_profile = np.column_stack(
        [
            np.interp(requested, solution.t, solution.y[line_mass_slice.start + index])
            for index in range(segment_count)
        ]
    )
    intersegment_profile = np.column_stack(
        [
            np.interp(requested, solution.t, interface_flows[:, index])
            for index in range(segment_count - 1)
        ]
    ) if segment_count > 1 else np.empty((len(requested), 0))
    # Valve position is a prescribed command, so evaluate it exactly at the
    # requested timestamps instead of interpolating adaptive solver samples.
    requested_upstream_opening = np.asarray([
        _opening_fraction(
            float(time_s),
            inputs.valve_opening_time_s,
            inputs.valve_opening_shape_exponent,
            inputs.upstream_valve_initial_fraction,
        )
        for time_s in requested
    ])
    requested_terminal_opening = np.asarray([
        _opening_fraction(
            float(time_s),
            inputs.terminal_valve_opening_time_s,
            inputs.terminal_valve_opening_shape_exponent,
            inputs.terminal_valve_initial_fraction,
        )
        for time_s in requested
    ])
    return ReleaseNetworkResult(
        time_s=requested,
        source_pressure_pa_abs=np.interp(requested, solution.t, source_p),
        line_pressure_pa_abs=line_pressure_profile[:, -1],
        source_temperature_k=np.interp(requested, solution.t, source_t),
        line_temperature_k=line_temperature_profile[:, -1],
        source_wall_temperature_k=np.interp(
            requested, solution.t, solution.y[source_wall_index]
        ),
        line_wall_temperature_k=np.mean(
            np.column_stack(
                [
                    np.interp(requested, solution.t, solution.y[line_wall_slice.start + index])
                    for index in range(segment_count)
                ]
            ),
            axis=1,
        ),
        source_mass_kg=np.interp(requested, solution.t, solution.y[source_mass_index]),
        line_mass_kg=np.sum(line_mass_profile, axis=1),
        upstream_mass_flow_kg_s=np.interp(requested, solution.t, upstream),
        terminal_mass_flow_kg_s=np.interp(requested, solution.t, terminal),
        cumulative_terminal_release_kg=cumulative_terminal_release,
        cumulative_terminal_enthalpy_j=cumulative_terminal_enthalpy,
        cumulative_thermal_boundary_energy_j=cumulative_thermal_boundary,
        mass_balance_residual_kg=np.interp(requested, solution.t, mass_residual),
        energy_balance_residual_j=np.interp(requested, solution.t, energy_residual),
        valve_opening_fraction=requested_upstream_opening,
        upstream_valve_opening_fraction=requested_upstream_opening,
        terminal_valve_opening_fraction=requested_terminal_opening,
        line_pressure_profile_pa_abs=line_pressure_profile,
        line_temperature_profile_k=line_temperature_profile,
        line_mass_profile_kg=line_mass_profile,
        intersegment_mass_flow_kg_s=intersegment_profile,
    )


__all__ = ["ReleaseNetworkInputs", "ReleaseNetworkResult", "simulate_release_network"]
