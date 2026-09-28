"""Generate the runtime H2 property table from CoolProp HEOS."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from CoolProp.CoolProp import PropsSI


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "src" / "h2station" / "data" / "hydrogen_properties_v1.npz"
FLUID = "Hydrogen"
PROPERTIES = {
    "pressure": "P", "density": "Dmass",
    "internal_energy": "Umass", "enthalpy": "Hmass",
    "entropy": "Smass", "cp": "Cpmass", "cv": "Cvmass",
    "viscosity": "VISCOSITY", "conductivity": "CONDUCTIVITY",
    "compressibility": "Z", "speed_of_sound": "A",
}


def evaluate_grid(
    first_name: str,
    first_grid: np.ndarray,
    second_name: str,
    second_grid: np.ndarray,
) -> dict[str, np.ndarray]:
    first, second = np.meshgrid(first_grid, second_grid, indexing="ij")
    flat_first = first.ravel()
    flat_second = second.ravel()
    return {
        name: np.asarray(
            PropsSI(output, first_name, flat_first, second_name, flat_second, FLUID),
            dtype=np.float64,
        ).reshape(first.shape)
        for name, output in PROPERTIES.items()
    }


def main() -> None:
    pressure_grid = np.geomspace(1.0e4, 1.2e8, 321)
    temperature_grid = np.linspace(60.0, 700.0, 421)
    density_grid = np.geomspace(1.0e-3, 100.0, 321)
    pt = evaluate_grid("P", pressure_grid, "T", temperature_grid)
    rhot = evaluate_grid("Dmass", density_grid, "T", temperature_grid)
    shape = (len(pressure_grid), len(temperature_grid))
    rho_shape = (len(density_grid), len(temperature_grid))
    pt["pressure"] = np.broadcast_to(pressure_grid[:, None], shape)
    pt["temperature"] = np.broadcast_to(temperature_grid[None, :], shape)
    rhot["density"] = np.broadcast_to(density_grid[:, None], rho_shape)
    rhot["temperature"] = np.broadcast_to(temperature_grid[None, :], rho_shape)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUTPUT,
        pressure_grid_pa=pressure_grid,
        temperature_grid_k=temperature_grid,
        density_grid_kg_m3=density_grid,
        **{f"pt_{name}": values for name, values in pt.items()},
        **{f"rhot_{name}": values for name, values in rhot.items()},
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
