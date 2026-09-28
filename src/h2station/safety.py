"""Sampled safety-instrumented supervision for the continuous station model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import exp
from typing import Callable, Mapping

import numpy as np

from .components import TankInventory
from .network import CommandProvider, NetworkCommands, StationNetwork
from .thermo import ThermoState


class SensorVariable(str, Enum):
    PRESSURE = "pressure"
    TEMPERATURE = "temperature"


class SensorFaultMode(str, Enum):
    NORMAL = "normal"
    FROZEN = "frozen"
    FAILED_LOW = "failed_low"
    FAILED_HIGH = "failed_high"


class HyRAMFailureMode(str, Enum):
    NOZZLE_POP_OFF = "Nozzle: Pop-off"
    NOZZLE_FAILURE_TO_CLOSE = "Nozzle: Failure to close"
    MANUAL_VALVE_FAILURE_TO_CLOSE = "Manual valve: Failure to close"
    SOLENOID_FAILURE_TO_CLOSE = "Solenoid valves: Failure to close"
    SOLENOID_COMMON_CAUSE = "Solenoid valves: Common-cause failure"
    RELIEF_FAILURE_TO_OPEN = "Pressure-relief valve: Failure to open"
    BREAKAWAY_FAILURE_TO_CLOSE = "Breakaway coupling: Failure to close"
    FUELING_OVERPRESSURE = "Accident: Overpressure during fueling"
    DRIVEOFF = "Accident: Driveoff"


@dataclass(frozen=True, slots=True)
class SensorParameters:
    name: str
    tank: str
    variable: SensorVariable
    time_constant: float
    minimum_indication: float
    maximum_indication: float
    bias: float = 0.0
    response_time_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if self.time_constant <= 0.0 or self.response_time_multiplier <= 0.0:
            raise ValueError("Sensor response time must be positive")
        if self.maximum_indication <= self.minimum_indication:
            raise ValueError("Sensor indication range is invalid")


@dataclass(slots=True)
class SensorRuntime:
    indication: float | None = None


class DynamicSensor:
    """First-order deterministic transmitter model with injectable faults."""

    def __init__(self, parameters: SensorParameters) -> None:
        self.parameters = parameters
        self.runtime = SensorRuntime()

    def true_value(self, states: Mapping[str, ThermoState]) -> float:
        state = states[self.parameters.tank]
        return float(getattr(state, self.parameters.variable.value))

    def step(
        self,
        states: Mapping[str, ThermoState],
        elapsed_time: float,
        fault: SensorFaultMode = SensorFaultMode.NORMAL,
    ) -> float:
        p = self.parameters
        if fault is SensorFaultMode.FAILED_LOW:
            self.runtime.indication = p.minimum_indication
            return p.minimum_indication
        if fault is SensorFaultMode.FAILED_HIGH:
            self.runtime.indication = p.maximum_indication
            return p.maximum_indication
        if fault is SensorFaultMode.FROZEN and self.runtime.indication is not None:
            return self.runtime.indication

        target = min(
            max(self.true_value(states) + p.bias, p.minimum_indication),
            p.maximum_indication,
        )
        if self.runtime.indication is None or elapsed_time <= 0.0:
            self.runtime.indication = target
        else:
            time_constant = p.time_constant * p.response_time_multiplier
            fraction = 1.0 - exp(-elapsed_time / time_constant)
            self.runtime.indication += fraction * (target - self.runtime.indication)
        return self.runtime.indication


@dataclass(frozen=True, slots=True)
class TripRule:
    name: str
    sensor: str
    trip_threshold: float
    reset_threshold: float
    delay: float = 0.0
    trip_above: bool = True
    latching: bool = True

    def __post_init__(self) -> None:
        if self.delay < 0.0:
            raise ValueError("Trip delay cannot be negative")
        if self.trip_above and self.reset_threshold >= self.trip_threshold:
            raise ValueError("High-trip reset threshold must be below trip threshold")
        if not self.trip_above and self.reset_threshold <= self.trip_threshold:
            raise ValueError("Low-trip reset threshold must be above trip threshold")


@dataclass(slots=True)
class TripRuntime:
    elapsed_in_trip_condition: float = 0.0
    active: bool = False


@dataclass(frozen=True, slots=True)
class FlowTripRule:
    name: str
    connection: str
    maximum_mass_flow: float
    delay: float = 0.0
    latching: bool = True


@dataclass(frozen=True, slots=True)
class SafetyActions:
    stop_compressors: tuple[str, ...] = ()
    deenergize_actuators: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FaultInjection:
    sensor_faults: Mapping[str, SensorFaultMode] = field(default_factory=dict)
    stuck_actuators: tuple[str, ...] = ()
    failed_relief_valves: tuple[str, ...] = ()
    external_trip_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SafetyDecision:
    tripped: bool
    causes: tuple[str, ...]
    actions: SafetyActions

    def apply(
        self,
        base: NetworkCommands,
        faults: FaultInjection = FaultInjection(),
    ) -> NetworkCommands:
        restrictions = dict(base.restriction_openings)
        compressors = dict(base.compressor_speeds)
        available = dict(base.actuator_available)
        stuck = dict(base.actuator_stuck)
        relief_available = dict(base.relief_available)
        for name in faults.stuck_actuators:
            stuck[name] = True
        for name in faults.failed_relief_valves:
            relief_available[name] = False
        if self.tripped:
            for name in self.actions.stop_compressors:
                compressors[name] = 0.0
            for name in self.actions.deenergize_actuators:
                available[name] = False
        return NetworkCommands(
            restriction_openings=restrictions,
            compressor_speeds=compressors,
            actuator_available=available,
            actuator_stuck=stuck,
            relief_available=relief_available,
        )


@dataclass(frozen=True, slots=True)
class SafetyEvent:
    time: float
    name: str
    active: bool


class SafetySupervisor:
    """Fixed-period alarm/trip logic kept outside adaptive ODE evaluations."""

    def __init__(
        self,
        sensors: tuple[DynamicSensor, ...],
        trip_rules: tuple[TripRule, ...],
        flow_trip_rules: tuple[FlowTripRule, ...],
        actions: SafetyActions,
    ) -> None:
        self.sensors = {sensor.parameters.name: sensor for sensor in sensors}
        self.trip_rules = trip_rules
        self.flow_trip_rules = flow_trip_rules
        self.actions = actions
        self.trip_runtime = {
            rule.name: TripRuntime() for rule in (*trip_rules, *flow_trip_rules)
        }
        for rule in trip_rules:
            if rule.sensor not in self.sensors:
                raise ValueError(f"Trip {rule.name} references an unknown sensor")

    def reset_latches(self) -> None:
        for runtime in self.trip_runtime.values():
            runtime.active = False
            runtime.elapsed_in_trip_condition = 0.0

    def step(
        self,
        time: float,
        elapsed_time: float,
        states: Mapping[str, ThermoState],
        mass_flows: Mapping[str, float],
        faults: FaultInjection = FaultInjection(),
        operator_estop: bool = False,
    ) -> tuple[SafetyDecision, dict[str, float], tuple[SafetyEvent, ...]]:
        readings = {
            name: sensor.step(
                states,
                elapsed_time,
                faults.sensor_faults.get(name, SensorFaultMode.NORMAL),
            )
            for name, sensor in self.sensors.items()
        }
        events: list[SafetyEvent] = []
        for rule in self.trip_rules:
            reading = readings[rule.sensor]
            condition = reading >= rule.trip_threshold if rule.trip_above else reading <= rule.trip_threshold
            reset_condition = reading <= rule.reset_threshold if rule.trip_above else reading >= rule.reset_threshold
            self._advance_rule(time, elapsed_time, rule.name, condition, reset_condition, rule.delay, rule.latching, events)
        for rule in self.flow_trip_rules:
            condition = mass_flows.get(rule.connection, 0.0) >= rule.maximum_mass_flow
            self._advance_rule(time, elapsed_time, rule.name, condition, not condition, rule.delay, rule.latching, events)
        causes = [name for name, runtime in self.trip_runtime.items() if runtime.active]
        causes.extend(faults.external_trip_reasons)
        if operator_estop:
            causes.append("operator_estop")
        return SafetyDecision(bool(causes), tuple(dict.fromkeys(causes)), self.actions), readings, tuple(events)

    def _advance_rule(
        self,
        time: float,
        elapsed_time: float,
        name: str,
        condition: bool,
        reset_condition: bool,
        delay: float,
        latching: bool,
        events: list[SafetyEvent],
    ) -> None:
        runtime = self.trip_runtime[name]
        previous = runtime.active
        if condition:
            runtime.elapsed_in_trip_condition += elapsed_time
            if runtime.elapsed_in_trip_condition >= delay:
                runtime.active = True
        else:
            runtime.elapsed_in_trip_condition = 0.0
            if not latching and reset_condition:
                runtime.active = False
        if runtime.active != previous:
            events.append(SafetyEvent(time, name, runtime.active))


@dataclass(frozen=True, slots=True)
class SafetySimulationResult:
    time: np.ndarray
    inventories: Mapping[str, tuple[np.ndarray, np.ndarray, np.ndarray]]
    actuator_positions: Mapping[str, np.ndarray]
    sensor_readings: Mapping[str, np.ndarray]
    trip_active: np.ndarray
    events: tuple[SafetyEvent, ...]


FaultProvider = Callable[[float], FaultInjection]
EmergencyStopProvider = Callable[[float], bool]


class SafetyCoSimulator:
    """Advances process dynamics between deterministic safety-system scans."""

    def __init__(
        self,
        station: StationNetwork,
        supervisor: SafetySupervisor,
        base_command_provider: CommandProvider,
        ambient_temperature: float,
        scan_period: float = 0.1,
    ) -> None:
        if scan_period <= 0.0:
            raise ValueError("Safety scan period must be positive")
        self.station = station
        self.supervisor = supervisor
        self.base_command_provider = base_command_provider
        self.ambient_temperature = ambient_temperature
        self.scan_period = scan_period

    def run(
        self,
        initial: Mapping[str, TankInventory],
        time_span: tuple[float, float],
        initial_actuator_positions: Mapping[str, float] | None = None,
        fault_provider: FaultProvider | None = None,
        emergency_stop_provider: EmergencyStopProvider | None = None,
    ) -> SafetySimulationResult:
        start, finish = time_span
        if finish <= start:
            raise ValueError("Safety simulation finish time must exceed start time")
        fault_provider = fault_provider or (lambda _time: FaultInjection())
        emergency_stop_provider = emergency_stop_provider or (lambda _time: False)
        current_inventory = dict(initial)
        current_actuators = dict(initial_actuator_positions or {})
        times = [start]
        inventory_history = {name: [[value.mass], [value.internal_energy], [value.wall_temperature]] for name, value in current_inventory.items()}
        actuator_history: dict[str, list[float]] = {}
        sensor_history = {name: [] for name in self.supervisor.sensors}
        trip_history = [False]
        events: list[SafetyEvent] = []
        states = self.station.thermodynamic_states(current_inventory)
        decision, readings, initial_events = self.supervisor.step(start, 0.0, states, {}, fault_provider(start), emergency_stop_provider(start))
        events.extend(initial_events)
        for name, value in readings.items():
            sensor_history[name].append(value)

        time = start
        while time < finish:
            next_time = min(time + self.scan_period, finish)
            elapsed = next_time - time
            faults = fault_provider(time)

            def safe_commands(evaluation_time: float, evaluation_states: Mapping[str, ThermoState]) -> NetworkCommands:
                return decision.apply(self.base_command_provider(evaluation_time, evaluation_states), faults)

            segment = self.station.simulate(
                current_inventory,
                (time, next_time),
                safe_commands,
                self.ambient_temperature,
                evaluation_times=np.asarray([next_time]),
                maximum_step=elapsed,
                initial_actuator_positions=current_actuators,
            )
            if not segment.solver_success:
                raise RuntimeError(segment.solver_message)
            current_inventory = {
                name: TankInventory(float(series[0][-1]), float(series[1][-1]), float(series[2][-1]))
                for name, series in segment.inventories.items()
            }
            current_actuators = {name: float(values[-1]) for name, values in segment.actuator_positions.items()}
            states = self.station.thermodynamic_states(current_inventory)
            applied_commands = safe_commands(next_time, states)
            _, connection_flows = self.station.evaluate(current_inventory, applied_commands, self.ambient_temperature, actual_openings=current_actuators)
            mass_flows = {flow.name: flow.mass_flow for flow in connection_flows}
            decision, readings, new_events = self.supervisor.step(next_time, elapsed, states, mass_flows, fault_provider(next_time), emergency_stop_provider(next_time))
            events.extend(new_events)
            time = next_time
            times.append(time)
            trip_history.append(decision.tripped)
            for name, inventory in current_inventory.items():
                history = inventory_history[name]
                history[0].append(inventory.mass)
                history[1].append(inventory.internal_energy)
                history[2].append(inventory.wall_temperature)
            for name, value in current_actuators.items():
                actuator_history.setdefault(name, [value] * (len(times) - 1)).append(value)
            for name, value in readings.items():
                sensor_history[name].append(value)

        return SafetySimulationResult(
            time=np.asarray(times),
            inventories={name: tuple(np.asarray(values) for values in history) for name, history in inventory_history.items()},
            actuator_positions={name: np.asarray(values) for name, values in actuator_history.items()},
            sensor_readings={name: np.asarray(values) for name, values in sensor_history.items()},
            trip_active=np.asarray(trip_history, dtype=bool),
            events=tuple(events),
        )
