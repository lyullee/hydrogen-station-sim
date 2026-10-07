"""Fast zero-dimensional model for ignited pressure peaking in enclosures.

The equations follow the species and energy balances reported by Lach and
Gaathaug (2021, doi:10.1016/j.ijhydene.2020.12.015).  The intended domain is
an immediately ignited hydrogen release into a vented, well-mixed enclosure.
It is a component consequence model, not a deflagration or outdoor jet model.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.integrate import solve_ivp


R_J_MOL_K = 8.314462618
SPECIES = ("H2", "O2", "N2", "H2O")
MOLAR_MASS_KG_MOL = np.asarray((0.00201588, 0.0319988, 0.0280134, 0.01801528))
# Standard near-ambient ideal-gas heat capacities.  The source model uses
# molar heat capacities in its temperature balance; fixed values keep the
# calculation deterministic and are adequate for its pressure endpoint.
CP_J_MOL_K = np.asarray((28.84, 29.37, 29.12, 33.58))
CV_J_MOL_K = CP_J_MOL_K - R_J_MOL_K


@dataclass(frozen=True)
class IgnitedPressurePeakingConfig:
    enclosure_volume_m3: float = 14.9
    enclosure_dimensions_m: tuple[float, float, float] = (2.5, 2.0, 2.98)
    ambient_pressure_pa: float = 101_325.0
    discharge_coefficient: float = 0.9
    wall_heat_transfer_w_m2_k: float = 30.0
    underpressure_heat_transfer_multiplier: float = 0.5
    wall_thickness_m: float = 0.02
    steel_density_kg_m3: float = 7_850.0
    steel_heat_capacity_j_kg_k: float = 470.0
    hydrogen_heat_release_j_mol: float = 241_826.0
    outside_air_density_kg_m3: float = 1.225
    reference_temperature_k: float = 298.15
    maximum_solver_step_s: float = 0.02

    @property
    def wall_area_m2(self) -> float:
        length, width, height = self.enclosure_dimensions_m
        return 2.0 * (length * width + length * height + width * height)

    @property
    def wall_mass_kg(self) -> float:
        return self.wall_area_m2 * self.wall_thickness_m * self.steel_density_kg_m3


@dataclass(frozen=True)
class IgnitedPressurePeakingResult:
    time_s: np.ndarray
    gauge_overpressure_kpa: np.ndarray
    enclosure_temperature_k: np.ndarray
    wall_temperature_k: np.ndarray
    species_moles: np.ndarray

    @property
    def peak_overpressure_kpa(self) -> float:
        return float(np.max(self.gauge_overpressure_kpa))

    @property
    def peak_time_s(self) -> float:
        return float(self.time_s[int(np.argmax(self.gauge_overpressure_kpa))])


def vent_area_m2(open_vent_count: int) -> float:
    """Return the documented passive vent area for the USN enclosure."""
    areas = {1: 0.0055, 2: 0.0109, 3: 0.0164}
    try:
        return areas[int(open_vent_count)]
    except (KeyError, ValueError) as exc:
        raise ValueError("open_vent_count must be 1, 2, or 3") from exc


def simulate_ignited_pressure_peaking(
    mass_flow_time_s: np.ndarray,
    hydrogen_mass_flow_g_s: np.ndarray,
    *,
    initial_temperature_k: float,
    vent_area_m2_value: float,
    output_time_s: np.ndarray | None = None,
    config: IgnitedPressurePeakingConfig | None = None,
) -> IgnitedPressurePeakingResult:
    """Integrate the fixed reacting-enclosure balance.

    Hydrogen is burned stoichiometrically on entry while oxygen remains, as
    assumed by the source model.  Positive pressure vents the well-mixed gas;
    negative pressure draws ambient air through the same opening.
    """
    cfg = config or IgnitedPressurePeakingConfig()
    flow_time = np.asarray(mass_flow_time_s, dtype=float)
    flow = np.asarray(hydrogen_mass_flow_g_s, dtype=float)
    if flow_time.ndim != 1 or flow.ndim != 1 or flow_time.size != flow.size:
        raise ValueError("mass-flow time and value arrays must be equal-length vectors")
    if flow_time.size < 2 or not np.all(np.isfinite(flow_time)) or not np.all(np.diff(flow_time) > 0.0):
        raise ValueError("mass-flow time must be finite and strictly increasing")
    if not np.all(np.isfinite(flow)):
        raise ValueError("mass-flow values must be finite")
    if initial_temperature_k <= 0.0 or vent_area_m2_value <= 0.0:
        raise ValueError("initial temperature and vent area must be positive")

    if output_time_s is None:
        output_time = np.arange(flow_time[0], flow_time[-1] + 0.005, 0.01)
        output_time = output_time[output_time <= flow_time[-1]]
    else:
        output_time = np.asarray(output_time_s, dtype=float)
    if (
        output_time.ndim != 1
        or output_time.size < 2
        or not np.all(np.isfinite(output_time))
        or not np.all(np.diff(output_time) > 0.0)
        or output_time[0] < flow_time[0]
        or output_time[-1] > flow_time[-1]
    ):
        raise ValueError("output time must be increasing and inside the mass-flow time range")

    initial_total_moles = (
        cfg.ambient_pressure_pa * cfg.enclosure_volume_m3
        / (R_J_MOL_K * initial_temperature_k)
    )
    initial_state = np.asarray(
        (
            0.0,
            0.21 * initial_total_moles,
            0.79 * initial_total_moles,
            0.0,
            initial_temperature_k,
            initial_temperature_k,
        ),
        dtype=float,
    )

    clipped_flow = np.maximum(flow, 0.0)

    def rhs(time_s: float, state: np.ndarray) -> np.ndarray:
        species_moles = np.maximum(state[:4], 1.0e-12)
        temperature_k = max(float(state[4]), 150.0)
        wall_temperature_k = max(float(state[5]), 150.0)
        total_moles = float(np.sum(species_moles))
        mole_fractions = species_moles / total_moles
        mixture_molar_mass = float(np.dot(mole_fractions, MOLAR_MASS_KG_MOL))
        pressure_pa = total_moles * R_J_MOL_K * temperature_k / cfg.enclosure_volume_m3
        pressure_delta_pa = pressure_pa - cfg.ambient_pressure_pa

        hydrogen_in_mol_s = (
            float(np.interp(time_s, flow_time, clipped_flow, left=0.0, right=0.0))
            / 1000.0
            / MOLAR_MASS_KG_MOL[0]
        )
        if pressure_delta_pa >= 0.001:
            total_out_mol_s = (
                cfg.discharge_coefficient
                * vent_area_m2_value
                * math.sqrt(
                    max(
                        2.0 * pressure_delta_pa * total_moles
                        / (cfg.enclosure_volume_m3 * mixture_molar_mass),
                        0.0,
                    )
                )
            )
            ambient_air_in_mol_s = 0.0
        elif pressure_delta_pa <= -0.001:
            total_out_mol_s = 0.0
            ambient_air_in_mol_s = (
                cfg.discharge_coefficient
                * vent_area_m2_value
                / MOLAR_MASS_KG_MOL[2]
                * math.sqrt(2.0 * (-pressure_delta_pa) * cfg.outside_air_density_kg_m3)
            )
        else:
            total_out_mol_s = 0.0
            ambient_air_in_mol_s = 0.0

        # The validation domain has ample oxygen.  The guard prevents negative
        # oxygen if the function is used beyond that domain.
        reaction_mol_s = hydrogen_in_mol_s if species_moles[1] > 1.0e-8 else 0.0
        inflow = np.asarray(
            (hydrogen_in_mol_s, 0.21 * ambient_air_in_mol_s, 0.79 * ambient_air_in_mol_s, 0.0)
        )
        reaction = np.asarray((-reaction_mol_s, -0.5 * reaction_mol_s, 0.0, reaction_mol_s))
        species_derivative = inflow - mole_fractions * total_out_mol_s + reaction

        inlet_enthalpy_w = (
            hydrogen_in_mol_s * CP_J_MOL_K[0] * (initial_temperature_k - cfg.reference_temperature_k)
            + ambient_air_in_mol_s
            * (0.21 * CP_J_MOL_K[1] + 0.79 * CP_J_MOL_K[2])
            * (initial_temperature_k - cfg.reference_temperature_k)
        )
        outlet_enthalpy_w = (
            total_out_mol_s
            * float(np.dot(mole_fractions, CP_J_MOL_K))
            * (temperature_k - cfg.reference_temperature_k)
        )
        reaction_heat_w = reaction_mol_s * cfg.hydrogen_heat_release_j_mol
        heat_transfer = cfg.wall_heat_transfer_w_m2_k
        if pressure_delta_pa < 0.0:
            heat_transfer *= cfg.underpressure_heat_transfer_multiplier
        wall_heat_loss_w = (
            heat_transfer * cfg.wall_area_m2 * (temperature_k - wall_temperature_k)
        )
        mixture_heat_capacity_j_k = float(np.dot(species_moles, CV_J_MOL_K))
        temperature_derivative = (
            inlet_enthalpy_w
            - outlet_enthalpy_w
            + reaction_heat_w
            - wall_heat_loss_w
            - (temperature_k - cfg.reference_temperature_k)
            * float(np.dot(CV_J_MOL_K, species_derivative))
        ) / mixture_heat_capacity_j_k
        wall_temperature_derivative = (
            wall_heat_loss_w / (cfg.wall_mass_kg * cfg.steel_heat_capacity_j_kg_k)
        )
        return np.concatenate(
            (species_derivative, (temperature_derivative, wall_temperature_derivative))
        )

    solution = solve_ivp(
        rhs,
        (float(output_time[0]), float(output_time[-1])),
        initial_state,
        method="RK45",
        t_eval=output_time,
        rtol=1.0e-6,
        atol=1.0e-8,
        max_step=cfg.maximum_solver_step_s,
    )
    if not solution.success:
        raise RuntimeError(f"ignited pressure-peaking integration failed: {solution.message}")

    total_moles = np.sum(solution.y[:4], axis=0)
    pressure_pa = total_moles * R_J_MOL_K * solution.y[4] / cfg.enclosure_volume_m3
    return IgnitedPressurePeakingResult(
        time_s=solution.t,
        gauge_overpressure_kpa=(pressure_pa - cfg.ambient_pressure_pa) / 1000.0,
        enclosure_temperature_k=solution.y[4],
        wall_temperature_k=solution.y[5],
        species_moles=solution.y[:4],
    )
