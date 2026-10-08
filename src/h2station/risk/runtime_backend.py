"""Runtime loading for a site-configured HyRAM+ evaluator."""

from __future__ import annotations

import importlib
import json
import math
import os
from typing import Mapping

import numpy as np

from ..dispenser import IsentropicRealGasRestriction, RestrictionParameters
from ..ignited_pressure_peaking import (
    IgnitedPressurePeakingConfig,
    simulate_ignited_pressure_peaking,
)
from ..thermo import HydrogenEOS
from .hyram_adapter import (
    AmbientCondition,
    HyRAMRiskMonitor,
    IndoorScenario,
    LeakScenario as AdapterLeakScenario,
)
from .delayed_ignition import delayed_ignition_envelope
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


def consequence_validation_context() -> dict[str, str | bool]:
    """Return the claim boundary that travels with every consequence result.

    The simulator has traceable component evidence for its *outdoor,
    unconfined free-jet display mapping*: the bundled HyRAM+ adapter is checked
    against its upstream suite and the geometry mapping is checked against
    independent plume, radiation, and overpressure data.  That is deliberately
    narrower than validating source depletion, a particular station layout, or
    a station-to-vehicle fueling loop.  Keeping the boundary on each result
    prevents an API/LLM consumer from turning a calculated screening radius into
    a field-verified separation or evacuation distance.

    This function is static by design.  It exposes only public artifact paths
    and claim states; it never reads or exposes restricted measurement data.
    """
    return {
        "consequence_validation_scope": "COMPONENT_SCREENING_BOUNDED",
        "geometry_display_mapping_verified": True,
        "source_depletion_external_holdout_supported": False,
        "full_station_vehicle_validation_supported": False,
        "site_specific_safety_distance_supported": False,
        "consequence_validation_artifacts": (
            "research/consequence_geometry_validation.json; "
            "research/hyram_adapter_verification.json; "
            "research/usn_17934047_ignited_pressure_peaking_result_2026_10_08.json; "
            "data/public_validation/results/closed_loop_external_holdout/validation.json"
        ),
        "consequence_validation_claim_limit": (
            "외부 비밀폐 수소 자유제트의 표본 표시 매핑과 검증 범위 내 즉시점화 밀폐공간 "
            "압력 피크는 구성요소 수준에서 확인되었으나, 현재 설비의 감압·배치·충전소-차량 "
            "전체 루프 또는 현장 안전·대피거리는 검증되지 않았습니다."
        ),
    }


