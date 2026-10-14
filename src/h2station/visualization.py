"""Read-only renderer contract. Physics, consequence and LLM remain server-owned.

Three.js scene metres (X/right, Y/up, Z/depth) are mapped to Unreal centimetres
as (X, Z, Y) * 100. Missing telemetry is null, never a fabricated normal value.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import math
from typing import Any, Mapping

SCHEMA_VERSION = 1


def unreal_position(position: list[float] | tuple[float, ...]) -> list[float]:
    x, y, z = position
    return [round(100.0 * axis, 8) for axis in (x, z, y)]


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


# Reference layout, not a claim about a confidential facility or vessel capacity.
_EQUIPMENT = (
    ("cascade.low", "low", "저압 저장 뱅크", "N07", (-1, 0, -6), (2.65, 2.8, 4.6)),
    ("cascade.medium", "medium", "중압 저장 뱅크", "N08", (3, 0, -6), (2.65, 2.8, 4.6)),
    ("cascade.high", "high", "고압 저장 뱅크", "N09", (7, 0, -6), (2.65, 2.8, 4.6)),
    ("supply", "supply", "공급 트레일러", "N01", (-22, 0, -1.5), (2.6, 3.7, 16)),
    ("compressor", "compressor", "수소 압축기", "N06", (-6.4, 0, -6), (5, 3.6, 4.4)),
    ("cooler", "cooler", "프리쿨러", "N19", (11, 0, -6), (4.2, 3, 4)),
    ("header", "header", "공통 헤더", "N10", (3, 0, -3), (4, 1.5, 1)),
    ("dispenser.pcv", "dispenser", "디스펜서 1", "N11", (0, 0, 4.2), (1.2, 2.2, 1)),
    ("dispenser_2.pcv", "standby", "디스펜서 2", "N15", (8, 0, 4.2), (1.2, 2.2, 1)),
    ("dispenser.hose", "dispenser", "충전 호스 1", "N13", (1.8, 1.2, 5.2), (2.4, 1, 2)),
    ("dispenser_2.hose", "standby", "충전 호스 2", "N17", (9.8, 1.2, 5.2), (2.4, 1, 2)),
    ("vehicle.tank", "vehicle", "차량 1", "N14", (2.8, 0, 7), (4.9, 1.5, 1.9)),
    ("vehicle_2.tank", "vehicle2", "차량 2", "N18", (10.8, 0, 7), (4.9, 1.5, 1.9)),
    ("vent", "vent", "벤트 출구", "N20", (14, 0, -9), (1, 6, 1)),
)

_DETECTORS = (
    ("GD-0101", (-22, 2.7, 5)), ("GD-0201", (-22, 2.5, -8)),
    ("GD-0601", (-6, 2.8, -4)), ("GD-0701", (-2, 2.7, -5)),
    ("GD-0801", (1, 2.7, -5)), ("GD-0901", (5, 2.7, -5)),
    ("GD-1001", (8, 2.7, -3)), ("GD-1301", (0, 4.66, 4.25)),
    ("GD-1701", (8, 4.66, 4.25)), ("GD-1901", (11, 2.7, -4)),
    ("GD-2001", (12, 2.8, -3)), ("GD-2101", (-6, 3.8, -3)),
    ("GD-2201", (3, 3.7, -5)), ("GD-2301", (4, 4.7, 4)),
    ("GD-2302", (11, 3.5, -4)),
    ("FD-0101", (-22, 3.3, 3)), ("FD-0601", (-6, 3.7, -3)),
    ("FD-0701", (-2, 3.5, -4)), ("FD-0801", (1, 3.5, -4)),
    ("FD-0901", (5, 3.5, -4)), ("FD-1301", (0, 4.55, 3.6)),
    ("FD-1701", (8, 4.55, 3.6)), ("FD-1901", (11, 3.6, -3)),
    ("FD-2001", (12, 3.5, -2)),
)


def scene_manifest() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "layout_basis": "PUBLIC_REFERENCE_SCHEMATIC",
        "coordinate_mapping": "three_metres(x,y,z) -> unreal_centimetres(100*x,100*z,100*y)",
        "units": {"position": "cm", "pressure": "MPa_abs", "temperature": "degC",
                  "flow": "g/s", "mass": "kg", "effect_distance": "m", "time": "simulation_s"},
        "equipment": [{"component_id": cid, "ui_id": ui, "label": label,
                       "node_id": node, "position_cm": unreal_position(pos),
                       "dimensions_cm": unreal_position(dim),
                       "dimensions_basis": "illustrative_reference_envelope"}
                      for cid, ui, label, node, pos, dim in _EQUIPMENT],
        "detectors": [{"sensor_id": tag, "kind": "flame" if tag.startswith("FD-") else "gas",
                       "position_cm": unreal_position(pos)} for tag, pos in _DETECTORS],
        "cameras": [{"camera_id": cid, "position_cm": unreal_position(pos)} for cid, pos in (
            ("CAM-01", (3, 3.4, -3.6)), ("CAM-02", (-6.2, 3.1, -3.8)),
            ("CAM-03", (4.1, 3.6, 3.25)), ("CAM-04", (13.5, 3, -3.3)),
            ("CAM-05", (-22, 3.8, 1.2)))],
    }


def build_snapshot(job_id: str, job: Mapping[str, Any], frame: Mapping[str, Any] | None,
                   safety: Mapping[str, Any] | None = None,
                   risk: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Project public simulator state without running a solver or a risk evaluator."""
    frame = frame or {}
    safety = safety if safety is not None else frame.get("virtual_safety") or {}
    hazop = frame.get("hazop") or {}
    signals = hazop.get("signals") or {}
    equipment = []

    def sensor(prefix: str, node: str) -> float | None:
        tag = f"{prefix}-{node[1:]}01"
        return number((signals.get(tag) or {}).get("value"))

    for cid, ui, label, node, _pos, _dim in _EQUIPMENT:
        p, t, mass, flow = None, None, None, sensor("FT", node)
        if cid.startswith("cascade."):
            bank = cid.split(".")[1]
            p = number((frame.get("bank_pressure_mpa") or {}).get(bank))
            t = number((frame.get("bank_temperature_c") or {}).get(bank))
            mass = number((frame.get("bank_mass_kg") or {}).get(bank))
        elif cid in ("vehicle.tank", "vehicle_2.tank"):
            prefix = "vehicle" if cid == "vehicle.tank" else "vehicle_2"
            p, t = number(frame.get(prefix + "_pressure_mpa")), number(frame.get(prefix + "_temperature_c"))
            mass = number(frame.get(prefix + "_mass_kg"))
        elif cid in ("dispenser.hose", "dispenser_2.hose"):
            second = cid.startswith("dispenser_2")
            prefix = "hose_2" if second else "hose"
            p, t = number(frame.get(prefix + "_pressure_mpa")), number(frame.get(prefix + "_temperature_c"))
            flow = number(frame.get("nozzle_2_flow_g_s" if second else "nozzle_1_flow_g_s"))
        elif cid in ("header", "compressor"):
            prefix = "header" if cid == "header" else "compressor_package"
            p, t = number(frame.get(prefix + "_pressure_mpa")), number(frame.get(prefix + "_temperature_c"))
            mass = number(frame.get(prefix + "_mass_kg"))
        equipment.append({"component_id": cid, "ui_id": ui, "label": label,
                          "pressure_mpa": p if p is not None else sensor("PT", node),
                          "temperature_c": t if t is not None else sensor("TT", node),
                          "mass_kg": mass, "flow_g_s": flow})

    releases = []
    for source in hazop.get("releases") or []:
        effect = source.get("consequence") or {}
        releases.append({
            "release_id": source.get("release_id"), "component_id": source.get("component_id"),
            "mass_flow_g_s": number(source.get("mass_flow_g_s")),
            "sampled_effect_radius_m": number(effect.get("sampled_effect_radius_m", effect.get("effect_radius_m"))),
            "flammable_plume_distance_m": number(effect.get("flammable_plume_streamline_distance_m")),
            "consequence": deepcopy(effect), "basis": "SERVER_RELEASE_RECORD",
            "calculated_time_s": number(source.get("calculated_time_s")),
            "release_source_boundary": deepcopy(source.get("release_source_boundary")),
            "outlet_height_m": 6.0 if str(source.get("release_id", "")).startswith("vent-") else None,
        })
    detector_signals = dict(signals)
    detector_signals.update(frame.get("gas_detectors") or {})
    detector_signals.update(frame.get("flame_detectors") or {})
    detectors = [{"sensor_id": tag, "value": (float(row["value"]) if tag.startswith("FD-")
                  and isinstance(row.get("value"), bool) else number(row.get("value"))),
                  "quality": row.get("quality", "UNKNOWN"), "unit": row.get("unit")}
                 for tag, row in sorted(detector_signals.items())
                 if tag.startswith(("GD-", "FD-")) and isinstance(row, dict)]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": job_id, "run_created_at": job.get("created_at"),
        "sequence": int(frame.get("sequence", -1)), "time_s": number(frame.get("time_s")),
        "status": job.get("status", "unknown"),
        "produced_at": datetime.now(timezone.utc).isoformat(),
        "data_available": bool(frame), "esd": frame.get("esd"),
        "equipment": equipment, "detectors": detectors, "releases": releases,
        "active_faults": deepcopy(frame.get("active_faults") or []),
        "process_activity": deepcopy(frame.get("process_activity") or {}),
        "process_operations": deepcopy(frame.get("process_operations") or {}),
        "safety": deepcopy(dict(safety)),
        "risk_zones": deepcopy(dict(risk)) if risk is not None else {
            "status": "not_requested", "zones": [], "time_s": None},
        "risk_basis": "server_screening_index_not_annual_probability",
        "effect_basis": "sampled_consequence_not_certified_evacuation_distance",
    }
