"""Configuration example for the Type IV tank and fueling controller."""

from CoolProp.CoolProp import PropsSI

from h2station.protocol import FuelingSchedule, SampledFuelingController
from h2station.vehicle import (
    CompositeTankFillSimulator,
    CompositeTankParameters,
    CompositeVehicleTank,
)


tank = CompositeVehicleTank(
    CompositeTankParameters(
        internal_volume_m3=0.122,
        liner_mass_kg=8.0,
        liner_specific_heat_j_kg_k=1580.0,
        shell_mass_kg=70.0,
        shell_specific_heat_j_kg_k=1120.0,
        gas_liner_ua_w_k=18.0,
        liner_shell_ua_w_k=35.0,
        shell_ambient_ua_w_k=12.0,
    )
)

schedule = FuelingSchedule(
    target_pressure_pa=70.0e6,
    average_pressure_ramp_rate_pa_s=2.0e5,
    delivery_temperature_k=233.15,
    maximum_mass_flow_kg_s=0.060,
)
controller = SampledFuelingController(schedule)


def station_inlet_model(time_s, vehicle_gas, command):
    """Placeholder boundary; replace with the station hose/restriction model."""
    pressure_error = max(0.0, command.reference_pressure_pa - vehicle_gas.pressure_pa)
    mass_flow = command.valve_opening * min(0.060, pressure_error / 2.0e8)
    enthalpy = PropsSI(
        "Hmass",
        "P",
        max(vehicle_gas.pressure_pa, 1.0e5),
        "T",
        command.delivery_temperature_target_k,
        "Hydrogen",
    )
    return mass_flow, enthalpy


simulator = CompositeTankFillSimulator(tank, controller, station_inlet_model)
initial_state = tank.initial_state(5.0e6, 298.15)

# Intentionally not run at import time. The boundary above is demonstrative only;
# production runs should connect the station's real-gas hose/restriction model.
# result = simulator.simulate(initial_state, duration_s=300.0)