def ignited_enclosure_consequence(
    request: HyRAMDynamicReleaseRequest,
    *,
    enclosure_volume_m3: float,
    enclosure_vent_area_m2: float,
    ambient_temperature_k: float = 298.15,
) -> dict[str, float | str | bool | None]:
    """Calculate a bounded immediately ignited enclosure pressure endpoint.

    Runtime source history is represented by its elapsed average mass flow.
    The result is identified as externally supported only inside the public
    USN validation envelope; extrapolations remain available for training but
    carry an explicit out-of-domain flag.
    """
    if enclosure_volume_m3 <= 0.0 or enclosure_vent_area_m2 <= 0.0:
        raise ValueError("Ignited enclosure volume and vent area must be positive")
    if ambient_temperature_k <= 0.0:
        raise ValueError("Ambient temperature must be positive")

    elapsed_s = max(0.0, float(request.duration_s))
    horizon_s = max(0.02, min(elapsed_s, 12.0))
    average_flow_kg_s = (
        max(0.0, float(request.cumulative_released_mass_kg)) / elapsed_s
        if elapsed_s > 1.0e-9
        else max(0.0, float(request.mass_flow_override_kg_s))
    )
    scale = (enclosure_volume_m3 / 14.9) ** (1.0 / 3.0)
    config = IgnitedPressurePeakingConfig(
        enclosure_volume_m3=enclosure_volume_m3,
        enclosure_dimensions_m=(2.5 * scale, 2.0 * scale, 2.98 * scale),
        ambient_pressure_pa=float(request.ambient_pressure_pa),
    )
    mass_flow_time_s = np.asarray((0.0, horizon_s), dtype=float)
    output_time_s = np.linspace(
        0.0,
        horizon_s,
        max(2, int(math.ceil(horizon_s / 0.02)) + 1),
    )
    result = simulate_ignited_pressure_peaking(
        mass_flow_time_s,
        np.full(2, average_flow_kg_s * 1000.0),
        initial_temperature_k=ambient_temperature_k,
        vent_area_m2_value=enclosure_vent_area_m2,
        output_time_s=output_time_s,
        config=config,
    )
    in_validation_domain = (
        abs(enclosure_volume_m3 - 14.9) / 14.9 <= 0.05
        and 0.0055 <= enclosure_vent_area_m2 <= 0.0164
        and 0.0013 <= average_flow_kg_s <= 0.012
        and elapsed_s >= 5.0
        and 275.0 <= ambient_temperature_k <= 300.0
    )
    return {
        "ignited_enclosure_status": "calculated",
        "ignited_enclosure_model": "LACH_GAATHAUG_2021_ZERO_DIMENSIONAL",
        "maximum_ignited_enclosure_overpressure_pa": (
            result.peak_overpressure_kpa * 1000.0
        ),
        "ignited_enclosure_peak_time_s": result.peak_time_s,
        "ignited_enclosure_average_mass_flow_kg_s": average_flow_kg_s,
        "ignited_enclosure_volume_m3": enclosure_volume_m3,
        "ignited_enclosure_vent_area_m2": enclosure_vent_area_m2,
        "ignited_enclosure_external_holdout_supported": in_validation_domain,
        "ignited_enclosure_validation_artifact": (
            "research/usn_17934047_ignited_pressure_peaking_result_2026_10_08.json"
        ),
        "ignited_enclosure_claim_limit": (
            "즉시 점화된 환기식 밀폐공간의 압력 피크 구성요소 모델입니다. "
            "폭연 전파, 옥외 제트화염, 전체 충전소 또는 대피거리를 검증하지 않습니다."
        ),
    }


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


def mass_flow_override_metadata(
    requested_mass_flow_kg_s: float | None,
    modeled_mass_flow_kg_s: float | None,
) -> dict[str, float | str | bool | None]:
    """Expose whether HyRAM retained a process-flow boundary.

    HyRAM's high-pressure choked-flow path can recompute an orifice flow even
    when the digital twin supplies a measured/process flow override.  The
    consequence result remains useful as a model-bound screening result, but
    the distinction must be visible to operators and to the LLM instead of
    being silently treated as a measured release.
    """
    if requested_mass_flow_kg_s is None:
        return {
            "mass_flow_override_requested": False,
            "mass_flow_override_status": "MODEL_CALCULATED",
            "mass_flow_override_ratio": None,
            "mass_flow_override_claim_limit": "HyRAM orifice/model flow; no process-flow override supplied",
        }
    requested = max(0.0, float(requested_mass_flow_kg_s))
    modeled = None if modeled_mass_flow_kg_s is None else max(0.0, float(modeled_mass_flow_kg_s))
    if modeled is None:
        return {
            "mass_flow_override_requested": True,
            "mass_flow_override_status": "NO_MODELED_FLOW",
            "mass_flow_override_ratio": None,
            "mass_flow_override_claim_limit": "Process-flow override supplied, but no modeled consequence flow is available",
        }
    if requested <= 1.0e-12:
        # A ratio against zero is undefined; keep the field JSON-safe and use
        # the explicit status to describe the mismatch.
        ratio = None
        status = "OVERRIDE_ZERO_REQUESTED" if modeled <= 1.0e-12 else "HYRAM_FLOW_EXCEEDS_ZERO_REQUEST"
    else:
        ratio = modeled / requested
        status = "OVERRIDE_RETAINED" if abs(ratio - 1.0) <= 0.05 else (
            "HYRAM_CHOKED_MODEL_EXCEEDS_REQUEST" if ratio > 1.05 else "HYRAM_MODEL_BELOW_REQUEST"
        )
    return {
        "mass_flow_override_requested": True,
        "mass_flow_override_status": status,
        "mass_flow_override_ratio": ratio,
        "mass_flow_override_claim_limit": (
            "Modeled consequence flow differs from the process-flow boundary; "
            "screening results must not be described as a measured release consequence"
            if status not in {"OVERRIDE_RETAINED", "OVERRIDE_ZERO_REQUESTED"}
            else "Modeled consequence flow is within 5% of the supplied process-flow boundary"
        ),
    }


