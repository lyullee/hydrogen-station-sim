"""Finite-volume line-pack model for station piping and dispenser hoses."""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Mapping

from fluids.compressible import isothermal_gas
from fluids.friction import friction_factor

from .components import (
    LumpedTank,
    RealGasRestriction,
    RestrictionFlow,
    RestrictionParameters,
    TankInventory,
    TankParameters,
)
from .network import RestrictionConnection
from .thermo import HydrogenEOS, ThermoState


@dataclass(frozen=True, slots=True)
class PipeParameters:
    length: float
    inner_diameter: float
    outer_diameter: float
    absolute_roughness: float
    segments: int
    wall_density: float
    wall_specific_heat: float
    internal_htc: float
    external_htc: float
    minor_loss_coefficient: float = 0.0
    roughness_multiplier: float = 1.0
    friction_multiplier: float = 1.0
    internal_htc_multiplier: float = 1.0
    external_htc_multiplier: float = 1.0
    flow_multiplier: float = 1.0

    def __post_init__(self) -> None:
        positive = (
            self.length,
            self.inner_diameter,
            self.outer_diameter,
            self.wall_density,
            self.wall_specific_heat,
            self.internal_htc,
            self.external_htc,
            self.roughness_multiplier,
            self.friction_multiplier,
            self.internal_htc_multiplier,
            self.external_htc_multiplier,
            self.flow_multiplier,
        )
        if any(value <= 0.0 for value in positive):
            raise ValueError("Pipe geometry and physical parameters must be positive")
        if self.outer_diameter <= self.inner_diameter:
            raise ValueError("Pipe outer diameter must exceed inner diameter")
        if self.absolute_roughness < 0.0 or self.minor_loss_coefficient < 0.0:
            raise ValueError("Pipe roughness and minor-loss coefficient cannot be negative")
        if self.segments < 1:
            raise ValueError("Pipe needs at least one finite-volume segment")


@dataclass(frozen=True, slots=True)
class PipeFlowParameters:
    length: float
    diameter: float
    absolute_roughness: float
    minor_loss_coefficient: float = 0.0
    roughness_multiplier: float = 1.0
    friction_multiplier: float = 1.0
    flow_multiplier: float = 1.0
    iteration_count: int = 8
    minimum_pressure: float = 1_000.0


class CompressiblePipeFlow(RealGasRestriction):
    """Quasi-steady compressible Darcy flow between dynamic line-pack cells."""

    def __init__(self, parameters: PipeFlowParameters, eos: HydrogenEOS) -> None:
        self.pipe_parameters = parameters
        self.eos = eos
        self._inviscid_cap = RealGasRestriction(
            RestrictionParameters(
                diameter=parameters.diameter,
                discharge_coefficient=1.0,
                minimum_pressure=parameters.minimum_pressure,
            ),
            eos,
        )

    def mass_flow(
        self,
        upstream: ThermoState,
        downstream_pressure: float,
        opening: float = 1.0,
    ) -> RestrictionFlow:
        p = self.pipe_parameters
        opening = min(max(opening, 0.0), 1.0)
        area = pi * p.diameter**2 / 4.0
        effective_area = area * opening
        if opening == 0.0 or downstream_pressure >= upstream.pressure:
            return RestrictionFlow(0.0, upstream.pressure, False, effective_area)

        downstream_pressure = max(downstream_pressure, p.minimum_pressure)
        inviscid = self._inviscid_cap.mass_flow(
            upstream, downstream_pressure, opening=1.0
        )
        average_pressure = 0.5 * (upstream.pressure + downstream_pressure)
        average_state = self.eos.state_pt(average_pressure, upstream.temperature)
        mass_flow = max(inviscid.mass_flow * 0.5, 1.0e-12)
        relative_roughness = (
            p.absolute_roughness * p.roughness_multiplier / p.diameter
        )

        for _ in range(p.iteration_count):
            reynolds = max(
                4.0 * mass_flow / (pi * p.diameter * average_state.viscosity),
                1.0,
            )
            darcy_factor = friction_factor(Re=reynolds, eD=relative_roughness)
            effective_factor = p.friction_multiplier * darcy_factor
            if p.minor_loss_coefficient > 0.0:
                effective_factor += p.minor_loss_coefficient * p.diameter / p.length
            try:
                calculated = isothermal_gas(
                    rho=average_state.density,
                    fd=effective_factor,
                    P1=upstream.pressure,
                    P2=downstream_pressure,
                    L=p.length,
                    D=p.diameter,
                )
            except ValueError:
                calculated = inviscid.mass_flow
            bounded = min(float(calculated), inviscid.mass_flow)
            mass_flow = 0.5 * mass_flow + 0.5 * bounded

        mass_flow *= opening * p.flow_multiplier
        mass_flow = min(mass_flow, inviscid.mass_flow * opening)
        choked = mass_flow >= inviscid.mass_flow * opening * 0.999
        return RestrictionFlow(
            mass_flow=mass_flow,
            throat_pressure=inviscid.throat_pressure,
            choked=choked,
            effective_area=effective_area,
        )


