"""Coordinate active process releases with sampled HyRAM calculations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..network import ConnectionFlow
from ..thermo import ThermoState
from .hyram_adapter import (
    AmbientCondition,
    HyRAMRiskMonitor,
    IndoorAccumulationResult,
    IndoorScenario,
    LeakScenario,
    RiskSnapshot,
)


@dataclass(frozen=True, slots=True)
class ReleaseSource:
    name: str
    state_node: str
    leak_scenario: LeakScenario
    connection_name: str | None = None
    indoor_scenario: IndoorScenario | None = None
    evaluate_outdoor_consequences: bool = True
    minimum_active_mass_flow: float = 1.0e-8


@dataclass(frozen=True, slots=True)
class ReleaseAssessment:
    source: str
    actual_mass_flow: float | None
    consequence: RiskSnapshot | None
    indoor_accumulation: IndoorAccumulationResult | None
    accumulation_mode: str | None


@dataclass(frozen=True, slots=True)
class DynamicRiskFrame:
    simulation_time: float
    releases: tuple[ReleaseAssessment, ...]

    @property
    def maximum_heat_flux(self) -> float:
        values = [
            value
            for release in self.releases
            if release.consequence is not None
            for value in release.consequence.heat_fluxes
        ]
        return max(values, default=0.0)

    @property
    def maximum_overpressure(self) -> float:
        outdoor = [
            value
            for release in self.releases
            if release.consequence is not None
            for value in release.consequence.overpressures
        ]
        indoor = [
            release.indoor_accumulation.maximum_overpressure
            for release in self.releases
            if release.indoor_accumulation is not None
        ]
        return max((*outdoor, *indoor), default=0.0)

    @property
    def maximum_hydrogen_concentration_percent(self) -> float:
        values = [
            value
            for release in self.releases
            if release.indoor_accumulation is not None
            for value in release.indoor_accumulation.concentrations_percent
        ]
        return max(values, default=0.0)


@dataclass(frozen=True, slots=True)
class ConcentrationTripRule:
    release_source: str
    threshold_percent: float
    reason: str

    def __post_init__(self) -> None:
        if not 0.0 < self.threshold_percent <= 100.0:
            raise ValueError("Concentration threshold must be in (0, 100]")


class RiskToSafetyBridge:
    """Map configured HyRAM concentration results to external ESD reasons."""

    def __init__(self, rules: tuple[ConcentrationTripRule, ...]) -> None:
        self.rules = rules

    def external_trip_reasons(self, frame: DynamicRiskFrame) -> tuple[str, ...]:
        releases = {release.source: release for release in frame.releases}
        reasons: list[str] = []
        for rule in self.rules:
            release = releases.get(rule.release_source)
            if release is None or release.indoor_accumulation is None:
                continue
            values = release.indoor_accumulation.concentrations_percent
            if values and max(values) >= rule.threshold_percent:
                reasons.append(rule.reason)
        return tuple(dict.fromkeys(reasons))


@dataclass(slots=True)
class _IndoorSession:
    start_time: float
    initial_release_state: ThermoState


class DynamicRiskCoordinator:
    """Schedule outdoor consequences and indoor accumulation for active releases."""

    def __init__(
        self,
        sources: tuple[ReleaseSource, ...],
        consequence_period: float = 1.0,
        indoor_period: float = 2.0,
        ambient: AmbientCondition = AmbientCondition(),
    ) -> None:
        if indoor_period <= 0.0:
            raise ValueError("Indoor evaluation period must be positive")
        names = [source.name for source in sources]
        if len(names) != len(set(names)):
            raise ValueError("Release source names must be unique")
        self.sources = sources
        self.ambient = ambient
        self.indoor_period = indoor_period
        self.monitors = {
            source.name: HyRAMRiskMonitor(consequence_period) for source in sources
        }
        self._last_indoor_time = {source.name: float("-inf") for source in sources}
        self._indoor_sessions: dict[str, _IndoorSession] = {}

    def evaluate_if_due(
        self,
        simulation_time: float,
        states: Mapping[str, ThermoState],
        connection_flows: tuple[ConnectionFlow, ...] = (),
        active_release_names: frozenset[str] = frozenset(),
        mass_flow_overrides: Mapping[str, float] | None = None,
    ) -> DynamicRiskFrame:
        flow_by_name = {flow.name: flow.mass_flow for flow in connection_flows}
        overrides = {} if mass_flow_overrides is None else mass_flow_overrides
        assessments: list[ReleaseAssessment] = []

        for source in self.sources:
            actual_mass_flow = overrides.get(source.name)
            if actual_mass_flow is None and source.connection_name is not None:
                actual_mass_flow = flow_by_name.get(source.connection_name, 0.0)
            active = (
                source.name in active_release_names
                if source.connection_name is None and actual_mass_flow is None
                else actual_mass_flow is not None
                and actual_mass_flow >= source.minimum_active_mass_flow
            )
            if not active:
                self._indoor_sessions.pop(source.name, None)
                continue

            release_state = states[source.state_node]
            consequence = None
            if source.evaluate_outdoor_consequences:
                consequence = self.monitors[source.name].evaluate_if_due(
                    simulation_time,
                    release_state,
                    source.leak_scenario,
                    self.ambient,
                    mass_flow_override=actual_mass_flow,
                )

            indoor = None
            accumulation_mode = None
            if (
                source.indoor_scenario is not None
                and simulation_time - self._last_indoor_time[source.name]
                >= self.indoor_period
            ):
                session = self._indoor_sessions.get(source.name)
                if session is None:
                    session = _IndoorSession(simulation_time, release_state)
                    self._indoor_sessions[source.name] = session
                elapsed = max(simulation_time - session.start_time, 0.0)
                indoor = self.monitors[source.name].analyze_indoor(
                    session.initial_release_state,
                    source.leak_scenario,
                    source.indoor_scenario,
                    times=(elapsed,),
                    ambient=self.ambient,
                    maximum_time=max(
                        elapsed + self.indoor_period, self.indoor_period
                    ),
                )
                self._last_indoor_time[source.name] = simulation_time
                accumulation_mode = (
                    "transient_from_release_onset"
                    if actual_mass_flow is None
                    else "orifice_model_not_actual_flow_override"
                )

            assessments.append(
                ReleaseAssessment(
                    source.name,
                    actual_mass_flow,
                    consequence,
                    indoor,
                    accumulation_mode,
                )
            )
        return DynamicRiskFrame(simulation_time, tuple(assessments))