def consequence_orifice_boundary(
    request: HyRAMDynamicReleaseRequest,
) -> dict[str, float | str | bool | None]:
    """Represent a defensible flow-limited source in HyRAM's orifice interface.

    HyRAM 6.1 may recompute choked flow and ignore a supplied mass-flow value.
    For a declared flow-limited line, use the area ratio implied by the process
    source model so the consequence jet carries the bounded flow. This is a
    source-boundary transformation, not a post-outcome fit to a desired radius.
    """
    physical_diameter = float(request.orifice_diameter_m)
    base = {
        "physical_orifice_diameter_m": physical_diameter,
        "consequence_equivalent_orifice_diameter_m": physical_diameter,
        "free_orifice_mass_flow_kg_s": None,
        "flow_limited_equivalent_orifice_applied": False,
        "flow_limited_consequence_status": "NOT_APPLICABLE",
        "flow_limited_consequence_claim_limit": (
            "Physical aperture used directly; no flow-limited source boundary applied"
        ),
    }
    if request.release_boundary != "flow_limited_line":
        return base

    area = math.pi * physical_diameter ** 2 / 4.0
    free_flow = IsentropicRealGasRestriction(
        RestrictionParameters(
            flow_area_m2=area,
            discharge_coefficient=float(request.discharge_coefficient),
            minimum_pressure_pa=max(1.0, float(request.ambient_pressure_pa)),
        )
    ).mass_flow_kg_s(
        float(request.source_pressure_pa),
        float(request.source_temperature_k),
        float(request.ambient_pressure_pa),
    )
    bounded_flow = max(0.0, float(request.mass_flow_override_kg_s))
    if free_flow <= 0.0 or bounded_flow >= free_flow * (1.0 - 1.0e-9):
        return {
            **base,
            "free_orifice_mass_flow_kg_s": free_flow,
            "flow_limited_consequence_status": "CAP_NOT_ACTIVE",
            "flow_limited_consequence_claim_limit": (
                "Declared process limit does not reduce the current free-orifice flow"
            ),
        }

    equivalent_diameter = physical_diameter * math.sqrt(
        max(bounded_flow, 1.0e-15) / free_flow
    )
    return {
        **base,
        "consequence_equivalent_orifice_diameter_m": equivalent_diameter,
        "free_orifice_mass_flow_kg_s": free_flow,
        "flow_limited_equivalent_orifice_applied": True,
        "flow_limited_consequence_status": "EQUIVALENT_AREA_APPLIED",
        "flow_limited_consequence_claim_limit": (
            "Equivalent area preserves the declared process-flow boundary in HyRAM's "
            "choked-orifice interface; it is not a measured aperture or calibrated distance"
        ),
    }


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
            "release_source_boundary": request.release_boundary,
            "process_flow_limit_kg_s": request.process_flow_limit_kg_s,
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
        source_boundary = consequence_orifice_boundary(request)
        leak = AdapterLeakScenario(
            orifice_diameter=float(
                source_boundary["consequence_equivalent_orifice_diameter_m"]
            ),
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
            "release_source_boundary": request.release_boundary,
            "process_flow_limit_kg_s": request.process_flow_limit_kg_s,
            "observation_locations_m": self.observation_locations,
        }
        output.update(source_boundary)
        output.update(mass_flow_override_metadata(
            result.requested_mass_flow_rate, result.mass_flow_rate,
        ))
        output.update(delayed_ignition_envelope(
            storage_pressure_pa=request.source_pressure_pa,
            storage_temperature_k=request.source_temperature_k,
            release_diameter_m=request.orifice_diameter_m,
            ambient_pressure_pa=request.ambient_pressure_pa,
            release_boundary=request.release_boundary,
        ))
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
        thermal_affected = [
            distance for distance, value in thermal_points if value >= 5000.0
        ]
        blast_affected = [
            distance for distance, value in blast_points if value >= 5000.0
        ]
        affected = thermal_affected + blast_affected
        sampled_max = max((distance for distance, _ in thermal_points + blast_points), default=0.0)
        extent = max(affected, default=0.0)
        thermal_extent = max(thermal_affected, default=0.0)
        blast_extent = max(blast_affected, default=0.0)
        distances = sorted({distance for distance, _ in thermal_points + blast_points})
        next_sample = next((distance for distance in distances if distance > extent), None) if extent > 0 else None
        output["sampled_effect_radius_m"] = extent
        output["sampled_thermal_radius_m"] = thermal_extent
        output["sampled_overpressure_radius_m"] = blast_extent
        output["sampled_max_distance_m"] = sampled_max
        output["sampled_next_distance_m"] = next_sample
        output["observation_point_count"] = len(self.observation_locations)
        output["effect_range_status"] = ("BEYOND_SAMPLED_POINTS" if extent >= sampled_max and extent > 0
            else "WITHIN_SAMPLED_POINTS" if extent > 0 else "BELOW_THRESHOLDS_AT_SAMPLES")
        output["thermal_range_status"] = (
            "BEYOND_SAMPLED_POINTS" if thermal_extent >= sampled_max and thermal_extent > 0
            else "WITHIN_SAMPLED_POINTS" if thermal_extent > 0
            else "BELOW_THRESHOLD_AT_SAMPLES"
        )
        output["overpressure_range_status"] = (
            "BEYOND_SAMPLED_POINTS" if blast_extent >= sampled_max and blast_extent > 0
            else "WITHIN_SAMPLED_POINTS" if blast_extent > 0
            else "BELOW_THRESHOLD_AT_SAMPLES"
        )
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
                output["maximum_overpressure_pa"] = max(
                    float(output["maximum_overpressure_pa"] or 0.0),
                    float(accumulation.maximum_overpressure or 0.0),
                )
                output["indoor_status"] = "calculated"
        if request.indoor and request.ignited:
            volume_m3 = request.enclosure_volume_m3
            vent_area_m2 = request.enclosure_vent_area_m2
            if self.indoor_scenario is not None:
                if volume_m3 is None:
                    volume_m3 = (
                        self.indoor_scenario.floor_ceiling_area
                        * self.indoor_scenario.enclosure_height
                    )
                if vent_area_m2 is None:
                    vent_area_m2 = (
                        self.indoor_scenario.ceiling_vent_area
                        + self.indoor_scenario.floor_vent_area
                    )
            if volume_m3 is None or vent_area_m2 is None:
                output["ignited_enclosure_status"] = "enclosure-not-configured"
            else:
                try:
                    ignited = ignited_enclosure_consequence(
                        request,
                        enclosure_volume_m3=volume_m3,
                        enclosure_vent_area_m2=vent_area_m2,
                        ambient_temperature_k=ambient.temperature,
                    )
                    output.update(ignited)
                    output["maximum_overpressure_pa"] = max(
                        float(output["maximum_overpressure_pa"] or 0.0),
                        float(ignited["maximum_ignited_enclosure_overpressure_pa"] or 0.0),
                    )
                except (RuntimeError, ValueError, FloatingPointError) as exc:
                    output["ignited_enclosure_status"] = "integration-failed"
                    output["ignited_enclosure_error"] = f"{type(exc).__name__}: {exc}"
        # Risk must be calculated after indoor consequences have been merged.
        output.update(consequence_risk_summary(output))
        output.update(consequence_validation_context())
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
