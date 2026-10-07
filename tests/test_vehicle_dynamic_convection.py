from __future__ import annotations

from dataclasses import replace

import pytest

from h2station.vehicle import (
    CompositeTankParameters,
    CompositeVehicleTank,
    TankBoundaryFlow,
)


def _parameters(**changes: object) -> CompositeTankParameters:
    base = CompositeTankParameters(
        internal_volume_m3=0.075,
        liner_mass_kg=11.2,
        liner_specific_heat_j_kg_k=900.0,
        shell_mass_kg=14.6,
        shell_specific_heat_j_kg_k=1494.0,
        gas_liner_ua_w_k=42.0,
        liner_shell_ua_w_k=138.0,
        shell_ambient_ua_w_k=8.3,
        internal_diameter_m=0.358,
        internal_length_m=0.7451,
    )
    return replace(base, **changes)


def _hot_gas(tank: CompositeVehicleTank):
    return tank.gas_state(tank.initial_state(25.0e6, 340.0))


def test_default_constant_ua_path_is_unchanged() -> None:
    tank = CompositeVehicleTank(_parameters())
    assert tank.gas_liner_ua_w_k(_hot_gas(tank), 295.0) == pytest.approx(42.0)


def test_natural_convection_produces_positive_conductance() -> None:
    tank = CompositeVehicleTank(_parameters(natural_convection_gas_liner=True))
    assert tank.gas_liner_ua_w_k(_hot_gas(tank), 295.0) > 0.0


def test_forced_convection_increases_conductance_during_fill() -> None:
    natural_tank = CompositeVehicleTank(
        _parameters(natural_convection_gas_liner=True)
    )
    mixed_tank = CompositeVehicleTank(_parameters(
        natural_convection_gas_liner=True,
        forced_convection_gas_liner=True,
    ))
    gas = _hot_gas(mixed_tank)
    boundary = TankBoundaryFlow(
        inlet_mass_flow_kg_s=0.04,
        inlet_pressure_pa=43.8e6,
        inlet_temperature_k=293.4,
        inlet_nozzle_diameter_m=0.005,
    )
    natural_ua = natural_tank.gas_liner_ua_w_k(gas, 295.0, boundary)
    mixed_ua = mixed_tank.gas_liner_ua_w_k(gas, 295.0, boundary)
    assert mixed_ua > natural_ua


def test_forced_convection_requires_explicit_inlet_geometry() -> None:
    tank = CompositeVehicleTank(_parameters(forced_convection_gas_liner=True))
    with pytest.raises(ValueError, match="nozzle diameter"):
        tank.gas_liner_ua_w_k(
            _hot_gas(tank),
            295.0,
            TankBoundaryFlow(inlet_mass_flow_kg_s=0.04),
        )


def test_dynamic_convection_requires_internal_geometry() -> None:
    with pytest.raises(ValueError, match="internal_diameter_m"):
        _parameters(
            internal_diameter_m=None,
            forced_convection_gas_liner=True,
        )
