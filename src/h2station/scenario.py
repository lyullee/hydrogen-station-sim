"""Traceable reference scenario assembly for API and scripted operation."""

from __future__ import annotations

from dataclasses import dataclass

from .dispenser import (
    DispenserFitParameters,
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
from .vehicle import (
    CompositeTankFitParameters,
    CompositeTankParameters,
    CompositeVehicleTank,
)


BANK_REFERENCE_MAX_PRESSURE_PA = (50.0e6, 70.0e6, 100.0e6)
DEFAULT_BANK_INITIAL_FILL_PERCENT = (90.0, 100.0 * 65.0 / 70.0, 90.0)


@dataclass(frozen=True)
class ReferenceScenario:
    duration_s: float = 300.0
    control_period_s: float = 0.2
    ambient_temperature_k: float = 298.15
    initial_vehicle_pressure_pa: float = 5.0e6
    initial_vehicle_temperature_k: float = 298.15
    vehicle_internal_volume_m3: float = 0.122
    vehicle_nominal_working_pressure_pa: float = 70.0e6
    vehicle_effective_volume_multiplier: float = 1.0
    vehicle_gas_liner_ua_multiplier: float = 1.0
    dispenser_flow_area_multiplier: float = 1.0
    precooler_duty_multiplier: float = 1.0
    initial_vehicle_2_pressure_pa: float = 5.0e6
    initial_vehicle_2_temperature_k: float = 298.15
    vehicle_2_internal_volume_m3: float = 0.122
    vehicle_2_nominal_working_pressure_pa: float = 70.0e6
    target_vehicle_pressure_pa: float = 70.0e6
    target_vehicle_2_pressure_pa: float = 70.0e6
    average_pressure_ramp_rate_pa_s: float = 2.0e5
    delivery_temperature_k: float = 233.15
    maximum_precooler_temperature_deviation_k: float = 15.0
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


def build_vehicle_tank(
    internal_volume_m3: float,
    fit: CompositeTankFitParameters | None = None,
) -> CompositeVehicleTank:
    """Build a Type-IV surrogate while preserving reference mass ratios."""

    reference_volume_m3 = 0.122
    scale = internal_volume_m3 / reference_volume_m3
    area_scale = scale ** (2.0 / 3.0)
    return CompositeVehicleTank(
        CompositeTankParameters(
            internal_volume_m3=internal_volume_m3,
            liner_mass_kg=8.0 * scale,
            liner_specific_heat_j_kg_k=1580.0,
            shell_mass_kg=70.0 * scale,
            shell_specific_heat_j_kg_k=1120.0,
            gas_liner_ua_w_k=18.0 * area_scale,
            liner_shell_ua_w_k=35.0 * area_scale,
            shell_ambient_ua_w_k=12.0 * area_scale,
        ),
        fit,
    )


def build_reference_scenario(
    config: ReferenceScenario,
    hyram_backend: HyRAMConsequenceBackend,
) -> BuiltScenario:
    if len(config.initial_bank_fill_percent) != len(BANK_REFERENCE_MAX_PRESSURE_PA) or any(
        not 1.0 <= percent <= 100.0 for percent in config.initial_bank_fill_percent
    ):
        raise ValueError("initial_bank_fill_percent must contain three values from 1 to 100")
    if config.vehicle_internal_volume_m3 <= 0.0 or config.vehicle_2_internal_volume_m3 <= 0.0:
        raise ValueError("vehicle tank volumes must be positive")
    if min(
        config.vehicle_nominal_working_pressure_pa,
        config.vehicle_2_nominal_working_pressure_pa,
    ) <= 0.0:
        raise ValueError("vehicle nominal working pressures must be positive")
    if min(
        config.vehicle_effective_volume_multiplier,
        config.vehicle_gas_liner_ua_multiplier,
        config.dispenser_flow_area_multiplier,
        config.precooler_duty_multiplier,
        config.maximum_precooler_temperature_deviation_k,
    ) <= 0.0:
        raise ValueError("fit multipliers and precooler tolerance must be positive")
    vehicle_fit = CompositeTankFitParameters(
        effective_volume_multiplier=config.vehicle_effective_volume_multiplier,
        gas_liner_ua_multiplier=config.vehicle_gas_liner_ua_multiplier,
    )
    vehicle = build_vehicle_tank(config.vehicle_internal_volume_m3, vehicle_fit)
    secondary_vehicle = build_vehicle_tank(config.vehicle_2_internal_volume_m3, vehicle_fit)
    dispenser_fit = DispenserFitParameters(
        pcv_area_multiplier=config.dispenser_flow_area_multiplier,
        nozzle_area_multiplier=config.dispenser_flow_area_multiplier,
        precooler_ua_multiplier=config.precooler_duty_multiplier,
        chiller_ua_multiplier=config.precooler_duty_multiplier,
    )
    controller = SampledFuelingController(
        FuelingSchedule(
            target_pressure_pa=config.target_vehicle_pressure_pa,
            average_pressure_ramp_rate_pa_s=(
                config.average_pressure_ramp_rate_pa_s
            ),
            delivery_temperature_k=config.delivery_temperature_k,
            maximum_mass_flow_kg_s=config.maximum_mass_flow_kg_s,
            nominal_working_pressure_pa=(
                config.vehicle_nominal_working_pressure_pa
            ),
        )
    )
    partial = PartialStationModel(
        vehicle_tank=vehicle,
        controller=controller,
        supply=lambda time_s: SupplyState(90.0e6, config.ambient_temperature_k),
        pcv=RestrictionParameters(flow_area_m2=1.5e-6),
        precooler=PrecoolerParameters(
            hydrogen_coolant_ua_w_k=2200.0,
            coolant_thermal_capacity_j_k=3.0e5,
            chiller_ua_w_k=6000.0,
            hydrogen_pressure_drop_pa=1.0e5,
        ),
        hose=HoseParameters(
            internal_volume_m3=2.0e-3,
            wall_thermal_capacity_j_k=1.2e4,
            gas_wall_ua_w_k=45.0,
            wall_ambient_ua_w_k=18.0,
            nozzle_flow_area_m2=2.0e-6,
        ),
        fit=dispenser_fit,
        ambient_temperature_k=config.ambient_temperature_k,
    )
    secondary_controller = SampledFuelingController(
        FuelingSchedule(
            target_pressure_pa=config.target_vehicle_2_pressure_pa,
            average_pressure_ramp_rate_pa_s=config.average_pressure_ramp_rate_pa_s,
            delivery_temperature_k=config.delivery_temperature_k,
            maximum_mass_flow_kg_s=config.maximum_mass_flow_kg_s,
            nominal_working_pressure_pa=(
                config.vehicle_2_nominal_working_pressure_pa
            ),
        )
    )
    secondary_partial = PartialStationModel(
        vehicle_tank=secondary_vehicle,
        controller=secondary_controller,
        supply=lambda time_s: SupplyState(90.0e6, config.ambient_temperature_k),
        pcv=RestrictionParameters(flow_area_m2=1.5e-6),
        precooler=PrecoolerParameters(
            hydrogen_coolant_ua_w_k=2200.0,
            coolant_thermal_capacity_j_k=3.0e5,
            chiller_ua_w_k=6000.0,
            hydrogen_pressure_drop_pa=1.0e5,
        ),
        hose=HoseParameters(
            internal_volume_m3=2.0e-3,
            wall_thermal_capacity_j_k=1.2e4,
            gas_wall_ua_w_k=45.0,
            wall_ambient_ua_w_k=18.0,
            nozzle_flow_area_m2=2.0e-6,
        ),
        fit=dispenser_fit,
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
    initial_vehicle_2 = secondary_vehicle.initial_state(
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
            # A fixed -20 °C trip is only appropriate for a T40-class request.
            # Warm/slow public fills legitimately command warmer delivery gas;
            # their safety limit must follow the requested temperature class.
            maximum_precooler_outlet_temperature_k=max(
                253.15,
                config.delivery_temperature_k
                + config.maximum_precooler_temperature_deviation_k,
            ),
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
