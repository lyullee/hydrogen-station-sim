"""Traceable reference scenario assembly for API and scripted operation."""

from __future__ import annotations

from dataclasses import dataclass

from .dispenser import (
    HoseParameters,
    PartialStationModel,
    PrecoolerParameters,
    RestrictionParameters,
    SupplyState,
)
from .full_station import (
    CascadeBank,
    CascadeBankParameters,
    CompressorParameters,
    FullStationModel,
    FullStationState,
    MultistageHydrogenCompressor,
)
from .protocol import FuelingSchedule, SampledFuelingController
from .risk.live import DynamicRiskMonitor, HyRAMConsequenceBackend
from .safe_operation import SafeFullStationSimulator
from .safety_runtime import (
    FaultEvent,
    FaultInjector,
    FaultSchedule,
    SafetyLimits,
    SafetyPLC,
)
from .vehicle import CompositeTankParameters, CompositeVehicleTank


BANK_REFERENCE_MAX_PRESSURE_PA = (50.0e6, 70.0e6, 100.0e6)
DEFAULT_BANK_INITIAL_FILL_PERCENT = (90.0, 100.0 * 65.0 / 70.0, 90.0)


@dataclass(frozen=True)
class ReferenceScenario:
    duration_s: float = 300.0
    control_period_s: float = 0.2
    ambient_temperature_k: float = 298.15
    initial_vehicle_pressure_pa: float = 5.0e6
    initial_vehicle_temperature_k: float = 298.15
    initial_vehicle_2_pressure_pa: float = 5.0e6
    initial_vehicle_2_temperature_k: float = 298.15
    target_vehicle_pressure_pa: float = 70.0e6
    target_vehicle_2_pressure_pa: float = 70.0e6
    average_pressure_ramp_rate_pa_s: float = 2.0e5
    delivery_temperature_k: float = 233.15
    maximum_mass_flow_kg_s: float = 0.060
    risk_update_period_s: float = 1.0
    compressor_suction_pressure_pa: float = 20.0e6
    compressor_suction_temperature_k: float = 298.15
    initial_bank_fill_percent: tuple[float, float, float] = DEFAULT_BANK_INITIAL_FILL_PERCENT
    fault_events: tuple[FaultEvent, ...] = ()


@dataclass(frozen=True)
class BuiltScenario:
    simulator: SafeFullStationSimulator
    station: FullStationModel
    initial_state: FullStationState
    config: ReferenceScenario


def build_reference_scenario(
    config: ReferenceScenario,
    hyram_backend: HyRAMConsequenceBackend,
) -> BuiltScenario:
    if len(config.initial_bank_fill_percent) != len(BANK_REFERENCE_MAX_PRESSURE_PA) or any(
        not 1.0 <= percent <= 100.0 for percent in config.initial_bank_fill_percent
    ):
        raise ValueError("initial_bank_fill_percent must contain three values from 1 to 100")
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
            target_pressure_pa=config.target_vehicle_pressure_pa,
            average_pressure_ramp_rate_pa_s=(
                config.average_pressure_ramp_rate_pa_s
            ),
            delivery_temperature_k=config.delivery_temperature_k,
            maximum_mass_flow_kg_s=config.maximum_mass_flow_kg_s,
        )
    )
    partial = PartialStationModel(
        vehicle_tank=vehicle,
        controller=controller,
        supply=lambda time_s: SupplyState(90.0e6, config.ambient_temperature_k),
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
        ambient_temperature_k=config.ambient_temperature_k,
    )
    secondary_controller = SampledFuelingController(
        FuelingSchedule(
            target_pressure_pa=config.target_vehicle_2_pressure_pa,
            average_pressure_ramp_rate_pa_s=config.average_pressure_ramp_rate_pa_s,
            delivery_temperature_k=config.delivery_temperature_k,
            maximum_mass_flow_kg_s=config.maximum_mass_flow_kg_s,
        )
    )
    secondary_partial = PartialStationModel(
        vehicle_tank=vehicle,
        controller=secondary_controller,
        supply=lambda time_s: SupplyState(90.0e6, config.ambient_temperature_k),
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
        ambient_temperature_k=config.ambient_temperature_k,
    )
    banks = tuple(
        CascadeBank(
            CascadeBankParameters(
                name=name,
                internal_volume_m3=0.35,
                target_pressure_pa=target_pressure_pa,
                wall_mass_kg=300.0,
                wall_specific_heat_j_kg_k=500.0,
                gas_wall_ua_w_k=30.0,
                wall_ambient_ua_w_k=12.0,
            )
        )
        for name, target_pressure_pa in (
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
        compressor_suction=lambda time_s: SupplyState(
            config.compressor_suction_pressure_pa,
            config.compressor_suction_temperature_k,
        ),
        partial_station=partial,
        secondary_partial_station=secondary_partial,
        ambient_temperature_k=config.ambient_temperature_k,
    )
    initial_vehicle = vehicle.initial_state(
        config.initial_vehicle_pressure_pa,
        config.initial_vehicle_temperature_k,
    )
    initial_partial = partial.initial_state(
        vehicle=initial_vehicle,
        hose_pressure_pa=config.initial_vehicle_pressure_pa + 1.0e5,
        hose_temperature_k=config.ambient_temperature_k,
        coolant_temperature_k=config.delivery_temperature_k,
    )
    initial_vehicle_2 = vehicle.initial_state(
        config.initial_vehicle_2_pressure_pa,
        config.initial_vehicle_2_temperature_k,
    )
    initial_partial_2 = secondary_partial.initial_state(
        vehicle=initial_vehicle_2,
        hose_pressure_pa=config.initial_vehicle_2_pressure_pa + 1.0e5,
        hose_temperature_k=config.ambient_temperature_k,
        coolant_temperature_k=config.delivery_temperature_k,
    )
    initial_state = FullStationState(
        banks=tuple(
            bank.initial_state(maximum_pa * percent / 100.0, config.ambient_temperature_k)
            for bank, maximum_pa, percent in zip(
                banks,
                BANK_REFERENCE_MAX_PRESSURE_PA,
                config.initial_bank_fill_percent,
            )
        ),
        partial_station=initial_partial,
        secondary_partial_station=initial_partial_2,
    )
    fault_injector = FaultInjector(FaultSchedule(config.fault_events))
    safety_plc = SafetyPLC(
        SafetyLimits(
            maximum_vehicle_pressure_pa=87.5e6,
            maximum_vehicle_temperature_k=358.15,
            maximum_precooler_outlet_temperature_k=253.15,
            maximum_flow_imbalance_kg_s=0.050,
            detector_alarm_volume_fraction=0.01,
            detector_trip_volume_fraction=0.02,
            trip_persistence_s=0.5,
        )
    )
    risk_monitor = DynamicRiskMonitor(
        hyram_backend,
        update_period_s=config.risk_update_period_s,
    )
    simulator = SafeFullStationSimulator(
        station,
        fault_injector,
        safety_plc,
        risk_monitor,
    )
    return BuiltScenario(simulator, station, initial_state, config)
