from __future__ import annotations

import pytest

from h2station.scenario import build_vehicle_tank


def test_mass_temperature_initialization_preserves_observed_mass_and_temperature():
    tank = build_vehicle_tank(0.122)
    state = tank.initial_state_from_mass_temperature(0.75, 300.15)
    gas = tank.gas_state(state)

    assert state.hydrogen_mass_kg == pytest.approx(0.75)
    assert gas.temperature_k == pytest.approx(300.15, abs=1.0e-8)
    assert gas.pressure_pa > 0.0


def test_mass_temperature_initialization_rejects_nonphysical_boundary():
    tank = build_vehicle_tank(0.122)
    with pytest.raises(ValueError, match="Hydrogen mass"):
        tank.initial_state_from_mass_temperature(0.0, 300.15)
    with pytest.raises(ValueError, match="Gas temperature"):
        tank.initial_state_from_mass_temperature(0.75, 0.0)

