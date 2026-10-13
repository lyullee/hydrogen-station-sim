"""Point-in-time consequence estimates from simulated HAZOP sensor readings."""

from __future__ import annotations

import math
import re
from typing import Any, Mapping

from ..thermo import HydrogenEOS
from .live import DynamicLeakModel, HyRAMDynamicReleaseRequest, LeakScenario, LeakSourceState
from .runtime_backend import consequence_risk_summary, consequence_validation_context


def _good_signal(signals: Mapping[str, Any], tags: str | None, prefix: str) -> tuple[str, float] | None:
    for tag in re.findall(rf"{prefix}-\d{{4}}", tags or ""):
        signal = signals.get(tag)
        if not isinstance(signal, dict) or signal.get("quality") != "GOOD":
            continue
        try:
            value = float(signal["value"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(value):
            return tag, value
    return None


def available_sensor_inputs(frame: Mapping[str, Any], catalog: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Expose usable current P/T readings with their actual HAZOP node provenance."""
    signals = (frame.get("hazop") or {}).get("signals") or {}
    result: dict[str, list[dict[str, Any]]] = {"pressure": [], "temperature": []}
    for sensor in catalog["sensors"]:
        tag = sensor["sensor_id"]
        if tag.startswith("PT-"):
            reading = _good_signal(signals, tag, "PT")
            if reading and reading[1] > 0.101325:
                result["pressure"].append({"sensor_id": tag, "node_id": sensor["node_id"],
                                            "value": reading[1], "unit": "MPa_abs"})
        elif tag.startswith("TT-"):
            reading = _good_signal(signals, tag, "TT")
            if reading and reading[1] > -273.15:
                result["temperature"].append({"sensor_id": tag, "node_id": sensor["node_id"],
                                               "value": reading[1], "unit": "degC"})
    return result


# Spatial detector nodes have no process P/T of their own. A nearby process
# source is usable only as an explicitly labelled hypothetical proxy.
_AREA_PROCESS_SOURCES = {
    "N19": ("N12", "N16"),
    "N21": ("N04", "N05"),
    "N22": ("N07", "N08", "N09"),
    "N23": ("N13", "N17"),
}


def _positive_finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0.0 else None


def _source_inventory_screen(
    frame: Mapping[str, Any],
    node: Mapping[str, Any],
    component: str,
    *,
    pressure_pa: float,
    temperature_k: float,
    ambient_pressure_pa: float,
) -> dict[str, Any]:
    """Return an auditable inventory/current-rate screening basis.

    The live simulator publishes exact state inventory for banks and vehicles.
    Other modeled volumes can only use an EOS estimate from the selected P/T
    sensors.  This helper deliberately stops at inventory:flow ratios.  It is
    not a pressure-decay integration and therefore cannot be presented as an
    isolation, evacuation, or blowdown completion time.
    """

    volume_m3 = _positive_finite(
        (frame.get("component_internal_volume_m3") or {}).get(component)
    ) or _positive_finite(node.get("모델체적_m3"))
    if volume_m3 is None:
        return {}

    inventory_kg: float | None = None
    origin = "EOS_FROM_SENSOR_AND_MODEL_VOLUME"
    if component.startswith("cascade."):
        bank_name = component.split(".", 1)[1]
        inventory_kg = _positive_finite(
            (frame.get("bank_mass_kg") or {}).get(bank_name)
        )
        if inventory_kg is not None:
            origin = "DIGITAL_TWIN_STATE"
    elif component == "vehicle.tank":
        inventory_kg = _positive_finite(frame.get("vehicle_mass_kg"))
        if inventory_kg is not None:
            origin = "DIGITAL_TWIN_STATE"
    elif component == "vehicle_2.tank":
        inventory_kg = _positive_finite(frame.get("vehicle_2_mass_kg"))
        if inventory_kg is not None:
            origin = "DIGITAL_TWIN_STATE"

    try:
        eos = HydrogenEOS()
        if inventory_kg is None:
            inventory_kg = eos.state_pt(pressure_pa, temperature_k).density * volume_m3
        ambient_inventory_kg = (
            eos.state_pt(ambient_pressure_pa, temperature_k).density * volume_m3
        )
    except (RuntimeError, ValueError, FloatingPointError):
        return {}
    if not math.isfinite(inventory_kg) or inventory_kg <= 0.0:
        return {}
    releasable_inventory_kg = max(0.0, inventory_kg - ambient_inventory_kg)
    return {
        "source_inventory_kg": float(inventory_kg),
        "source_inventory_model_volume_m3": float(volume_m3),
        "ambient_equilibrium_inventory_kg": float(ambient_inventory_kg),
        "releasable_inventory_kg": float(releasable_inventory_kg),
        "source_inventory_origin": origin,
        "inventory_duration_status": "CURRENT_RATE_RATIO_ONLY",
        "inventory_duration_claim_limit": (
            "Current model inventory divided by current release-flow bounds only; "
            "not a validated pressure-decay, isolation, evacuation, or blowdown time."
        ),
    }


def _inventory_duration_screen(
    inventory: Mapping[str, Any],
    *,
    point_flow_kg_s: float,
    lower_flow_kg_s: Any,
    upper_flow_kg_s: Any,
) -> dict[str, Any]:
    releasable = _positive_finite(inventory.get("releasable_inventory_kg"))
    if releasable is None:
        return dict(inventory)
    point = _positive_finite(point_flow_kg_s)
    lower = _positive_finite(lower_flow_kg_s) or point
    upper = _positive_finite(upper_flow_kg_s) or point
    if lower is None or upper is None:
        return dict(inventory)
    low_flow, high_flow = sorted((lower, upper))
    result = dict(inventory)
    result.update({
        "constant_rate_inventory_time_lower_s": releasable / high_flow,
        "constant_rate_inventory_time_upper_s": releasable / low_flow,
    })
    return result


def assess_sensor_cases(
    frame: Mapping[str, Any], catalog: Mapping[str, Any], backend: Any,
    node_ids: list[str], *, max_cases: int = 3,
    proposals: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate a clearly hypothetical 1 mm release unless a physical release exists.

    Geometry is assumed because the HAZOP workbook does not identify a precise
    leak point or direction. These sampled results are never a validated safe radius.
    """
    signals = (frame.get("hazop") or {}).get("signals") or {}
    releases = (frame.get("hazop") or {}).get("releases") or []
    cases = {case["node_id"]: case for case in catalog["cases"]}
    nodes = {node["node_id"]: node for node in catalog["nodes"]}
    sizes = {size["size_id"]: size for size in catalog["leak_sizes"]}
    results: list[dict[str, Any]] = []
    leak_model = DynamicLeakModel()
    entries = proposals if proposals is not None else [{"node_id": node_id} for node_id in dict.fromkeys(node_ids)]
    for entry in entries:
        if len(results) >= max_cases:
            break
        node_id = entry["node_id"]
        case, node = cases.get(node_id), nodes.get(node_id)
        if not case or not node:
            continue
        pressure = _good_signal(signals, entry.get("pressure_sensor") or case.get("압력_sensor"), "PT")
        temperature = _good_signal(signals, entry.get("temperature_sensor") or case.get("온도_sensor"), "TT")
        proxy_node_id = None
        if proposals is None and (not pressure or not temperature) and node_id in _AREA_PROCESS_SOURCES:
            for source_id in _AREA_PROCESS_SOURCES[node_id]:
                source_case = cases.get(source_id) or {}
                source_pressure = _good_signal(signals, source_case.get("압력_sensor"), "PT")
                source_temperature = _good_signal(signals, source_case.get("온도_sensor"), "TT")
                if source_pressure and source_temperature:
                    pressure, temperature, proxy_node_id = source_pressure, source_temperature, source_id
                    break
        result: dict[str, Any] = {
            "case_id": case["case_id"], "node_id": node_id,
            "node_name": node.get("설비_라인"),
            "sensor_time_s": frame.get("time_s"),
            "calculation_basis": "SENSOR_BASED_HYPOTHESIS",
            "calculation_status": "input_unavailable",
        }
        # Put the consequence claim boundary on every case, including an
        # input-unavailable one.  The API may filter non-calculated cases, but
        # a caller that keeps them must still not infer field validation.
        result.update(consequence_validation_context())
        if proxy_node_id:
            result.update(calculation_basis="SENSOR_BASED_PROXY_HYPOTHESIS", sensor_basis="PROXY",
                          pressure_source_node_id=proxy_node_id,
                          temperature_source_node_id=proxy_node_id,
                          source_note="인접 공정 설비의 계측값으로 공간 누출을 가정한 근사; 해당 공간의 직접 압력·온도 계측값 아님")
        if proposals is not None:
            result.update(calculation_basis="LLM_PROPOSED_HYPOTHESIS",
                          scenario_id=entry["scenario_id"],
                          scenario_rationale=entry["rationale"],
                          leak_size_id=entry["leak_size_id"])
            direct_pressure = pressure and pressure[0] in re.findall(r"PT-\d{4}", case.get("압력_sensor") or "")
            direct_temperature = temperature and temperature[0] in re.findall(r"TT-\d{4}", case.get("온도_sensor") or "")
            proxy = not (direct_pressure and direct_temperature)
            result.update(sensor_basis="PROXY" if proxy else "DIRECT",
                          pressure_source_node_id=entry.get("pressure_source_node_id", node_id),
                          temperature_source_node_id=entry.get("temperature_source_node_id", node_id))
            if proxy:
                result["calculation_basis"] = "LLM_PROPOSED_PROXY_HYPOTHESIS"
                result["source_note"] = "선택한 대체 센서로 목표 설비의 가상 누출 조건을 근사; 목표 설비의 직접 계측값 아님"
        if pressure:
            result.update(pressure_sensor=pressure[0], current_pressure_mpa=pressure[1])
        if temperature:
            result.update(temperature_sensor=temperature[0], current_temperature_c=temperature[1])
        if not pressure or not temperature:
            result["reason"] = "GOOD quality pressure and temperature sensor pair unavailable"
            results.append(result)
            continue
        source_pressure_pa = pressure[1] * 1e6
        source_temperature_k = temperature[1] + 273.15
        if source_pressure_pa <= 101325.0 or source_temperature_k <= 0:
            result["reason"] = "No valid pressurized hydrogen source at current sensor values"
            results.append(result)
            continue
        component = node.get("누출_target") or case.get("누출_위치_target") or node_id
        release = next((item for item in releases if isinstance(item, dict) and item.get("component_id") == component), None) if proposals is None else None
        if release:
            result["calculation_basis"] = "ACTIVE_RELEASE_CURRENT_SENSORS"
            result["release_id"] = release.get("release_id")
        size_id = entry.get("leak_size_id", "L03")
        size = sizes.get(size_id) or {}
        orifice_m = (float(release["orifice_diameter_m"]) if release and release.get("orifice_diameter_m")
                     else float(size.get("직경_mm") or 1.0) / 1000.0)
        coefficient = float(case.get("discharge_coefficient") or 0.8)
        result.update(orifice_diameter_mm=orifice_m * 1000.0,
                      orifice_source="ACTIVE_RELEASE" if release and release.get("orifice_diameter_m") else f"HAZOP_{size_id}_ASSUMPTION",
                      assumed_release_height_m=1.0, assumed_release_angle_rad=0.0,
                      assumed_ambient_pressure_pa=101325.0,
                      assumption_note="누출 위치·방향·높이 미확정. 1 m 높이 수평 분출과 표본 관측점을 가정; 현장 안전반경 아님")
        inventory_screen = _source_inventory_screen(
            frame,
            node,
            str(component),
            pressure_pa=source_pressure_pa,
            temperature_k=source_temperature_k,
            ambient_pressure_pa=101325.0,
        )
        result.update(inventory_screen)
        if not getattr(backend, "available", False):
            result.update(calculation_status="backend_unavailable", reason=getattr(backend, "reason", "Consequence backend unavailable"))
            results.append(result)
            continue
        try:
            scenario = LeakScenario(
                release_id=str(result.get("release_id") or f"sensor-{node_id}"),
                component_id=str(component), location=str(node_id), start_time_s=0.0,
                orifice_diameter_m=orifice_m, discharge_coefficient=coefficient,
                release_boundary=str(
                    (release or {}).get("release_source_boundary") or "free_orifice"
                ),
                maximum_mass_flow_kg_s=(release or {}).get(
                    "process_flow_limit_kg_s"
                ),
            )
            source = LeakSourceState(source_pressure_pa, source_temperature_k)
            estimated_flow = leak_model.mass_flow_kg_s(scenario, source)
            observed_flow = release.get("mass_flow_g_s") if release else None
            mass_flow = (float(observed_flow) / 1000.0 if observed_flow is not None else estimated_flow)
            if not math.isfinite(mass_flow) or mass_flow < 0:
                raise ValueError("Invalid release mass flow")
            request = HyRAMDynamicReleaseRequest(
                release_id=scenario.release_id, component_id=scenario.component_id,
                location=scenario.location, time_s=float(frame.get("time_s") or 0.0),
                duration_s=1.0, source_pressure_pa=source_pressure_pa,
                source_temperature_k=source_temperature_k, ambient_pressure_pa=101325.0,
                orifice_diameter_m=orifice_m, discharge_coefficient=coefficient,
                mass_flow_override_kg_s=mass_flow,
                cumulative_released_mass_kg=mass_flow,
                release_angle_rad=0.0, release_height_m=1.0, indoor=False,
                annual_frequency_per_year=None, immediate_ignition_probability=None,
                delayed_ignition_probability=None,
                release_boundary=scenario.release_boundary,
                process_flow_limit_kg_s=scenario.maximum_mass_flow_kg_s,
            )
            consequence = dict(backend.evaluate_release(request))
            consequence.update(consequence_risk_summary(consequence))
            result.update(_inventory_duration_screen(
                inventory_screen,
                point_flow_kg_s=mass_flow,
                lower_flow_kg_s=consequence.get("release_flow_lower_bound_kg_s"),
                upper_flow_kg_s=consequence.get("release_flow_upper_bound_kg_s"),
            ))
            radius = consequence.get("sampled_effect_radius_m")
            result.update(calculation_status=consequence.get("status", "unknown"),
                          mass_flow_g_s=mass_flow * 1000.0,
                          maximum_heat_flux_w_m2=consequence.get("maximum_heat_flux_w_m2"),
                          maximum_overpressure_pa=consequence.get("maximum_overpressure_pa"),
                          sampled_effect_radius_m=radius if radius and radius > 0 else None,
                          sampled_thermal_radius_m=consequence.get("sampled_thermal_radius_m"),
                          sampled_overpressure_radius_m=consequence.get("sampled_overpressure_radius_m"),
                          thermal_range_status=consequence.get("thermal_range_status"),
                          overpressure_range_status=consequence.get("overpressure_range_status"),
                          flammable_contour_volume_fraction=consequence.get("flammable_contour_volume_fraction"),
                          flammable_plume_streamline_distance_m=consequence.get("flammable_plume_streamline_distance_m"),
                          flammable_plume_x_extent_m=consequence.get("flammable_plume_x_extent_m"),
                          flammable_plume_y_extent_m=consequence.get("flammable_plume_y_extent_m"),
                          modeled_consequence_mass_flow_kg_s=consequence.get("modeled_consequence_mass_flow_kg_s"),
                          mass_flow_override_requested=consequence.get("mass_flow_override_requested"),
                          mass_flow_override_status=consequence.get("mass_flow_override_status"),
                          mass_flow_override_ratio=consequence.get("mass_flow_override_ratio"),
                          mass_flow_override_claim_limit=consequence.get("mass_flow_override_claim_limit"),
                          release_flow_point_kg_s=consequence.get("release_flow_point_kg_s"),
                          release_flow_lower_bound_kg_s=consequence.get("release_flow_lower_bound_kg_s"),
                          release_flow_upper_bound_kg_s=consequence.get("release_flow_upper_bound_kg_s"),
                          release_flow_lower_multiplier=consequence.get("release_flow_lower_multiplier"),
                          release_flow_upper_multiplier=consequence.get("release_flow_upper_multiplier"),
                          release_flow_model_discharge_coefficient=consequence.get("release_flow_model_discharge_coefficient"),
                          release_flow_empirical_cd_lower=consequence.get("release_flow_empirical_cd_lower"),
                          release_flow_empirical_cd_upper=consequence.get("release_flow_empirical_cd_upper"),
                          release_flow_uncertainty_status=consequence.get("release_flow_uncertainty_status"),
                          release_flow_public_domain=consequence.get("release_flow_public_domain"),
                          release_flow_evidence_doi=consequence.get("release_flow_evidence_doi"),
                          release_flow_evidence_artifact=consequence.get("release_flow_evidence_artifact"),
                          release_flow_envelope_kind=consequence.get("release_flow_envelope_kind"),
                          release_flow_claim_limit=consequence.get("release_flow_claim_limit"),
                          release_source_boundary=consequence.get("release_source_boundary"),
                          process_flow_limit_kg_s=consequence.get("process_flow_limit_kg_s"),
                          literature_delayed_ignition_status=consequence.get("literature_delayed_ignition_status"),
                          literature_delayed_ignition_in_validation_domain=consequence.get("literature_delayed_ignition_in_validation_domain"),
                          literature_delayed_ignition_5kpa_radial_distance_m=consequence.get("literature_delayed_ignition_5kpa_radial_distance_m"),
                          literature_delayed_ignition_no_harm_radial_distance_m=consequence.get("literature_delayed_ignition_no_harm_radial_distance_m"),
                          literature_delayed_ignition_injury_radial_distance_m=consequence.get("literature_delayed_ignition_injury_radial_distance_m"),
                          literature_delayed_ignition_fatality_radial_distance_m=consequence.get("literature_delayed_ignition_fatality_radial_distance_m"),
                          literature_delayed_ignition_distance_origin=consequence.get("literature_delayed_ignition_distance_origin"),
                          literature_delayed_ignition_site_safety_distance=consequence.get("literature_delayed_ignition_site_safety_distance"),
                          literature_delayed_ignition_doi=consequence.get("literature_delayed_ignition_doi"),
                          literature_delayed_ignition_claim_limit=consequence.get("literature_delayed_ignition_claim_limit"),
                          literature_jet_flame_status=consequence.get("literature_jet_flame_status"),
                          literature_jet_flame_in_validation_domain=consequence.get("literature_jet_flame_in_validation_domain"),
                          literature_jet_flame_length_m=consequence.get("literature_jet_flame_length_m"),
                          literature_jet_flame_mass_flow_basis=consequence.get("literature_jet_flame_mass_flow_basis"),
                          literature_jet_flame_is_harm_distance=consequence.get("literature_jet_flame_is_harm_distance"),
                          literature_jet_flame_doi=consequence.get("literature_jet_flame_doi"),
                          literature_jet_flame_claim_limit=consequence.get("literature_jet_flame_claim_limit"),
                          sampled_max_distance_m=consequence.get("sampled_max_distance_m"),
                          sampled_next_distance_m=consequence.get("sampled_next_distance_m"),
                          observation_point_count=consequence.get("observation_point_count"),
                          effect_range_status=consequence.get("effect_range_status"),
                          risk_score=consequence.get("risk_score"),
                          risk_level=consequence.get("risk_level"),
                          risk_basis=consequence.get("risk_basis"),
                          risk_scope=consequence.get("risk_scope"),
                          risk_confidence=consequence.get("risk_confidence"),
                          risk_claim_limit=consequence.get("risk_claim_limit"),
                          range_interpretation=("표본 관측점에서 기준 미달, 영향 반경 미확정"
                              if consequence.get("effect_range_status") == "BELOW_THRESHOLDS_AT_SAMPLES"
                              else "임계값 초과 표본 거리만 확인, 현장 안전반경 아님"))
        except Exception as exc:
            result.update(calculation_status="calculation_failed", reason=f"{type(exc).__name__}: {exc}")
        results.append(result)
    return results
