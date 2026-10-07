"""Traceable reference scenario assembly for API and scripted operation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .dispenser import (
    DispenserFitParameters,
    HoseParameters,
    PartialStationModel,
    PrecoolerParameters,
    RestrictionParameters,
    SupplyState,
)
from .detector_policy import load_public_detector_policy
from .full_station import (
    CascadeBank,
    CascadeBankParameters,
    CascadeSupervisor,
    CascadeSupervisorParameters,
    CompressorParameters,
    FullStationModel,
    FullStationState,
    MultistageHydrogenCompressor,
)
from .protocol import FuelingSchedule, SampledFuelingController, _profile_value
from .risk.live import DynamicRiskMonitor, HyRAMConsequenceBackend
from .safe_operation import SafeFullStationSimulator
from .public_tank_calibration import load_public_type_iv_tank_calibration
from .safety_runtime import (
    FaultEvent,
    FaultInjector,
    FaultSchedule,
    SafetyLimits,
    SafetyPLC,
)
from .tabulated import PropsSI
from .vehicle import (
    CompositeTankFitParameters,
    CompositeTankParameters,
    CompositeVehicleTank,
)


BANK_REFERENCE_MAX_PRESSURE_PA = (50.0e6, 70.0e6, 100.0e6)
DEFAULT_BANK_INITIAL_FILL_PERCENT = (90.0, 100.0 * 65.0 / 70.0, 90.0)
CAPACITY_EOS_REFERENCE_TEMPERATURE_K = 288.15


@dataclass(frozen=True)
class ReferenceScenario:
    duration_s: float = 300.0
    control_period_s: float = 0.2
    ambient_temperature_k: float = 298.15
    initial_vehicle_pressure_pa: float = 5.0e6
    initial_vehicle_temperature_k: float = 298.15
    vehicle_internal_volume_m3: float = 0.122
    vehicle_nominal_working_pressure_pa: float = 70.0e6
    # ``reference`` preserves the historical 0.122 m³ geometry.  The
    # capacity-EOS option derives the tank volume from its declared capacity
    # and the hydrogen property table at the public 15 °C reference state.
    # It remains opt-in until a frozen external holdout is re-run.
    vehicle_geometry_basis: Literal["reference", "capacity_eos"] = "reference"
    vehicle_capacity_kg: float | None = None
    # The default is a public, split-validated Type-IV tank fit for this
    # demonstrator's 4.7 kg / 70 MPa reference surrogate.  ``reference`` is
    # retained for sensitivity work and any configuration outside that model
    # scope.  Neither mode validates the station-side source topology.
    vehicle_tank_calibration: Literal["public_type_iv", "reference"] = "public_type_iv"
    vehicle_effective_volume_multiplier: float | None = None
    vehicle_gas_liner_ua_multiplier: float | None = None
    dispenser_flow_area_multiplier: float = 1.0
    precooler_duty_multiplier: float = 1.0
    initial_vehicle_2_pressure_pa: float = 5.0e6
    initial_vehicle_2_temperature_k: float = 298.15
    vehicle_2_internal_volume_m3: float = 0.122
    vehicle_2_nominal_working_pressure_pa: float = 70.0e6
    vehicle_2_capacity_kg: float | None = None
    target_vehicle_pressure_pa: float = 70.0e6
    target_vehicle_2_pressure_pa: float = 70.0e6
    average_pressure_ramp_rate_pa_s: float = 2.0e5
    delivery_temperature_k: float = 233.15
    maximum_gas_temperature_k: float = 358.15
    maximum_precooler_temperature_deviation_k: float = 15.0
    maximum_mass_flow_kg_s: float = 0.060
    risk_update_period_s: float = 1.0
    compressor_suction_pressure_pa: float = 20.0e6
    compressor_suction_temperature_k: float = 298.15
    # Optional owner-approved station calibration.  None preserves the
    # conservative reference defaults; a controlled replay may provide a
    # measured restart margin without embedding raw station data.
    station_dispatch_pressure_margin_pa: float | None = None
    station_recharge_hysteresis_pa: float | None = None
    # Optional owner-attested station-side dynamic calibration.  It represents
    # the observed compressor restart dwell only; it is not a vehicle-fill or
    # compressor-capacity validation result.
    station_minimum_recharge_off_time_s: float | None = None
    # Finite common-header inventory between the cascade selectors and both
    # dispenser PCVs. These are declared reference geometry values, not fitted
    # station data; frozen station-side validation must evaluate them unchanged.
    header_internal_volume_m3: float = 0.015
    bank_header_flow_area_m2: float = 6.0e-6
    initial_bank_fill_percent: tuple[float, float, float] = DEFAULT_BANK_INITIAL_FILL_PERCENT
    fault_events: tuple[FaultEvent, ...] = ()
    # Optional time-dependent boundary traces used by partial-station validation.
    # Empty profiles retain the original constant-boundary behavior.
    supply_pressure_profile_pa: tuple[tuple[float, float], ...] = ()
    supply_temperature_profile_k: tuple[tuple[float, float], ...] = ()
    delivery_temperature_profile_k: tuple[tuple[float, float], ...] = ()
    pressure_reference_profile_pa: tuple[tuple[float, float], ...] = ()


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


def capacity_eos_volume_m3(
    capacity_kg: float,
    nominal_working_pressure_pa: float,
    reference_temperature_k: float = CAPACITY_EOS_REFERENCE_TEMPERATURE_K,
) -> float:
    """Convert a declared gas capacity to volume using the runtime H2 EOS."""

    if capacity_kg <= 0.0:
        raise ValueError("capacity_kg must be positive")
    if nominal_working_pressure_pa <= 0.0 or reference_temperature_k <= 0.0:
        raise ValueError("reference pressure and temperature must be positive")
    density = float(
        PropsSI(
            "Dmass", "P", nominal_working_pressure_pa,
            "T", reference_temperature_k, "Hydrogen",
        )
    )
    if density <= 0.0:
        raise ValueError("hydrogen EOS returned a non-positive density")
    return capacity_kg / density


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
    if config.vehicle_tank_calibration not in {"public_type_iv", "reference"}:
        raise ValueError("vehicle_tank_calibration must be public_type_iv or reference")
    calibrated_tank = (
        load_public_type_iv_tank_calibration()
        if config.vehicle_tank_calibration == "public_type_iv" else None
    )
    if config.vehicle_tank_calibration == "public_type_iv" and calibrated_tank is None:
        raise RuntimeError("public Type-IV tank calibration artifact is unavailable or invalid")
    effective_volume_multiplier = (
        config.vehicle_effective_volume_multiplier
        if config.vehicle_effective_volume_multiplier is not None
        else (
            calibrated_tank.effective_volume_multiplier
            if calibrated_tank is not None else 1.0
        )
    )
    gas_liner_ua_multiplier = (
        config.vehicle_gas_liner_ua_multiplier
        if config.vehicle_gas_liner_ua_multiplier is not None
        else (
            calibrated_tank.gas_liner_ua_multiplier
            if calibrated_tank is not None else 1.0
        )
    )
    if min(
        effective_volume_multiplier,
        gas_liner_ua_multiplier,
        config.dispenser_flow_area_multiplier,
        config.precooler_duty_multiplier,
        config.maximum_gas_temperature_k,
        config.maximum_precooler_temperature_deviation_k,
        config.header_internal_volume_m3,
        config.bank_header_flow_area_m2,
    ) <= 0.0:
        raise ValueError("fit multipliers and precooler tolerance must be positive")
    if config.vehicle_geometry_basis not in {"reference", "capacity_eos"}:
        raise ValueError("vehicle_geometry_basis must be 'reference' or 'capacity_eos'")
    if any(
        value is not None and value <= 0.0
        for value in (config.vehicle_capacity_kg, config.vehicle_2_capacity_kg)
    ):
        raise ValueError("vehicle capacities must be positive when provided")
    if config.vehicle_geometry_basis == "capacity_eos":
        if config.vehicle_capacity_kg is None or config.vehicle_2_capacity_kg is None:
            raise ValueError("capacity_eos geometry requires both vehicle capacities")
        vehicle_volume_m3 = capacity_eos_volume_m3(
            config.vehicle_capacity_kg, config.vehicle_nominal_working_pressure_pa
        )
        vehicle_2_volume_m3 = capacity_eos_volume_m3(
            config.vehicle_2_capacity_kg, config.vehicle_2_nominal_working_pressure_pa
        )
    else:
        vehicle_volume_m3 = config.vehicle_internal_volume_m3
        vehicle_2_volume_m3 = config.vehicle_2_internal_volume_m3
    if any(
        value is not None and value <= 0.0
        for value in (
            config.station_dispatch_pressure_margin_pa,
            config.station_recharge_hysteresis_pa,
        )
    ):
        raise ValueError("station calibration margins must be positive when provided")
    if (
        config.station_minimum_recharge_off_time_s is not None
        and config.station_minimum_recharge_off_time_s < 0.0
    ):
        raise ValueError("station_minimum_recharge_off_time_s cannot be negative")
    vehicle_fit = CompositeTankFitParameters(
        effective_volume_multiplier=effective_volume_multiplier,
        gas_liner_ua_multiplier=gas_liner_ua_multiplier,
    )
    vehicle = build_vehicle_tank(vehicle_volume_m3, vehicle_fit)
    secondary_vehicle = build_vehicle_tank(vehicle_2_volume_m3, vehicle_fit)
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
            maximum_gas_temperature_k=config.maximum_gas_temperature_k,
            maximum_mass_flow_kg_s=config.maximum_mass_flow_kg_s,
            delivery_temperature_profile_k=config.delivery_temperature_profile_k,
            pressure_reference_profile_pa=config.pressure_reference_profile_pa,
            nominal_working_pressure_pa=(
                config.vehicle_nominal_working_pressure_pa
            ),
        )
    )
    partial = PartialStationModel(
        vehicle_tank=vehicle,
        controller=controller,
        supply=lambda time_s: SupplyState(
            _profile_value(config.supply_pressure_profile_pa, time_s, 90.0e6),
            _profile_value(
                config.supply_temperature_profile_k,
                time_s,
                config.ambient_temperature_k,
            ),
        ),
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
            maximum_gas_temperature_k=config.maximum_gas_temperature_k,
            maximum_mass_flow_kg_s=config.maximum_mass_flow_kg_s,
            delivery_temperature_profile_k=config.delivery_temperature_profile_k,
            pressure_reference_profile_pa=config.pressure_reference_profile_pa,
            nominal_working_pressure_pa=(
                config.vehicle_2_nominal_working_pressure_pa
            ),
        )
    )
    secondary_partial = PartialStationModel(
        vehicle_tank=secondary_vehicle,
        controller=secondary_controller,
        supply=lambda time_s: SupplyState(
            _profile_value(config.supply_pressure_profile_pa, time_s, 90.0e6),
            _profile_value(
                config.supply_temperature_profile_k,
                time_s,
                config.ambient_temperature_k,
            ),
        ),
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
    common_header = CascadeBank(
        CascadeBankParameters(
            name="common-header",
            internal_volume_m3=config.header_internal_volume_m3,
            target_pressure_pa=100.0e6,
            wall_mass_kg=45.0,
            wall_specific_heat_j_kg_k=500.0,
            gas_wall_ua_w_k=18.0,
            wall_ambient_ua_w_k=8.0,
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
        common_header=common_header,
        bank_header_restriction=RestrictionParameters(
            flow_area_m2=config.bank_header_flow_area_m2,
        ),
        supervisor=CascadeSupervisor(
            CascadeSupervisorParameters(
                minimum_dispatch_pressure_margin_pa=(
                    config.station_dispatch_pressure_margin_pa
                    if config.station_dispatch_pressure_margin_pa is not None
                    else 1.0e6
                ),
                recharge_pressure_hysteresis_pa=(
                    config.station_recharge_hysteresis_pa
                    if config.station_recharge_hysteresis_pa is not None
                    else 1.0e6
                ),
                minimum_recharge_off_time_s=(
                    config.station_minimum_recharge_off_time_s
                    if config.station_minimum_recharge_off_time_s is not None
                    else 0.0
                ),
            )
        ),
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
    initial_bank_states = tuple(
        bank.initial_state(maximum_pa * percent / 100.0, config.ambient_temperature_k)
        for bank, maximum_pa, percent in zip(
            banks,
            BANK_REFERENCE_MAX_PRESSURE_PA,
            config.initial_bank_fill_percent,
        )
    )
    # The reference startup aligns the isolated header with the first (low)
    # cascade step. This avoids inventing a retained high-bank line pack at a
    # cold start while still allowing a continued run to preserve its true
    # residual header pressure in ``final_state``.
    initial_header_pressure_pa = min(
        maximum_pa * percent / 100.0
        for maximum_pa, percent in zip(
            BANK_REFERENCE_MAX_PRESSURE_PA,
            config.initial_bank_fill_percent,
        )
    )
    initial_state = FullStationState(
        banks=initial_bank_states,
        partial_station=initial_partial,
        secondary_partial_station=initial_partial_2,
        common_header=common_header.initial_state(
            initial_header_pressure_pa,
            config.ambient_temperature_k,
        ),
    )
    fault_injector = FaultInjector(FaultSchedule(config.fault_events))
    detector_policy = load_public_detector_policy()
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
            detector_alarm_volume_fraction=detector_policy.alarm_volume_fraction,
            detector_trip_volume_fraction=detector_policy.trip_volume_fraction,
            trip_persistence_s=detector_policy.persistence_s,
            detector_policy_source=detector_policy.source_artifact,
            detector_policy_doi=detector_policy.source_doi,
            detector_policy_status=detector_policy.evidence_status,
            detector_policy_claim_limit=detector_policy.claim_limit,
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
