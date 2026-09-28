"""First-principles thermal model for a Type IV vehicle hydrogen tank."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

import numpy as np
from .tabulated import PropsSI
from scipy.integrate import solve_ivp

from .protocol import (
    FuelingCommand,
    FuelingObservation,
    FuelingPhase,
    SampledFuelingController,
)


@dataclass(frozen=True)
class CompositeTankParameters:
    internal_volume_m3: float
    liner_mass_kg: float
    liner_specific_heat_j_kg_k: float
    shell_mass_kg: float
    shell_specific_heat_j_kg_k: float
    gas_liner_ua_w_k: float
    liner_shell_ua_w_k: float
    shell_ambient_ua_w_k: float
    fluid: str = "Hydrogen"

    def __post_init__(self) -> None:
        positive = (
            self.internal_volume_m3,
            self.liner_mass_kg,
            self.liner_specific_heat_j_kg_k,
            self.shell_mass_kg,
            self.shell_specific_heat_j_kg_k,
        )
        if any(value <= 0.0 for value in positive):
            raise ValueError("Tank volume, masses, and heat capacities must be positive")
        if min(
            self.gas_liner_ua_w_k,
            self.liner_shell_ua_w_k,
            self.shell_ambient_ua_w_k,
        ) < 0.0:
            raise ValueError("UA values cannot be negative")


@dataclass(frozen=True)
class CompositeTankFitParameters:
    effective_volume_multiplier: float = 1.0
    gas_liner_ua_multiplier: float = 1.0
    liner_shell_ua_multiplier: float = 1.0
    shell_ambient_ua_multiplier: float = 1.0
    liner_heat_capacity_multiplier: float = 1.0
    shell_heat_capacity_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if any(value <= 0.0 for value in self.__dict__.values()):
            raise ValueError("All fitting multipliers must be positive")


@dataclass(frozen=True)
class CompositeTankState:
    hydrogen_mass_kg: float
    hydrogen_internal_energy_j: float
    liner_temperature_k: float
    shell_temperature_k: float

    def as_vector(self) -> np.ndarray:
        return np.array(
            [
                self.hydrogen_mass_kg,
                self.hydrogen_internal_energy_j,
                self.liner_temperature_k,
                self.shell_temperature_k,
            ],
            dtype=float,
        )

    @classmethod
    def from_vector(cls, values: np.ndarray) -> "CompositeTankState":
        return cls(*(float(value) for value in values))


@dataclass(frozen=True)
class CompositeTankGasState:
    pressure_pa: float
    temperature_k: float
    density_kg_m3: float
    specific_internal_energy_j_kg: float
    specific_enthalpy_j_kg: float


@dataclass(frozen=True)
class TankBoundaryFlow:
    inlet_mass_flow_kg_s: float = 0.0
    inlet_specific_enthalpy_j_kg: float = 0.0
    outlet_mass_flow_kg_s: float = 0.0
    ambient_temperature_k: float = 298.15


@dataclass(frozen=True)
class CompositeTankTrajectory:
    time_s: np.ndarray
    state: np.ndarray
    pressure_pa: np.ndarray
    gas_temperature_k: np.ndarray
    state_of_charge: np.ndarray
    valve_opening: np.ndarray
    mass_flow_kg_s: np.ndarray
    phase: tuple[FuelingPhase, ...]
    stop_reason: str | None


class CompositeVehicleTank:
    """Uniform gas, liner, and composite-shell thermal zones at fixed volume."""

    def __init__(
        self,
        parameters: CompositeTankParameters,
        fit: CompositeTankFitParameters | None = None,
    ) -> None:
        self.parameters = parameters
        self.fit = fit or CompositeTankFitParameters()

    @property
    def effective_volume_m3(self) -> float:
        return (
            self.parameters.internal_volume_m3
            * self.fit.effective_volume_multiplier
        )

    def initial_state(
        self,
        pressure_pa: float,
        gas_temperature_k: float,
        liner_temperature_k: float | None = None,
        shell_temperature_k: float | None = None,
    ) -> CompositeTankState:
        density = float(
            PropsSI(
                "Dmass", "P", pressure_pa, "T", gas_temperature_k,
                self.parameters.fluid,
            )
        )
        internal_energy = float(
            PropsSI(
                "Umass", "P", pressure_pa, "T", gas_temperature_k,
                self.parameters.fluid,
            )
        )
        mass = density * self.effective_volume_m3
        return CompositeTankState(
            hydrogen_mass_kg=mass,
            hydrogen_internal_energy_j=mass * internal_energy,
            liner_temperature_k=liner_temperature_k or gas_temperature_k,
            shell_temperature_k=shell_temperature_k or gas_temperature_k,
        )

    def gas_state(self, state: CompositeTankState) -> CompositeTankGasState:
        if state.hydrogen_mass_kg <= 0.0:
            raise ValueError("Hydrogen mass must remain positive")
        density = state.hydrogen_mass_kg / self.effective_volume_m3
        specific_internal_energy = (
            state.hydrogen_internal_energy_j / state.hydrogen_mass_kg
        )
        pressure = float(
            PropsSI(
                "P", "Dmass", density, "Umass", specific_internal_energy,
                self.parameters.fluid,
            )
        )
        temperature = float(
            PropsSI(
                "T", "Dmass", density, "Umass", specific_internal_energy,
                self.parameters.fluid,
            )
        )
        enthalpy = float(
            PropsSI(
                "Hmass", "Dmass", density, "Umass", specific_internal_energy,
                self.parameters.fluid,
            )
        )
        return CompositeTankGasState(
            pressure_pa=pressure,
            temperature_k=temperature,
            density_kg_m3=density,
            specific_internal_energy_j_kg=specific_internal_energy,
            specific_enthalpy_j_kg=enthalpy,
        )

    def derivative(
        self,
        state: CompositeTankState,
        boundary: TankBoundaryFlow,
    ) -> CompositeTankState:
        gas = self.gas_state(state)
        p = self.parameters
        f = self.fit

        gas_liner_heat_w = (
            p.gas_liner_ua_w_k
            * f.gas_liner_ua_multiplier
            * (gas.temperature_k - state.liner_temperature_k)
        )
        liner_shell_heat_w = (
            p.liner_shell_ua_w_k
            * f.liner_shell_ua_multiplier
            * (state.liner_temperature_k - state.shell_temperature_k)
        )
        shell_ambient_heat_w = (
            p.shell_ambient_ua_w_k
            * f.shell_ambient_ua_multiplier
            * (state.shell_temperature_k - boundary.ambient_temperature_k)
        )

        mass_rate = boundary.inlet_mass_flow_kg_s - boundary.outlet_mass_flow_kg_s
        energy_rate = (
            boundary.inlet_mass_flow_kg_s * boundary.inlet_specific_enthalpy_j_kg
            - boundary.outlet_mass_flow_kg_s * gas.specific_enthalpy_j_kg
            - gas_liner_heat_w
        )
        liner_temperature_rate = (
            gas_liner_heat_w - liner_shell_heat_w
        ) / (
            p.liner_mass_kg
            * p.liner_specific_heat_j_kg_k
            * f.liner_heat_capacity_multiplier
        )
        shell_temperature_rate = (
            liner_shell_heat_w - shell_ambient_heat_w
        ) / (
            p.shell_mass_kg
            * p.shell_specific_heat_j_kg_k
            * f.shell_heat_capacity_multiplier
        )
        return CompositeTankState(
            mass_rate,
            energy_rate,
            liner_temperature_rate,
            shell_temperature_rate,
        )


InletModel = Callable[
    [float, CompositeTankGasState, FuelingCommand],
    tuple[float, float],
]


class CompositeTankFillSimulator:
    """Piecewise BDF integration synchronized to a sampled fueling controller."""

    def __init__(
        self,
        tank: CompositeVehicleTank,
        controller: SampledFuelingController,
        inlet_model: InletModel,
        ambient_temperature_k: float = 298.15,
    ) -> None:
        self.tank = tank
        self.controller = controller
        self.inlet_model = inlet_model
        self.ambient_temperature_k = ambient_temperature_k

    def simulate(
        self,
        initial_state: CompositeTankState,
        duration_s: float,
        controller_period_s: float = 0.1,
    ) -> CompositeTankTrajectory:
        if duration_s <= 0.0 or controller_period_s <= 0.0:
            raise ValueError("Simulation duration and controller period must be positive")

        times = [0.0]
        states = [initial_state.as_vector()]
        gas = self.tank.gas_state(initial_state)
        pressures = [gas.pressure_pa]
        temperatures = [gas.temperature_k]
        openings = [0.0]
        flows = [0.0]
        phases = [FuelingPhase.IDLE]
        soc_values = [self.controller.soc_model.calculate(gas.density_kg_m3)]
        current = initial_state
        previous_flow = 0.0
        stop_reason = None

        while times[-1] < duration_s:
            time_s = times[-1]
            gas = self.tank.gas_state(current)
            observation = FuelingObservation(
                time_s=time_s,
                pressure_pa=gas.pressure_pa,
                temperature_k=gas.temperature_k,
                density_kg_m3=gas.density_kg_m3,
                measured_mass_flow_kg_s=previous_flow,
            )
            command = self.controller.update(observation, controller_period_s)
            if command.phase in (FuelingPhase.COMPLETE, FuelingPhase.ABORTED):
                stop_reason = command.stop_reason
                break

            step_end_s = min(duration_s, time_s + controller_period_s)

            def rhs(local_time_s: float, values: np.ndarray) -> np.ndarray:
                local_state = CompositeTankState.from_vector(values)
                local_gas = self.tank.gas_state(local_state)
                mass_flow, inlet_enthalpy = self.inlet_model(
                    local_time_s, local_gas, command
                )
                mass_flow = min(
                    max(0.0, mass_flow),
                    self.controller.schedule.maximum_mass_flow_kg_s,
                )
                derivative = self.tank.derivative(
                    local_state,
                    TankBoundaryFlow(
                        inlet_mass_flow_kg_s=mass_flow,
                        inlet_specific_enthalpy_j_kg=inlet_enthalpy,
                        ambient_temperature_k=self.ambient_temperature_k,
                    ),
                )
                return derivative.as_vector()

            solution = solve_ivp(
                rhs,
                (time_s, step_end_s),
                current.as_vector(),
                method="BDF",
                t_eval=[step_end_s],
                rtol=1.0e-6,
                atol=1.0e-8,
            )
            if not solution.success:
                raise RuntimeError(f"Vehicle tank integration failed: {solution.message}")

            current = CompositeTankState.from_vector(solution.y[:, -1])
            gas = self.tank.gas_state(current)
            previous_flow, _ = self.inlet_model(step_end_s, gas, command)
            previous_flow = min(
                max(0.0, previous_flow),
                self.controller.schedule.maximum_mass_flow_kg_s,
            )
            times.append(step_end_s)
            states.append(current.as_vector())
            pressures.append(gas.pressure_pa)
            temperatures.append(gas.temperature_k)
            openings.append(command.valve_opening)
            flows.append(previous_flow)
            phases.append(command.phase)
            soc_values.append(self.controller.soc_model.calculate(gas.density_kg_m3))

        return CompositeTankTrajectory(
            time_s=np.asarray(times),
            state=np.vstack(states),
            pressure_pa=np.asarray(pressures),
            gas_temperature_k=np.asarray(temperatures),
            state_of_charge=np.asarray(soc_values),
            valve_opening=np.asarray(openings),
            mass_flow_kg_s=np.asarray(flows),
            phase=tuple(phases),
            stop_reason=stop_reason,
        )