@dataclass(frozen=True, slots=True)
class PipeAssembly:
    tanks: Mapping[str, LumpedTank]
    initial_inventories: Mapping[str, TankInventory]
    connections: tuple[RestrictionConnection, ...]


class FiniteVolumePipe:
    """Factory that expands one physical line into dynamic cells and flow faces."""

    def __init__(self, parameters: PipeParameters, eos: HydrogenEOS) -> None:
        self.parameters = parameters
        self.eos = eos

    def build(
        self,
        name: str,
        source: str,
        target: str,
        initial_pressure: float,
        initial_temperature: float,
        initial_wall_temperature: float | None = None,
    ) -> PipeAssembly:
        p = self.parameters
        cell_length = p.length / p.segments
        gas_volume = pi * p.inner_diameter**2 * cell_length / 4.0
        internal_area = pi * p.inner_diameter * cell_length
        external_area = pi * p.outer_diameter * cell_length
        wall_volume = (
            pi
            * (p.outer_diameter**2 - p.inner_diameter**2)
            * cell_length
            / 4.0
        )
        wall_heat_capacity = wall_volume * p.wall_density * p.wall_specific_heat

        tanks: dict[str, LumpedTank] = {}
        inventories: dict[str, TankInventory] = {}
        cell_names: list[str] = []
        for index in range(p.segments):
            cell_name = f"{name}.cell_{index + 1}"
            model = LumpedTank(
                TankParameters(
                    volume=gas_volume,
                    gas_wall_area=internal_area,
                    wall_ambient_area=external_area,
                    wall_heat_capacity=wall_heat_capacity,
                    gas_wall_htc=p.internal_htc,
                    wall_ambient_htc=p.external_htc,
                    gas_wall_htc_multiplier=p.internal_htc_multiplier,
                    ambient_htc_multiplier=p.external_htc_multiplier,
                ),
                self.eos,
            )
            tanks[cell_name] = model
            inventories[cell_name] = model.initial_inventory(
                initial_pressure,
                initial_temperature,
                initial_wall_temperature,
            )
            cell_names.append(cell_name)

        nodes = [source, *cell_names, target]
        face_lengths = [cell_length * 0.5]
        face_lengths.extend([cell_length] * max(p.segments - 1, 0))
        face_lengths.append(cell_length * 0.5)
        minor_loss_per_face = p.minor_loss_coefficient / (p.segments + 1)
        connections: list[RestrictionConnection] = []

        for index, (left, right, face_length) in enumerate(
            zip(nodes[:-1], nodes[1:], face_lengths)
        ):
            flow_model = CompressiblePipeFlow(
                PipeFlowParameters(
                    length=face_length,
                    diameter=p.inner_diameter,
                    absolute_roughness=p.absolute_roughness,
                    minor_loss_coefficient=minor_loss_per_face,
                    roughness_multiplier=p.roughness_multiplier,
                    friction_multiplier=p.friction_multiplier,
                    flow_multiplier=p.flow_multiplier,
                ),
                self.eos,
            )
            connections.append(
                RestrictionConnection(
                    name=f"{name}.face_{index + 1}",
                    source=left,
                    target=right,
                    restriction=flow_model,
                    allow_reverse=True,
                    default_opening=1.0,
                )
            )

        return PipeAssembly(tanks, inventories, tuple(connections))
