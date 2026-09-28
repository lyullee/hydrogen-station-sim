"""Dynamic release source terms and a rate-limited HyRAM consequence bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

import numpy as np

from ..dispenser import IsentropicRealGasRestriction, RestrictionParameters


@dataclass(frozen=True)
class LeakScenario:
    release_id: str
    component_id: str
    location: str
    start_time_s: float
    orifice_diameter_m: float
    discharge_coefficient: float = 0.8
    release_angle_rad: float = 0.0
    release_height_m: float = 1.0
    indoor: bool = False
    annual_frequency_per_year: float | None = None
    immediate_ignition_probability: float | None = None
    delayed_ignition_probability: float | None = None

    def __post_init__(self) -> None:
        if not self.release_id or not self.component_id or not self.location:
            raise ValueError("Release, component, and location identifiers are required")
        if self.start_time_s < 0.0 or self.orifice_diameter_m <= 0.0:
            raise ValueError("Release start time and orifice diameter are invalid")
        if not 0.0 < self.discharge_coefficient <= 1.0:
            raise ValueError("discharge_coefficient must be in (0, 1]")
        probabilities = (
            self.immediate_ignition_probability,
            self.delayed_ignition_probability,
        )
        if any(value is not None and not 0.0 <= value <= 1.0 for value in probabilities):
            raise ValueError("Ignition probabilities must be in [0, 1]")
        if self.annual_frequency_per_year is not None and self.annual_frequency_per_year < 0.0:
            raise ValueError("Annual frequency cannot be negative")


@dataclass(frozen=True)
class LeakSourceState:
    pressure_pa: float
    temperature_k: float
    ambient_pressure_pa: float = 101325.0


@dataclass(frozen=True)
class HyRAMDynamicReleaseRequest:
    release_id: str
    component_id: str
    location: str
    time_s: float
    duration_s: float
    source_pressure_pa: float
    source_temperature_k: float
    ambient_pressure_pa: float
    orifice_diameter_m: float
    discharge_coefficient: float
    mass_flow_override_kg_s: float
    cumulative_released_mass_kg: float
    release_angle_rad: float
    release_height_m: float
    indoor: bool
    annual_frequency_per_year: float | None
    immediate_ignition_probability: float | None
    delayed_ignition_probability: float | None


class HyRAMConsequenceBackend(Protocol):
    """Interface implemented by the local HyRAM+ 6.1 adapter/coordinator."""

    def evaluate_release(
        self,
        request: HyRAMDynamicReleaseRequest,
    ) -> Mapping[str, float | str | bool | None]: ...


class CallableHyRAMBackend:
    """Bind an existing HyRAM adapter/coordinator call to the runtime contract."""

    def __init__(
        self,
        evaluator: Callable[
            [HyRAMDynamicReleaseRequest],
            Mapping[str, float | str | bool | None],
        ],
    ) -> None:
        self.evaluator = evaluator

    def evaluate_release(
        self,
        request: HyRAMDynamicReleaseRequest,
    ) -> Mapping[str, float | str | bool | None]:
        return self.evaluator(request)


@dataclass(frozen=True)
class DynamicRiskSnapshot:
    time_s: float
    release_id: str
    mass_flow_kg_s: float
    cumulative_released_mass_kg: float
    consequence: Mapping[str, float | str | bool | None]
    annualized_risk: float | None
    consequence_updated: bool


class DynamicLeakModel:
    """Calculate time-varying leak flow with the same real-gas restriction model."""

    def __init__(self, fluid: str = "Hydrogen") -> None:
        self.fluid = fluid

    def mass_flow_kg_s(
        self,
        scenario: LeakScenario,
        source: LeakSourceState,
    ) -> float:
        area = 0.25 * np.pi * scenario.orifice_diameter_m ** 2
        restriction = IsentropicRealGasRestriction(
            RestrictionParameters(
                flow_area_m2=area,
                discharge_coefficient=scenario.discharge_coefficient,
                minimum_pressure_pa=max(1.0, source.ambient_pressure_pa),
            ),
            self.fluid,
        )
        return restriction.mass_flow_kg_s(
            source.pressure_pa,
            source.temperature_k,
            source.ambient_pressure_pa,
        )


class DynamicRiskMonitor:
    """Integrate released mass and rate-limit computationally heavier HyRAM calls."""

    def __init__(
        self,
        backend: HyRAMConsequenceBackend,
        update_period_s: float = 1.0,
        fluid: str = "Hydrogen",
    ) -> None:
        if update_period_s <= 0.0:
            raise ValueError("update_period_s must be positive")
        self.backend = backend
        self.update_period_s = update_period_s
        self.leak_model = DynamicLeakModel(fluid)
        self.reset()

    def reset(self) -> None:
        self._released_mass_kg: dict[str, float] = {}
        self._last_update_s: dict[str, float] = {}
        self._last_consequence: dict[
            str, Mapping[str, float | str | bool | None]
        ] = {}

    def update(
        self,
        time_s: float,
        sample_period_s: float,
        active_releases: Mapping[LeakScenario, LeakSourceState],
    ) -> tuple[DynamicRiskSnapshot, ...]:
        if sample_period_s <= 0.0:
            raise ValueError("sample_period_s must be positive")
        snapshots: list[DynamicRiskSnapshot] = []
        for scenario, source in active_releases.items():
            mass_flow = self.leak_model.mass_flow_kg_s(scenario, source)
            cumulative_mass = self._released_mass_kg.get(scenario.release_id, 0.0)
            cumulative_mass += mass_flow * sample_period_s
            self._released_mass_kg[scenario.release_id] = cumulative_mass

            last_update = self._last_update_s.get(scenario.release_id)
            should_update = (
                last_update is None
                or time_s - last_update >= self.update_period_s
            )
            if should_update:
                request = HyRAMDynamicReleaseRequest(
                    release_id=scenario.release_id,
                    component_id=scenario.component_id,
                    location=scenario.location,
                    time_s=time_s,
                    duration_s=max(0.0, time_s - scenario.start_time_s),
                    source_pressure_pa=source.pressure_pa,
                    source_temperature_k=source.temperature_k,
                    ambient_pressure_pa=source.ambient_pressure_pa,
                    orifice_diameter_m=scenario.orifice_diameter_m,
                    discharge_coefficient=scenario.discharge_coefficient,
                    mass_flow_override_kg_s=mass_flow,
                    cumulative_released_mass_kg=cumulative_mass,
                    release_angle_rad=scenario.release_angle_rad,
                    release_height_m=scenario.release_height_m,
                    indoor=scenario.indoor,
                    annual_frequency_per_year=scenario.annual_frequency_per_year,
                    immediate_ignition_probability=(
                        scenario.immediate_ignition_probability
                    ),
                    delayed_ignition_probability=scenario.delayed_ignition_probability,
                )
                consequence = dict(self.backend.evaluate_release(request))
                self._last_consequence[scenario.release_id] = consequence
                self._last_update_s[scenario.release_id] = time_s
            else:
                consequence = self._last_consequence.get(scenario.release_id, {})

            annualized_risk = self._annualized_risk(scenario, consequence)
            snapshots.append(
                DynamicRiskSnapshot(
                    time_s=time_s,
                    release_id=scenario.release_id,
                    mass_flow_kg_s=mass_flow,
                    cumulative_released_mass_kg=cumulative_mass,
                    consequence=consequence,
                    annualized_risk=annualized_risk,
                    consequence_updated=should_update,
                )
            )
        return tuple(snapshots)

    @staticmethod
    def _annualized_risk(
        scenario: LeakScenario,
        consequence: Mapping[str, float | str | bool | None],
    ) -> float | None:
        harm_probability = consequence.get("harm_probability")
        if (
            scenario.annual_frequency_per_year is None
            or not isinstance(harm_probability, (int, float))
        ):
            return None
        ignition_probability = sum(
            probability or 0.0
            for probability in (
                scenario.immediate_ignition_probability,
                scenario.delayed_ignition_probability,
            )
        )
        ignition_probability = min(1.0, ignition_probability)
        return (
            scenario.annual_frequency_per_year
            * ignition_probability
            * float(harm_probability)
        )
