"""Tabulated hydrogen thermodynamic states for the dynamic runtime."""

from __future__ import annotations

from .tabulated import hydrogen_table
from .thermo_types import ThermoDomainError, ThermoState


class HydrogenEOS:
    """Fast single-fluid H2 provider backed by an offline CoolProp table."""

    def __init__(self, backend: str = "TABLE", fluid: str = "Hydrogen") -> None:
        if fluid.lower() not in {"hydrogen", "h2"}:
            raise ValueError("HydrogenEOS supports Hydrogen only")
        self.backend = "TABLE"
        self.fluid = "Hydrogen"

    def state_pt(self, pressure: float, temperature: float) -> ThermoState:
        return hydrogen_table().state_pt(pressure, temperature)

    def state_rho_u(self, density: float, internal_energy: float) -> ThermoState:
        return hydrogen_table().state_rho_u(density, internal_energy)

    def state_rho_t(self, density: float, temperature: float) -> ThermoState:
        return hydrogen_table().state_rho_t(density, temperature)

    def state_ps(self, pressure: float, entropy: float) -> ThermoState:
        return hydrogen_table().state_ps(pressure, entropy)

    def state_ph(self, pressure: float, enthalpy: float) -> ThermoState:
        return hydrogen_table().state_ph(pressure, enthalpy)


__all__ = ["HydrogenEOS", "ThermoDomainError", "ThermoState"]
