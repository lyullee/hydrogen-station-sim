"""Pressure-driven lumped thermal model for independent blowdown checks.

The measured pressure trace is an imposed boundary.  The model predicts only
bulk gas and wall temperature, so an unknown valve coefficient cannot be
silently inferred from the same experiment.  Mass and energy remain linked by
the real-gas equation of state and the open-system enthalpy balance.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import PchipInterpolator

from .preslhy_nonadiabatic import (
    _CoolPropHydrogen,
    _internal_heat_transfer_coefficient,
)


@dataclass(frozen=True, slots=True)
class PressureDrivenThermalParameters:
    volume_m3: float
    internal_area_m2: float
    characteristic_length_m: float
    wall_heat_capacity_j_k: float
    external_area_m2: float
    external_heat_transfer_w_m2_k: float
    ambient_temperature_k: float
    initial_wall_temperature_k: float

    def __post_init__(self) -> None:
        positive = (
            self.volume_m3,
            self.internal_area_m2,
            self.characteristic_length_m,
            self.wall_heat_capacity_j_k,
            self.external_area_m2,
        )
        if any(not isfinite(value) or value <= 0.0 for value in positive):
            raise ValueError("vessel geometry and wall heat capacity must be positive")
        if self.external_heat_transfer_w_m2_k < 0.0:
            raise ValueError("external heat-transfer coefficient cannot be negative")
        if self.ambient_temperature_k <= 0.0 or self.initial_wall_temperature_k <= 0.0:
            raise ValueError("absolute temperatures must be positive")


@dataclass(frozen=True, slots=True)
class PressureDrivenThermalResult:
    time_s: np.ndarray
    imposed_pressure_pa: np.ndarray
    gas_temperature_k: np.ndarray
    wall_temperature_k: np.ndarray
    mass_kg: np.ndarray
    cumulative_outflow_enthalpy_j: np.ndarray
    cumulative_external_heat_j: np.ndarray
    energy_balance_residual_j: np.ndarray


def _validate_trace(
    time_s: np.ndarray, pressure_pa: np.ndarray, initial_temperature_k: float
) -> tuple[np.ndarray, np.ndarray]:
    time = np.asarray(time_s, dtype=float)
    pressure = np.asarray(pressure_pa, dtype=float)
    if time.ndim != 1 or pressure.ndim != 1 or len(time) != len(pressure):
        raise ValueError("time and pressure must be aligned one-dimensional arrays")
    if len(time) < 3 or np.any(~np.isfinite(time)) or np.any(~np.isfinite(pressure)):
        raise ValueError("at least three finite pressure samples are required")
    if time[0] < 0.0 or np.any(np.diff(time) <= 0.0):
        raise ValueError("time must be non-negative and strictly increasing")
    if np.any(pressure <= 0.0):
        raise ValueError("absolute pressure must be positive")
    if not isfinite(initial_temperature_k) or initial_temperature_k <= 0.0:
        raise ValueError("initial gas temperature must be positive")
    return time, pressure


def simulate_pressure_driven_thermal(
    time_s: np.ndarray,
    pressure_pa: np.ndarray,
    *,
    initial_temperature_k: float,
    parameters: PressureDrivenThermalParameters,
) -> PressureDrivenThermalResult:
    """Predict temperature while imposing the measured vessel pressure.

    For ``m(P,T)=rho(P,T)V`` and ``U(P,T)=m u(P,T)``, the open-system
    balance ``dU/dt = Q + h dm/dt`` is solved algebraically for ``dT/dt``.
    Thermodynamic partial derivatives are evaluated symmetrically from the
    HEOS hydrogen state.  No release-area or discharge-coefficient parameter is
    present in this model.
    """

    requested, imposed_pressure = _validate_trace(
        time_s, pressure_pa, initial_temperature_k
    )
    pressure_curve = PchipInterpolator(requested, imposed_pressure, extrapolate=False)
    pressure_rate = pressure_curve.derivative()
    eos = _CoolPropHydrogen()

    def storage(pressure: float, temperature: float) -> tuple[float, float, float, object]:
        state = eos.storage_from_pt(float(pressure), float(temperature))
        mass = float(state.rhomass() * parameters.volume_m3)
        internal_energy = float(mass * state.umass())
        return mass, internal_energy, float(state.hmass()), state

    def partials(pressure: float, temperature: float):
        dp = max(abs(pressure) * 1.0e-5, 10.0)
        dt = max(abs(temperature) * 1.0e-5, 1.0e-3)
        p_lo = max(pressure - dp, 1.0)
        p_hi = pressure + dp
        t_lo = max(temperature - dt, 2.0)
        t_hi = temperature + dt
        m_lo_p, u_lo_p, _, _ = storage(p_lo, temperature)
        m_hi_p, u_hi_p, _, _ = storage(p_hi, temperature)
        m_lo_t, u_lo_t, _, _ = storage(pressure, t_lo)
        m_hi_t, u_hi_t, _, _ = storage(pressure, t_hi)
        return (
            (m_hi_p - m_lo_p) / (p_hi - p_lo),
            (m_hi_t - m_lo_t) / (t_hi - t_lo),
            (u_hi_p - u_lo_p) / (p_hi - p_lo),
            (u_hi_t - u_lo_t) / (t_hi - t_lo),
        )

    initial_mass, initial_gas_energy, _, _ = storage(
        imposed_pressure[0], initial_temperature_k
    )
    initial_stored_energy = (
        initial_gas_energy
        + parameters.wall_heat_capacity_j_k * parameters.initial_wall_temperature_k
    )

    def rates(at_time: float, vector: np.ndarray):
        pressure = float(pressure_curve(at_time))
        dp_dt = float(pressure_rate(at_time))
        gas_temperature = float(vector[0])
        wall_temperature = float(vector[1])
        mass, _energy, enthalpy, state = storage(pressure, gas_temperature)
        m_p, m_t, u_p, u_t = partials(pressure, gas_temperature)
        h_inside = _internal_heat_transfer_coefficient(
            state,
            wall_temperature - gas_temperature,
            parameters.characteristic_length_m,
        )
        heat_to_gas = (
            h_inside
            * parameters.internal_area_m2
            * (wall_temperature - gas_temperature)
        )
        denominator = u_t - enthalpy * m_t
        if abs(denominator) < 1.0e-9:
            raise RuntimeError("ill-conditioned pressure-driven energy balance")
        dtemperature_dt = (
            heat_to_gas - (u_p - enthalpy * m_p) * dp_dt
        ) / denominator
        dmass_dt = m_p * dp_dt + m_t * dtemperature_dt
        external_heat = (
            parameters.external_heat_transfer_w_m2_k
            * parameters.external_area_m2
            * (parameters.ambient_temperature_k - wall_temperature)
        )
        dwall_dt = (
            -heat_to_gas + external_heat
        ) / parameters.wall_heat_capacity_j_k
        # Positive cumulative enthalpy denotes energy carried out of the vessel.
        outflow_enthalpy = -dmass_dt * enthalpy
        return np.asarray(
            [dtemperature_dt, dwall_dt, outflow_enthalpy, external_heat],
            dtype=float,
        ), mass

    def derivative(at_time: float, vector: np.ndarray) -> np.ndarray:
        return rates(at_time, vector)[0]

    solution = solve_ivp(
        derivative,
        (float(requested[0]), float(requested[-1])),
        np.asarray(
            [
                initial_temperature_k,
                parameters.initial_wall_temperature_k,
                0.0,
                0.0,
            ],
            dtype=float,
        ),
        t_eval=requested,
        method="LSODA",
        rtol=2.0e-6,
        atol=(1.0e-6, 1.0e-6, 1.0e-3, 1.0e-3),
        max_step=max(0.01, min(0.25, (requested[-1] - requested[0]) / 1000.0)),
    )
    if not solution.success:
        raise RuntimeError(f"pressure-driven thermal integration failed: {solution.message}")

    gas_temperature = solution.y[0]
    wall_temperature = solution.y[1]
    mass = np.empty(len(requested), dtype=float)
    gas_energy = np.empty(len(requested), dtype=float)
    for index, (pressure, temperature) in enumerate(
        zip(imposed_pressure, gas_temperature, strict=True)
    ):
        mass[index], gas_energy[index], _, _ = storage(pressure, temperature)
    stored_energy = gas_energy + parameters.wall_heat_capacity_j_k * wall_temperature
    residual = (
        stored_energy
        + solution.y[2]
        - solution.y[3]
        - initial_stored_energy
    )
    return PressureDrivenThermalResult(
        time_s=requested,
        imposed_pressure_pa=imposed_pressure,
        gas_temperature_k=gas_temperature,
        wall_temperature_k=wall_temperature,
        mass_kg=mass,
        cumulative_outflow_enthalpy_j=solution.y[2],
        cumulative_external_heat_j=solution.y[3],
        energy_balance_residual_j=residual,
    )


__all__ = [
    "PressureDrivenThermalParameters",
    "PressureDrivenThermalResult",
    "simulate_pressure_driven_thermal",
]
