"""Coupled partial-station model from PCV inlet to a Type IV vehicle tank."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Mapping

import numpy as np
from .tabulated import PropsSI, hydrogen_table
from .thermo_types import ThermoDomainError
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar

from .protocol import (
    FuelingCommand,
    FuelingObservation,
    FuelingPhase,
    SampledFuelingController,
)
from .validation import OutputChannel, ValidationTrace
from .vehicle import (
    CompositeTankGasState,
    CompositeTankState,
    CompositeVehicleTank,
    TankBoundaryFlow,
)


@dataclass(frozen=True)
class SupplyState:
    pressure_pa: float
    temperature_k: float


SupplyModel = Callable[[float], SupplyState]


@dataclass(frozen=True)
class RestrictionParameters:
    flow_area_m2: float
    discharge_coefficient: float = 0.8
    minimum_pressure_pa: float = 1.0e5

    def __post_init__(self) -> None:
        if self.flow_area_m2 <= 0.0:
            raise ValueError("flow_area_m2 must be positive")
        if not 0.0 < self.discharge_coefficient <= 1.0:
            raise ValueError("discharge_coefficient must be in (0, 1]")


@dataclass(frozen=True)
class PrecoolerParameters:
    hydrogen_coolant_ua_w_k: float
    coolant_thermal_capacity_j_k: float
    chiller_ua_w_k: float
    hydrogen_pressure_drop_pa: float = 0.0

    def __post_init__(self) -> None:
        if min(
            self.hydrogen_coolant_ua_w_k,
            self.coolant_thermal_capacity_j_k,
            self.chiller_ua_w_k,
        ) <= 0.0:
            raise ValueError("Precooler UA and thermal capacity values must be positive")
        if self.hydrogen_pressure_drop_pa < 0.0:
            raise ValueError("hydrogen_pressure_drop_pa cannot be negative")


@dataclass(frozen=True)
class HoseParameters:
    internal_volume_m3: float
    wall_thermal_capacity_j_k: float
    gas_wall_ua_w_k: float
    wall_ambient_ua_w_k: float
    nozzle_flow_area_m2: float
    nozzle_discharge_coefficient: float = 0.8

    def __post_init__(self) -> None:
        if min(
            self.internal_volume_m3,
            self.wall_thermal_capacity_j_k,
            self.nozzle_flow_area_m2,
        ) <= 0.0:
            raise ValueError("Hose volume, thermal capacity, and nozzle area must be positive")
        if min(self.gas_wall_ua_w_k, self.wall_ambient_ua_w_k) < 0.0:
            raise ValueError("Hose UA values cannot be negative")
        if not 0.0 < self.nozzle_discharge_coefficient <= 1.0:
            raise ValueError("nozzle_discharge_coefficient must be in (0, 1]")


@dataclass(frozen=True)
class DispenserFitParameters:
    pcv_area_multiplier: float = 1.0
    nozzle_area_multiplier: float = 1.0
    precooler_ua_multiplier: float = 1.0
    precooler_capacity_multiplier: float = 1.0
    chiller_ua_multiplier: float = 1.0
    hose_volume_multiplier: float = 1.0
    hose_gas_wall_ua_multiplier: float = 1.0
    hose_wall_ambient_ua_multiplier: float = 1.0
    hose_wall_capacity_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if any(value <= 0.0 for value in self.__dict__.values()):
            raise ValueError("All dispenser fitting multipliers must be positive")


@dataclass(frozen=True)
class PartialStationState:
    coolant_temperature_k: float
    hose_hydrogen_mass_kg: float
    hose_hydrogen_internal_energy_j: float
    hose_wall_temperature_k: float
    vehicle: CompositeTankState

    def as_vector(self) -> np.ndarray:
        return np.concatenate(
            (
                np.array(
                    [
                        self.coolant_temperature_k,
                        self.hose_hydrogen_mass_kg,
                        self.hose_hydrogen_internal_energy_j,
                        self.hose_wall_temperature_k,
                    ],
                    dtype=float,
                ),
                self.vehicle.as_vector(),
            )
        )

    @classmethod
    def from_vector(cls, values: np.ndarray) -> "PartialStationState":
        if len(values) != 8:
            raise ValueError("PartialStationState requires eight state values")
        return cls(
            coolant_temperature_k=float(values[0]),
            hose_hydrogen_mass_kg=float(values[1]),
            hose_hydrogen_internal_energy_j=float(values[2]),
            hose_wall_temperature_k=float(values[3]),
            vehicle=CompositeTankState.from_vector(values[4:8]),
        )


@dataclass(frozen=True)
class PartialStationTrajectory:
    time_s: np.ndarray
    states: np.ndarray
    channels: Mapping[OutputChannel, np.ndarray]
    phases: tuple[FuelingPhase, ...]
    stop_reason: str | None

    def validation_traces(
        self,
        case_id: str,
        source: str = "h2station-partial-model",
    ) -> dict[OutputChannel, ValidationTrace]:
        units = {
            OutputChannel.DISPENSED_MASS_FLOW: "kg/s",
            OutputChannel.PCV_INLET_PRESSURE: "Pa",
            OutputChannel.PCV_INLET_TEMPERATURE: "K",
            OutputChannel.PCV_OUTLET_PRESSURE: "Pa",
            OutputChannel.PCV_OUTLET_TEMPERATURE: "K",
            OutputChannel.PRESSURE_REFERENCE: "Pa",
            OutputChannel.PRECOOLER_OUTLET_TEMPERATURE: "K",
            OutputChannel.PRECOOLER_HEAT_RATE: "W",
            OutputChannel.HOSE_PRESSURE: "Pa",
            OutputChannel.HOSE_TEMPERATURE: "K",
            OutputChannel.RECEPTACLE_PRESSURE: "Pa",
            OutputChannel.RECEPTACLE_TEMPERATURE: "K",
            OutputChannel.VEHICLE_INLET_PRESSURE: "Pa",
            OutputChannel.VEHICLE_INLET_TEMPERATURE: "K",
            OutputChannel.VEHICLE_GAS_PRESSURE: "Pa",
            OutputChannel.VEHICLE_GAS_TEMPERATURE: "K",
            OutputChannel.LINER_INNER_TEMPERATURE: "K",
            OutputChannel.LINER_CFRP_TEMPERATURE: "K",
            OutputChannel.CFRP_OUTER_TEMPERATURE: "K",
            OutputChannel.VEHICLE_SOC: "1",
            OutputChannel.INJECTOR_VELOCITY: "m/s",
        }
        return {
            channel: ValidationTrace(
                channel=channel,
                time_s=self.time_s,
                values=values,
                unit=units[channel],
                source=source,
                case_id=case_id,
            )
            for channel, values in self.channels.items()
        }


class IsentropicRealGasRestriction:
    """Adiabatic real-gas restriction using the hydrogen property table."""

    # The sonic pressure ratio is smooth across the operating envelope. Build
    # this small table from the same EOS lookup once, then evaluate only one
    # isentropic state for each RHS flow call instead of optimizing every time.
    _critical_pressure_grid = np.array(
        [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 60.0, 80.0, 100.0, 120.0]
    ) * 1.0e6
    _critical_temperature_grid = np.array(
        [210.0, 240.0, 280.0, 320.0, 360.0, 420.0, 500.0]
    )

    @classmethod
    @lru_cache(maxsize=1)
    def _critical_ratios(cls) -> np.ndarray:
        table = hydrogen_table()
        ratios = np.empty((len(cls._critical_pressure_grid), len(cls._critical_temperature_grid)))
        for ip, pressure in enumerate(cls._critical_pressure_grid):
            for it, temperature in enumerate(cls._critical_temperature_grid):
                upstream = table.state_pt(float(pressure), float(temperature))

                def negative_flux(log_pressure: float) -> float:
                    outlet_pressure = float(np.exp(log_pressure))
                    density, enthalpy = table.flow_properties_ps(outlet_pressure, upstream.entropy)
                    return -density * np.sqrt(max(0.0, 2.0 * (upstream.enthalpy - enthalpy)))

                result = minimize_scalar(
                    negative_flux,
                    bounds=(np.log(max(table.pressure_grid[0], pressure * 0.25)), np.log(pressure)),
                    method="bounded",
                    options={"xatol": 1.0e-8},
                )
                if not result.success:
                    raise RuntimeError("Could not build the hydrogen choking lookup")
                ratios[ip, it] = np.exp(result.x) / pressure
        return ratios

    @classmethod
    def _critical_ratio(cls, pressure: float, temperature: float) -> float | None:
        pressures, temperatures = cls._critical_pressure_grid, cls._critical_temperature_grid
        if not (pressures[0] <= pressure <= pressures[-1]
                and temperatures[0] <= temperature <= temperatures[-1]):
            return None
        ip = min(int(np.searchsorted(pressures, pressure, side="right")) - 1, len(pressures) - 2)
        it = min(int(np.searchsorted(temperatures, temperature, side="right")) - 1, len(temperatures) - 2)
        pressure_weight = (np.log(pressure) - np.log(pressures[ip])) / (
            np.log(pressures[ip + 1]) - np.log(pressures[ip])
        )
        temperature_weight = (temperature - temperatures[it]) / (temperatures[it + 1] - temperatures[it])
        ratios = cls._critical_ratios()
        low = ratios[ip, it] * (1.0 - temperature_weight) + ratios[ip, it + 1] * temperature_weight
        high = ratios[ip + 1, it] * (1.0 - temperature_weight) + ratios[ip + 1, it + 1] * temperature_weight
        return float(low * (1.0 - pressure_weight) + high * pressure_weight)

    def __init__(self, parameters: RestrictionParameters, fluid: str = "Hydrogen") -> None:
        self.parameters = parameters
        self.fluid = fluid

    def mass_flow_kg_s(
        self,
        upstream_pressure_pa: float,
        upstream_temperature_k: float,
        downstream_pressure_pa: float,
        opening: float = 1.0,
        area_multiplier: float = 1.0,
        allow_reverse_flow: bool = False,
    ) -> float:
        opening = min(1.0, max(0.0, opening))
        if opening == 0.0:
            return 0.0
        if upstream_pressure_pa <= downstream_pressure_pa:
            if not allow_reverse_flow or downstream_pressure_pa <= upstream_pressure_pa:
                return 0.0
            return -self.mass_flow_kg_s(
                downstream_pressure_pa, upstream_temperature_k,
                upstream_pressure_pa, opening, area_multiplier, False,
            )

        lower_pressure = max(
            self.parameters.minimum_pressure_pa,
            min(downstream_pressure_pa, upstream_pressure_pa * (1.0 - 1.0e-10)),
        )
        if self.fluid.lower() not in {"hydrogen", "h2"}:
            raise ValueError("The tabulated runtime supports Hydrogen only")
        table = hydrogen_table()
        upstream = table.state_pt(upstream_pressure_pa, upstream_temperature_k)
        entropy = upstream.entropy
        stagnation_enthalpy = upstream.enthalpy

        def mass_flux(pressure_pa: float) -> float:
            density, enthalpy = table.flow_properties_ps(pressure_pa, entropy)
            velocity = np.sqrt(max(0.0, 2.0 * (stagnation_enthalpy - enthalpy)))
            return density * velocity

        critical_ratio = self._critical_ratio(upstream_pressure_pa, upstream_temperature_k)
        if critical_ratio is not None:
            critical_pressure = upstream_pressure_pa * critical_ratio
            # A subcritical restriction is controlled by its downstream state;
            # a choked one is controlled by the interpolated sonic state.
            maximum_flux = mass_flux(max(lower_pressure, critical_pressure))
            return (
                self.parameters.discharge_coefficient
                * self.parameters.flow_area_m2
                * area_multiplier
                * opening
                * maximum_flux
            )

        # Deep expansion to atmospheric pressure can leave the single-phase
        # table although the choking point itself remains inside it. Bracket
        # only the admissible isentrope; never extrapolate its properties.
        clipped_isentrope = False
        try:
            lower_flux = mass_flux(lower_pressure)
        except ThermoDomainError:
            clipped_isentrope = True
            invalid, valid = lower_pressure, upstream_pressure_pa
            for _ in range(32):
                candidate = np.sqrt(invalid * valid)
                try:
                    mass_flux(candidate)
                    valid = candidate
                except ThermoDomainError:
                    invalid = candidate
            lower_pressure = valid
            lower_flux = mass_flux(lower_pressure)

        result = minimize_scalar(
            lambda log_pressure: -mass_flux(float(np.exp(log_pressure))),
            bounds=(np.log(lower_pressure), np.log(upstream_pressure_pa)),
            method="bounded",
            options={"xatol": 1.0e-8},
        )
        if clipped_isentrope and (not result.success or -float(result.fun) <= lower_flux):
            raise ThermoDomainError("Restriction choking point is outside the hydrogen table")
        maximum_flux = max(
            lower_flux,
            -float(result.fun) if result.success else 0.0,
        )
        return (
            self.parameters.discharge_coefficient
            * self.parameters.flow_area_m2
            * area_multiplier
            * opening
            * maximum_flux
        )


class PartialStationModel:
    """PCV, finite-capacity precooler, hose line-pack, nozzle, and vehicle tank."""

    def __init__(
        self,
        vehicle_tank: CompositeVehicleTank,
        controller: SampledFuelingController,
        supply: SupplyModel,
        pcv: RestrictionParameters,
        precooler: PrecoolerParameters,
        hose: HoseParameters,
        fit: DispenserFitParameters | None = None,
        ambient_temperature_k: float = 298.15,
    ) -> None:
        self.vehicle_tank = vehicle_tank
        self.controller = controller
        self.supply = supply
        self.pcv_parameters = pcv
        self.precooler = precooler
        self.hose = hose
        self.fit = fit or DispenserFitParameters()
        self.ambient_temperature_k = ambient_temperature_k
        self.pcv_restriction = IsentropicRealGasRestriction(
            pcv, vehicle_tank.parameters.fluid
        )
        self.nozzle_restriction = IsentropicRealGasRestriction(
            RestrictionParameters(
                flow_area_m2=hose.nozzle_flow_area_m2,
                discharge_coefficient=hose.nozzle_discharge_coefficient,
            ),
            vehicle_tank.parameters.fluid,
        )

    @property
    def fluid(self) -> str:
        return self.vehicle_tank.parameters.fluid

    def initial_state(
        self,
        vehicle: CompositeTankState,
        hose_pressure_pa: float,
        hose_temperature_k: float,
        coolant_temperature_k: float,
        hose_wall_temperature_k: float | None = None,
    ) -> PartialStationState:
        density = float(
            PropsSI(
                "Dmass", "P", hose_pressure_pa, "T", hose_temperature_k,
                self.fluid,
            )
        )
        specific_internal_energy = float(
            PropsSI(
                "Umass", "P", hose_pressure_pa, "T", hose_temperature_k,
                self.fluid,
            )
        )
        mass = density * self.hose.internal_volume_m3 * self.fit.hose_volume_multiplier
        return PartialStationState(
            coolant_temperature_k=coolant_temperature_k,
            hose_hydrogen_mass_kg=mass,
            hose_hydrogen_internal_energy_j=mass * specific_internal_energy,
            hose_wall_temperature_k=hose_wall_temperature_k or hose_temperature_k,
            vehicle=vehicle,
        )

    def hose_gas_state(self, state: PartialStationState) -> CompositeTankGasState:
        if state.hose_hydrogen_mass_kg <= 0.0:
            raise ValueError("Hose hydrogen mass must remain positive")
        volume = self.hose.internal_volume_m3 * self.fit.hose_volume_multiplier
        density = state.hose_hydrogen_mass_kg / volume
        internal_energy = (
            state.hose_hydrogen_internal_energy_j / state.hose_hydrogen_mass_kg
        )
        pressure = float(
            PropsSI("P", "Dmass", density, "Umass", internal_energy, self.fluid)
        )
        temperature = float(
            PropsSI("T", "Dmass", density, "Umass", internal_energy, self.fluid)
        )
        enthalpy = float(
            PropsSI("Hmass", "Dmass", density, "Umass", internal_energy, self.fluid)
        )
        return CompositeTankGasState(
            pressure_pa=pressure,
            temperature_k=temperature,
            density_kg_m3=density,
            specific_internal_energy_j_kg=internal_energy,
            specific_enthalpy_j_kg=enthalpy,
        )

    def _flow_and_thermal_states(
        self,
        time_s: float,
        state: PartialStationState,
        command: FuelingCommand,
        supply_override: SupplyState | None = None,
        precooler_effectiveness_multiplier: float = 1.0,
        pcv_area_multiplier: float = 1.0,
        nozzle_area_multiplier: float = 1.0,
        allow_reverse_flow: bool = False,
    ) -> dict[str, float]:
        supply = supply_override or self.supply(time_s)
        hose_gas = self.hose_gas_state(state)
        vehicle_gas = self.vehicle_tank.gas_state(state.vehicle)
        pcv_outlet_pressure = max(
            hose_gas.pressure_pa + self.precooler.hydrogen_pressure_drop_pa,
            self.pcv_parameters.minimum_pressure_pa,
        )
        pcv_mass_flow = self.pcv_restriction.mass_flow_kg_s(
            supply.pressure_pa,
            supply.temperature_k,
            pcv_outlet_pressure,
            command.valve_opening,
            self.fit.pcv_area_multiplier * max(0.0, pcv_area_multiplier),
        )
        supply_enthalpy = float(
            PropsSI(
                "Hmass", "P", supply.pressure_pa, "T", supply.temperature_k,
                self.fluid,
            )
        )
        pcv_outlet_temperature = float(
            PropsSI(
                "T", "P", pcv_outlet_pressure, "Hmass", supply_enthalpy,
                self.fluid,
            )
        )

        if pcv_mass_flow > 1.0e-12:
            cp = float(
                PropsSI(
                    "Cpmass", "P", pcv_outlet_pressure, "T",
                    pcv_outlet_temperature, self.fluid,
                )
            )
            ua = (
                self.precooler.hydrogen_coolant_ua_w_k
                * self.fit.precooler_ua_multiplier
                * max(0.0, precooler_effectiveness_multiplier)
            )
            effectiveness = 1.0 - np.exp(-ua / (pcv_mass_flow * cp))
            precooler_outlet_temperature = (
                pcv_outlet_temperature
                - effectiveness
                * (pcv_outlet_temperature - state.coolant_temperature_k)
            )
            cooled_enthalpy = float(
                PropsSI(
                    "Hmass", "P", hose_gas.pressure_pa, "T",
                    precooler_outlet_temperature, self.fluid,
                )
            )
            precooler_heat_rate = pcv_mass_flow * (
                supply_enthalpy - cooled_enthalpy
            )
        else:
            precooler_outlet_temperature = state.coolant_temperature_k
            cooled_enthalpy = hose_gas.specific_enthalpy_j_kg
            precooler_heat_rate = 0.0

        nozzle_mass_flow = self.nozzle_restriction.mass_flow_kg_s(
            hose_gas.pressure_pa,
            hose_gas.temperature_k,
            vehicle_gas.pressure_pa,
            1.0,
            self.fit.nozzle_area_multiplier * max(0.0, nozzle_area_multiplier),
            allow_reverse_flow,
        )
        nozzle_mass_flow = min(
            nozzle_mass_flow,
            self.controller.schedule.maximum_mass_flow_kg_s,
        )
        receptacle_pressure = max(
            vehicle_gas.pressure_pa,
            self.pcv_parameters.minimum_pressure_pa,
        )
        receptacle_temperature = float(
            PropsSI(
                "T", "P", receptacle_pressure, "Hmass",
                hose_gas.specific_enthalpy_j_kg, self.fluid,
            )
        )
        receptacle_density = float(
            PropsSI(
                "Dmass", "P", receptacle_pressure, "Hmass",
                hose_gas.specific_enthalpy_j_kg, self.fluid,
            )
        )
        injector_velocity = nozzle_mass_flow / max(
            receptacle_density
            * self.hose.nozzle_flow_area_m2
            * self.fit.nozzle_area_multiplier,
            1.0e-30,
        )
        return {
            "supply_pressure": supply.pressure_pa,
            "supply_temperature": supply.temperature_k,
            "pcv_outlet_pressure": pcv_outlet_pressure,
            "pcv_outlet_temperature": pcv_outlet_temperature,
            "pcv_mass_flow": pcv_mass_flow,
            "cooled_enthalpy": cooled_enthalpy,
            "precooler_outlet_temperature": precooler_outlet_temperature,
            "precooler_heat_rate": precooler_heat_rate,
            "nozzle_mass_flow": nozzle_mass_flow,
            "receptacle_pressure": receptacle_pressure,
            "receptacle_temperature": receptacle_temperature,
            "injector_velocity": injector_velocity,
        }

    def derivative(
        self,
        time_s: float,
        state: PartialStationState,
        command: FuelingCommand,
        supply_override: SupplyState | None = None,
        precooler_effectiveness_multiplier: float = 1.0,
        pcv_area_multiplier: float = 1.0,
        nozzle_area_multiplier: float = 1.0,
        allow_reverse_flow: bool = False,
    ) -> PartialStationState:
        values = self._flow_and_thermal_states(
            time_s,
            state,
            command,
            supply_override,
            precooler_effectiveness_multiplier,
            pcv_area_multiplier,
            nozzle_area_multiplier,
            allow_reverse_flow,
        )
        hose_gas = self.hose_gas_state(state)
        gas_wall_heat_rate = (
            self.hose.gas_wall_ua_w_k
            * self.fit.hose_gas_wall_ua_multiplier
            * (hose_gas.temperature_k - state.hose_wall_temperature_k)
        )
        wall_ambient_heat_rate = (
            self.hose.wall_ambient_ua_w_k
            * self.fit.hose_wall_ambient_ua_multiplier
            * (state.hose_wall_temperature_k - self.ambient_temperature_k)
        )
        chiller_heat_rate = (
            self.precooler.chiller_ua_w_k
            * self.fit.chiller_ua_multiplier
            * (
                state.coolant_temperature_k
                - command.delivery_temperature_target_k
            )
        )
        coolant_temperature_rate = (
            values["precooler_heat_rate"] - chiller_heat_rate
        ) / (
            self.precooler.coolant_thermal_capacity_j_k
            * self.fit.precooler_capacity_multiplier
        )
        hose_mass_rate = values["pcv_mass_flow"] - values["nozzle_mass_flow"]
        hose_energy_rate = (
            values["pcv_mass_flow"] * values["cooled_enthalpy"]
            - values["nozzle_mass_flow"] * hose_gas.specific_enthalpy_j_kg
            - gas_wall_heat_rate
        )
        hose_wall_temperature_rate = (
            gas_wall_heat_rate - wall_ambient_heat_rate
        ) / (
            self.hose.wall_thermal_capacity_j_k
            * self.fit.hose_wall_capacity_multiplier
        )
        vehicle_rate = self.vehicle_tank.derivative(
            state.vehicle,
            TankBoundaryFlow(
                inlet_mass_flow_kg_s=values["nozzle_mass_flow"],
                inlet_specific_enthalpy_j_kg=hose_gas.specific_enthalpy_j_kg,
                ambient_temperature_k=self.ambient_temperature_k,
            ),
        )
        return PartialStationState(
            coolant_temperature_rate,
            hose_mass_rate,
            hose_energy_rate,
            hose_wall_temperature_rate,
            vehicle_rate,
        )

    def simulate(
        self,
        initial_state: PartialStationState,
        duration_s: float,
        controller_period_s: float = 0.1,
    ) -> PartialStationTrajectory:
        if duration_s <= 0.0 or controller_period_s <= 0.0:
            raise ValueError("Simulation duration and controller period must be positive")

        time_values: list[float] = []
        state_values: list[np.ndarray] = []
        phases: list[FuelingPhase] = []
        channel_values: dict[OutputChannel, list[float]] = {
            channel: [] for channel in self._reported_channels()
        }
        current = initial_state
        time_s = 0.0
        measured_mass_flow = 0.0
        stop_reason = None

        while time_s <= duration_s:
            hose_gas = self.hose_gas_state(current)
            vehicle_gas = self.vehicle_tank.gas_state(current.vehicle)
            observation = FuelingObservation(
                time_s=time_s,
                pressure_pa=vehicle_gas.pressure_pa,
                temperature_k=vehicle_gas.temperature_k,
                density_kg_m3=vehicle_gas.density_kg_m3,
                measured_mass_flow_kg_s=measured_mass_flow,
            )
            command = self.controller.update(observation, controller_period_s)
            instantaneous = self._flow_and_thermal_states(time_s, current, command)
            measured_mass_flow = instantaneous["nozzle_mass_flow"]
            self._append_outputs(
                time_values,
                state_values,
                phases,
                channel_values,
                time_s,
                current,
                command,
                instantaneous,
                hose_gas,
                vehicle_gas,
            )

            if command.phase in (FuelingPhase.COMPLETE, FuelingPhase.ABORTED):
                stop_reason = command.stop_reason
                break
            if time_s >= duration_s:
                break

            end_s = min(duration_s, time_s + controller_period_s)
            solution = solve_ivp(
                lambda local_time, vector: self.derivative(
                    local_time,
                    PartialStationState.from_vector(vector),
                    command,
                ).as_vector(),
                (time_s, end_s),
                current.as_vector(),
                method="BDF",
                t_eval=[end_s],
                rtol=1.0e-6,
                atol=1.0e-8,
            )
            if not solution.success:
                raise RuntimeError(f"Partial-station integration failed: {solution.message}")
            current = PartialStationState.from_vector(solution.y[:, -1])
            time_s = end_s

        return PartialStationTrajectory(
            time_s=np.asarray(time_values),
            states=np.vstack(state_values),
            channels={
                channel: np.asarray(values)
                for channel, values in channel_values.items()
            },
            phases=tuple(phases),
            stop_reason=stop_reason,
        )

    @staticmethod
    def _reported_channels() -> tuple[OutputChannel, ...]:
        return (
            OutputChannel.DISPENSED_MASS_FLOW,
            OutputChannel.PCV_INLET_PRESSURE,
            OutputChannel.PCV_INLET_TEMPERATURE,
            OutputChannel.PCV_OUTLET_PRESSURE,
            OutputChannel.PCV_OUTLET_TEMPERATURE,
            OutputChannel.PRESSURE_REFERENCE,
            OutputChannel.PRECOOLER_OUTLET_TEMPERATURE,
            OutputChannel.PRECOOLER_HEAT_RATE,
            OutputChannel.HOSE_PRESSURE,
            OutputChannel.HOSE_TEMPERATURE,
            OutputChannel.RECEPTACLE_PRESSURE,
            OutputChannel.RECEPTACLE_TEMPERATURE,
            OutputChannel.VEHICLE_INLET_PRESSURE,
            OutputChannel.VEHICLE_INLET_TEMPERATURE,
            OutputChannel.VEHICLE_GAS_PRESSURE,
            OutputChannel.VEHICLE_GAS_TEMPERATURE,
            OutputChannel.LINER_INNER_TEMPERATURE,
            OutputChannel.LINER_CFRP_TEMPERATURE,
            OutputChannel.CFRP_OUTER_TEMPERATURE,
            OutputChannel.VEHICLE_SOC,
            OutputChannel.INJECTOR_VELOCITY,
        )

    def _append_outputs(
        self,
        times: list[float],
        states: list[np.ndarray],
        phases: list[FuelingPhase],
        channels: dict[OutputChannel, list[float]],
        time_s: float,
        state: PartialStationState,
        command: FuelingCommand,
        instantaneous: Mapping[str, float],
        hose_gas: CompositeTankGasState,
        vehicle_gas: CompositeTankGasState,
    ) -> None:
        times.append(time_s)
        states.append(state.as_vector())
        phases.append(command.phase)
        soc = self.controller.soc_model.calculate(vehicle_gas.density_kg_m3)
        output = {
            OutputChannel.DISPENSED_MASS_FLOW: instantaneous["nozzle_mass_flow"],
            OutputChannel.PCV_INLET_PRESSURE: instantaneous["supply_pressure"],
            OutputChannel.PCV_INLET_TEMPERATURE: instantaneous["supply_temperature"],
            OutputChannel.PCV_OUTLET_PRESSURE: instantaneous["pcv_outlet_pressure"],
            OutputChannel.PCV_OUTLET_TEMPERATURE: instantaneous["pcv_outlet_temperature"],
            OutputChannel.PRESSURE_REFERENCE: command.reference_pressure_pa,
            OutputChannel.PRECOOLER_OUTLET_TEMPERATURE: instantaneous[
                "precooler_outlet_temperature"
            ],
            OutputChannel.PRECOOLER_HEAT_RATE: instantaneous["precooler_heat_rate"],
            OutputChannel.HOSE_PRESSURE: hose_gas.pressure_pa,
            OutputChannel.HOSE_TEMPERATURE: hose_gas.temperature_k,
            OutputChannel.RECEPTACLE_PRESSURE: instantaneous["receptacle_pressure"],
            OutputChannel.RECEPTACLE_TEMPERATURE: instantaneous[
                "receptacle_temperature"
            ],
            OutputChannel.VEHICLE_INLET_PRESSURE: instantaneous["receptacle_pressure"],
            OutputChannel.VEHICLE_INLET_TEMPERATURE: instantaneous[
                "receptacle_temperature"
            ],
            OutputChannel.VEHICLE_GAS_PRESSURE: vehicle_gas.pressure_pa,
            OutputChannel.VEHICLE_GAS_TEMPERATURE: vehicle_gas.temperature_k,
            OutputChannel.LINER_INNER_TEMPERATURE: state.vehicle.liner_temperature_k,
            OutputChannel.LINER_CFRP_TEMPERATURE: 0.5
            * (
                state.vehicle.liner_temperature_k
                + state.vehicle.shell_temperature_k
            ),
            OutputChannel.CFRP_OUTER_TEMPERATURE: state.vehicle.shell_temperature_k,
            OutputChannel.VEHICLE_SOC: soc,
            OutputChannel.INJECTOR_VELOCITY: instantaneous["injector_velocity"],
        }
        for channel, value in output.items():
            channels[channel].append(float(value))
