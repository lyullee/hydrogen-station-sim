"""HyRAM+ 6.1 interface for sampled dynamic consequence evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

import numpy as np

from ..thermo import ThermoState


class HyRAMNotInstalledError(ImportError):
    """Raised when the optional HyRAM+ package is unavailable."""


@dataclass(frozen=True, slots=True)
class AmbientCondition:
    temperature: float = 298.15
    pressure: float = 101_325.0
    relative_humidity: float = 0.50


@dataclass(frozen=True, slots=True)
class LeakScenario:
    orifice_diameter: float
    locations: tuple[tuple[float, float, float], ...]
    discharge_coefficient: float = 1.0
    release_angle: float = 0.0
    nozzle_model: str = "yuce"
    overpressure_method: str = "bst"
    bst_flame_speed: float = 0.35
    tnt_factor: float = 0.03
    calculate_flame: bool = True
    calculate_overpressure: bool = True


@dataclass(frozen=True, slots=True)
class IndoorScenario:
    source_volume: float
    release_height: float
    enclosure_height: float
    floor_ceiling_area: float
    ceiling_vent_area: float
    ceiling_vent_height: float
    floor_vent_area: float
    floor_vent_height: float
    ceiling_vent_coefficient: float = 1.0
    floor_vent_coefficient: float = 1.0
    forced_ventilation_rate: float = 0.0
    distance_to_wall: float = float("inf")
    steady_release: bool = False


@dataclass(frozen=True, slots=True)
class IndoorAccumulationResult:
    times: tuple[float, ...]
    pressures: tuple[float, ...]
    layer_depths: tuple[float, ...]
    concentrations_percent: tuple[float, ...]
    mass_flow_rates: tuple[float, ...]
    maximum_overpressure: float
    time_of_maximum_overpressure: float


@dataclass(frozen=True, slots=True)
class RiskSnapshot:
    simulation_time: float
    release_pressure: float
    release_temperature: float
    mass_flow_rate: float
    heat_fluxes: tuple[float, ...]
    overpressures: tuple[float, ...]
    impulses: tuple[float, ...]
    visible_flame_length: float | None
    radiant_fraction: float | None


def _as_float_tuple(values: Any) -> tuple[float, ...]:
    if values is None:
        return ()
    return tuple(float(value) for value in np.asarray(values).reshape(-1))


class HyRAMRiskMonitor:
    """Runs HyRAM consequence models no faster than a configured sample period."""

    def __init__(self, evaluation_period: float = 1.0) -> None:
        if evaluation_period <= 0.0:
            raise ValueError("HyRAM evaluation period must be positive")
        self.evaluation_period = evaluation_period
        self._last_evaluation_time = float("-inf")
        self._last_snapshot: RiskSnapshot | None = None

    @staticmethod
    def _physics_api() -> Any:
        try:
            return import_module("hyram.phys.api")
        except ImportError as exc:
            raise HyRAMNotInstalledError(
                "Install the optional risk dependencies with: pip install -e '.[risk]'"
            ) from exc

    def evaluate_if_due(
        self,
        simulation_time: float,
        release_state: ThermoState,
        scenario: LeakScenario,
        ambient: AmbientCondition = AmbientCondition(),
        mass_flow_override: float | None = None,
        force: bool = False,
    ) -> RiskSnapshot | None:
        if (
            not force
            and simulation_time - self._last_evaluation_time < self.evaluation_period
        ):
            return None
        snapshot = self.evaluate(
            simulation_time,
            release_state,
            scenario,
            ambient,
            mass_flow_override=mass_flow_override,
        )
        self._last_evaluation_time = simulation_time
        self._last_snapshot = snapshot
        return snapshot

    def evaluate(
        self,
        simulation_time: float,
        release_state: ThermoState,
        scenario: LeakScenario,
        ambient: AmbientCondition = AmbientCondition(),
        mass_flow_override: float | None = None,
    ) -> RiskSnapshot:
        api = self._physics_api()
        ambient_fluid = api.create_fluid(
            "air", temp=ambient.temperature, pres=ambient.pressure
        )
        release_fluid = api.create_fluid(
            "H2", temp=release_state.temperature, pres=release_state.pressure
        )
        if mass_flow_override is None:
            mass_flow_result = api.compute_mass_flow(
                release_fluid,
                scenario.orifice_diameter,
                amb_pres=ambient.pressure,
                is_steady=True,
                dis_coeff=scenario.discharge_coefficient,
                create_plot=False,
            )
            mass_flow_rate = float(
                np.asarray(mass_flow_result["rates"]).reshape(-1)[0]
            )
        else:
            mass_flow_rate = max(float(mass_flow_override), 0.0)

        heat_fluxes: tuple[float, ...] = ()
        visible_flame_length: float | None = None
        radiant_fraction: float | None = None
        if scenario.calculate_flame:
            flame_result = api.jet_flame_analysis(
                ambient_fluid,
                release_fluid,
                scenario.orifice_diameter,
                mass_flow=mass_flow_rate,
                dis_coeff=scenario.discharge_coefficient,
                rel_angle=scenario.release_angle,
                nozzle_key=scenario.nozzle_model,
                rel_humid=ambient.relative_humidity,
                create_temp_plot=False,
                analyze_flux=bool(scenario.locations),
                create_flux_plot=False,
                flux_coordinates=list(scenario.locations),
            )
            heat_fluxes = _as_float_tuple(flame_result[2])
            visible_flame_length = float(flame_result[5])
            radiant_fraction = float(flame_result[6])

        overpressures: tuple[float, ...] = ()
        impulses: tuple[float, ...] = ()
        if scenario.calculate_overpressure and scenario.locations:
            overpressure_result = api.compute_overpressure(
                scenario.overpressure_method,
                list(scenario.locations),
                ambient_fluid,
                release_fluid,
                scenario.orifice_diameter,
                mass_flow=mass_flow_rate,
                release_angle=scenario.release_angle,
                discharge_coefficient=scenario.discharge_coefficient,
                nozzle_model=scenario.nozzle_model,
                bst_flame_speed=scenario.bst_flame_speed,
                tnt_factor=scenario.tnt_factor,
                create_overpressure_plot=False,
                create_impulse_plot=False,
            )
            overpressures = _as_float_tuple(overpressure_result["overpressures"])
            impulses = _as_float_tuple(overpressure_result["impulses"])

        return RiskSnapshot(
            simulation_time=simulation_time,
            release_pressure=release_state.pressure,
            release_temperature=release_state.temperature,
            mass_flow_rate=mass_flow_rate,
            heat_fluxes=heat_fluxes,
            overpressures=overpressures,
            impulses=impulses,
            visible_flame_length=visible_flame_length,
            radiant_fraction=radiant_fraction,
        )

    def analyze_indoor(
        self,
        release_state: ThermoState,
        leak: LeakScenario,
        enclosure: IndoorScenario,
        times: tuple[float, ...],
        ambient: AmbientCondition = AmbientCondition(),
        maximum_time: float | None = None,
    ) -> IndoorAccumulationResult:
        if not times:
            raise ValueError("At least one indoor accumulation time is required")
        api = self._physics_api()
        ambient_fluid = api.create_fluid(
            "air", temp=ambient.temperature, pres=ambient.pressure
        )
        release_fluid = api.create_fluid(
            "H2", temp=release_state.temperature, pres=release_state.pressure
        )
        result = api.analyze_accumulation(
            ambient_fluid,
            release_fluid,
            tank_volume=enclosure.source_volume,
            orif_diam=leak.orifice_diameter,
            rel_height=enclosure.release_height,
            enclos_height=enclosure.enclosure_height,
            floor_ceil_area=enclosure.floor_ceiling_area,
            ceil_vent_xarea=enclosure.ceiling_vent_area,
            ceil_vent_height=enclosure.ceiling_vent_height,
            floor_vent_xarea=enclosure.floor_vent_area,
            floor_vent_height=enclosure.floor_vent_height,
            times=np.asarray(times, dtype=float),
            orif_dis_coeff=leak.discharge_coefficient,
            ceil_vent_coeff=enclosure.ceiling_vent_coefficient,
            floor_vent_coeff=enclosure.floor_vent_coefficient,
            vol_flow_rate=enclosure.forced_ventilation_rate,
            dist_rel_to_wall=enclosure.distance_to_wall,
            tmax=maximum_time,
            rel_angle=leak.release_angle,
            nozzle_key=leak.nozzle_model,
            is_steady=enclosure.steady_release,
            create_plots=False,
        )
        return IndoorAccumulationResult(
            times=tuple(float(value) for value in times),
            pressures=_as_float_tuple(result["pressures_per_time"]),
            layer_depths=_as_float_tuple(result["depths"]),
            concentrations_percent=_as_float_tuple(result["concentrations"]),
            mass_flow_rates=_as_float_tuple(result["mass_flow_rates"]),
            maximum_overpressure=float(result["overpressure"]),
            time_of_maximum_overpressure=float(result["time_of_overp"]),
        )

    @staticmethod
    def conduct_qra(**parameters: Any) -> dict[str, Any]:
        """Pass a reviewed design-level input set to HyRAM's QRA entry point."""
        try:
            analysis = import_module("hyram.qra.analysis")
        except ImportError as exc:
            raise HyRAMNotInstalledError(
                "Install the optional risk dependencies with: pip install -e '.[risk]'"
            ) from exc
        return analysis.conduct_analysis(**parameters)

    @property
    def last_snapshot(self) -> RiskSnapshot | None:
        return self._last_snapshot
