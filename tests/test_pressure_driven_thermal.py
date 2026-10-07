from __future__ import annotations

import numpy as np

from h2station.pressure_driven_thermal import (
    PressureDrivenThermalParameters,
    simulate_pressure_driven_thermal,
)


def test_pressure_driven_model_is_finite_mass_depleting_and_energy_closed() -> None:
    time_s = np.linspace(0.0, 20.0, 81)
    pressure_pa = 1.0e5 + 19.9e6 * np.exp(-time_s / 7.0)
    parameters = PressureDrivenThermalParameters(
        volume_m3=0.0499,
        internal_area_m2=1.1,
        characteristic_length_m=0.217,
        wall_heat_capacity_j_k=30_000.0,
        external_area_m2=1.2,
        external_heat_transfer_w_m2_k=2.0,
        ambient_temperature_k=293.15,
        initial_wall_temperature_k=293.15,
    )

    result = simulate_pressure_driven_thermal(
        time_s,
        pressure_pa,
        initial_temperature_k=293.15,
        parameters=parameters,
    )

    assert np.all(np.isfinite(result.gas_temperature_k))
    assert np.all(np.isfinite(result.wall_temperature_k))
    assert np.all(np.diff(result.mass_kg) <= 1.0e-8)
    assert result.gas_temperature_k.min() > 50.0
    energy_scale = max(abs(result.cumulative_outflow_enthalpy_j[-1]), 1.0)
    assert np.max(np.abs(result.energy_balance_residual_j)) / energy_scale < 1.0e-4


def test_pressure_driven_model_rejects_non_increasing_time() -> None:
    parameters = PressureDrivenThermalParameters(
        volume_m3=0.01,
        internal_area_m2=0.5,
        characteristic_length_m=0.1,
        wall_heat_capacity_j_k=10_000.0,
        external_area_m2=0.5,
        external_heat_transfer_w_m2_k=0.0,
        ambient_temperature_k=293.15,
        initial_wall_temperature_k=293.15,
    )
    with np.testing.assert_raises(ValueError):
        simulate_pressure_driven_thermal(
            np.asarray([0.0, 1.0, 1.0]),
            np.asarray([2.0e6, 1.5e6, 1.0e6]),
            initial_temperature_k=293.15,
            parameters=parameters,
        )
