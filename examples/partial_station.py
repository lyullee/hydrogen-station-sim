"""Partial H70 station configuration from PCV inlet to vehicle tank."""

from h2station.dispenser import (
    HoseParameters,
    PartialStationModel,
    PrecoolerParameters,
    RestrictionParameters,
    SupplyState,
)
from h2station.protocol import FuelingSchedule, SampledFuelingController
from h2station.vehicle import CompositeTankParameters, CompositeVehicleTank


vehicle_tank = CompositeVehicleTank(
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
controller = SampledFuelingController(
    FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=2.0e5,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.060,
    )
)
model = PartialStationModel(
    vehicle_tank=vehicle_tank,
    controller=controller,
    supply=lambda time_s: SupplyState(pressure_pa=90.0e6, temperature_k=298.15),
    pcv=RestrictionParameters(flow_area_m2=1.5e-6),
    precooler=PrecoolerParameters(
        hydrogen_coolant_ua_w_k=900.0,
        coolant_thermal_capacity_j_k=1.5e5,
        chiller_ua_w_k=3000.0,
        hydrogen_pressure_drop_pa=1.0e5,
    ),
    hose=HoseParameters(
        internal_volume_m3=2.0e-3,
        wall_thermal_capacity_j_k=1.2e4,
        gas_wall_ua_w_k=45.0,
        wall_ambient_ua_w_k=18.0,
        nozzle_flow_area_m2=2.0e-6,
    ),
)
vehicle_initial = vehicle_tank.initial_state(5.0e6, 298.15)
initial_state = model.initial_state(
    vehicle=vehicle_initial,
    hose_pressure_pa=5.1e6,
    hose_temperature_k=298.15,
    coolant_temperature_k=233.15,
)

# Illustrative dimensions only. Replace them with traceable hardware values before
# running a design or safety case.
# result = model.simulate(initial_state, duration_s=300.0)

