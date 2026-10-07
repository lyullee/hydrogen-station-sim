"""Closed-loop full-station operation with faults, ESD, leaks, and HyRAM."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from time import sleep

import numpy as np
from scipy.integrate import solve_ivp

from .dispenser import PartialStationState, SupplyState
from .full_station import (
    CascadeBankState,
    CompressorResult,
    FullStationModel,
    FullStationState,
)
from .integration_lock import nonreentrant_integrator_lock
from .operations import ProcessRuntime
from .protocol import FuelingCommand, FuelingObservation, FuelingPhase
from .risk.live import (
    DynamicRiskMonitor,
    DynamicRiskSnapshot,
    LeakScenario,
    LeakSourceState,
)
from .safety_runtime import (
    FaultEvent,
    FaultInjector,
    FaultKind,
    SafetyCommand,
    SafetyPLC,
    StationMeasurements,
)


ConcentrationExtractor = Callable[
    [tuple[DynamicRiskSnapshot, ...]],
    Mapping[str, float],
]


@dataclass(frozen=True)
class SafeOperationTrajectory:
    time_s: np.ndarray
    states: np.ndarray
    vehicle_pressure_pa: np.ndarray
    vehicle_temperature_k: np.ndarray
    vehicle_density_kg_m3: np.ndarray
    vehicle_2_pressure_pa: np.ndarray
    vehicle_2_temperature_k: np.ndarray
    vehicle_2_density_kg_m3: np.ndarray
    pcv_mass_flow_kg_s: np.ndarray
    nozzle_mass_flow_kg_s: np.ndarray
    pcv_1_mass_flow_kg_s: np.ndarray
    pcv_2_mass_flow_kg_s: np.ndarray
    nozzle_1_mass_flow_kg_s: np.ndarray
    nozzle_2_mass_flow_kg_s: np.ndarray
    leak_mass_flow_by_release: Mapping[str, np.ndarray]
    safety_commands: tuple[SafetyCommand, ...]
    fueling_commands: tuple[FuelingCommand, ...]
    risk_snapshots: tuple[tuple[DynamicRiskSnapshot, ...], ...]
    dispatch_bank: tuple[str | None, ...]
    dispatch_bank_2: tuple[str | None, ...]
    recharge_bank: tuple[str | None, ...]
    esd_time_s: float | None
    final_state: FullStationState | None = None


@dataclass(frozen=True)
class SafeOperationSample:
    """One completed sampled-control state for live monitoring."""

    time_s: float
    vehicle_pressure_pa: float
    vehicle_temperature_k: float
    vehicle_density_kg_m3: float
    vehicle_2_pressure_pa: float
    vehicle_2_temperature_k: float
    vehicle_2_density_kg_m3: float
    hose_pressure_pa: float
    hose_temperature_k: float
    precooler_outlet_temperature_k: float
    pcv_mass_flow_kg_s: float
    nozzle_mass_flow_kg_s: float
    pcv_1_mass_flow_kg_s: float
    pcv_2_mass_flow_kg_s: float
    nozzle_1_mass_flow_kg_s: float
    nozzle_2_mass_flow_kg_s: float
    total_leak_mass_flow_kg_s: float
    bank_pressure_pa: Mapping[str, float]
    dispatch_bank: str | None
    dispatch_bank_2: str | None
    recharge_bank: str | None
    esd_latched: bool
    trip_causes: tuple[str, ...]
    consequence_updated: bool
    hose_2_pressure_pa: float | None = None
    hose_2_temperature_k: float | None = None
    hazop: Mapping | None = None
    active_faults: tuple[str, ...] = ()
    process_operations: Mapping | None = None
    process_activity: Mapping | None = None
    vehicle_mass_kg: float | None = None
    vehicle_2_mass_kg: float | None = None
    virtual_safety: Mapping | None = None
    bank_temperature_k: Mapping[str, float] | None = None
    bank_mass_kg: Mapping[str, float] | None = None


class SafeFullStationSimulator:
    """Hybrid runtime that closes the physics, protection, and risk feedback loops."""

    def __init__(
        self,
        station: FullStationModel,
        fault_injector: FaultInjector,
        safety_plc: SafetyPLC,
        risk_monitor: DynamicRiskMonitor,
        leak_scenarios: Mapping[str, LeakScenario] | None = None,
        concentration_extractor: ConcentrationExtractor | None = None,
        hazop_monitor=None,
        process_runtime: ProcessRuntime | None = None,
    ) -> None:
        self.station = station
        self.fault_injector = fault_injector
        self.safety_plc = safety_plc
        self.risk_monitor = risk_monitor
        self.leak_scenarios = dict(leak_scenarios or {})
        self.hazop_monitor = hazop_monitor
        self.process_runtime = process_runtime
        self.concentration_extractor = (
            concentration_extractor or self._default_concentration_extractor
        )

    def simulate(
        self,
        initial_state: FullStationState,
        duration_s: float,
        control_period_s: float = 0.1,
        progress_callback: Callable[[float, float], None] | None = None,
        sample_callback: Callable[[SafeOperationSample], None] | None = None,
        *,
        start_time_s: float = 0.0,
        reset_runtime: bool = True,
        stop_callback: Callable[[], bool] | None = None,
        runtime_command_callback: Callable[[float], None] | None = None,
        pace_idle: bool = True,
    ) -> SafeOperationTrajectory:
        if duration_s <= 0.0 or control_period_s <= 0.0:
            raise ValueError("Simulation duration and control period must be positive")
        if len(initial_state.banks) != len(self.station.banks):
            raise ValueError("Initial-state bank count does not match the station")

        if start_time_s < 0.0:
            raise ValueError("Simulation start time must be non-negative")
        if reset_runtime:
            self.fault_injector.reset()
            self.risk_monitor.reset()
            self.station.supervisor.reset()
            self.station.valve_sequencer.reset()
            self.station.secondary_valve_sequencer.reset()
            self._last_vehicle_requested = (False, False)
        leak_ids = tuple(
            event.event_id
            for event in self.fault_injector.schedule.events
            if event.kind is FaultKind.HYDROGEN_LEAK
        )
        leak_histories: dict[str, list[float]] = {
            release_id: [] for release_id in leak_ids
        }
        times: list[float] = []
        states: list[np.ndarray] = []
        vehicle_pressures: list[float] = []
        vehicle_temperatures: list[float] = []
        vehicle_densities: list[float] = []
        vehicle_2_pressures: list[float] = []
        vehicle_2_temperatures: list[float] = []
        vehicle_2_densities: list[float] = []
        pcv_flows: list[float] = []
        nozzle_flows: list[float] = []
        pcv_1_flows: list[float] = []
        pcv_2_flows: list[float] = []
        nozzle_1_flows: list[float] = []
        nozzle_2_flows: list[float] = []
        safety_history: list[SafetyCommand] = []
        fueling_history: list[FuelingCommand] = []
        risk_history: list[tuple[DynamicRiskSnapshot, ...]] = []
        dispatch_history: list[str | None] = []
        dispatch_2_history: list[str | None] = []
        recharge_history: list[str | None] = []

        current = initial_state
        time_s = float(start_time_s)
        end_time_s = float(start_time_s + duration_s)
        previous_pcv_flow = 0.0
        previous_nozzle_flow = 0.0
        previous_pcv_2_flow = 0.0
        previous_nozzle_2_flow = 0.0
        previous_precooler_temperature = (
            current.partial_station.coolant_temperature_k
        )
        previous_precooler_2_temperature = (
            current.secondary_partial_station.coolant_temperature_k
            if current.secondary_partial_station is not None
            else previous_precooler_temperature
        )
        detector_concentrations: Mapping[str, float] = {}
        esd_time_s: float | None = (
            getattr(self, "_continuous_esd_time_s", None) if not reset_runtime else None
        )
        previous_dispatch_index: int | None = None
        previous_dispatch_2_index: int | None = None
        current_fueling_phase = FuelingPhase.IDLE

        if progress_callback is not None:
            progress_callback(time_s, end_time_s)

        while time_s <= end_time_s:
            if runtime_command_callback is not None:
                runtime_command_callback(time_s)
            bank_gases = tuple(
                bank.gas_state(bank_state)
                for bank, bank_state in zip(self.station.banks, current.banks)
            )
            hose_gas = self.station.partial_station.hose_gas_state(
                current.partial_station
            )
            vehicle_gas = self.station.partial_station.vehicle_tank.gas_state(
                current.partial_station.vehicle
            )
            if (
                self.station.secondary_partial_station is None
                or current.secondary_partial_station is None
            ):
                raise ValueError("Dual-dispenser scenario requires a secondary state")
            hose_2_gas = self.station.secondary_partial_station.hose_gas_state(
                current.secondary_partial_station
            )
            vehicle_2_gas = (
                self.station.secondary_partial_station.vehicle_tank.gas_state(
                    current.secondary_partial_station.vehicle
                )
            )
            process = self.process_runtime
            virtual_safety = process.safety if process is not None else None
            if virtual_safety is not None:
                virtual_safety.tick(time_s)
            if process is not None:
                process.stop_recharge_at_targets(tuple(gas.pressure_pa for gas in bank_gases))
                requested_1 = process.requested("vehicle_1")
                requested_2 = process.requested("vehicle_2")
            else:
                requested_1 = requested_2 = True
            raw_measurements = StationMeasurements(
                time_s=time_s,
                fueling_phase=current_fueling_phase,
                vehicle_pressure_pa=max(
                    vehicle_gas.pressure_pa, vehicle_2_gas.pressure_pa
                ),
                vehicle_temperature_k=max(
                    vehicle_gas.temperature_k, vehicle_2_gas.temperature_k
                ),
                hose_pressure_pa=max(hose_gas.pressure_pa, hose_2_gas.pressure_pa),
                hose_temperature_k=max(
                    hose_gas.temperature_k, hose_2_gas.temperature_k
                ),
                pcv_mass_flow_kg_s=previous_pcv_flow + previous_pcv_2_flow,
                nozzle_mass_flow_kg_s=(
                    previous_nozzle_flow + previous_nozzle_2_flow
                ),
                precooler_outlet_temperature_k=max(
                    previous_precooler_temperature,
                    previous_precooler_2_temperature,
                ),
                hydrogen_concentration_by_detector=detector_concentrations,
            )
            measured = self.fault_injector.measurements(raw_measurements)
            override = self.fault_injector.operational_override(time_s)
            safety_command = self.safety_plc.update(
                measured,
                control_period_s,
                override.emergency_stop_requested or bool(virtual_safety and virtual_safety.esd_requested),
            )
            if safety_command.esd_latched and esd_time_s is None:
                esd_time_s = time_s

            observation = FuelingObservation(
                time_s=time_s,
                pressure_pa=vehicle_gas.pressure_pa,
                temperature_k=vehicle_gas.temperature_k,
                density_kg_m3=vehicle_gas.density_kg_m3,
                measured_mass_flow_kg_s=previous_nozzle_flow,
            )
            if process is not None and not requested_1:
                if self._last_vehicle_requested[0]:
                    self.station.partial_station.controller.reset()
                fueling_command = FuelingCommand(FuelingPhase.IDLE, 0.0, vehicle_gas.pressure_pa,
                    self.station.partial_station.controller.schedule.delivery_temperature_k,
                    self.station.partial_station.controller.soc_model.calculate(vehicle_gas.density_kg_m3), "operator-idle")
            else:
                if process is not None and not self._last_vehicle_requested[0]:
                    self.station.supervisor.reset_dispatch("primary")
                    self.station.partial_station.controller.start(time_s, vehicle_gas.pressure_pa)
                fueling_command = self.station.partial_station.controller.update(
                    observation, control_period_s,
                    auto_stop=process.settings["vehicle_1_auto_stop"] if process is not None else True,
                    target_pressure_pa=(process.settings["vehicle_1_target_pressure_mpa"] * 1e6
                                        if process is not None else None))
            current_fueling_phase = fueling_command.phase
            observation_2 = FuelingObservation(
                time_s=time_s,
                pressure_pa=vehicle_2_gas.pressure_pa,
                temperature_k=vehicle_2_gas.temperature_k,
                density_kg_m3=vehicle_2_gas.density_kg_m3,
                measured_mass_flow_kg_s=previous_nozzle_2_flow,
            )
            if process is not None and not requested_2:
                if self._last_vehicle_requested[1]:
                    self.station.secondary_partial_station.controller.reset()
                fueling_command_2 = FuelingCommand(FuelingPhase.IDLE, 0.0, vehicle_2_gas.pressure_pa,
                    self.station.secondary_partial_station.controller.schedule.delivery_temperature_k,
                    self.station.secondary_partial_station.controller.soc_model.calculate(vehicle_2_gas.density_kg_m3), "operator-idle")
            else:
                if process is not None and not self._last_vehicle_requested[1]:
                    self.station.supervisor.reset_dispatch("secondary")
                    self.station.secondary_partial_station.controller.start(time_s, vehicle_2_gas.pressure_pa)
                fueling_command_2 = self.station.secondary_partial_station.controller.update(
                    observation_2, control_period_s,
                    auto_stop=process.settings["vehicle_2_auto_stop"] if process is not None else True,
                    target_pressure_pa=(process.settings["vehicle_2_target_pressure_mpa"] * 1e6
                                        if process is not None else None))
            if process is not None:
                self._last_vehicle_requested = (requested_1, requested_2)
                if fueling_command.phase is FuelingPhase.COMPLETE:
                    process.stop("vehicle_1", "vehicle-target")
                elif fueling_command.phase is FuelingPhase.ABORTED:
                    process.stop("vehicle_1", "safety-temperature")
                if fueling_command_2.phase is FuelingPhase.COMPLETE:
                    process.stop("vehicle_2", "vehicle-target")
                elif fueling_command_2.phase is FuelingPhase.ABORTED:
                    process.stop("vehicle_2", "safety-temperature")
            if current_fueling_phase is FuelingPhase.IDLE:
                current_fueling_phase = fueling_command_2.phase
            if safety_command.close_pcv:
                fueling_command = replace(fueling_command, valve_opening=0.0)
                fueling_command_2 = replace(fueling_command_2, valve_opening=0.0)
            forced_pcv_1 = self._forced_pcv_opening(override, "dispenser")
            forced_pcv_2 = self._forced_pcv_opening(override, "dispenser_2")
            if forced_pcv_1 is not None:
                fueling_command = replace(
                    fueling_command,
                    valve_opening=forced_pcv_1,
                )
            if forced_pcv_2 is not None:
                fueling_command_2 = replace(
                    fueling_command_2,
                    valve_opening=forced_pcv_2,
                )

            blocked_outlets = frozenset(
                index for index, bank in enumerate(self.station.banks)
                if virtual_safety is not None and
                virtual_safety.opening(f"bank.{bank.parameters.name}.outlet") == 0.0
            )
            blocked_inlets = frozenset(
                index for index, bank in enumerate(self.station.banks)
                if virtual_safety is not None and
                virtual_safety.opening(f"bank.{bank.parameters.name}.inlet") == 0.0
            )
            requested_dispatch_index = (
                None
                if safety_command.close_cascade_valves or
                (virtual_safety is not None and (not virtual_safety.allows("dispenser.1") or
                                                 virtual_safety.power_isolated["dispenser"])) or
                (process is not None and not requested_1 and forced_pcv_1 is None)
                else self.station.supervisor.select_dispatch_bank(
                    self.station.banks,
                    bank_gases,
                    hose_gas.pressure_pa,
                    excluded_indices=blocked_outlets,
                )
            )
            dispatch_index, dispatch_opening, _ = (
                self.station.valve_sequencer.update(
                    requested_dispatch_index,
                    control_period_s,
                )
            )
            requested_dispatch_2_index = (
                None
                if safety_command.close_cascade_valves or
                (virtual_safety is not None and (not virtual_safety.allows("dispenser.2") or
                                                 virtual_safety.power_isolated["dispenser"])) or
                (process is not None and not requested_2 and forced_pcv_2 is None)
                else self.station.supervisor.select_dispatch_bank(
                    self.station.banks,
                    bank_gases,
                    hose_2_gas.pressure_pa,
                    excluded_indices=blocked_outlets,
                    circuit_id="secondary",
                )
            )
            dispatch_2_index, dispatch_2_opening, _ = (
                self.station.secondary_valve_sequencer.update(
                    requested_dispatch_2_index,
                    control_period_s,
                )
            )
            if override.forced_cascade_valve_opening is not None:
                dispatch_opening = override.forced_cascade_valve_opening
                if dispatch_opening > 0.0 and dispatch_index is None:
                    dispatch_index = previous_dispatch_index or requested_dispatch_index
                dispatch_2_opening = override.forced_cascade_valve_opening
                if dispatch_2_opening > 0.0 and dispatch_2_index is None:
                    dispatch_2_index = (
                        previous_dispatch_2_index or requested_dispatch_2_index
                    )
            if virtual_safety is not None:
                if dispatch_index is not None:
                    dispatch_opening *= (virtual_safety.opening(f"bank.{self.station.banks[dispatch_index].parameters.name}.outlet")
                                         * virtual_safety.opening("dispenser.1"))
                if dispatch_2_index is not None:
                    dispatch_2_opening *= (virtual_safety.opening(f"bank.{self.station.banks[dispatch_2_index].parameters.name}.outlet")
                                           * virtual_safety.opening("dispenser.2"))
            if dispatch_index is not None:
                previous_dispatch_index = dispatch_index
            if dispatch_2_index is not None:
                previous_dispatch_2_index = dispatch_2_index

            recharge_index = (
                None
                if safety_command.stop_compressor or not override.compressor_enabled or
                (process is not None and not process.source_available()) or
                (virtual_safety is not None and (
                    any(not virtual_safety.allows(name) for name in
                        ("trailer.source", "trailer.station", "compressor.suction", "compressor.discharge"))
                    or virtual_safety.power_isolated["compressor"]
                    or virtual_safety.power_isolated["unloading"]))
                else self.station.supervisor.select_recharge_bank(
                    self.station.banks,
                    bank_gases,
                    (dispatch_index, dispatch_2_index),
                    target_pressures_pa=process.recharge_targets_pa() if process is not None else None,
                    restart_margins_pa=process.recharge_restart_margins_pa() if process is not None else None,
                    ignore_targets=not process.settings["recharge_auto_stop"] if process is not None else False,
                    excluded_indices=blocked_inlets,
                    time_s=time_s,
                )
            )
            compressor_flow_multiplier = (
                min((virtual_safety.opening(name) for name in
                     ("trailer.source", "trailer.station", "compressor.suction", "compressor.discharge",
                      f"bank.{self.station.banks[recharge_index].parameters.name}.inlet")), default=1.0)
                if virtual_safety is not None and recharge_index is not None else 1.0
            )
            supply_index = dispatch_index if dispatch_index is not None else int(
                np.argmax([gas.pressure_pa for gas in bank_gases])
            )
            supply = SupplyState(
                bank_gases[supply_index].pressure_pa,
                bank_gases[supply_index].temperature_k,
            )
            effective_command = fueling_command
            effective_primary_pcv_multiplier = (
                self._flow_multipliers(override, "dispenser")[0] * dispatch_opening
                if dispatch_index is not None else 0.0
            )
            instantaneous = self.station.partial_station._flow_and_thermal_states(
                time_s,
                current.partial_station,
                effective_command,
                supply,
                override.precooler_capacity_multiplier,
                effective_primary_pcv_multiplier,
                (self._flow_multipliers(override, "dispenser")[1] *
                 (virtual_safety.opening("dispenser.1") if virtual_safety is not None else 1.0)) if requested_1 and not safety_command.esd_latched else 0.0,
                self._allow_reverse_flow(override, "dispenser"),
            )
            supply_2_index = (
                dispatch_2_index if dispatch_2_index is not None else supply_index
            )
            supply_2 = SupplyState(
                bank_gases[supply_2_index].pressure_pa,
                bank_gases[supply_2_index].temperature_k,
            )
            effective_command_2 = fueling_command_2
            effective_secondary_pcv_multiplier = (
                self._flow_multipliers(override, "dispenser_2")[0] * dispatch_2_opening
                if dispatch_2_index is not None else 0.0
            )
            instantaneous_2 = (
                self.station.secondary_partial_station._flow_and_thermal_states(
                    time_s,
                    current.secondary_partial_station,
                    effective_command_2,
                    supply_2,
                    override.precooler_capacity_multiplier,
                    effective_secondary_pcv_multiplier,
                    (self._flow_multipliers(override, "dispenser_2")[1] *
                     (virtual_safety.opening("dispenser.2") if virtual_safety is not None else 1.0)) if requested_2 and not safety_command.esd_latched else 0.0,
                    self._allow_reverse_flow(override, "dispenser_2"),
                )
            )
            previous_pcv_flow = instantaneous["pcv_mass_flow"]
            previous_nozzle_flow = instantaneous["nozzle_mass_flow"]
            previous_pcv_2_flow = instantaneous_2["pcv_mass_flow"]
            previous_nozzle_2_flow = instantaneous_2["nozzle_mass_flow"]
            previous_precooler_temperature = instantaneous[
                "precooler_outlet_temperature"
            ]
            previous_precooler_2_temperature = instantaneous_2[
                "precooler_outlet_temperature"
            ]

            relief_events = process.relief_events({
                "low": bank_gases[0].pressure_pa,
                "medium": bank_gases[1].pressure_pa,
                "high": bank_gases[2].pressure_pa,
                "hose_1": hose_gas.pressure_pa,
                "hose_2": hose_2_gas.pressure_pa,
                "vehicle_1": vehicle_gas.pressure_pa,
                "vehicle_2": vehicle_2_gas.pressure_pa,
            }, time_s) if process is not None else ()
            vent_events = virtual_safety.vent_events(time_s) if virtual_safety is not None else ()
            cooling_events = (virtual_safety.cooling_events(time_s, self.station.ambient_temperature_k)
                              if virtual_safety is not None else ())
            if relief_events or vent_events:
                override = replace(override, active_leaks=override.active_leaks + relief_events + vent_events)
            active_events = self.fault_injector.schedule.active_events(time_s) + relief_events + vent_events
            active_leaks = self._active_leak_inputs(
                override.active_leaks,
                current,
            )
            risk_snapshots = self.risk_monitor.update(
                time_s,
                control_period_s,
                {
                    scenario: source
                    for _, scenario, source, _ in active_leaks
                },
            )
            detector_concentrations = self.concentration_extractor(risk_snapshots)
            leak_rates = {
                event.event_id: self.risk_monitor.leak_model.mass_flow_kg_s(
                    scenario, source
                )
                for event, scenario, source, _ in active_leaks
            }

            times.append(time_s)
            states.append(current.as_vector())
            vehicle_pressures.append(vehicle_gas.pressure_pa)
            vehicle_temperatures.append(vehicle_gas.temperature_k)
            vehicle_densities.append(vehicle_gas.density_kg_m3)
            vehicle_2_pressures.append(vehicle_2_gas.pressure_pa)
            vehicle_2_temperatures.append(vehicle_2_gas.temperature_k)
            vehicle_2_densities.append(vehicle_2_gas.density_kg_m3)
            pcv_flows.append(previous_pcv_flow + previous_pcv_2_flow)
            nozzle_flows.append(previous_nozzle_flow + previous_nozzle_2_flow)
            pcv_1_flows.append(previous_pcv_flow)
            pcv_2_flows.append(previous_pcv_2_flow)
            nozzle_1_flows.append(previous_nozzle_flow)
            nozzle_2_flows.append(previous_nozzle_2_flow)
            safety_history.append(safety_command)
            fueling_history.append(fueling_command)
            risk_history.append(risk_snapshots)
            dispatch_history.append(
                self.station.banks[dispatch_index].parameters.name
                if dispatch_index is not None else None
            )
            dispatch_2_history.append(
                self.station.banks[dispatch_2_index].parameters.name
                if dispatch_2_index is not None else None
            )
            recharge_history.append(
                self.station.banks[recharge_index].parameters.name
                if recharge_index is not None else None
            )
            # A release can be injected after integration has begun. Backfill its
            # earlier samples so every trajectory keeps a rectangular time series.
            for release_id in leak_rates:
                leak_histories.setdefault(release_id, [0.0] * (len(times) - 1))
            for release_id in leak_histories:
                leak_histories[release_id].append(leak_rates.get(release_id, 0.0))

            process_snapshot = process.snapshot() if process is not None else None
            virtual_safety_snapshot = (
                virtual_safety.snapshot(include_actions=False)
                if virtual_safety is not None else None
            )
            hazop_frame = None
            if self.hazop_monitor is not None:
                hazop_frame = self.hazop_monitor.sample(
                    time_s, station=self.station, state=current,
                    commands=(fueling_command, fueling_command_2),
                    instantaneous=(instantaneous, instantaneous_2),
                    dispatch_indices=(dispatch_index, dispatch_2_index),
                    dispatch_openings=(dispatch_opening, dispatch_2_opening),
                    recharge_index=recharge_index, safety=safety_command,
                    fault_events=active_events,
                    active_leaks=active_leaks, risk_snapshots=risk_snapshots,
                    compressor_flow_multiplier=compressor_flow_multiplier,
                    detector_multiplier=(virtual_safety.detector_multiplier if virtual_safety is not None else None),
                    process_snapshot=process_snapshot,
                    virtual_safety_snapshot=virtual_safety_snapshot,
                )

            process_activity = None
            if process_snapshot is not None:
                settings = process_snapshot["settings"]
                reasons = process_snapshot["stop_reason"]
                compressor_flow_g_s = 0.0
                if recharge_index is not None:
                    compressor_flow_g_s = 1000.0 * self.station.compressor.evaluate(
                        self.station.compressor_suction(time_s),
                        bank_gases[recharge_index].pressure_pa
                        + self.station.compressor.parameters.discharge_pressure_margin_pa,
                        enabled=True,
                    ).mass_flow_kg_s
                    compressor_flow_g_s *= compressor_flow_multiplier

                def operation_state(key: str, flow_g_s: float, wait_reason: str) -> dict[str, object]:
                    if not settings[key]:
                        reason = reasons[key]
                        state = ("auto-stopped" if reason in ("bank-target", "vehicle-target")
                                 else "blocked" if reason in ("source-depleted", "safety-temperature") else "idle")
                    elif safety_command.esd_latched:
                        state, reason = "blocked", "esd"
                    elif flow_g_s > 1e-5:
                        state, reason = "flowing", None
                    else:
                        state, reason = "waiting", wait_reason
                    return {"state": state, "reason": reason, "flow_g_s": flow_g_s}

                supply_wait = ("recharge-off" if not settings["pressure_recharge"]
                               else "bank-target" if recharge_index is None else "compressor-starting")
                recharge_wait = ("supply-off" if not settings["trailer_supply"]
                                 else "bank-target" if recharge_index is None else "compressor-starting")
                process_activity = {
                    "trailer_supply": operation_state("trailer_supply", compressor_flow_g_s, supply_wait),
                    "pressure_recharge": operation_state("pressure_recharge", compressor_flow_g_s, recharge_wait),
                    "vehicle_1": operation_state("vehicle_1", 1000.0 * previous_nozzle_flow,
                        "bank-unavailable" if dispatch_index is None else "valve-starting"),
                    "vehicle_2": operation_state("vehicle_2", 1000.0 * previous_nozzle_2_flow,
                        "bank-unavailable" if dispatch_2_index is None else "valve-starting"),
                }

            if virtual_safety is not None:
                virtual_safety.observe(time_s, recharge_bank=(
                    self.station.banks[recharge_index].parameters.name if recharge_index is not None else None),
                    dispatch_banks=(
                        self.station.banks[dispatch_index].parameters.name if dispatch_index is not None else None,
                        self.station.banks[dispatch_2_index].parameters.name if dispatch_2_index is not None else None),
                    compressor_flow_g_s=compressor_flow_g_s if process is not None else 0.0,
                    dispenser_flows_g_s=(previous_nozzle_flow * 1000.0, previous_nozzle_2_flow * 1000.0),
                    pcv_flows_g_s=(previous_pcv_flow * 1000.0, previous_pcv_2_flow * 1000.0),
                    pressure_sources_mpa={
                        "trailer.source": process_snapshot["trailer_pressure_mpa"],
                        "trailer.station": process_snapshot["trailer_pressure_mpa"],
                        "compressor.suction": process_snapshot["trailer_pressure_mpa"],
                        **{f"bank.{bank.parameters.name}.{side}": gas.pressure_pa / 1e6
                           for bank, gas in zip(self.station.banks, bank_gases)
                           for side in ("inlet", "outlet")},
                        "dispenser.1": hose_gas.pressure_pa / 1e6,
                        "dispenser.2": hose_2_gas.pressure_pa / 1e6,
                        **({"compressor.discharge": bank_gases[recharge_index].pressure_pa / 1e6}
                           if recharge_index is not None else {})})

            if sample_callback is not None:
                sample_callback(
                    SafeOperationSample(
                        time_s=time_s,
                        vehicle_pressure_pa=vehicle_gas.pressure_pa,
                        vehicle_temperature_k=vehicle_gas.temperature_k,
                        vehicle_density_kg_m3=vehicle_gas.density_kg_m3,
                        vehicle_2_pressure_pa=vehicle_2_gas.pressure_pa,
                        vehicle_2_temperature_k=vehicle_2_gas.temperature_k,
                        vehicle_2_density_kg_m3=vehicle_2_gas.density_kg_m3,
                        hose_pressure_pa=hose_gas.pressure_pa,
                        hose_temperature_k=hose_gas.temperature_k,
                        precooler_outlet_temperature_k=(
                            previous_precooler_temperature
                        ),
                        pcv_mass_flow_kg_s=(
                            previous_pcv_flow + previous_pcv_2_flow
                        ),
                        nozzle_mass_flow_kg_s=(
                            previous_nozzle_flow + previous_nozzle_2_flow
                        ),
                        pcv_1_mass_flow_kg_s=previous_pcv_flow,
                        pcv_2_mass_flow_kg_s=previous_pcv_2_flow,
                        nozzle_1_mass_flow_kg_s=previous_nozzle_flow,
                        nozzle_2_mass_flow_kg_s=previous_nozzle_2_flow,
                        total_leak_mass_flow_kg_s=sum(leak_rates.values()),
                        bank_pressure_pa={
                            bank.parameters.name: gas.pressure_pa
                            for bank, gas in zip(self.station.banks, bank_gases)
                        },
                        bank_temperature_k={
                            bank.parameters.name: gas.temperature_k
                            for bank, gas in zip(self.station.banks, bank_gases)
                        },
                        bank_mass_kg={
                            bank.parameters.name: state.hydrogen_mass_kg
                            for bank, state in zip(self.station.banks, current.banks)
                        },
                        dispatch_bank=(
                            self.station.banks[dispatch_index].parameters.name
                            if dispatch_index is not None else None
                        ),
                        dispatch_bank_2=(
                            self.station.banks[dispatch_2_index].parameters.name
                            if dispatch_2_index is not None else None
                        ),
                        recharge_bank=(
                            self.station.banks[recharge_index].parameters.name
                            if recharge_index is not None else None
                        ),
                        esd_latched=safety_command.esd_latched,
                        trip_causes=safety_command.trip_causes,
                        consequence_updated=any(
                            snapshot.consequence_updated
                            for snapshot in risk_snapshots
                        ),
                        hose_2_pressure_pa=hose_2_gas.pressure_pa,
                        hose_2_temperature_k=hose_2_gas.temperature_k,
                        hazop=hazop_frame,
                        active_faults=tuple(
                            f"{'relief-open' if event.event_id.startswith('relief-') else event.kind.value}:{event.target}"
                            for event in active_events
                        ),
                        process_operations=process_snapshot,
                        process_activity=process_activity,
                        vehicle_mass_kg=current.partial_station.vehicle.hydrogen_mass_kg,
                        vehicle_2_mass_kg=current.secondary_partial_station.vehicle.hydrogen_mass_kg,
                        virtual_safety=virtual_safety_snapshot,
                    )
                )

            if time_s >= end_time_s or (stop_callback is not None and stop_callback()):
                break
            # Clamp a nearly-complete controller period to the requested end
            # time.  Repeated floating-point additions can otherwise leave a
            # sub-nanosecond final interval.  LSODA rejects that degenerate
            # span, then the BDF fallback hides the issue behind a warning.
            # This is a time-grid correction only; no physical duration is
            # skipped because the residual is below numerical resolution for
            # the controller step.
            remaining_s = end_time_s - time_s
            time_tolerance_s = max(1.0e-9, control_period_s * 1.0e-9)
            end_s = (
                end_time_s
                if remaining_s <= control_period_s + time_tolerance_s
                else time_s + control_period_s
            )
            if process is not None and not process.any_requested() and not active_events and not cooling_events:
                # Idle monitoring keeps all process inventories exactly unchanged.
                # The controller scans at wall-clock pace until an operator request.
                if pace_idle:
                    sleep(min(control_period_s, 0.25))
                time_s = end_s
                if progress_callback is not None:
                    progress_callback(time_s, end_time_s)
                continue
            def rhs(local_time_s: float, vector: np.ndarray) -> np.ndarray:
                local_state = FullStationState.from_vector(
                    vector[:-1] if process is not None else vector, len(self.station.banks)
                )
                base_rate, compressor_result, _ = self.station.derivative(
                    local_time_s,
                    local_state,
                    effective_command,
                    dispatch_index,
                    recharge_index,
                    dispatch_opening,
                    override.precooler_capacity_multiplier,
                    secondary_command=effective_command_2,
                    secondary_dispatch_index=dispatch_2_index,
                    secondary_dispatch_valve_opening=dispatch_2_opening,
                    primary_pcv_area_multiplier=self._flow_multipliers(override, "dispenser")[0],
                    primary_nozzle_area_multiplier=(self._flow_multipliers(override, "dispenser")[1] *
                        (virtual_safety.opening("dispenser.1") if virtual_safety is not None else 1.0)) if requested_1 and not safety_command.esd_latched else 0.0,
                    secondary_pcv_area_multiplier=self._flow_multipliers(override, "dispenser_2")[0],
                    secondary_nozzle_area_multiplier=(self._flow_multipliers(override, "dispenser_2")[1] *
                        (virtual_safety.opening("dispenser.2") if virtual_safety is not None else 1.0)) if requested_2 and not safety_command.esd_latched else 0.0,
                    primary_allow_reverse_flow=self._allow_reverse_flow(override, "dispenser"),
                    secondary_allow_reverse_flow=self._allow_reverse_flow(override, "dispenser_2"),
                    compressor_flow_multiplier=compressor_flow_multiplier,
                )
                rates = self._apply_fault_effects(
                    self._apply_leak_sinks(
                    base_rate,
                    local_state,
                    override.active_leaks,
                    ),
                    local_state,
                    active_events + cooling_events,
                ).as_vector()
                return np.append(rates, compressor_result.mass_flow_kg_s) if process is not None else rates

            initial_vector = np.append(current.as_vector(), 0.0) if process is not None else current.as_vector()
            method = "LSODA" if process is not None and not active_events else "BDF"
            if method == "LSODA":
                with nonreentrant_integrator_lock:
                    solution = solve_ivp(rhs, (time_s, end_s), initial_vector, method=method,
                                         t_eval=[end_s], rtol=1.0e-6, atol=1.0e-8)
            else:
                solution = solve_ivp(rhs, (time_s, end_s), initial_vector, method=method,
                                     t_eval=[end_s], rtol=1.0e-6, atol=1.0e-8)
            if not solution.success and method == "LSODA":
                solution = solve_ivp(rhs, (time_s, end_s), initial_vector, method="BDF",
                                     t_eval=[end_s], rtol=1.0e-6, atol=1.0e-8)
            if not solution.success:
                raise RuntimeError(f"Safe-operation integration failed: {solution.message}")
            current = FullStationState.from_vector(
                solution.y[:-1, -1] if process is not None else solution.y[:, -1], len(self.station.banks)
            )
            if process is not None:
                process.account_compressor(float(solution.y[-1, -1]), 1.0)
            time_s = end_s
            if progress_callback is not None:
                progress_callback(time_s, end_time_s)

        self._continuous_esd_time_s = esd_time_s

        return SafeOperationTrajectory(
            time_s=np.asarray(times),
            states=np.vstack(states),
            vehicle_pressure_pa=np.asarray(vehicle_pressures),
            vehicle_temperature_k=np.asarray(vehicle_temperatures),
            vehicle_density_kg_m3=np.asarray(vehicle_densities),
            vehicle_2_pressure_pa=np.asarray(vehicle_2_pressures),
            vehicle_2_temperature_k=np.asarray(vehicle_2_temperatures),
            vehicle_2_density_kg_m3=np.asarray(vehicle_2_densities),
            pcv_mass_flow_kg_s=np.asarray(pcv_flows),
            nozzle_mass_flow_kg_s=np.asarray(nozzle_flows),
            pcv_1_mass_flow_kg_s=np.asarray(pcv_1_flows),
            pcv_2_mass_flow_kg_s=np.asarray(pcv_2_flows),
            nozzle_1_mass_flow_kg_s=np.asarray(nozzle_1_flows),
            nozzle_2_mass_flow_kg_s=np.asarray(nozzle_2_flows),
            leak_mass_flow_by_release={
                release_id: np.asarray(values)
                for release_id, values in leak_histories.items()
            },
            safety_commands=tuple(safety_history),
            fueling_commands=tuple(fueling_history),
            risk_snapshots=tuple(risk_history),
            dispatch_bank=tuple(dispatch_history),
            dispatch_bank_2=tuple(dispatch_2_history),
            recharge_bank=tuple(recharge_history),
            esd_time_s=esd_time_s,
            final_state=current,
        )

    def _active_leak_inputs(
        self,
        events: tuple[FaultEvent, ...],
        state: FullStationState,
    ) -> tuple[tuple[FaultEvent, LeakScenario, LeakSourceState, float], ...]:
        active: list[tuple[FaultEvent, LeakScenario, LeakSourceState, float]] = []
        for event in events:
            scenario = self.leak_scenarios.get(event.event_id)
            if scenario is None:
                scenario = LeakScenario(
                    release_id=event.event_id,
                    component_id=event.target,
                    location=event.target,
                    start_time_s=event.start_time_s,
                    orifice_diameter_m=float(event.leak_diameter_m),
                    indoor=event.indoor,
                    release_angle_rad=(np.pi / 2 if event.event_id.startswith("vent-") else 0.0),
                    release_height_m=(6.0 if event.event_id.startswith("vent-") else 1.0),
                )
            source, enthalpy = self._resolve_leak_source(event.target, state)
            active.append((event, scenario, source, enthalpy))
        return tuple(active)

    @staticmethod
    def _forced_pcv_opening(
        override: OperationalOverride, prefix: str,
    ) -> float | None:
        per_dispenser = override.forced_pcv_opening_by_dispenser
        if per_dispenser:
            return per_dispenser.get(prefix, override.forced_pcv_opening)
        return override.forced_pcv_opening

    @staticmethod
    def _flow_multipliers(override: OperationalOverride, prefix: str) -> tuple[float, float]:
        restrictions = override.pipe_restrictions
        pcv = min(
            restrictions.get(prefix, 1.0),
            restrictions.get(f"{prefix}.pcv", 1.0),
            restrictions.get("pcv", 1.0),
        )
        nozzle_target = f"{prefix}.hose"
        nozzle = min(restrictions.get(nozzle_target, 1.0), restrictions.get("nozzle", 1.0))
        return pcv, nozzle

    @staticmethod
    def _allow_reverse_flow(override: OperationalOverride, prefix: str) -> bool:
        return prefix in override.check_valve_failures or f"{prefix}.hose" in override.check_valve_failures or "check-valve" in override.check_valve_failures

    def _apply_fault_effects(
        self,
        base_rate: FullStationState,
        state: FullStationState,
        events: tuple[FaultEvent, ...],
    ) -> FullStationState:
        """Add physical disturbances to the ODE state, preserving mass/energy paths."""
        bank_rates = list(base_rate.banks)
        partial_rate = base_rate.partial_station
        secondary_rate = base_rate.secondary_partial_station
        for event in events:
            if event.kind is FaultKind.PRESSURE_DISTURBANCE:
                bank_rates, partial_rate, secondary_rate = self._apply_pressure_disturbance(
                    event, state, bank_rates, partial_rate, secondary_rate
                )
            elif event.kind in (FaultKind.EXTERNAL_FIRE, FaultKind.TEMPERATURE_DISTURBANCE):
                bank_rates, partial_rate, secondary_rate = self._apply_heat_transfer(
                    event, state, bank_rates, partial_rate, secondary_rate
                )
        return FullStationState(tuple(bank_rates), partial_rate, secondary_rate)

    def _apply_pressure_disturbance(self, event, state, bank_rates, partial_rate, secondary_rate):
        target = event.target
        gas = self._gas_for_target(target, state)
        if gas is None:
            return bank_rates, partial_rate, secondary_rate
        # A pressure disturbance is a controlled mass source/sink. The EOS then
        # determines pressure and temperature, so the process responds naturally.
        desired = gas.pressure_pa + event.magnitude * 1.0e6
        mass = self._mass_for_target(target, state)
        mass_rate = np.clip(
            mass * (desired - gas.pressure_pa) / max(abs(gas.pressure_pa), 1.0e5) / event.rate_s,
            -mass / event.rate_s,
            10.0,
        )
        return self._add_mass_energy(target, mass_rate, gas.specific_enthalpy_j_kg, bank_rates, partial_rate, secondary_rate)

    @staticmethod
    def _add_mass_energy(target, mass_rate, enthalpy, bank_rates, partial_rate, secondary_rate):
        energy_rate = mass_rate * enthalpy
        if target.startswith("cascade.") or target in ("compressor", "header"):
            index = ({"low": 0, "medium": 1, "high": 2}.get(target.split(".", 1)[1]) if target.startswith("cascade.") else 2)
            if index is not None:
                bank_rates[index] = replace(bank_rates[index], hydrogen_mass_kg=bank_rates[index].hydrogen_mass_kg + mass_rate, hydrogen_internal_energy_j=bank_rates[index].hydrogen_internal_energy_j + energy_rate)
        elif target == "dispenser.hose":
            partial_rate = replace(partial_rate, hose_hydrogen_mass_kg=partial_rate.hose_hydrogen_mass_kg + mass_rate, hose_hydrogen_internal_energy_j=partial_rate.hose_hydrogen_internal_energy_j + energy_rate)
        elif target == "dispenser_2.hose" and secondary_rate is not None:
            secondary_rate = replace(secondary_rate, hose_hydrogen_mass_kg=secondary_rate.hose_hydrogen_mass_kg + mass_rate, hose_hydrogen_internal_energy_j=secondary_rate.hose_hydrogen_internal_energy_j + energy_rate)
        elif target in ("vehicle.tank", "vehicle_2.tank"):
            selected = partial_rate if target == "vehicle.tank" else secondary_rate
            if selected is not None:
                vehicle = replace(selected.vehicle, hydrogen_mass_kg=selected.vehicle.hydrogen_mass_kg + mass_rate, hydrogen_internal_energy_j=selected.vehicle.hydrogen_internal_energy_j + energy_rate)
                if target == "vehicle.tank": partial_rate = replace(selected, vehicle=vehicle)
                else: secondary_rate = replace(selected, vehicle=vehicle)
        return bank_rates, partial_rate, secondary_rate

    def _apply_heat_transfer(self, event, state, bank_rates, partial_rate, secondary_rate):
        source_temperature = event.external_temperature_k or 298.15
        ua = event.heat_transfer_ua_w_k or 500.0
        target = event.target
        if target.startswith("cascade.") or target in ("compressor", "header"):
            index = ({"low": 0, "medium": 1, "high": 2}.get(target.split(".", 1)[1]) if target.startswith("cascade.") else 2)
            if index is not None:
                bank = self.station.banks[index]; current = state.banks[index]
                heat = ua * (source_temperature - current.wall_temperature_k)
                capacity = bank.parameters.wall_mass_kg * bank.parameters.wall_specific_heat_j_kg_k * bank.fit.wall_heat_capacity_multiplier
                bank_rates[index] = replace(bank_rates[index], wall_temperature_k=bank_rates[index].wall_temperature_k + heat / capacity)
        elif target in ("vehicle.tank", "vehicle_2.tank"):
            selected_state = state.partial_station if target == "vehicle.tank" else state.secondary_partial_station
            selected_rate = partial_rate if target == "vehicle.tank" else secondary_rate
            model = self.station.partial_station if target == "vehicle.tank" else self.station.secondary_partial_station
            if selected_state is not None and selected_rate is not None and model is not None:
                heat = ua * (source_temperature - selected_state.vehicle.shell_temperature_k)
                p = model.vehicle_tank.parameters; f = model.vehicle_tank.fit
                capacity = p.shell_mass_kg * p.shell_specific_heat_j_kg_k * f.shell_heat_capacity_multiplier
                vehicle = replace(selected_rate.vehicle, shell_temperature_k=selected_rate.vehicle.shell_temperature_k + heat / capacity)
                if target == "vehicle.tank": partial_rate = replace(selected_rate, vehicle=vehicle)
                else: secondary_rate = replace(selected_rate, vehicle=vehicle)
        elif target in ("dispenser.hose", "dispenser_2.hose"):
            selected_state = state.partial_station if target == "dispenser.hose" else state.secondary_partial_station
            selected_rate = partial_rate if target == "dispenser.hose" else secondary_rate
            model = self.station.partial_station if target == "dispenser.hose" else self.station.secondary_partial_station
            if selected_state is not None and selected_rate is not None and model is not None:
                heat = ua * (source_temperature - selected_state.hose_wall_temperature_k)
                capacity = model.hose.wall_thermal_capacity_j_k * model.fit.hose_wall_capacity_multiplier
                updated = replace(selected_rate, hose_wall_temperature_k=selected_rate.hose_wall_temperature_k + heat / capacity)
                if target == "dispenser.hose": partial_rate = updated
                else: secondary_rate = updated
        return bank_rates, partial_rate, secondary_rate

    def _gas_for_target(self, target, state):
        if target.startswith("cascade.") or target in ("compressor", "header"):
            index = ({"low": 0, "medium": 1, "high": 2}.get(target.split(".", 1)[1]) if target.startswith("cascade.") else 2)
            return self.station.banks[index].gas_state(state.banks[index]) if index is not None else None
        if target == "dispenser.hose": return self.station.partial_station.hose_gas_state(state.partial_station)
        if target == "dispenser_2.hose" and state.secondary_partial_station is not None and self.station.secondary_partial_station is not None: return self.station.secondary_partial_station.hose_gas_state(state.secondary_partial_station)
        if target == "vehicle.tank": return self.station.partial_station.vehicle_tank.gas_state(state.partial_station.vehicle)
        if target == "vehicle_2.tank" and state.secondary_partial_station is not None and self.station.secondary_partial_station is not None: return self.station.secondary_partial_station.vehicle_tank.gas_state(state.secondary_partial_station.vehicle)
        return None

    def _mass_for_target(self, target, state):
        if target.startswith("cascade.") or target in ("compressor", "header"):
            index = ({"low": 0, "medium": 1, "high": 2}.get(target.split(".", 1)[1]) if target.startswith("cascade.") else 2); return state.banks[index].hydrogen_mass_kg if index is not None else 0.0
        if target == "dispenser.hose": return state.partial_station.hose_hydrogen_mass_kg
        if target == "dispenser_2.hose" and state.secondary_partial_station is not None: return state.secondary_partial_station.hose_hydrogen_mass_kg
        if target == "vehicle.tank": return state.partial_station.vehicle.hydrogen_mass_kg
        if target == "vehicle_2.tank" and state.secondary_partial_station is not None: return state.secondary_partial_station.vehicle.hydrogen_mass_kg
        return 0.0

    def _resolve_leak_source(
        self,
        target: str,
        state: FullStationState,
    ) -> tuple[LeakSourceState, float]:
        if target == "dispenser.hose":
            gas = self.station.partial_station.hose_gas_state(state.partial_station)
        elif target == "dispenser_2.hose":
            if self.station.secondary_partial_station is None or state.secondary_partial_station is None:
                raise ValueError("Secondary dispenser state is unavailable")
            gas = self.station.secondary_partial_station.hose_gas_state(
                state.secondary_partial_station
            )
        elif target == "vehicle.tank":
            gas = self.station.partial_station.vehicle_tank.gas_state(
                state.partial_station.vehicle
            )
        elif target == "vehicle_2.tank":
            if self.station.secondary_partial_station is None or state.secondary_partial_station is None:
                raise ValueError("Secondary vehicle state is unavailable")
            gas = self.station.secondary_partial_station.vehicle_tank.gas_state(
                state.secondary_partial_station.vehicle
            )
        elif target.startswith("cascade."):
            bank_name = target.split(".", 1)[1]
            matches = [
                index
                for index, bank in enumerate(self.station.banks)
                if bank.parameters.name == bank_name
            ]
            if not matches:
                raise ValueError(f"Unknown leak target: {target}")
            index = matches[0]
            gas = self.station.banks[index].gas_state(state.banks[index])
        elif target in ("compressor", "header"):
            # The current full-station model has no separate compressor/header
            # inventory. Use the connected high-bank volume as an explicit
            # conservative proxy and retain the original component_id in risk output.
            index = next((i for i, bank in enumerate(self.station.banks) if bank.parameters.name == "high"), len(self.station.banks)-1)
            gas = self.station.banks[index].gas_state(state.banks[index])
        else:
            raise ValueError(f"Unsupported leak target: {target}")
        return (
            LeakSourceState(gas.pressure_pa, gas.temperature_k),
            gas.specific_enthalpy_j_kg,
        )

    def _apply_leak_sinks(
        self,
        base_rate: FullStationState,
        state: FullStationState,
        events: tuple[FaultEvent, ...],
    ) -> FullStationState:
        bank_rates = list(base_rate.banks)
        partial_rate = base_rate.partial_station
        secondary_rate = base_rate.secondary_partial_station
        for event, scenario, source, enthalpy in self._active_leak_inputs(events, state):
            mass_flow = self.risk_monitor.leak_model.mass_flow_kg_s(scenario, source)
            # Do not allow an adaptive ODE trial step to remove more inventory
            # than the source can physically provide. The rate limiter preserves
            # a finite depletion trajectory for large emergency openings.
            available_mass = self._mass_for_target(event.target, state)
            mass_flow = min(mass_flow, max(available_mass, 0.0) / max(event.rate_s, 1.0e-3))
            if event.target == "dispenser.hose":
                partial_rate = replace(
                    partial_rate,
                    hose_hydrogen_mass_kg=(
                        partial_rate.hose_hydrogen_mass_kg - mass_flow
                    ),
                    hose_hydrogen_internal_energy_j=(
                        partial_rate.hose_hydrogen_internal_energy_j
                        - mass_flow * enthalpy
                    ),
                )
            elif event.target == "dispenser_2.hose":
                if secondary_rate is None:
                    raise ValueError("Secondary dispenser rate is unavailable")
                secondary_rate = replace(
                    secondary_rate,
                    hose_hydrogen_mass_kg=(
                        secondary_rate.hose_hydrogen_mass_kg - mass_flow
                    ),
                    hose_hydrogen_internal_energy_j=(
                        secondary_rate.hose_hydrogen_internal_energy_j
                        - mass_flow * enthalpy
                    ),
                )
            elif event.target == "vehicle.tank":
                vehicle_rate = replace(
                    partial_rate.vehicle,
                    hydrogen_mass_kg=(
                        partial_rate.vehicle.hydrogen_mass_kg - mass_flow
                    ),
                    hydrogen_internal_energy_j=(
                        partial_rate.vehicle.hydrogen_internal_energy_j
                        - mass_flow * enthalpy
                    ),
                )
                partial_rate = replace(partial_rate, vehicle=vehicle_rate)
            elif event.target == "vehicle_2.tank":
                if secondary_rate is None:
                    raise ValueError("Secondary vehicle rate is unavailable")
                vehicle_rate = replace(
                    secondary_rate.vehicle,
                    hydrogen_mass_kg=(
                        secondary_rate.vehicle.hydrogen_mass_kg - mass_flow
                    ),
                    hydrogen_internal_energy_j=(
                        secondary_rate.vehicle.hydrogen_internal_energy_j
                        - mass_flow * enthalpy
                    ),
                )
                secondary_rate = replace(secondary_rate, vehicle=vehicle_rate)
            else:
                bank_name = event.target.split(".", 1)[1] if event.target.startswith("cascade.") else "high"
                index = next((index for index, bank in enumerate(self.station.banks) if bank.parameters.name == bank_name), len(self.station.banks)-1)
                bank_rates[index] = replace(
                    bank_rates[index],
                    hydrogen_mass_kg=(
                        bank_rates[index].hydrogen_mass_kg - mass_flow
                    ),
                    hydrogen_internal_energy_j=(
                        bank_rates[index].hydrogen_internal_energy_j
                        - mass_flow * enthalpy
                    ),
                )
        return FullStationState(tuple(bank_rates), partial_rate, secondary_rate)

    @staticmethod
    def _default_concentration_extractor(
        snapshots: tuple[DynamicRiskSnapshot, ...],
    ) -> Mapping[str, float]:
        concentrations: dict[str, float] = {}
        for snapshot in snapshots:
            detector_values = snapshot.consequence.get("detector_concentrations")
            if isinstance(detector_values, Mapping):
                concentrations.update(
                    {
                        str(name): float(value)
                        for name, value in detector_values.items()
                        if isinstance(value, (int, float))
                    }
                )
            maximum = snapshot.consequence.get("maximum_concentration")
            if isinstance(maximum, (int, float)):
                concentrations[f"virtual:{snapshot.release_id}"] = float(maximum)
        return concentrations
