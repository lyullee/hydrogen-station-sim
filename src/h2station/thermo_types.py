"""Shared thermodynamic value types independent of the property backend."""

from __future__ import annotations

from dataclasses import dataclass


class ThermoDomainError(ValueError):
    """Raised when a requested thermodynamic state is outside the table domain."""


@dataclass(frozen=True, slots=True)
class ThermoState:
    pressure: float
    temperature: float
    density: float
    internal_energy: float
    enthalpy: float
    entropy: float
    cp: float
    cv: float
    viscosity: float
    conductivity: float
    compressibility: float
    speed_of_sound: float
