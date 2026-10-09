"""Development-only two-volume hydrogen blowdown model.

The frozen release evaluators deliberately use a single well-mixed vessel and
are kept unchanged.  This module adds the first missing physical state for
development work: hydrogen inventory and internal energy in the downstream
line.  It is therefore useful for diagnosing early transients and source-side
versus outlet-flow differences, but it is not enabled in the station runtime
and cannot change an existing prospective holdout result.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi

import numpy as np
from scipy.integrate import solve_ivp

from .preslhy_nonadiabatic import _CoolPropHydrogen


@dataclass(frozen=True, slots=True)
class LineTransientParameters:
    """Geometry and initial conditions for a source vessel plus a line."""

    source_volume_m3: float
    source_pressure_pa_abs: float
    source_temperature_k: float
    line_length_m: float
    line_inner_diameter_m: float
    outlet_inner_diameter_m: float
    source_to_line_discharge_coefficient: float = 1.0
    outlet_discharge_coefficient: float = 1.0
    source_valve_time_constant_s: float = 0.0
    outlet_valve_time_constant_s: float = 0.0
    ambient_pressure_pa: float = 101_325.0
    line_initial_pressure_pa_abs: float | None = None
    line_initial_temperature_k: float = 293.15

    @property
    def line_volume_m3(self) -> float:
        return pi * self.line_inner_diameter_m**2 / 4.0 * self.line_length_m


@dataclass(frozen=True, slots=True)
class LineTransientResult:
    time_s: np.ndarray
    source_pressure_pa: np.ndarray
    line_pressure_pa: np.ndarray
    source_flow_kg_s: np.ndarray
    outlet_flow_kg_s: np.ndarray
    source_mass_kg: np.ndarray
    line_mass_kg: np.ndarray


def _orifice_flow(
    flux_eos: _CoolPropHydrogen,
    upstream,
    downstream_pressure_pa: float,
    area_m2: float,
    discharge_coefficient: float,
) -> float:
    """Return one-way real-gas isentropic flow from an upstream state."""

    if upstream.p() <= downstream_pressure_pa * (1.0 + 1.0e-8):
        return 0.0
    return max(
        0.0,
        float(discharge_coefficient)
        * area_m2
        * flux_eos.isentropic_mass_flux(
            float(upstream.p()), float(upstream.T()), downstream_pressure_pa
        ),
    )


def _valve_open_fraction(time_s: float, time_constant_s: float) -> float:
    """Return a monotone first-order opening fraction.

    A zero time constant is the frozen evaluator's instantaneous-open limit.
    Positive values are an explicit development assumption and must be
    independently frozen before a future holdout is scored.
    """

    if time_constant_s <= 0.0:
        return 1.0
    return float(1.0 - np.exp(-max(time_s, 0.0) / time_constant_s))


def simulate_line_transient(
    evaluation_time_s: np.ndarray,
    *,
    parameters: LineTransientParameters,
) -> LineTransientResult:
    """Integrate source and line inventories without outcome fitting.

    The returned source flow is the flow entering the downstream line; the
    outlet flow is the flow leaving the line to ambient.  Both are retained so
    an instrument boundary can be selected explicitly during a development
    diagnostic rather than silently conflating the two.
    """

    requested = np.asarray(evaluation_time_s, dtype=float)
    if (
        requested.ndim != 1
        or requested.size < 2
        or not np.isfinite(requested).all()
        or requested[0] < 0.0
        or np.any(np.diff(requested) <= 0.0)
    ):
        raise ValueError("evaluation times must be finite, non-negative and strictly increasing")
    p = parameters
    if p.source_volume_m3 <= 0.0 or p.line_volume_m3 <= 0.0:
        raise ValueError("source and line volumes must be positive")
    if p.line_inner_diameter_m <= 0.0 or p.outlet_inner_diameter_m <= 0.0:
        raise ValueError("line and outlet diameters must be positive")

    # CoolProp's AbstractState is mutable.  Keep independent source and line
    # storage states so evaluating one volume never overwrites the other.
    source_eos = _CoolPropHydrogen()
    line_eos = _CoolPropHydrogen()
    flux_eos = _CoolPropHydrogen()
    source_state = source_eos.storage_from_pt(
        p.source_pressure_pa_abs, p.source_temperature_k
    )
    line_pressure = (
        p.ambient_pressure_pa
        if p.line_initial_pressure_pa_abs is None
        else p.line_initial_pressure_pa_abs
    )
    line_state = line_eos.storage_from_pt(line_pressure, p.line_initial_temperature_k)
    source_mass = float(source_state.rhomass() * p.source_volume_m3)
    line_mass = float(line_state.rhomass() * p.line_volume_m3)
    source_energy = source_mass * float(source_state.umass())
    line_energy = line_mass * float(line_state.umass())
    minimum_source_mass = max(source_mass * 1.0e-9, 1.0e-10)
    minimum_line_mass = max(line_mass * 1.0e-9, 1.0e-12)
    source_area = pi * p.line_inner_diameter_m**2 / 4.0
    outlet_area = pi * p.outlet_inner_diameter_m**2 / 4.0

    def states(vector: np.ndarray):
        mass_source = max(float(vector[0]), minimum_source_mass)
        mass_line = max(float(vector[2]), minimum_line_mass)
        source = source_eos.storage_from_rho_u(
            mass_source / p.source_volume_m3, float(vector[1]) / mass_source
        )
        line = line_eos.storage_from_rho_u(
            mass_line / p.line_volume_m3, float(vector[3]) / mass_line
        )
        source_flow = _orifice_flow(
            flux_eos,
            source,
            float(line.p()),
            source_area,
            p.source_to_line_discharge_coefficient,
        )
        outlet_flow = _orifice_flow(
            flux_eos,
            line,
            p.ambient_pressure_pa,
            outlet_area,
            p.outlet_discharge_coefficient,
        )
        return source, line, source_flow, outlet_flow

    def derivative(time_s: float, vector: np.ndarray) -> np.ndarray:
        source, line, source_flow, outlet_flow = states(vector)
        source_flow *= _valve_open_fraction(
            time_s, p.source_valve_time_constant_s
        )
        outlet_flow *= _valve_open_fraction(
            time_s, p.outlet_valve_time_constant_s
        )
        source_flow = min(source_flow, max(float(vector[0]), 0.0) / 1.0e-4)
        outlet_flow = min(outlet_flow, max(float(vector[2]), 0.0) / 1.0e-4)
        return np.asarray(
            (
                -source_flow,
                -source_flow * float(source.hmass()),
                source_flow - outlet_flow,
                source_flow * float(source.hmass())
                - outlet_flow * float(line.hmass()),
            ),
            dtype=float,
        )

    valve_time_constants = [
        value
        for value in (
            p.source_valve_time_constant_s,
            p.outlet_valve_time_constant_s,
        )
        if value > 0.0
    ]
    transient_step = min(valve_time_constants) / 20.0 if valve_time_constants else 0.05
    solution = solve_ivp(
        derivative,
        (0.0, float(requested[-1])),
        np.asarray((source_mass, source_energy, line_mass, line_energy), dtype=float),
        # A finite valve time constant introduces a sharp but smooth initial
        # layer. BDF avoids the nonphysical trial states that LSODA can produce
        # while calling the real-gas EOS during that layer.
        method="BDF" if valve_time_constants else "LSODA",
        rtol=2.0e-7,
        atol=(1.0e-10, 1.0e-2, 1.0e-12, 1.0e-2),
        max_step=max(
            1.0e-5,
            min(0.05, float(requested[-1]) / 1500.0, transient_step),
        ),
    )
    if not solution.success:
        raise RuntimeError(f"line transient integration failed: {solution.message}")

    source_pressure: list[float] = []
    line_pressure_values: list[float] = []
    source_flow_values: list[float] = []
    outlet_flow_values: list[float] = []
    for index in range(solution.y.shape[1]):
        source, line, source_flow, outlet_flow = states(solution.y[:, index])
        source_flow *= _valve_open_fraction(
            float(solution.t[index]), p.source_valve_time_constant_s
        )
        outlet_flow *= _valve_open_fraction(
            float(solution.t[index]), p.outlet_valve_time_constant_s
        )
        source_pressure.append(float(source.p()))
        line_pressure_values.append(float(line.p()))
        source_flow_values.append(source_flow)
        outlet_flow_values.append(outlet_flow)

    return LineTransientResult(
        time_s=requested,
        source_pressure_pa=np.interp(requested, solution.t, source_pressure),
        line_pressure_pa=np.interp(requested, solution.t, line_pressure_values),
        source_flow_kg_s=np.interp(requested, solution.t, source_flow_values),
        outlet_flow_kg_s=np.interp(requested, solution.t, outlet_flow_values),
        source_mass_kg=np.interp(requested, solution.t, solution.y[0]),
        line_mass_kg=np.interp(requested, solution.t, solution.y[2]),
    )


__all__ = ["LineTransientParameters", "LineTransientResult", "simulate_line_transient"]
