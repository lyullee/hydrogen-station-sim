"""Physical component models used by the dynamic station network."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, pi, sqrt

from scipy.optimize import minimize_scalar

from .thermo import HydrogenEOS, ThermoState


@dataclass(frozen=True, slots=True)
class TankParameters:
    volume: float
    gas_wall_area: float
    wall_ambient_area: float
    wall_heat_capacity: float
    gas_wall_htc: float
    wall_ambient_htc: float
    gas_wall_htc_multiplier: float = 1.0
    ambient_htc_multiplier: float = 1.0
    minimum_mass: float = 1.0e-6

    def __post_init__(self) -> None:
        positive = (
            self.volume,
            self.gas_wall_area,
            self.wall_ambient_area,
            self.wall_heat_capacity,
            self.gas_wall_htc,
            self.wall_ambient_htc,
            self.gas_wall_htc_multiplier,
            self.ambient_htc_multiplier,
            self.minimum_mass,
        )
        if any(value <= 0.0 for value in positive):
            raise ValueError("Tank parameters must be positive")


@dataclass(frozen=True, slots=True)
class TankInventory:
    mass: float
    internal_energy: float
    wall_temperature: float


@dataclass(slots=True)
class TankBoundaryFlows:
    mass_in: float = 0.0
    enthalpy_in_rate: float = 0.0
    mass_out: float = 0.0


@dataclass(frozen=True, slots=True)
class TankDerivative:
    mass: float
    internal_energy: float
    wall_temperature: float


class LumpedTank:
    """Two-zone gas/wall vessel with real-gas mass and energy conservation."""

    def __init__(self, parameters: TankParameters, eos: HydrogenEOS) -> None:
        self.parameters = parameters
        self.eos = eos

    def initial_inventory(
        self,
        pressure: float,
        temperature: float,
        wall_temperature: float | None = None,
    ) -> TankInventory:
        state = self.eos.state_pt(pressure, temperature)
        mass = state.density * self.parameters.volume
        return TankInventory(
            mass=mass,
            internal_energy=mass * state.internal_energy,
            wall_temperature=temperature if wall_temperature is None else wall_temperature,
        )

    def fluid_state(self, inventory: TankInventory) -> ThermoState:
        mass = max(inventory.mass, self.parameters.minimum_mass)
        density = mass / self.parameters.volume
        specific_internal_energy = inventory.internal_energy / mass
        return self.eos.state_rho_u(density, specific_internal_energy)

    def derivatives(
        self,
        inventory: TankInventory,
        boundary: TankBoundaryFlows,
        ambient_temperature: float,
    ) -> TankDerivative:
        state = self.fluid_state(inventory)
        p = self.parameters
        ua_gas_wall = (
            p.gas_wall_htc * p.gas_wall_area * p.gas_wall_htc_multiplier
        )
        ua_wall_ambient = (
            p.wall_ambient_htc
            * p.wall_ambient_area
            * p.ambient_htc_multiplier
        )
        heat_to_gas = ua_gas_wall * (inventory.wall_temperature - state.temperature)
        heat_to_wall_from_ambient = ua_wall_ambient * (
            ambient_temperature - inventory.wall_temperature
        )

        mass_out = boundary.mass_out
        if inventory.mass <= p.minimum_mass and mass_out > boundary.mass_in:
            mass_out = boundary.mass_in

        return TankDerivative(
            mass=boundary.mass_in - mass_out,
            internal_energy=(
                boundary.enthalpy_in_rate
                - mass_out * state.enthalpy
                + heat_to_gas
            ),
            wall_temperature=(
                -heat_to_gas + heat_to_wall_from_ambient
            )
            / p.wall_heat_capacity,
        )


@dataclass(frozen=True, slots=True)
class RestrictionParameters:
    diameter: float
    discharge_coefficient: float = 0.85
    area_multiplier: float = 1.0
    characteristic: str = "linear"
    rangeability: float = 50.0
    minimum_pressure: float = 1_000.0

    def __post_init__(self) -> None:
        if self.diameter <= 0.0:
            raise ValueError("Restriction diameter must be positive")
        if not 0.0 < self.discharge_coefficient <= 1.5:
            raise ValueError("Discharge coefficient is outside a usable range")
        if self.area_multiplier <= 0.0 or self.rangeability <= 1.0:
            raise ValueError("Area multiplier and rangeability are invalid")
        if self.characteristic not in {"linear", "equal_percentage"}:
            raise ValueError("Unknown valve characteristic")


@dataclass(frozen=True, slots=True)
class RestrictionFlow:
    mass_flow: float
    throat_pressure: float
    choked: bool
    effective_area: float


class RealGasRestriction:
    """Adiabatic real-gas restriction using maximum isentropic mass flux."""

    def __init__(self, parameters: RestrictionParameters, eos: HydrogenEOS) -> None:
        self.parameters = parameters
        self.eos = eos

    def _opening_fraction(self, opening: float) -> float:
        opening = min(max(opening, 0.0), 1.0)
        if self.parameters.characteristic == "linear":
            return opening
        r = self.parameters.rangeability
        return (r**opening - 1.0) / (r - 1.0)

    def mass_flow(
        self,
        upstream: ThermoState,
        downstream_pressure: float,
        opening: float = 1.0,
    ) -> RestrictionFlow:
        opening_fraction = self._opening_fraction(opening)
        geometric_area = pi * self.parameters.diameter**2 / 4.0
        effective_area = (
            geometric_area * self.parameters.area_multiplier * opening_fraction
        )
        if effective_area == 0.0 or downstream_pressure >= upstream.pressure:
            return RestrictionFlow(0.0, upstream.pressure, False, effective_area)

        lower_pressure = max(downstream_pressure, self.parameters.minimum_pressure)
        upper_pressure = upstream.pressure * (1.0 - 1.0e-10)
        if lower_pressure >= upper_pressure:
            return RestrictionFlow(0.0, upstream.pressure, False, effective_area)

        def mass_flux(log_pressure: float) -> float:
            pressure = exp(log_pressure)
            throat = self.eos.state_ps(pressure, upstream.entropy)
            available_enthalpy = max(upstream.enthalpy - throat.enthalpy, 0.0)
            velocity = sqrt(2.0 * available_enthalpy)
            return throat.density * velocity

        lower_log = log(lower_pressure)
        upper_log = log(upper_pressure)
        optimum = minimize_scalar(
            lambda value: -mass_flux(value),
            bounds=(lower_log, upper_log),
            method="bounded",
            options={"xatol": 1.0e-8},
        )
        candidates = (lower_log, optimum.x, upper_log)
        best_log = max(candidates, key=mass_flux)
        best_pressure = exp(best_log)
        best_flux = mass_flux(best_log)
        mass_flow = (
            self.parameters.discharge_coefficient * effective_area * best_flux
        )
        choked = best_pressure > lower_pressure * 1.001
        return RestrictionFlow(mass_flow, best_pressure, choked, effective_area)


@dataclass(frozen=True, slots=True)
class CheckValveParameters:
    cracking_pressure: float
    fully_open_pressure_difference: float
    cracking_pressure_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if self.cracking_pressure < 0.0:
            raise ValueError("Check-valve cracking pressure cannot be negative")
        if self.fully_open_pressure_difference <= self.cracking_pressure:
            raise ValueError("Full-open pressure difference must exceed cracking pressure")
        if self.cracking_pressure_multiplier <= 0.0:
            raise ValueError("Cracking-pressure multiplier must be positive")


class CheckValve:
    """Pressure-actuated check valve backed by a real-gas restriction."""

    def __init__(
        self,
        parameters: CheckValveParameters,
        restriction: RealGasRestriction,
    ) -> None:
        self.parameters = parameters
        self.restriction = restriction
        self.eos = restriction.eos

    def mass_flow(
        self,
        upstream: ThermoState,
        downstream_pressure: float,
        opening: float = 1.0,
    ) -> RestrictionFlow:
        pressure_difference = upstream.pressure - downstream_pressure
        cracking = (
            self.parameters.cracking_pressure
            * self.parameters.cracking_pressure_multiplier
        )
        if pressure_difference <= cracking:
            return RestrictionFlow(0.0, upstream.pressure, False, 0.0)
        full_open = self.parameters.fully_open_pressure_difference
        pressure_opening = min(
            (pressure_difference - cracking) / (full_open - cracking), 1.0
        )
        return self.restriction.mass_flow(
            upstream, downstream_pressure, opening * pressure_opening
        )


@dataclass(frozen=True, slots=True)
class PressureReliefParameters:
    set_pressure: float
    full_open_pressure: float
    diameter: float
    discharge_coefficient: float = 0.975
    set_pressure_multiplier: float = 1.0
    area_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if self.set_pressure <= 0.0:
            raise ValueError("Relief-valve set pressure must be positive and absolute")
        if self.full_open_pressure <= self.set_pressure:
            raise ValueError("Full-open pressure must exceed set pressure")
        if self.diameter <= 0.0:
            raise ValueError("Relief-valve diameter must be positive")
        if self.set_pressure_multiplier <= 0.0 or self.area_multiplier <= 0.0:
            raise ValueError("Relief-valve fitting multipliers must be positive")


class PressureReliefValve:
    """Proportional pressure relief valve discharging through a real-gas nozzle."""

    def __init__(self, parameters: PressureReliefParameters, eos: HydrogenEOS) -> None:
        self.parameters = parameters
        self.eos = eos
        self.restriction = RealGasRestriction(
            RestrictionParameters(
                diameter=parameters.diameter,
                discharge_coefficient=parameters.discharge_coefficient,
                area_multiplier=parameters.area_multiplier,
            ),
            eos,
        )

    def opening(self, upstream_pressure: float, available: bool = True) -> float:
        if not available:
            return 0.0
        p = self.parameters
        set_pressure = p.set_pressure * p.set_pressure_multiplier
        full_open_pressure = set_pressure + (
            p.full_open_pressure - p.set_pressure
        ) * p.set_pressure_multiplier
        return min(
            max(
                (upstream_pressure - set_pressure)
                / (full_open_pressure - set_pressure),
                0.0,
            ),
            1.0,
        )

    def mass_flow(
        self,
        upstream: ThermoState,
        back_pressure: float,
        available: bool = True,
    ) -> RestrictionFlow:
        return self.restriction.mass_flow(
            upstream,
            back_pressure,
            opening=self.opening(upstream.pressure, available),
        )


@dataclass(frozen=True, slots=True)
class CompressorParameters:
    stages: int
    rated_mass_flow: float
    reference_inlet_density: float
    isentropic_efficiency: float = 0.72
    volumetric_efficiency: float = 0.85
    mechanical_efficiency: float = 0.95
    intercooler_effectiveness: float = 0.85
    maximum_stage_pressure_ratio: float = 4.0
    flow_multiplier: float = 1.0
    efficiency_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if self.stages < 1:
            raise ValueError("Compressor needs at least one stage")
        if self.rated_mass_flow <= 0.0 or self.reference_inlet_density <= 0.0:
            raise ValueError("Compressor rating must be positive")
        efficiencies = (
            self.isentropic_efficiency,
            self.volumetric_efficiency,
            self.mechanical_efficiency,
            self.intercooler_effectiveness,
            self.efficiency_multiplier,
        )
        if any(value <= 0.0 for value in efficiencies):
            raise ValueError("Compressor efficiencies must be positive")
        if self.intercooler_effectiveness > 1.0:
            raise ValueError("Intercooler effectiveness cannot exceed one")


@dataclass(frozen=True, slots=True)
class CompressorResult:
    mass_flow: float
    outlet: ThermoState
    shaft_power: float
    pressure_limited: bool


class MultistageCompressor:
    """Positive-displacement compressor with equal-ratio stages."""

    def __init__(self, parameters: CompressorParameters, eos: HydrogenEOS) -> None:
        self.parameters = parameters
        self.eos = eos

    def evaluate(
        self,
        inlet: ThermoState,
        discharge_pressure: float,
        speed_fraction: float,
        ambient_temperature: float,
    ) -> CompressorResult:
        speed_fraction = min(max(speed_fraction, 0.0), 1.0)
        if speed_fraction == 0.0 or discharge_pressure <= inlet.pressure:
            return CompressorResult(0.0, inlet, 0.0, False)

        overall_ratio = discharge_pressure / inlet.pressure
        stage_ratio = overall_ratio ** (1.0 / self.parameters.stages)
        if stage_ratio > self.parameters.maximum_stage_pressure_ratio:
            return CompressorResult(0.0, inlet, 0.0, True)

        mass_flow = (
            self.parameters.rated_mass_flow
            * speed_fraction
            * self.parameters.volumetric_efficiency
            * self.parameters.flow_multiplier
            * inlet.density
            / self.parameters.reference_inlet_density
        )
        eta_is = min(
            self.parameters.isentropic_efficiency
            * self.parameters.efficiency_multiplier,
            0.999,
        )
        current = inlet
        shaft_power = 0.0

        for stage_index in range(self.parameters.stages):
            stage_pressure = inlet.pressure * stage_ratio ** (stage_index + 1)
            ideal_outlet = self.eos.state_ps(stage_pressure, current.entropy)
            outlet_enthalpy = current.enthalpy + (
                ideal_outlet.enthalpy - current.enthalpy
            ) / eta_is
            actual_outlet = self.eos.state_ph(stage_pressure, outlet_enthalpy)
            shaft_power += (
                mass_flow
                * (actual_outlet.enthalpy - current.enthalpy)
                / self.parameters.mechanical_efficiency
            )

            if stage_index < self.parameters.stages - 1:
                cooled_temperature = ambient_temperature + (
                    actual_outlet.temperature - ambient_temperature
                ) * (1.0 - self.parameters.intercooler_effectiveness)
                current = self.eos.state_pt(stage_pressure, cooled_temperature)
            else:
                current = actual_outlet

        return CompressorResult(mass_flow, current, shaft_power, False)


@dataclass(frozen=True, slots=True)
class PrecoolerParameters:
    nominal_ua: float
    coolant_temperature: float
    ua_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if self.nominal_ua <= 0.0 or self.ua_multiplier <= 0.0:
            raise ValueError("Precooler UA must be positive")
        if self.coolant_temperature <= 0.0:
            raise ValueError("Coolant temperature must be in kelvin")


class FiniteUAPrecooler:
    """Quasi-steady single-stream cooler with an infinite coolant reservoir."""

    def __init__(self, parameters: PrecoolerParameters, eos: HydrogenEOS) -> None:
        self.parameters = parameters
        self.eos = eos

    def outlet(
        self,
        inlet: ThermoState,
        mass_flow: float,
        outlet_pressure: float,
    ) -> ThermoState:
        if mass_flow <= 0.0:
            return inlet
        ua = self.parameters.nominal_ua * self.parameters.ua_multiplier
        capacity_rate = max(mass_flow * inlet.cp, 1.0e-9)
        outlet_temperature = self.parameters.coolant_temperature + (
            inlet.temperature - self.parameters.coolant_temperature
        ) * exp(-ua / capacity_rate)
        return self.eos.state_pt(outlet_pressure, outlet_temperature)


@dataclass(frozen=True, slots=True)
class ValveActuatorParameters:
    opening_time_constant: float
    closing_time_constant: float
    maximum_opening_rate: float = 1.0
    maximum_closing_rate: float = 2.0
    deadband: float = 0.0
    fail_safe_position: float = 0.0
    time_constant_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if self.opening_time_constant <= 0.0 or self.closing_time_constant <= 0.0:
            raise ValueError("Actuator time constants must be positive")
        if self.maximum_opening_rate <= 0.0 or self.maximum_closing_rate <= 0.0:
            raise ValueError("Actuator stroke rates must be positive")
        if not 0.0 <= self.deadband < 1.0:
            raise ValueError("Actuator deadband must be in [0, 1)")
        if not 0.0 <= self.fail_safe_position <= 1.0:
            raise ValueError("Fail-safe position must be in [0, 1]")
        if self.time_constant_multiplier <= 0.0:
            raise ValueError("Time-constant multiplier must be positive")


class ValveActuator:
    """First-order valve-position dynamics with asymmetric stroke limits."""

    def __init__(self, parameters: ValveActuatorParameters) -> None:
        self.parameters = parameters

    def derivative(
        self,
        actual_position: float,
        demanded_position: float,
        available: bool = True,
    ) -> float:
        p = self.parameters
        actual = min(max(actual_position, 0.0), 1.0)
        demanded = (
            min(max(demanded_position, 0.0), 1.0)
            if available
            else p.fail_safe_position
        )
        error = demanded - actual
        if abs(error) <= p.deadband:
            return 0.0

        if error > 0.0:
            time_constant = p.opening_time_constant * p.time_constant_multiplier
            rate = min(error / time_constant, p.maximum_opening_rate)
            return 0.0 if actual >= 1.0 else rate

        time_constant = p.closing_time_constant * p.time_constant_multiplier
        rate = max(error / time_constant, -p.maximum_closing_rate)
        return 0.0 if actual <= 0.0 else rate
