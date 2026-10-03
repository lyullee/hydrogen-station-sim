"""Non-adiabatic DisCha vessel model for post-validation development.

This module is deliberately separate from :mod:`preslhy_validation`.  The
adiabatic model and its negative external result are immutable development
evidence.  E3.1 Part A data may be used here to develop one global model;
claims require a later, prospectively frozen holdout evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log, pi, sqrt

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar

from .preslhy_validation import (
    PreslhyCaseResult,
    PreslhyTrace,
    _crossing_time,
    eligible_pressure_window,
)

try:  # Research-only dependency; the real-time twin remains table backed.
    from CoolProp import AbstractState, CoolProp as CP
except ImportError as exc:  # pragma: no cover - exercised by packaging users
    AbstractState = None
    CP = None
    _COOLPROP_IMPORT_ERROR = exc
else:
    _COOLPROP_IMPORT_ERROR = None


@dataclass(frozen=True, slots=True)
class DischaVesselParameters:
    internal_volume_m3: float = 0.002815
    internal_diameter_m: float = 0.160
    internal_height_m: float = 0.140
    wall_mass_kg: float = 28.0
    wall_specific_heat_j_kg_k: float = 500.0
    wall_conductivity_w_m_k: float = 16.3
    external_heat_transfer_w_m2_k: float = 6.0
    ambient_temperature_k: float = 293.15
    discharge_coefficient: float = 0.8

    @property
    def internal_area_m2(self) -> float:
        diameter = self.internal_diameter_m
        return pi * diameter * self.internal_height_m + 0.5 * pi * diameter**2

    @property
    def external_area_m2(self) -> float:
        # The outer dimensions differ by only a few centimetres.  Keeping the
        # measured wall mass while using the inner area avoids inventing an
        # unreported closure/head geometry.
        return self.internal_area_m2

    @property
    def wall_heat_capacity_j_k(self) -> float:
        return self.wall_mass_kg * self.wall_specific_heat_j_kg_k


@dataclass(frozen=True, slots=True)
class NonadiabaticBlowdownResult:
    time_s: np.ndarray
    pressure_pa: np.ndarray
    gas_temperature_k: np.ndarray
    wall_temperature_k: np.ndarray
    mass_kg: np.ndarray
    mass_flow_kg_s: np.ndarray


class _CoolPropHydrogen:
    """Two-state HEOS helper; one state never overwrites the other."""

    def __init__(self) -> None:
        if AbstractState is None:
            raise RuntimeError(
                "CoolProp is required for the non-adiabatic research model"
            ) from _COOLPROP_IMPORT_ERROR
        self.storage = AbstractState("HEOS", "Hydrogen")
        self.nozzle = AbstractState("HEOS", "Hydrogen")

    def storage_from_rho_u(self, density: float, specific_internal_energy: float):
        self.storage.update(CP.DmassUmass_INPUTS, density, specific_internal_energy)
        return self.storage

    def storage_from_pt(self, pressure: float, temperature: float):
        self.storage.update(CP.PT_INPUTS, pressure, temperature)
        return self.storage

    def isentropic_mass_flux(
        self,
        pressure: float,
        temperature: float,
        downstream_pressure: float,
    ) -> float:
        self.nozzle.update(CP.PT_INPUTS, pressure, temperature)
        entropy = self.nozzle.smass()
        stagnation_enthalpy = self.nozzle.hmass()
        lower = max(1_000.0, min(downstream_pressure, pressure * (1.0 - 1.0e-9)))
        if lower >= pressure * (1.0 - 1.0e-8):
            return 0.0

        def negative_flux(log_pressure: float) -> float:
            throat_pressure = float(np.exp(log_pressure))
            self.nozzle.update(CP.PSmass_INPUTS, throat_pressure, entropy)
            kinetic_energy = max(stagnation_enthalpy - self.nozzle.hmass(), 0.0)
            return -self.nozzle.rhomass() * sqrt(2.0 * kinetic_energy)

        result = minimize_scalar(
            negative_flux,
            bounds=(log(lower), log(pressure * (1.0 - 1.0e-9))),
            method="bounded",
            options={"xatol": 1.0e-7},
        )
        boundary_flux = -negative_flux(log(lower))
        return max(boundary_flux, -float(result.fun) if result.success else 0.0)


def _internal_heat_transfer_coefficient(state, delta_temperature_k: float, length_m: float) -> float:
    """Churchill--Chu all-range natural-convection correlation.

    The DisCha report does not publish a fitted internal coefficient.  This
    uses only state properties and measured vessel geometry, which keeps the
    model predictive rather than introducing a case-specific tuning value.
    """

    conductivity = state.conductivity()
    viscosity = state.viscosity()
    cp = state.cpmass()
    density = state.rhomass()
    prandtl = max(state.Prandtl(), 1.0e-9)
    beta = max(abs(state.isobaric_expansion_coefficient()), 1.0e-12)
    kinematic_viscosity = viscosity / density
    thermal_diffusivity = conductivity / (density * cp)
    rayleigh = (
        9.80665
        * beta
        * abs(delta_temperature_k)
        * length_m**3
        / max(kinematic_viscosity * thermal_diffusivity, 1.0e-30)
    )
    nusselt = (
        0.825
        + 0.387 * rayleigh ** (1.0 / 6.0)
        / (1.0 + (0.492 / prandtl) ** (9.0 / 16.0)) ** (8.0 / 27.0)
    ) ** 2
    return max(nusselt * conductivity / length_m, conductivity / length_m)


def simulate_nonadiabatic_blowdown(
    trace: PreslhyTrace,
    evaluation_time_s: np.ndarray,
    *,
    parameters: DischaVesselParameters | None = None,
) -> NonadiabaticBlowdownResult:
    """Integrate measured-geometry vessel blowdown at requested timestamps."""

    if len(evaluation_time_s) < 2 or np.any(np.diff(evaluation_time_s) <= 0.0):
        raise ValueError("evaluation times must be a strictly increasing array")
    p = parameters or DischaVesselParameters(
        ambient_temperature_k=trace.initial_temperature_k
    )
    eos = _CoolPropHydrogen()
    initial_pressure = trace.initial_pressure_pa
    initial_temperature = trace.initial_temperature_k
    initial_state = eos.storage_from_pt(initial_pressure, initial_temperature)
    initial_mass = initial_state.rhomass() * p.internal_volume_m3
    initial_energy = initial_mass * initial_state.umass()
    initial_vector = np.asarray(
        [initial_mass, initial_energy, initial_temperature], dtype=float
    )
    aperture_area = pi * (trace.nozzle_diameter_mm / 1000.0) ** 2 / 4.0
    ambient_pressure = trace.ambient_pressure_pa
    minimum_mass = max(initial_mass * 1.0e-8, 1.0e-10)

    def quantities(vector):
        mass = max(float(vector[0]), minimum_mass)
        specific_internal_energy = float(vector[1]) / mass
        state = eos.storage_from_rho_u(mass / p.internal_volume_m3, specific_internal_energy)
        pressure = state.p()
        temperature = state.T()
        if pressure <= ambient_pressure * (1.0 + 1.0e-7):
            mass_flow = 0.0
        else:
            mass_flux = eos.isentropic_mass_flux(
                pressure, temperature, ambient_pressure
            )
            mass_flow = p.discharge_coefficient * aperture_area * mass_flux
        h_internal = _internal_heat_transfer_coefficient(
            state, float(vector[2]) - temperature, p.internal_diameter_m
        )
        heat_to_gas = (
            h_internal
            * p.internal_area_m2
            * (float(vector[2]) - temperature)
        )
        return state, mass_flow, heat_to_gas

    def derivative(_time, vector):
        state, mass_flow, heat_to_gas = quantities(vector)
        mass_flow = min(mass_flow, max(float(vector[0]), 0.0) / 1.0e-3)
        heat_from_ambient = (
            p.external_heat_transfer_w_m2_k
            * p.external_area_m2
            * (p.ambient_temperature_k - float(vector[2]))
        )
        return np.asarray(
            [
                -mass_flow,
                heat_to_gas - mass_flow * state.hmass(),
                (-heat_to_gas + heat_from_ambient) / p.wall_heat_capacity_j_k,
            ],
            dtype=float,
        )

    end_time = float(evaluation_time_s[-1])
    solution = solve_ivp(
        derivative,
        (0.0, end_time),
        initial_vector,
        method="LSODA",
        rtol=2.0e-6,
        atol=(1.0e-10, 1.0e-2, 1.0e-7),
        max_step=max(0.002, min(0.05, end_time / 1000.0)),
    )
    if not solution.success:
        raise RuntimeError(f"non-adiabatic PRESLHY integration failed: {solution.message}")

    pressure, gas_temperature, flow = [], [], []
    for index in range(solution.y.shape[1]):
        state, mass_flow, _ = quantities(solution.y[:, index])
        pressure.append(state.p())
        gas_temperature.append(state.T())
        flow.append(mass_flow)
    requested = np.asarray(evaluation_time_s, dtype=float)
    return NonadiabaticBlowdownResult(
        time_s=requested,
        pressure_pa=np.interp(requested, solution.t, pressure),
        gas_temperature_k=np.interp(requested, solution.t, gas_temperature),
        wall_temperature_k=np.interp(requested, solution.t, solution.y[2]),
        mass_kg=np.interp(requested, solution.t, solution.y[0]),
        mass_flow_kg_s=np.interp(requested, solution.t, flow),
    )


def evaluate_nonadiabatic_trace(
    trace: PreslhyTrace,
    *,
    parameters: DischaVesselParameters | None = None,
) -> PreslhyCaseResult:
    """Apply the original frozen pressure screens to the development model."""

    time_s, measured_bar = eligible_pressure_window(trace)
    measured_pa = measured_bar * 1.0e5
    predicted = simulate_nonadiabatic_blowdown(
        trace, time_s, parameters=parameters
    )
    errors_bar = (predicted.pressure_pa - measured_pa) / 1.0e5
    initial_pressure = trace.initial_pressure_pa
    half_target = trace.ambient_pressure_pa + 0.5 * (
        initial_pressure - trace.ambient_pressure_pa
    )
    experimental_half = _crossing_time(time_s, measured_pa, half_target)
    predicted_half = _crossing_time(time_s, predicted.pressure_pa, half_target)
    if not np.isfinite(experimental_half) or experimental_half <= 0.0:
        half_error = float("inf")
    elif not np.isfinite(predicted_half):
        half_error = float("inf")
    else:
        half_error = (
            abs(predicted_half - experimental_half) / experimental_half * 100.0
        )
    nrmse = float(
        np.sqrt(np.mean(errors_bar**2)) * 1.0e5 / initial_pressure * 100.0
    )
    pressure_pass = nrmse <= 10.0
    half_pass = half_error <= 20.0
    return PreslhyCaseResult(
        case_id=trace.case_id,
        nozzle_diameter_mm=trace.nozzle_diameter_mm,
        initial_pressure_bar_abs=initial_pressure / 1.0e5,
        samples=len(time_s),
        pressure_rmse_bar=float(np.sqrt(np.mean(errors_bar**2))),
        pressure_mae_bar=float(np.mean(np.abs(errors_bar))),
        pressure_nrmse_percent_initial_absolute_pressure=nrmse,
        experimental_time_to_50_percent_gauge_s=float(experimental_half),
        predicted_time_to_50_percent_gauge_s=float(predicted_half),
        time_to_50_percent_gauge_relative_error_percent=float(half_error),
        pressure_screen_pass=pressure_pass,
        half_time_screen_pass=half_pass,
        joint_primary_screen_pass=pressure_pass and half_pass,
        peak_mass_flow_kg_s=float(np.max(predicted.mass_flow_kg_s)),
        cumulative_released_mass_kg=float(
            predicted.mass_kg[0] - predicted.mass_kg[-1]
        ),
    )


__all__ = [
    "DischaVesselParameters",
    "NonadiabaticBlowdownResult",
    "evaluate_nonadiabatic_trace",
    "simulate_nonadiabatic_blowdown",
]
