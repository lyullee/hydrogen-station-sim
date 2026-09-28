"""Runtime loading for a site-configured HyRAM+ evaluator."""

from __future__ import annotations

import importlib
import json
import os
from typing import Mapping

from ..thermo import HydrogenEOS
from .hyram_adapter import (
    AmbientCondition,
    HyRAMRiskMonitor,
    IndoorScenario,
    LeakScenario as AdapterLeakScenario,
)
from .live import CallableHyRAMBackend, HyRAMDynamicReleaseRequest


class UnavailableHyRAMBackend:
    """Honest fallback that preserves source terms without inventing consequences."""

    available = False
    name = "HyRAM+ not configured"

    def __init__(self, reason: str = "H2STATION_HYRAM_EVALUATOR is not set") -> None:
        self.reason = reason

    def evaluate_release(
        self,
        request: HyRAMDynamicReleaseRequest,
    ) -> Mapping[str, float | str | bool | None]:
        return {
            "status": "unavailable",
            "reason": self.reason,
            "mass_flow_override_kg_s": request.mass_flow_override_kg_s,
            "cumulative_released_mass_kg": request.cumulative_released_mass_kg,
        }


class LoadedHyRAMBackend(CallableHyRAMBackend):
    available = True

    def __init__(self, evaluator, name: str) -> None:
        super().__init__(evaluator)
        self.name = name


class NativeHyRAMBackend:
    """Direct bridge to the bundled HyRAM+ 6.1 physics API adapter."""

    available = True
    name = "HyRAM+ 6.1 native"

    def __init__(
        self,
        observation_locations: tuple[tuple[float, float, float], ...],
        indoor_scenario: IndoorScenario | None = None,
    ) -> None:
        self.observation_locations = observation_locations
        self.indoor_scenario = indoor_scenario
        self.eos = HydrogenEOS()
        self.monitor = HyRAMRiskMonitor(evaluation_period=1.0e-9)

    @classmethod
    def from_environment(cls) -> "NativeHyRAMBackend":
        locations_data = json.loads(
            os.getenv(
                "H2STATION_HYRAM_LOCATIONS",
                "[[1.0,0.0,1.5],[3.0,0.0,1.5],[5.0,0.0,1.5]]",
            )
        )
        locations = tuple(
            tuple(float(coordinate) for coordinate in location)
            for location in locations_data
        )
        if any(len(location) != 3 for location in locations):
            raise ValueError("Every HyRAM observation location requires x, y, z")
        indoor_data = os.getenv("H2STATION_HYRAM_INDOOR_JSON")
        indoor = IndoorScenario(**json.loads(indoor_data)) if indoor_data else None
        return cls(locations, indoor)

    def evaluate_release(
        self,
        request: HyRAMDynamicReleaseRequest,
    ) -> Mapping[str, float | str | bool | None]:
        release_state = self.eos.state_pt(
            request.source_pressure_pa,
            request.source_temperature_k,
        )
        ambient = AmbientCondition(pressure=request.ambient_pressure_pa)
        leak = AdapterLeakScenario(
            orifice_diameter=request.orifice_diameter_m,
            locations=self.observation_locations,
            discharge_coefficient=request.discharge_coefficient,
            release_angle=request.release_angle_rad,
            calculate_flame=True,
            calculate_overpressure=bool(self.observation_locations),
        )
        result = self.monitor.evaluate(
            request.time_s,
            release_state,
            leak,
            ambient,
            mass_flow_override=request.mass_flow_override_kg_s,
        )
        output: dict[str, float | str | bool | None] = {
            "status": "calculated",
            "maximum_heat_flux_w_m2": max(result.heat_fluxes, default=0.0),
            "maximum_overpressure_pa": max(result.overpressures, default=0.0),
            "maximum_impulse_pa_s": max(result.impulses, default=0.0),
            "visible_flame_length_m": result.visible_flame_length,
            "radiant_fraction": result.radiant_fraction,
            "mass_flow_override_kg_s": result.mass_flow_rate,
        }
        # Report only the sampled extent. Three observation points cannot
        # establish a validated safe boundary beyond the farthest point.
        thermal_points = [
            (float((x*x + y*y) ** .5), float(flux))
            for (x, y, _), flux in zip(self.observation_locations, result.heat_fluxes)
        ]
        blast_points = [
            (float((x*x + y*y) ** .5), float(pressure))
            for (x, y, _), pressure in zip(self.observation_locations, result.overpressures)
        ]
        affected = [distance for distance, value in thermal_points if value >= 5000.0]
        affected += [distance for distance, value in blast_points if value >= 5000.0]
        sampled_max = max((distance for distance, _ in thermal_points + blast_points), default=0.0)
        extent = max(affected, default=0.0)
        output["sampled_effect_radius_m"] = extent
        output["sampled_max_distance_m"] = sampled_max
        output["effect_range_status"] = ("BEYOND_SAMPLED_POINTS" if extent >= sampled_max and extent > 0
            else "WITHIN_SAMPLED_POINTS" if extent > 0 else "BELOW_THRESHOLDS_AT_SAMPLES")
        output["thermal_threshold_w_m2"] = 5000.0
        output["overpressure_threshold_pa"] = 5000.0
        if request.indoor:
            if self.indoor_scenario is None:
                output["indoor_status"] = "enclosure-not-configured"
            else:
                elapsed = max(request.duration_s, 1.0e-6)
                accumulation = self.monitor.analyze_indoor(
                    release_state,
                    leak,
                    self.indoor_scenario,
                    times=(elapsed,),
                    ambient=ambient,
                    maximum_time=elapsed + 1.0,
                )
                concentration_fraction = (
                    max(accumulation.concentrations_percent, default=0.0) / 100.0
                )
                output["maximum_concentration"] = concentration_fraction
                output["maximum_indoor_overpressure_pa"] = (
                    accumulation.maximum_overpressure
                )
                output["indoor_status"] = "calculated"
        return output


def load_hyram_backend(specification: str | None = None):
    """Load ``module:function`` from the argument or H2STATION_HYRAM_EVALUATOR."""

    specification = specification or os.getenv("H2STATION_HYRAM_EVALUATOR")
    try:
        if specification:
            module_name, function_name = specification.split(":", 1)
            module = importlib.import_module(module_name)
            evaluator = getattr(module, function_name)
            if not callable(evaluator):
                raise TypeError("Configured HyRAM evaluator is not callable")
            return LoadedHyRAMBackend(evaluator, specification)
        importlib.import_module("hyram")
        return NativeHyRAMBackend.from_environment()
    except Exception as exc:
        source = specification or "native hyram package"
        return UnavailableHyRAMBackend(
            f"Cannot load {source}: {type(exc).__name__}: {exc}"
        )
