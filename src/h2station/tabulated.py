"""Fast hydrogen property lookup generated from a reference CoolProp EOS."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Mapping

import numpy as np

from .thermo_types import ThermoDomainError, ThermoState


_OUTPUT_NAMES = {
    "P": "pressure", "T": "temperature", "DMASS": "density",
    "UMASS": "internal_energy", "HMASS": "enthalpy", "SMASS": "entropy",
    "CPMASS": "cp", "CVMASS": "cv", "VISCOSITY": "viscosity",
    "CONDUCTIVITY": "conductivity", "Z": "compressibility",
    "A": "speed_of_sound",
}


class HydrogenPropertyTable:
    """Bilinear P-T lookup plus monotone inverse state interpolation."""

    def __init__(self, path: Path | None = None) -> None:
        table_path = path or Path(__file__).with_name("data") / "hydrogen_properties_v1.npz"
        if not table_path.exists():
            raise RuntimeError(
                f"Hydrogen property table is missing: {table_path}. "
                "Run scripts/generate_hydrogen_table.py."
            )
        with np.load(table_path) as data:
            self.pressure_grid = data["pressure_grid_pa"]
            self.temperature_grid = data["temperature_grid_k"]
            self.density_grid = data["density_grid_kg_m3"]
            self.pt = {
                name: data[f"pt_{name}"]
                for name in _OUTPUT_NAMES.values()
                if f"pt_{name}" in data
            }
            self.rhot = {
                name: data[f"rhot_{name}"]
                for name in _OUTPUT_NAMES.values()
                if f"rhot_{name}" in data
            }
        self._log_pressure_grid = np.log(self.pressure_grid)
        self._log_density_grid = np.log(self.density_grid)

    @staticmethod
    def _bracket(grid: np.ndarray, value: float, label: str) -> tuple[int, float]:
        tolerance = 1.0e-10 * max(abs(grid[0]), abs(grid[-1]), 1.0)
        if value < grid[0] - tolerance or value > grid[-1] + tolerance:
            raise ThermoDomainError(
                f"Hydrogen table {label}={value:g} is outside "
                f"[{grid[0]:g}, {grid[-1]:g}]"
            )
        clipped = float(np.clip(value, grid[0], grid[-1]))
        index = int(np.searchsorted(grid, clipped, side="right") - 1)
        index = min(max(index, 0), len(grid) - 2)
        weight = (clipped - grid[index]) / (grid[index + 1] - grid[index])
        return index, float(weight)

    def _pt_value(self, name: str, pressure: float, temperature: float) -> float:
        ip, wp = self._bracket(
            self._log_pressure_grid, np.log(pressure), "pressure"
        )
        it, wt = self._bracket(self.temperature_grid, temperature, "temperature")
        values = self.pt[name]
        low = values[ip, it] * (1.0 - wt) + values[ip, it + 1] * wt
        high = values[ip + 1, it] * (1.0 - wt) + values[ip + 1, it + 1] * wt
        return float(low * (1.0 - wp) + high * wp)

    @lru_cache(maxsize=8192)
    def state_pt(self, pressure: float, temperature: float) -> ThermoState:
        if pressure <= 0.0 or temperature <= 0.0:
            raise ThermoDomainError("Pressure and temperature must be positive")
        ip, wp = self._bracket(
            self._log_pressure_grid, np.log(pressure), "pressure"
        )
        it, wt = self._bracket(self.temperature_grid, temperature, "temperature")
        values: dict[str, float] = {}
        for name, table in self.pt.items():
            if name in {"pressure", "temperature"}:
                continue
            low = table[ip, it] * (1.0 - wt) + table[ip, it + 1] * wt
            high = table[ip + 1, it] * (1.0 - wt) + table[ip + 1, it + 1] * wt
            values[name] = float(low * (1.0 - wp) + high * wp)
        values["pressure"] = float(pressure)
        values["temperature"] = float(temperature)
        return ThermoState(**values)

    def _temperature_from_pt_property(
        self, pressure: float, target: float, property_name: str
    ) -> float:
        ip, wp = self._bracket(
            self._log_pressure_grid, np.log(pressure), "pressure"
        )
        table = self.pt[property_name]
        curve = table[ip] * (1.0 - wp) + table[ip + 1] * wp
        if target < curve[0] or target > curve[-1]:
            raise ThermoDomainError(
                f"Hydrogen table {property_name}={target:g} is outside "
                f"the available range at P={pressure:g} Pa"
            )
        return float(np.interp(target, curve, self.temperature_grid))

    @lru_cache(maxsize=4096)
    def state_ps(self, pressure: float, entropy: float) -> ThermoState:
        return self.state_pt(
            pressure,
            self._temperature_from_pt_property(pressure, entropy, "entropy"),
        )

    @lru_cache(maxsize=4096)
    def state_ph(self, pressure: float, enthalpy: float) -> ThermoState:
        return self.state_pt(
            pressure,
            self._temperature_from_pt_property(pressure, enthalpy, "enthalpy"),
        )

    @lru_cache(maxsize=8192)
    def state_rho_u(self, density: float, internal_energy: float) -> ThermoState:
        if density <= 0.0:
            raise ThermoDomainError("Density must be positive")
        ir, wr = self._bracket(
            self._log_density_grid, np.log(density), "density"
        )
        energy_table = self.rhot["internal_energy"]
        temperatures: list[float] = []
        for row in (ir, ir + 1):
            curve = energy_table[row]
            if internal_energy < curve[0] or internal_energy > curve[-1]:
                raise ThermoDomainError(
                    f"Hydrogen table internal_energy={internal_energy:g} is "
                    f"outside the available range near rho={density:g} kg/m3"
                )
            temperatures.append(
                float(np.interp(internal_energy, curve, self.temperature_grid))
            )

        values: dict[str, float] = {}
        for name, table in self.rhot.items():
            if name in {"density", "internal_energy", "temperature"}:
                continue
            low = float(np.interp(temperatures[0], self.temperature_grid, table[ir]))
            high = float(
                np.interp(temperatures[1], self.temperature_grid, table[ir + 1])
            )
            values[name] = low * (1.0 - wr) + high * wr
        values["density"] = float(density)
        values["internal_energy"] = float(internal_energy)
        values["temperature"] = temperatures[0] * (1.0 - wr) + temperatures[1] * wr
        return ThermoState(**values)


_table: HydrogenPropertyTable | None = None
_table_lock = Lock()


def hydrogen_table() -> HydrogenPropertyTable:
    global _table
    if _table is None:
        with _table_lock:
            if _table is None:
                _table = HydrogenPropertyTable()
    return _table


def PropsSI(
    output: str,
    first_name: str,
    first_value: float,
    second_name: str,
    second_value: float,
    fluid: str = "Hydrogen",
) -> float:
    """Scalar subset of PropsSI backed entirely by the generated H2 table."""
    if fluid.lower() not in {"hydrogen", "h2"}:
        raise ValueError("The tabulated runtime supports Hydrogen only")
    inputs: Mapping[str, float] = {
        first_name.upper(): float(first_value),
        second_name.upper(): float(second_value),
    }
    table = hydrogen_table()
    if {"P", "T"} <= inputs.keys():
        state = table.state_pt(inputs["P"], inputs["T"])
    elif {"DMASS", "UMASS"} <= inputs.keys():
        state = table.state_rho_u(inputs["DMASS"], inputs["UMASS"])
    elif {"P", "SMASS"} <= inputs.keys():
        state = table.state_ps(inputs["P"], inputs["SMASS"])
    elif {"P", "HMASS"} <= inputs.keys():
        state = table.state_ph(inputs["P"], inputs["HMASS"])
    else:
        raise ValueError(f"Unsupported tabulated property input pair: {tuple(inputs)}")
    try:
        return float(getattr(state, _OUTPUT_NAMES[output.upper()]))
    except KeyError as exc:
        raise ValueError(f"Unsupported tabulated property output: {output}") from exc
