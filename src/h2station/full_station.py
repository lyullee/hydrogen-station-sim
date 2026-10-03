"""Dynamic cascade storage and compressor coupled to the partial station."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

import numpy as np
from .tabulated import PropsSI
from scipy.integrate import solve_ivp

from .dispenser import (
    PartialStationModel,
    PartialStationState,
    SupplyModel,
    SupplyState,
)
from .protocol import FuelingCommand, FuelingObservation, FuelingPhase
from .validation import OutputChannel
from .vehicle import CompositeTankGasState


@dataclass(frozen=True)
class CascadeBankParameters:
    name: str
    internal_volume_m3: float
    target_pressure_pa: float
    wall_mass_kg: float
    wall_specific_heat_j_kg_k: float
    gas_wall_ua_w_k: float
    wall_ambient_ua_w_k: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Cascade bank name is required")
        if min(
            self.internal_volume_m3,
            self.target_pressure_pa,
            self.wall_mass_kg,
            self.wall_specific_heat_j_kg_k,
        ) <= 0.0:
            raise ValueError("Cascade volume, pressure, mass, and heat capacity must be positive")
        if min(self.gas_wall_ua_w_k, self.wall_ambient_ua_w_k) < 0.0:
            raise ValueError("Cascade UA values cannot be negative")


@dataclass(frozen=True)
class CascadeBankFitParameters:
    volume_multiplier: float = 1.0
    gas_wall_ua_multiplier: float = 1.0
    wall_ambient_ua_multiplier: float = 1.0
    wall_heat_capacity_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if any(value <= 0.0 for value in self.__dict__.values()):
            raise ValueError("All cascade fitting multipliers must be positive")


@dataclass(frozen=True)
class CascadeBankState:
    hydrogen_mass_kg: float
    hydrogen_internal_energy_j: float
    wall_temperature_k: float

    def as_vector(self) -> np.ndarray:
        return np.asarray(
            [
                self.hydrogen_mass_kg,
                self.hydrogen_internal_energy_j,
                self.wall_temperature_k,
            ],
            dtype=float,
        )

    @classmethod
    def from_vector(cls, values: np.ndarray) -> "CascadeBankState":
        if len(values) != 3:
            raise ValueError("CascadeBankState requires three state values")
        return cls(*(float(value) for value in values))


class CascadeBank:
    def __init__(
        self,
        parameters: CascadeBankParameters,
        fit: CascadeBankFitParameters | None = None,
        fluid: str = "Hydrogen",
    ) -> None:
        self.parameters = parameters
        self.fit = fit or CascadeBankFitParameters()
        self.fluid = fluid

    @property
    def volume_m3(self) -> float:
        return self.parameters.internal_volume_m3 * self.fit.volume_multiplier

    def initial_state(
        self,
        pressure_pa: float,
        gas_temperature_k: float,
        wall_temperature_k: float | None = None,
    ) -> CascadeBankState:
        density = float(
            PropsSI("Dmass", "P", pressure_pa, "T", gas_temperature_k, self.fluid)
        )
        specific_internal_energy = float(
            PropsSI("Umass", "P", pressure_pa, "T", gas_temperature_k, self.fluid)
        )
        mass = density * self.volume_m3
        return CascadeBankState(
            mass,
            mass * specific_internal_energy,
            wall_temperature_k or gas_temperature_k,
        )

    def gas_state(self, state: CascadeBankState) -> CompositeTankGasState:
        if state.hydrogen_mass_kg <= 0.0:
            raise ValueError("Cascade hydrogen mass must remain positive")
        density = state.hydrogen_mass_kg / self.volume_m3
        internal_energy = state.hydrogen_internal_energy_j / state.hydrogen_mass_kg
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

    def derivative(
        self,
        state: CascadeBankState,
        inlet_mass_flow_kg_s: float,
        inlet_enthalpy_j_kg: float,
        outlet_mass_flow_kg_s: float,
        ambient_temperature_k: float,
    ) -> CascadeBankState:
        gas = self.gas_state(state)
        gas_wall_heat_w = (
            self.parameters.gas_wall_ua_w_k
            * self.fit.gas_wall_ua_multiplier
            * (gas.temperature_k - state.wall_temperature_k)
        )
        wall_ambient_heat_w = (
            self.parameters.wall_ambient_ua_w_k
            * self.fit.wall_ambient_ua_multiplier
            * (state.wall_temperature_k - ambient_temperature_k)
        )
        mass_rate = inlet_mass_flow_kg_s - outlet_mass_flow_kg_s
        energy_rate = (
            inlet_mass_flow_kg_s * inlet_enthalpy_j_kg
            - outlet_mass_flow_kg_s * gas.specific_enthalpy_j_kg
            - gas_wall_heat_w
        )
        wall_temperature_rate = (
            gas_wall_heat_w - wall_ambient_heat_w
        ) / (
            self.parameters.wall_mass_kg
            * self.parameters.wall_specific_heat_j_kg_k
            * self.fit.wall_heat_capacity_multiplier
        )
        return CascadeBankState(mass_rate, energy_rate, wall_temperature_rate)


@dataclass(frozen=True)
class CompressorParameters:
    number_of_stages: int
    swept_volume_rate_m3_s: float
    volumetric_efficiency: float
    isentropic_efficiency: float
    mechanical_efficiency: float
    motor_efficiency: float
    intercooler_outlet_temperature_k: float
    maximum_mass_flow_kg_s: float
    maximum_discharge_pressure_pa: float
    discharge_pressure_margin_pa: float = 2.0e5

    def __post_init__(self) -> None:
        if self.number_of_stages < 1:
            raise ValueError("number_of_stages must be at least one")
        if min(
            self.swept_volume_rate_m3_s,
            self.intercooler_outlet_temperature_k,
            self.maximum_mass_flow_kg_s,
            self.maximum_discharge_pressure_pa,
        ) <= 0.0:
            raise ValueError("Compressor rates, temperature, and pressure must be positive")
        efficiencies = (
            self.volumetric_efficiency,
            self.isentropic_efficiency,
            self.mechanical_efficiency,
            self.motor_efficiency,
        )
        if any(not 0.0 < value <= 1.0 for value in efficiencies):
            raise ValueError("Compressor efficiencies must be in (0, 1]")


@dataclass(frozen=True)
class CompressorFitParameters:
    flow_multiplier: float = 1.0
    isentropic_efficiency_multiplier: float = 1.0
    power_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if any(value <= 0.0 for value in self.__dict__.values()):
            raise ValueError("All compressor fitting multipliers must be positive")


@dataclass(frozen=True)
class CompressorResult:
    mass_flow_kg_s: float
    outlet_enthalpy_j_kg: float
    outlet_temperature_k: float
    electrical_power_w: float
    stage_outlets: tuple[tuple[float, float], ...] = ()  # (pressure Pa, discharge temperature K)


class MultistageHydrogenCompressor:
    """Quasi-steady positive-displacement compressor with perfect intercooling."""

    def __init__(
        self,
        parameters: CompressorParameters,
        fit: CompressorFitParameters | None = None,
        fluid: str = "Hydrogen",
    ) -> None:
        self.parameters = parameters
        self.fit = fit or CompressorFitParameters()
        self.fluid = fluid

    def evaluate(
        self,
        suction: SupplyState,
        discharge_pressure_pa: float,
        enabled: bool = True,
        include_stage_outlets: bool = False,
    ) -> CompressorResult:
        p = self.parameters
        if (
            not enabled
            or discharge_pressure_pa <= suction.pressure_pa
            or discharge_pressure_pa > p.maximum_discharge_pressure_pa
        ):
            enthalpy = float(
                PropsSI(
                    "Hmass", "P", suction.pressure_pa, "T", suction.temperature_k,
                    self.fluid,
                )
            )
            return CompressorResult(0.0, enthalpy, suction.temperature_k, 0.0)

        suction_density = float(
            PropsSI(
                "Dmass", "P", suction.pressure_pa, "T", suction.temperature_k,
                self.fluid,
            )
        )
        mass_flow = min(
            p.maximum_mass_flow_kg_s,
            suction_density
            * p.swept_volume_rate_m3_s
            * p.volumetric_efficiency
            * self.fit.flow_multiplier,
        )
        stage_ratio = (
            discharge_pressure_pa / suction.pressure_pa
        ) ** (1.0 / p.number_of_stages)
        inlet_pressure = suction.pressure_pa
        inlet_temperature = suction.temperature_k
        specific_work_j_kg = 0.0
        outlet_enthalpy = 0.0
        stage_outlets: list[tuple[float, float]] = []

        effective_isentropic_efficiency = min(
            1.0,
            p.isentropic_efficiency
            * self.fit.isentropic_efficiency_multiplier,
        )
        for stage_index in range(p.number_of_stages):
            outlet_pressure = (
                discharge_pressure_pa
                if stage_index == p.number_of_stages - 1
                else inlet_pressure * stage_ratio
            )
            inlet_enthalpy = float(
                PropsSI(
                    "Hmass", "P", inlet_pressure, "T", inlet_temperature,
                    self.fluid,
                )
            )
            inlet_entropy = float(
                PropsSI(
                    "Smass", "P", inlet_pressure, "T", inlet_temperature,
                    self.fluid,
                )
            )
            isentropic_outlet_enthalpy = float(
                PropsSI(
                    "Hmass", "P", outlet_pressure, "Smass", inlet_entropy,
                    self.fluid,
                )
            )
            outlet_enthalpy = inlet_enthalpy + (
                isentropic_outlet_enthalpy - inlet_enthalpy
            ) / effective_isentropic_efficiency
            if include_stage_outlets:
                stage_outlets.append((outlet_pressure, float(PropsSI(
                    "T", "P", outlet_pressure, "Hmass", outlet_enthalpy, self.fluid,
                ))))
            specific_work_j_kg += outlet_enthalpy - inlet_enthalpy
            if stage_index < p.number_of_stages - 1:
                inlet_pressure = outlet_pressure
                inlet_temperature = p.intercooler_outlet_temperature_k

        outlet_temperature = float(
            PropsSI(
                "T", "P", discharge_pressure_pa, "Hmass", outlet_enthalpy,
                self.fluid,
            )
        )
        electrical_power = (
            mass_flow
            * specific_work_j_kg
            / (p.mechanical_efficiency * p.motor_efficiency)
            * self.fit.power_multiplier
        )
        return CompressorResult(
            mass_flow,
            outlet_enthalpy,
            outlet_temperature,
            electrical_power,
            tuple(stage_outlets),
        )


@dataclass(frozen=True)
class CascadeSupervisorParameters:
    minimum_dispatch_pressure_margin_pa: float = 1.0e6
    recharge_pressure_hysteresis_pa: float = 1.0e6


class CascadeSupervisor:
    """Sampled bank dispatch and recharge selection logic."""

    def __init__(self, parameters: CascadeSupervisorParameters | None = None) -> None:
        self.parameters = parameters or CascadeSupervisorParameters()
        self.reset()

    def reset(self) -> None:
        self._dispatch_indices: dict[str, int] = {}
        self._recharge_index: int | None = None
        self._recharge_armed: list[bool] = []

    def reset_dispatch(self, circuit_id: str = "primary") -> None:
        self._dispatch_indices.pop(circuit_id, None)

    def select_dispatch_bank(
        self,
        banks: tuple[CascadeBank, ...],
        gas_states: tuple[CompositeTankGasState, ...],
        downstream_pressure_pa: float,
        excluded_indices: frozenset[int] = frozenset(),
        *,
        circuit_id: str = "primary",
    ) -> int | None:
        minimum_pressure = (
            downstream_pressure_pa
            + self.parameters.minimum_dispatch_pressure_margin_pa
        )
        available = [
            index
            for index, gas in enumerate(gas_states)
            if index not in excluded_indices and gas.pressure_pa > minimum_pressure
        ]
        if not available:
            return None
        previous = self._dispatch_indices.get(circuit_id)
        if previous in available:
            return previous
        if previous is not None:
            previous_target = banks[previous].parameters.target_pressure_pa
            # A cascade fill advances from low to high pressure. Do not return
            # to a lower bank when hose pressure falls during break-before-make;
            # that feedback otherwise causes rapid bank-switch oscillation and
            # can suppress nearly all delivered flow.
            higher = [
                index for index in available
                if banks[index].parameters.target_pressure_pa >= previous_target
            ]
            if higher:
                available = higher
        selected = min(
            available,
            key=lambda index: banks[index].parameters.target_pressure_pa,
        )
        self._dispatch_indices[circuit_id] = selected
        return selected

    def select_recharge_bank(
        self,
        banks: tuple[CascadeBank, ...],
        gas_states: tuple[CompositeTankGasState, ...],
        dispatch_index: int | tuple[int | None, ...] | None,
        target_pressures_pa: tuple[float, ...] | None = None,
        restart_margins_pa: tuple[float, ...] | None = None,
        ignore_targets: bool = False,
        excluded_indices: frozenset[int] = frozenset(),
    ) -> int | None:
        excluded = {
            index for index in (
                dispatch_index if isinstance(dispatch_index, tuple)
                else (dispatch_index,)
            ) if index is not None
        }
        if len(self._recharge_armed) != len(banks):
            self._recharge_armed = [True] * len(banks)
        targets = tuple(target_pressures_pa or tuple(
            bank.parameters.target_pressure_pa for bank in banks
        ))
        margins = tuple(restart_margins_pa or (
            self.parameters.recharge_pressure_hysteresis_pa for _ in banks
        ))
        if ignore_targets:
            self._recharge_index = None
            self._recharge_armed = [True] * len(banks)
        else:
            for index, (gas, target, margin) in enumerate(zip(gas_states, targets, margins)):
                if gas.pressure_pa >= target:
                    self._recharge_armed[index] = False
                    if self._recharge_index == index:
                        self._recharge_index = None
                elif gas.pressure_pa <= target - margin:
                    self._recharge_armed[index] = True

            # Keep one bank selected until it reaches its upper target.  This
            # prevents controller-sample noise and simultaneous vehicle draws
            # from making the compressor alternate between READY and CHARGE.
            if (self._recharge_index is not None
                    and self._recharge_index not in excluded
                    and self._recharge_index not in excluded_indices
                    and gas_states[self._recharge_index].pressure_pa < targets[self._recharge_index]):
                return self._recharge_index

        needs_charge = [
            index
            for index, (bank, gas) in enumerate(zip(banks, gas_states))
            if index not in excluded and index not in excluded_indices
            and (ignore_targets or (self._recharge_armed[index]
                                    and gas.pressure_pa < targets[index]))
        ]
        if not needs_charge:
            self._recharge_index = None
            return None
        if ignore_targets:
            # With operator auto-stop disabled, keep feeding the lowest-pressure
            # available bank instead of pinning the compressor to the high bank.
            return min(needs_charge, key=lambda index: gas_states[index].pressure_pa)
        self._recharge_index = max(
            needs_charge,
            key=lambda index: targets[index],
        )
        return self._recharge_index


@dataclass(frozen=True)
class CascadeValveSequencerParameters:
    opening_time_constant_s: float = 0.20
    closing_time_constant_s: float = 0.10
    break_before_make_s: float = 0.10
    closed_threshold: float = 1.0e-3

    def __post_init__(self) -> None:
        if self.opening_time_constant_s <= 0.0:
            raise ValueError("opening_time_constant_s must be positive")
        if self.closing_time_constant_s <= 0.0:
            raise ValueError("closing_time_constant_s must be positive")
        if self.break_before_make_s < 0.0:
            raise ValueError("break_before_make_s cannot be negative")
        if not 0.0 < self.closed_threshold < 1.0:
            raise ValueError("closed_threshold must be in (0, 1)")


class CascadeValveSequencer:
    """Single-open-valve, break-before-make cascade switching state machine."""

    def __init__(
        self,
        parameters: CascadeValveSequencerParameters | None = None,
    ) -> None:
        self.parameters = parameters or CascadeValveSequencerParameters()
        self.reset()

    def reset(self) -> None:
        self._active_index: int | None = None
        self._pending_index: int | None = None
        self._opening = 0.0
        self._phase = "closed"
        self._dead_time_elapsed_s = 0.0

    def update(
        self,
        requested_index: int | None,
        sample_period_s: float,
    ) -> tuple[int | None, float, str]:
        if sample_period_s <= 0.0:
            raise ValueError("sample_period_s must be positive")

        if requested_index != self._pending_index:
            self._pending_index = requested_index
            if self._active_index is not None and self._opening > 0.0:
                self._phase = "closing"
            elif requested_index is None:
                self._phase = "closed"
            else:
                self._active_index = requested_index
                self._phase = "opening"
                self._dead_time_elapsed_s = 0.0

        if self._phase == "closing":
            self._opening *= np.exp(
                -sample_period_s / self.parameters.closing_time_constant_s
            )
            if self._opening <= self.parameters.closed_threshold:
                self._opening = 0.0
                self._active_index = None
                self._dead_time_elapsed_s = 0.0
                self._phase = (
                    "dead-time" if self._pending_index is not None else "closed"
                )
        elif self._phase == "dead-time":
            self._dead_time_elapsed_s += sample_period_s
            if self._dead_time_elapsed_s >= self.parameters.break_before_make_s:
                self._active_index = self._pending_index
                self._phase = "opening"
        elif self._phase == "opening":
            self._opening = 1.0 - (1.0 - self._opening) * np.exp(
                -sample_period_s / self.parameters.opening_time_constant_s
            )
            if self._opening >= 1.0 - self.parameters.closed_threshold:
                self._opening = 1.0
                self._phase = "open"
        elif self._phase == "open" and requested_index is None:
            self._phase = "closing"

        return self._active_index, self._opening, self._phase


@dataclass(frozen=True)
class FullStationState:
    banks: tuple[CascadeBankState, ...]
    partial_station: PartialStationState
    secondary_partial_station: PartialStationState | None = None

    def as_vector(self) -> np.ndarray:
        parts = tuple(bank.as_vector() for bank in self.banks) + (
            self.partial_station.as_vector(),
        )
        if self.secondary_partial_station is not None:
            parts += (self.secondary_partial_station.as_vector(),)
        return np.concatenate(parts)

    @classmethod
    def from_vector(cls, values: np.ndarray, bank_count: int) -> "FullStationState":
        primary_size = 3 * bank_count + 8
        dual_size = primary_size + 8
        if len(values) not in (primary_size, dual_size):
            raise ValueError(
                f"FullStationState requires {primary_size} or {dual_size} state values"
            )
        banks = tuple(
            CascadeBankState.from_vector(values[3 * index:3 * index + 3])
            for index in range(bank_count)
        )
        offset = 3 * bank_count
        primary = PartialStationState.from_vector(values[offset:offset + 8])
        secondary = (
            PartialStationState.from_vector(values[offset + 8:offset + 16])
            if len(values) == dual_size else None
        )
        return cls(banks, primary, secondary)


@dataclass(frozen=True)
class FullStationTrajectory:
    time_s: np.ndarray
    states: np.ndarray
    bank_names: tuple[str, ...]
    bank_pressure_pa: np.ndarray
    bank_temperature_k: np.ndarray
    compressor_mass_flow_kg_s: np.ndarray
    compressor_power_w: np.ndarray
    requested_dispatch_bank: tuple[str | None, ...]
    dispatch_bank: tuple[str | None, ...]
    dispatch_valve_opening: np.ndarray
    dispatch_valve_phase: tuple[str, ...]
    recharge_bank: tuple[str | None, ...]
    partial_channels: Mapping[OutputChannel, np.ndarray]
    phases: tuple[FuelingPhase, ...]
    stop_reason: str | None


class FullStationModel:
    """Three-level cascade, compressor recharge, and complete dispenser transient."""

    def __init__(
        self,
        banks: tuple[CascadeBank, ...],
        compressor: MultistageHydrogenCompressor,
        compressor_suction: SupplyModel,
        partial_station: PartialStationModel,
        secondary_partial_station: PartialStationModel | None = None,
        supervisor: CascadeSupervisor | None = None,
        valve_sequencer: CascadeValveSequencer | None = None,
        ambient_temperature_k: float = 298.15,
    ) -> None:
        if len(banks) < 2:
            raise ValueError("A cascade station requires at least two banks")
        if len({bank.parameters.name for bank in banks}) != len(banks):
            raise ValueError("Cascade bank names must be unique")
        self.banks = banks
        self.compressor = compressor
        self.compressor_suction = compressor_suction
        self.partial_station = partial_station
        self.secondary_partial_station = secondary_partial_station
        self.supervisor = supervisor or CascadeSupervisor()
        self.valve_sequencer = valve_sequencer or CascadeValveSequencer()
        self.secondary_valve_sequencer = CascadeValveSequencer()
        self.ambient_temperature_k = ambient_temperature_k

    def derivative(
        self,
        time_s: float,
        state: FullStationState,
        command: FuelingCommand,
        dispatch_index: int | None,
        recharge_index: int | None,
        dispatch_valve_opening: float = 1.0,
        precooler_effectiveness_multiplier: float = 1.0,
        secondary_command: FuelingCommand | None = None,
        secondary_dispatch_index: int | None = None,
        secondary_dispatch_valve_opening: float = 1.0,
        primary_pcv_area_multiplier: float = 1.0,
        primary_nozzle_area_multiplier: float = 1.0,
        secondary_pcv_area_multiplier: float = 1.0,
        secondary_nozzle_area_multiplier: float = 1.0,
        primary_allow_reverse_flow: bool = False,
        secondary_allow_reverse_flow: bool = False,
        compressor_flow_multiplier: float = 1.0,
    ) -> tuple[FullStationState, CompressorResult, float]:
        bank_gases = tuple(
            bank.gas_state(bank_state)
            for bank, bank_state in zip(self.banks, state.banks)
        )
        if dispatch_index is None:
            supply_index = int(np.argmax([gas.pressure_pa for gas in bank_gases]))
        else:
            supply_index = dispatch_index
        # The cascade outlet valve acts upstream of the hose. The dispenser
        # nozzle remains controlled by the fueling command so trapped line-pack
        # can discharge into the vehicle while banks switch.
        effective_command = command
        effective_primary_pcv_multiplier = (
            primary_pcv_area_multiplier * dispatch_valve_opening
            if dispatch_index is not None else 0.0
        )
        dispatch_supply = SupplyState(
            bank_gases[supply_index].pressure_pa,
            bank_gases[supply_index].temperature_k,
        )
        instantaneous = self.partial_station._flow_and_thermal_states(
            time_s,
            state.partial_station,
            effective_command,
            dispatch_supply,
            precooler_effectiveness_multiplier,
            effective_primary_pcv_multiplier,
            primary_nozzle_area_multiplier,
            primary_allow_reverse_flow,
        )
        partial_rate = self.partial_station.derivative(
            time_s,
            state.partial_station,
            effective_command,
            dispatch_supply,
            precooler_effectiveness_multiplier,
            effective_primary_pcv_multiplier,
            primary_nozzle_area_multiplier,
            primary_allow_reverse_flow,
        )
        secondary_rate = None
        secondary_instantaneous = None
        if (
            self.secondary_partial_station is not None
            and state.secondary_partial_station is not None
            and secondary_command is not None
        ):
            secondary_supply_index = (
                secondary_dispatch_index
                if secondary_dispatch_index is not None else supply_index
            )
            secondary_supply = SupplyState(
                bank_gases[secondary_supply_index].pressure_pa,
                bank_gases[secondary_supply_index].temperature_k,
            )
            secondary_effective_command = secondary_command
            effective_secondary_pcv_multiplier = (
                secondary_pcv_area_multiplier * secondary_dispatch_valve_opening
                if secondary_dispatch_index is not None else 0.0
            )
            secondary_instantaneous = (
                self.secondary_partial_station._flow_and_thermal_states(
                    time_s,
                    state.secondary_partial_station,
                    secondary_effective_command,
                    secondary_supply,
                    precooler_effectiveness_multiplier,
                    effective_secondary_pcv_multiplier,
                    secondary_nozzle_area_multiplier,
                    secondary_allow_reverse_flow,
                )
            )
            secondary_rate = self.secondary_partial_station.derivative(
                time_s,
                state.secondary_partial_station,
                secondary_effective_command,
                secondary_supply,
                precooler_effectiveness_multiplier,
                effective_secondary_pcv_multiplier,
                secondary_nozzle_area_multiplier,
                secondary_allow_reverse_flow,
            )

        compressor_result = self.compressor.evaluate(
            self.compressor_suction(time_s),
            (
                bank_gases[recharge_index].pressure_pa
                + self.compressor.parameters.discharge_pressure_margin_pa
                if recharge_index is not None
                else self.compressor_suction(time_s).pressure_pa
            ),
            enabled=recharge_index is not None,
        )
        if compressor_flow_multiplier != 1.0:
            compressor_result = replace(
                compressor_result,
                mass_flow_kg_s=compressor_result.mass_flow_kg_s * compressor_flow_multiplier,
                electrical_power_w=compressor_result.electrical_power_w * compressor_flow_multiplier,
            )
        bank_rates: list[CascadeBankState] = []
        for index, (bank, bank_state) in enumerate(zip(self.banks, state.banks)):
            bank_rates.append(
                bank.derivative(
                    bank_state,
                    compressor_result.mass_flow_kg_s if index == recharge_index else 0.0,
                    compressor_result.outlet_enthalpy_j_kg,
                    (
                        (instantaneous["pcv_mass_flow"] if index == dispatch_index else 0.0)
                        + (
                            secondary_instantaneous["pcv_mass_flow"]
                            if secondary_instantaneous is not None
                            and index == secondary_dispatch_index else 0.0
                        )
                    ),
                    self.ambient_temperature_k,
                )
            )
        return (
            FullStationState(tuple(bank_rates), partial_rate, secondary_rate),
            compressor_result,
            instantaneous["nozzle_mass_flow"],
        )

    def simulate(
        self,
        initial_state: FullStationState,
        duration_s: float,
        controller_period_s: float = 0.1,
    ) -> FullStationTrajectory:
        if len(initial_state.banks) != len(self.banks):
            raise ValueError("Initial-state bank count does not match the model")
        if duration_s <= 0.0 or controller_period_s <= 0.0:
            raise ValueError("Simulation duration and controller period must be positive")

        times: list[float] = []
        states: list[np.ndarray] = []
        bank_pressures: list[list[float]] = []
        bank_temperatures: list[list[float]] = []
        compressor_flows: list[float] = []
        compressor_powers: list[float] = []
        requested_dispatch_names: list[str | None] = []
        dispatch_names: list[str | None] = []
        dispatch_valve_openings: list[float] = []
        dispatch_valve_phases: list[str] = []
        recharge_names: list[str | None] = []
        phases: list[FuelingPhase] = []
        partial_outputs: dict[OutputChannel, list[float]] = {
            channel: [] for channel in self._partial_output_channels()
        }
        current = initial_state
        time_s = 0.0
        measured_mass_flow = 0.0
        stop_reason = None
        self.valve_sequencer.reset()
        self.supervisor.reset()

        while time_s <= duration_s:
            bank_gases = tuple(
                bank.gas_state(bank_state)
                for bank, bank_state in zip(self.banks, current.banks)
            )
            hose_gas = self.partial_station.hose_gas_state(current.partial_station)
            vehicle_gas = self.partial_station.vehicle_tank.gas_state(
                current.partial_station.vehicle
            )
            requested_dispatch_index = self.supervisor.select_dispatch_bank(
                self.banks, bank_gases, hose_gas.pressure_pa
            )
            dispatch_index, dispatch_valve_opening, valve_phase = (
                self.valve_sequencer.update(
                    requested_dispatch_index,
                    controller_period_s,
                )
            )
            recharge_index = self.supervisor.select_recharge_bank(
                self.banks, bank_gases, dispatch_index
            )
            observation = FuelingObservation(
                time_s,
                vehicle_gas.pressure_pa,
                vehicle_gas.temperature_k,
                vehicle_gas.density_kg_m3,
                measured_mass_flow,
            )
            command = self.partial_station.controller.update(
                observation, controller_period_s
            )
            supply_index = dispatch_index if dispatch_index is not None else int(
                np.argmax([gas.pressure_pa for gas in bank_gases])
            )
            effective_command = (
                replace(
                    command,
                    valve_opening=command.valve_opening * dispatch_valve_opening,
                )
                if dispatch_index is not None
                else replace(command, valve_opening=0.0)
            )
            supply = SupplyState(
                bank_gases[supply_index].pressure_pa,
                bank_gases[supply_index].temperature_k,
            )
            instantaneous = self.partial_station._flow_and_thermal_states(
                time_s, current.partial_station, effective_command, supply
            )
            compressor_result = self.compressor.evaluate(
                self.compressor_suction(time_s),
                (
                    bank_gases[recharge_index].pressure_pa
                    + self.compressor.parameters.discharge_pressure_margin_pa
                    if recharge_index is not None
                    else self.compressor_suction(time_s).pressure_pa
                ),
                enabled=recharge_index is not None,
            )
            measured_mass_flow = instantaneous["nozzle_mass_flow"]
            times.append(time_s)
            states.append(current.as_vector())
            bank_pressures.append([gas.pressure_pa for gas in bank_gases])
            bank_temperatures.append([gas.temperature_k for gas in bank_gases])
            compressor_flows.append(compressor_result.mass_flow_kg_s)
            compressor_powers.append(compressor_result.electrical_power_w)
            requested_dispatch_names.append(
                self.banks[requested_dispatch_index].parameters.name
                if requested_dispatch_index is not None else None
            )
            dispatch_names.append(
                self.banks[dispatch_index].parameters.name
                if dispatch_index is not None else None
            )
            dispatch_valve_openings.append(dispatch_valve_opening)
            dispatch_valve_phases.append(valve_phase)
            recharge_names.append(
                self.banks[recharge_index].parameters.name
                if recharge_index is not None else None
            )
            phases.append(command.phase)
            sample = self._partial_output_sample(
                current.partial_station,
                command,
                instantaneous,
                hose_gas,
                vehicle_gas,
            )
            for channel, value in sample.items():
                partial_outputs[channel].append(value)

            if command.phase in (FuelingPhase.COMPLETE, FuelingPhase.ABORTED):
                stop_reason = command.stop_reason
                break
            if time_s >= duration_s:
                break

            end_s = min(duration_s, time_s + controller_period_s)
            solution = solve_ivp(
                lambda local_time, vector: self.derivative(
                    local_time,
                    FullStationState.from_vector(vector, len(self.banks)),
                    command,
                    dispatch_index,
                    recharge_index,
                    dispatch_valve_opening,
                )[0].as_vector(),
                (time_s, end_s),
                current.as_vector(),
                method="BDF",
                t_eval=[end_s],
                rtol=1.0e-6,
                atol=1.0e-8,
            )
            if not solution.success:
                raise RuntimeError(f"Full-station integration failed: {solution.message}")
            current = FullStationState.from_vector(solution.y[:, -1], len(self.banks))
            time_s = end_s

        return FullStationTrajectory(
            time_s=np.asarray(times),
            states=np.vstack(states),
            bank_names=tuple(bank.parameters.name for bank in self.banks),
            bank_pressure_pa=np.asarray(bank_pressures),
            bank_temperature_k=np.asarray(bank_temperatures),
            compressor_mass_flow_kg_s=np.asarray(compressor_flows),
            compressor_power_w=np.asarray(compressor_powers),
            requested_dispatch_bank=tuple(requested_dispatch_names),
            dispatch_bank=tuple(dispatch_names),
            dispatch_valve_opening=np.asarray(dispatch_valve_openings),
            dispatch_valve_phase=tuple(dispatch_valve_phases),
            recharge_bank=tuple(recharge_names),
            partial_channels={
                channel: np.asarray(values)
                for channel, values in partial_outputs.items()
            },
            phases=tuple(phases),
            stop_reason=stop_reason,
        )

    @staticmethod
    def _partial_output_channels() -> tuple[OutputChannel, ...]:
        return (
            OutputChannel.DISPENSED_MASS_FLOW,
            OutputChannel.PCV_INLET_PRESSURE,
            OutputChannel.PCV_INLET_TEMPERATURE,
            OutputChannel.PRESSURE_REFERENCE,
            OutputChannel.PRECOOLER_OUTLET_TEMPERATURE,
            OutputChannel.PRECOOLER_HEAT_RATE,
            OutputChannel.HOSE_PRESSURE,
            OutputChannel.HOSE_TEMPERATURE,
            OutputChannel.VEHICLE_GAS_PRESSURE,
            OutputChannel.VEHICLE_GAS_TEMPERATURE,
            OutputChannel.LINER_INNER_TEMPERATURE,
            OutputChannel.CFRP_OUTER_TEMPERATURE,
            OutputChannel.VEHICLE_SOC,
        )

    def _partial_output_sample(
        self,
        state: PartialStationState,
        command: FuelingCommand,
        instantaneous: Mapping[str, float],
        hose_gas: CompositeTankGasState,
        vehicle_gas: CompositeTankGasState,
    ) -> dict[OutputChannel, float]:
        return {
            OutputChannel.DISPENSED_MASS_FLOW: instantaneous["nozzle_mass_flow"],
            OutputChannel.PCV_INLET_PRESSURE: instantaneous["supply_pressure"],
            OutputChannel.PCV_INLET_TEMPERATURE: instantaneous["supply_temperature"],
            OutputChannel.PRESSURE_REFERENCE: command.reference_pressure_pa,
            OutputChannel.PRECOOLER_OUTLET_TEMPERATURE: instantaneous[
                "precooler_outlet_temperature"
            ],
            OutputChannel.PRECOOLER_HEAT_RATE: instantaneous["precooler_heat_rate"],
            OutputChannel.HOSE_PRESSURE: hose_gas.pressure_pa,
            OutputChannel.HOSE_TEMPERATURE: hose_gas.temperature_k,
            OutputChannel.VEHICLE_GAS_PRESSURE: vehicle_gas.pressure_pa,
            OutputChannel.VEHICLE_GAS_TEMPERATURE: vehicle_gas.temperature_k,
            OutputChannel.LINER_INNER_TEMPERATURE: state.vehicle.liner_temperature_k,
            OutputChannel.CFRP_OUTER_TEMPERATURE: state.vehicle.shell_temperature_k,
            OutputChannel.VEHICLE_SOC: self.partial_station.controller.soc_model.calculate(
                vehicle_gas.density_kg_m3
            ),
        }
