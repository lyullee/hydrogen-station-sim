"""Network assembly and dynamic integration for station components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping

import numpy as np
from scipy.integrate import solve_ivp

from .components import (
    FiniteUAPrecooler,
    LumpedTank,
    MultistageCompressor,
    PressureReliefValve,
    RealGasRestriction,
    TankBoundaryFlows,
    TankDerivative,
    TankInventory,
    ValveActuator,
)
from .thermo import ThermoState


@dataclass(frozen=True, slots=True)
class RestrictionConnection:
    name: str
    source: str
    target: str
    restriction: RealGasRestriction
    precooler: FiniteUAPrecooler | None = None
    allow_reverse: bool = False
    default_opening: float = 0.0
    actuator: ValveActuator | None = None


@dataclass(frozen=True, slots=True)
class CompressorConnection:
    name: str
    source: str
    target: str
    compressor: MultistageCompressor


@dataclass(frozen=True, slots=True)
class VentConnection:
    name: str
    source: str
    relief_valve: PressureReliefValve
    back_pressure: float = 101_325.0


@dataclass(frozen=True, slots=True)
class NetworkCommands:
    restriction_openings: Mapping[str, float] = field(default_factory=dict)
    compressor_speeds: Mapping[str, float] = field(default_factory=dict)
    actuator_available: Mapping[str, bool] = field(default_factory=dict)
    actuator_stuck: Mapping[str, bool] = field(default_factory=dict)
    relief_available: Mapping[str, bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConnectionFlow:
    name: str
    source: str
    target: str
    mass_flow: float
    stream_enthalpy: float
    shaft_power: float = 0.0
    choked: bool = False
    pressure_limited: bool = False


@dataclass(frozen=True, slots=True)
class SimulationResult:
    time: np.ndarray
    inventories: Mapping[str, tuple[np.ndarray, np.ndarray, np.ndarray]]
    actuator_positions: Mapping[str, np.ndarray]
    solver_success: bool
    solver_message: str


CommandProvider = Callable[[float, Mapping[str, ThermoState]], NetworkCommands]


class StationNetwork:
    """Connects tank control volumes with restrictions and compressors."""

    def __init__(
        self,
        tanks: Mapping[str, LumpedTank],
        restrictions: tuple[RestrictionConnection, ...] = (),
        compressors: tuple[CompressorConnection, ...] = (),
        vents: tuple[VentConnection, ...] = (),
    ) -> None:
        if not tanks:
            raise ValueError("A station network needs at least one tank")
        self.tanks = dict(tanks)
        self.tank_names = tuple(self.tanks)
        self.restrictions = restrictions
        self.compressors = compressors
        self.vents = vents
        self._validate_connections()

    def _validate_connections(self) -> None:
        names: set[str] = set()
        for connection in (*self.restrictions, *self.compressors):
            if connection.name in names:
                raise ValueError(f"Duplicate connection name: {connection.name}")
            names.add(connection.name)
            if connection.source not in self.tanks or connection.target not in self.tanks:
                raise ValueError(f"Unknown tank in connection {connection.name}")
        for connection in self.vents:
            if connection.name in names:
                raise ValueError(f"Duplicate connection name: {connection.name}")
            names.add(connection.name)
            if connection.source not in self.tanks:
                raise ValueError(f"Unknown vent source in connection {connection.name}")

    def pack(self, inventories: Mapping[str, TankInventory]) -> np.ndarray:
        values: list[float] = []
        for name in self.tank_names:
            inventory = inventories[name]
            values.extend(
                (
                    inventory.mass,
                    inventory.internal_energy,
                    inventory.wall_temperature,
                )
            )
        return np.asarray(values, dtype=float)

    def unpack(self, values: np.ndarray) -> dict[str, TankInventory]:
        return {
            name: TankInventory(
                mass=float(values[index]),
                internal_energy=float(values[index + 1]),
                wall_temperature=float(values[index + 2]),
            )
            for name, index in zip(self.tank_names, range(0, len(values), 3))
        }

    def thermodynamic_states(
        self, inventories: Mapping[str, TankInventory]
    ) -> dict[str, ThermoState]:
        return {
            name: self.tanks[name].fluid_state(inventory)
            for name, inventory in inventories.items()
        }

    @staticmethod
    def _add_transfer(
        ledgers: Mapping[str, TankBoundaryFlows],
        source: str,
        target: str,
        mass_flow: float,
        stream_enthalpy: float,
    ) -> None:
        ledgers[source].mass_out += mass_flow
        ledgers[target].mass_in += mass_flow
        ledgers[target].enthalpy_in_rate += mass_flow * stream_enthalpy

    def evaluate(
        self,
        inventories: Mapping[str, TankInventory],
        commands: NetworkCommands,
        ambient_temperature: float,
        actual_openings: Mapping[str, float] | None = None,
    ) -> tuple[dict[str, TankDerivative], tuple[ConnectionFlow, ...]]:
        states = self.thermodynamic_states(inventories)
        ledgers = {name: TankBoundaryFlows() for name in self.tank_names}
        connection_flows: list[ConnectionFlow] = []
        actual_openings = {} if actual_openings is None else actual_openings

        for connection in self.restrictions:
            demanded_opening = commands.restriction_openings.get(
                connection.name, connection.default_opening
            )
            opening = actual_openings.get(connection.name, demanded_opening)
            source = connection.source
            target = connection.target
            source_state = states[source]
            target_state = states[target]

            if source_state.pressure <= target_state.pressure:
                if not connection.allow_reverse:
                    continue
                source, target = target, source
                source_state, target_state = target_state, source_state

            result = connection.restriction.mass_flow(
                source_state, target_state.pressure, opening
            )
            if result.mass_flow <= 0.0:
                continue

            stream = connection.restriction.eos.state_ph(
                target_state.pressure, source_state.enthalpy
            )
            if connection.precooler is not None:
                stream = connection.precooler.outlet(
                    stream, result.mass_flow, target_state.pressure
                )
            self._add_transfer(
                ledgers, source, target, result.mass_flow, stream.enthalpy
            )
            connection_flows.append(
                ConnectionFlow(
                    name=connection.name,
                    source=source,
                    target=target,
                    mass_flow=result.mass_flow,
                    stream_enthalpy=stream.enthalpy,
                    choked=result.choked,
                )
            )

        for connection in self.compressors:
            speed = commands.compressor_speeds.get(connection.name, 0.0)
            source_state = states[connection.source]
            target_state = states[connection.target]
            result = connection.compressor.evaluate(
                source_state,
                target_state.pressure,
                speed,
                ambient_temperature,
            )
            if result.mass_flow > 0.0:
                self._add_transfer(
                    ledgers,
                    connection.source,
                    connection.target,
                    result.mass_flow,
                    result.outlet.enthalpy,
                )
            connection_flows.append(
                ConnectionFlow(
                    name=connection.name,
                    source=connection.source,
                    target=connection.target,
                    mass_flow=result.mass_flow,
                    stream_enthalpy=result.outlet.enthalpy,
                    shaft_power=result.shaft_power,
                    pressure_limited=result.pressure_limited,
                )
            )

        for connection in self.vents:
            source_state = states[connection.source]
            available = commands.relief_available.get(connection.name, True)
            result = connection.relief_valve.mass_flow(
                source_state, connection.back_pressure, available
            )
            if result.mass_flow > 0.0:
                ledgers[connection.source].mass_out += result.mass_flow
            connection_flows.append(
                ConnectionFlow(
                    name=connection.name,
                    source=connection.source,
                    target="ambient",
                    mass_flow=result.mass_flow,
                    stream_enthalpy=source_state.enthalpy,
                    choked=result.choked,
                )
            )

        derivatives = {
            name: self.tanks[name].derivatives(
                inventories[name], ledgers[name], ambient_temperature
            )
            for name in self.tank_names
        }
        return derivatives, tuple(connection_flows)

    def simulate(
        self,
        initial: Mapping[str, TankInventory],
        time_span: tuple[float, float],
        command_provider: CommandProvider,
        ambient_temperature: float,
        evaluation_times: np.ndarray | None = None,
        method: str = "BDF",
        relative_tolerance: float = 1.0e-6,
        absolute_tolerance: float = 1.0e-8,
        maximum_step: float = np.inf,
        initial_actuator_positions: Mapping[str, float] | None = None,
    ) -> SimulationResult:
        tank_vector = self.pack(initial)
        actuated_connections = tuple(
            connection
            for connection in self.restrictions
            if connection.actuator is not None
        )
        initial_actuator_positions = (
            {} if initial_actuator_positions is None else initial_actuator_positions
        )
        actuator_vector = np.asarray(
            [
                initial_actuator_positions.get(
                    connection.name,
                    connection.actuator.parameters.fail_safe_position,
                )
                for connection in actuated_connections
            ],
            dtype=float,
        )
        initial_vector = np.concatenate((tank_vector, actuator_vector))
        tank_state_count = len(tank_vector)

        def right_hand_side(time: float, values: np.ndarray) -> np.ndarray:
            inventories = self.unpack(values[:tank_state_count])
            states = self.thermodynamic_states(inventories)
            commands = command_provider(time, states)
            actual_openings = {
                connection.name: float(values[tank_state_count + index])
                for index, connection in enumerate(actuated_connections)
            }
            derivatives, _ = self.evaluate(
                inventories,
                commands,
                ambient_temperature,
                actual_openings=actual_openings,
            )
            packed: list[float] = []
            for name in self.tank_names:
                derivative = derivatives[name]
                packed.extend(
                    (
                        derivative.mass,
                        derivative.internal_energy,
                        derivative.wall_temperature,
                    )
                )
            for index, connection in enumerate(actuated_connections):
                actual_position = float(values[tank_state_count + index])
                demanded_position = commands.restriction_openings.get(
                    connection.name, connection.default_opening
                )
                available = commands.actuator_available.get(connection.name, True)
                stuck = commands.actuator_stuck.get(connection.name, False)
                packed.append(
                    0.0
                    if stuck
                    else connection.actuator.derivative(
                        actual_position, demanded_position, available
                    )
                )
            return np.asarray(packed, dtype=float)

        solution = solve_ivp(
            right_hand_side,
            time_span,
            initial_vector,
            method=method,
            t_eval=evaluation_times,
            rtol=relative_tolerance,
            atol=absolute_tolerance,
            max_step=maximum_step,
        )
        inventories = {
            name: (
                solution.y[index],
                solution.y[index + 1],
                solution.y[index + 2],
            )
            for name, index in zip(self.tank_names, range(0, tank_state_count, 3))
        }
        actuator_positions = {
            connection.name: solution.y[tank_state_count + index]
            for index, connection in enumerate(actuated_connections)
        }
        return SimulationResult(
            time=solution.t,
            inventories=inventories,
            actuator_positions=actuator_positions,
            solver_success=solution.success,
            solver_message=solution.message,
        )
