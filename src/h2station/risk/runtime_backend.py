"""Runtime loading for a site-configured HyRAM+ evaluator."""

from __future__ import annotations

import importlib
import json
import math
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


# The default is a one-direction screening transect at 1.5 m elevation,
# not a site-wide safety boundary. Keep near-field spacing fine enough that
# a threshold crossed between 1 m and 3 m is not reported simply as 1 m.
DEFAULT_OBSERVATION_DISTANCES_M = tuple(step / 2 for step in range(1, 21)) + (
    12.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0,
)
DEFAULT_OBSERVATION_LOCATIONS = tuple(
    (distance, 0.0, 1.5) for distance in DEFAULT_OBSERVATION_DISTANCES_M
)


def consequence_risk_summary(consequence: Mapping[str, float | str | bool | None]) -> dict[str, float | str]:
    """Return a transparent screening index for display beside consequences.

    This is deliberately a consequence index, not annual individual risk: a
    quantitative frequency is unavailable for sensor-based hypothetical leaks.
    """
    heat = max(0.0, float(consequence.get("maximum_heat_flux_w_m2") or 0.0))
    blast = max(0.0, float(consequence.get("maximum_overpressure_pa") or 0.0))
    radius = max(
        0.0,
        float(consequence.get("sampled_effect_radius_m") or 0.0),
        float(consequence.get("flammable_plume_streamline_distance_m") or 0.0),
    )
    flow = max(0.0, float(consequence.get("mass_flow_override_kg_s") or 0.0) * 1000.0)
    threshold_ratio = max(heat / 5000.0, blast / 5000.0)
    # Fixed scales let values remain comparable between different station runs.
    score = min(100.0, 12.0 * math.log10(1.0 + flow)
                + 30.0 * min(2.0, threshold_ratio) / 2.0
                + 25.0 * min(2.0, radius / 10.0) / 2.0)
    level = ("매우 높음" if score >= 80 else "높음" if score >= 60
             else "주의" if score >= 35 else "낮음" if score >= 15 else "매우 낮음")
    return {"risk_score": round(score, 1), "risk_level": level,
            "risk_basis": "CONSEQUENCE_SCREENING_NO_FREQUENCY"}


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
        configured = os.getenv("H2STATION_HYRAM_LOCATIONS")
        locations_data = json.loads(configured) if configured else DEFAULT_OBSERVATION_LOCATIONS
        locations = tuple(
            tuple(float(coordinate) for coordinate in location)
            for location in locations_data
        )
        if not locations or any(len(location) != 3 or not all(math.isfinite(value) for value in location)
                                for location in locations):
            raise ValueError("HyRAM observation locations require finite x, y, z coordinates")
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
            "requested_mass_flow_override_kg_s": result.requested_mass_flow_rate,
            "modeled_consequence_mass_flow_kg_s": result.mass_flow_rate,
            # Compatibility field retained for existing UI/API consumers. It
            # now states the mass flow actually used by HyRAM.
            "mass_flow_override_kg_s": result.mass_flow_rate,
            "flammable_contour_volume_fraction": 0.04,
            "flammable_plume_streamline_distance_m": result.flammable_streamline_distance,
            "flammable_plume_x_extent_m": result.flammable_x_extent,
            "flammable_plume_y_extent_m": result.flammable_y_extent,
            "release_angle_rad": request.release_angle_rad,
            "observation_locations_m": self.observation_locations,
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
        distances = sorted({distance for distance, _ in thermal_points + blast_points})
        next_sample = next((distance for distance in distances if distance > extent), None) if extent > 0 else None
        output["sampled_effect_radius_m"] = extent
        output["sampled_max_distance_m"] = sampled_max
        output["sampled_next_distance_m"] = next_sample
        output["observation_point_count"] = len(self.observation_locations)
        output["effect_range_status"] = ("BEYOND_SAMPLED_POINTS" if extent >= sampled_max and extent > 0
            else "WITHIN_SAMPLED_POINTS" if extent > 0 else "BELOW_THRESHOLDS_AT_SAMPLES")
        output["thermal_threshold_w_m2"] = 5000.0
        output["overpressure_threshold_pa"] = 5000.0
        output.update(consequence_risk_summary(output))
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
