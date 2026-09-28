"""Point-in-time consequence estimates from simulated HAZOP sensor readings."""

from __future__ import annotations

import math
import re
from typing import Any, Mapping

from .live import DynamicLeakModel, HyRAMDynamicReleaseRequest, LeakScenario, LeakSourceState


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


def available_sensor_cases(frame: Mapping[str, Any], catalog: Mapping[str, Any]) -> list[dict[str, Any]]:
    """List HAZOP cases whose current source P/T pair is usable for calculation."""
    signals = (frame.get("hazop") or {}).get("signals") or {}
    nodes = {node["node_id"]: node for node in catalog["nodes"]}
    available = []
    for case in catalog["cases"]:
        pressure = _good_signal(signals, case.get("압력_sensor"), "PT")
        temperature = _good_signal(signals, case.get("온도_sensor"), "TT")
        if not pressure or not temperature or pressure[1] <= 0.101325 or temperature[1] <= -273.15:
            continue
        available.append({"node_id": case["node_id"], "case_id": case["case_id"],
                          "name": nodes.get(case["node_id"], {}).get("설비_라인"),
                          "pressure_sensor": pressure[0], "pressure_mpa": pressure[1],
                          "temperature_sensor": temperature[0], "temperature_c": temperature[1]})
    return available


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
        pressure = _good_signal(signals, case.get("압력_sensor"), "PT")
        temperature = _good_signal(signals, case.get("온도_sensor"), "TT")
        result: dict[str, Any] = {
            "case_id": case["case_id"], "node_id": node_id,
            "node_name": node.get("설비_라인"),
            "sensor_time_s": frame.get("time_s"),
            "calculation_basis": "SENSOR_BASED_HYPOTHESIS",
            "calculation_status": "input_unavailable",
        }
        if proposals is not None:
            result.update(calculation_basis="LLM_PROPOSED_HYPOTHESIS",
                          scenario_id=entry["scenario_id"],
                          scenario_rationale=entry["rationale"],
                          leak_size_id=entry["leak_size_id"])
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
        if not getattr(backend, "available", False):
            result.update(calculation_status="backend_unavailable", reason=getattr(backend, "reason", "Consequence backend unavailable"))
            results.append(result)
            continue
        try:
            scenario = LeakScenario(
                release_id=str(result.get("release_id") or f"sensor-{node_id}"),
                component_id=str(component), location=str(node_id), start_time_s=0.0,
                orifice_diameter_m=orifice_m, discharge_coefficient=coefficient,
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
            )
            consequence = dict(backend.evaluate_release(request))
            radius = consequence.get("sampled_effect_radius_m")
            result.update(calculation_status=consequence.get("status", "unknown"),
                          mass_flow_g_s=mass_flow * 1000.0,
                          maximum_heat_flux_w_m2=consequence.get("maximum_heat_flux_w_m2"),
                          maximum_overpressure_pa=consequence.get("maximum_overpressure_pa"),
                          sampled_effect_radius_m=radius if radius and radius > 0 else None,
                          sampled_max_distance_m=consequence.get("sampled_max_distance_m"),
                          effect_range_status=consequence.get("effect_range_status"),
                          range_interpretation=("표본 관측점에서 기준 미달, 영향 반경 미확정"
                              if consequence.get("effect_range_status") == "BELOW_THRESHOLDS_AT_SAMPLES"
                              else "임계값 초과 표본 거리만 확인, 현장 안전반경 아님"))
        except Exception as exc:
            result.update(calculation_status="calculation_failed", reason=f"{type(exc).__name__}: {exc}")
        results.append(result)
    return results
