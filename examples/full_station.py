"""Three-bank cascade station configuration example."""

from h2station.dispenser import (
    HoseParameters,
    PartialStationModel,
    PrecoolerParameters,
    RestrictionParameters,
    SupplyState,
)
from h2station.full_station import (
    CascadeBank,
    CascadeBankParameters,
    FullStationModel,
    FullStationState,
    CompressorParameters,
    MultistageHydrogenCompressor,
)
from h2station.protocol import FuelingSchedule, SampledFuelingController
from h2station.vehicle import CompositeTankParameters, CompositeVehicleTank


vehicle = CompositeVehicleTank(
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
partial = PartialStationModel(
    vehicle_tank=vehicle,
    controller=controller,
    supply=lambda time_s: SupplyState(90.0e6, 298.15),
    pcv=RestrictionParameters(flow_area_m2=1.5e-6),
    precooler=PrecoolerParameters(900.0, 1.5e5, 3000.0, 1.0e5),
    hose=HoseParameters(2.0e-3, 1.2e4, 45.0, 18.0, 2.0e-6),
)
banks = tuple(
    CascadeBank(
        CascadeBankParameters(
            name=name,
            internal_volume_m3=0.35,
            target_pressure_pa=target_pressure,
            wall_mass_kg=300.0,
            wall_specific_heat_j_kg_k=500.0,
            gas_wall_ua_w_k=30.0,
            wall_ambient_ua_w_k=12.0,
        )
    )
    for name, target_pressure in (
        ("low", 45.0e6),
        ("medium", 65.0e6),
        ("high", 95.0e6),
    )
)
compressor = MultistageHydrogenCompressor(
    CompressorParameters(
        number_of_stages=3,
        swept_volume_rate_m3_s=8.0e-4,
        volumetric_efficiency=0.75,
        isentropic_efficiency=0.72,
        mechanical_efficiency=0.90,
        motor_efficiency=0.94,
        intercooler_outlet_temperature_k=303.15,
        maximum_mass_flow_kg_s=0.035,
        maximum_discharge_pressure_pa=100.0e6,
    )
)
station = FullStationModel(
    banks=banks,
    compressor=compressor,
    compressor_suction=lambda time_s: SupplyState(20.0e6, 298.15),
    partial_station=partial,
)
initial_bank_pressures = (45.0e6, 65.0e6, 90.0e6)
initial_vehicle = vehicle.initial_state(5.0e6, 298.15)
initial_partial = partial.initial_state(
    initial_vehicle, 5.1e6, 298.15, 233.15
)
initial_state = FullStationState(
    banks=tuple(
        bank.initial_state(pressure, 298.15)
        for bank, pressure in zip(banks, initial_bank_pressures)
    ),
    partial_station=initial_partial,
)

# Illustrative configuration only; substitute manufacturer and site parameters.
# result = station.simulate(initial_state, duration_s=300.0)

