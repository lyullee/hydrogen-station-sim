"""Compare canonical runtime consequence screens with DATA3632 method ranges.

The comparison is diagnostic.  DATA3632 is a simulation ensemble rather than
experimental truth, and PHAST weather/model settings are not fully reproduced
by the runtime HyRAM adapter.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from h2station.risk.live import (
    DynamicLeakModel,
    HyRAMDynamicReleaseRequest,
    LeakScenario,
    LeakSourceState,
)
from h2station.risk.runtime_backend import NativeHyRAMBackend


def benchmark_group(
    source: dict[str, Any], *, category: str, equipment: str
) -> dict[str, Any] | None:
    candidates = [
        item for item in source["matched_input_groups"]
        if item["signature"]["category"] == category
        and item["signature"]["equipment"] == equipment
        and item["signature"]["hole_size_mm"] == 10.0
        and item["signature"]["weather"] == "1.5F"
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item["method_count"])


def runtime_case(
    backend: NativeHyRAMBackend,
    *,
    equipment: str,
    pressure_bar: float,
    temperature_c: float,
    hole_size_mm: float,
) -> dict[str, Any]:
    pressure_pa = pressure_bar * 1.0e5
    temperature_k = temperature_c + 273.15
    diameter_m = hole_size_mm / 1000.0
    leak = LeakScenario(
        release_id=f"data3632-{equipment.lower()}",
        component_id=equipment.lower(),
        location=equipment,
        start_time_s=0.0,
        orifice_diameter_m=diameter_m,
        discharge_coefficient=0.8,
    )
    flow = DynamicLeakModel().mass_flow_kg_s(
        leak, LeakSourceState(pressure_pa, temperature_k)
    )
    request = HyRAMDynamicReleaseRequest(
        release_id=leak.release_id,
        component_id=leak.component_id,
        location=leak.location,
        time_s=0.0,
        duration_s=1.0,
        source_pressure_pa=pressure_pa,
        source_temperature_k=temperature_k,
        ambient_pressure_pa=101325.0,
        orifice_diameter_m=diameter_m,
        discharge_coefficient=0.8,
        mass_flow_override_kg_s=flow,
        cumulative_released_mass_kg=flow,
        release_angle_rad=0.0,
        release_height_m=1.0,
        indoor=False,
        annual_frequency_per_year=None,
        immediate_ignition_probability=None,
        delayed_ignition_probability=None,
    )
    result = backend.evaluate_release(request)
    return {
        "input_mass_flow_kg_s": flow,
        "modeled_mass_flow_kg_s": result["modeled_consequence_mass_flow_kg_s"],
        "mass_flow_override_status": result["mass_flow_override_status"],
        "thermal_radius_5_kw_m2_m": result["sampled_thermal_radius_m"],
        "overpressure_radius_5_kpa_m": result["sampled_overpressure_radius_m"],
        "combined_radius_m": result["sampled_effect_radius_m"],
        "thermal_range_status": result["thermal_range_status"],
        "overpressure_range_status": result["overpressure_range_status"],
        "sampled_max_distance_m": result["sampled_max_distance_m"],
        "visible_flame_length_m": result["visible_flame_length_m"],
    }


def position(value: float, envelope: dict[str, Any]) -> dict[str, Any]:
    minimum = float(envelope["minimum"])
    middle = float(envelope["median"])
    maximum = float(envelope["maximum"])
    return {
        "within_method_envelope": minimum <= value <= maximum,
        "ratio_to_method_median": value / middle if middle > 0.0 else None,
        "below_envelope_by_m": max(0.0, minimum - value),
        "above_envelope_by_m": max(0.0, value - maximum),
    }


def build(root: Path) -> dict[str, Any]:
    source_path = root / "research/qra_multimethod_comparison_2026_10_08.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    backend = NativeHyRAMBackend.from_environment()
    cases: list[dict[str, Any]] = []
    for equipment in ("Supply", "Compressor", "Buffer", "Dispenser"):
        explosion = benchmark_group(source, category="explosion", equipment=equipment)
        jet = benchmark_group(source, category="jet_fire", equipment=equipment)
        if jet is None:
            raise ValueError(f"missing jet-fire benchmark group for {equipment}")
        signatures = tuple(
            item["signature"] for item in (explosion, jet) if item is not None
        )
        if any(
            signature[key] != signatures[0][key]
            for signature in signatures[1:]
            for key in ("pressure_bar", "temperature_c", "hole_size_mm", "weather")
        ):
            raise ValueError(f"benchmark signatures do not align for {equipment}")
        signature = signatures[0]
        runtime = runtime_case(
            backend,
            equipment=equipment,
            pressure_bar=signature["pressure_bar"],
            temperature_c=signature["temperature_c"],
            hole_size_mm=signature["hole_size_mm"],
        )
        thermal_envelope = jet["distance_summary_m"]
        flow_envelope = jet["jet_fire_mass_rate_summary_kg_s"]
        if not flow_envelope or not flow_envelope["count"]:
            raise ValueError(f"missing jet-fire mass-rate envelope for {equipment}")
        blast_envelope = explosion["distance_summary_m"] if explosion else None
        cases.append({
            "equipment": equipment,
            "input": signature,
            "benchmark": {
                "thermal_5_kw_m2_distance_m": thermal_envelope,
                "overpressure_5_kpa_distance_m": blast_envelope,
                "thermal_method_count": jet["method_count"],
                "overpressure_method_count": explosion["method_count"] if explosion else 0,
                "jet_fire_mass_rate_kg_s": flow_envelope,
            },
            "runtime": runtime,
            "comparison": {
                "thermal": position(float(runtime["thermal_radius_5_kw_m2_m"]), thermal_envelope),
                "mass_rate": position(float(runtime["modeled_mass_flow_kg_s"]), flow_envelope),
                "overpressure": (
                    position(float(runtime["overpressure_radius_5_kpa_m"]), blast_envelope)
                    if blast_envelope else None
                ),
            },
        })
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_postaccess_runtime_to_qra_method_envelope_diagnostic",
        "source": {
            "doi": "10.34810/DATA3632",
            "version": "2.0",
            "comparison_artifact": "research/qra_multimethod_comparison_2026_10_08.json",
        },
        "runtime": {
            "backend": backend.name,
            "thermal_threshold_w_m2": 5000.0,
            "overpressure_threshold_pa": 5000.0,
            "discharge_coefficient": 0.8,
            "observation_locations_m": backend.observation_locations,
        },
        "cases": cases,
        "aggregate": {
            "case_count": len(cases),
            "thermal_within_method_envelope_count": sum(
                case["comparison"]["thermal"]["within_method_envelope"] for case in cases
            ),
            "overpressure_within_method_envelope_count": sum(
                case["comparison"]["overpressure"]["within_method_envelope"]
                for case in cases if case["comparison"]["overpressure"] is not None
            ),
            "overpressure_comparable_case_count": sum(
                case["comparison"]["overpressure"] is not None for case in cases
            ),
        },
        "limitations": [
            "DATA3632 is a simulation ensemble, not experimental truth.",
            "PHAST weather category 1.5/F is selected in the benchmark; the runtime adapter does not reproduce that weather category.",
            "The runtime uses a 0.8 discharge coefficient; source-method discharge coefficients are not harmonised in the exported rows.",
            "Runtime distances are discrete sampled extents, while DATA3632 5-unit distances are log-log interpolations between direct exported endpoints.",
        ],
        "model_action": "No automatic calibration or runtime parameter change is permitted from this diagnostic.",
        "claim_boundary": "This comparison detects material disagreement with an international QRA method envelope. It does not determine which model is physically correct and is not experimental validation, a safety distance or certification evidence.",
    }


def markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Runtime HyRAM vs DATA3632 QRA method envelope",
        "",
        "This is a post-access diagnostic against a simulation ensemble, not experimental validation.",
        "",
        "| Equipment | Runtime thermal 5 kW/m2 | Method envelope | Runtime 5 kPa | Method envelope |",
        "|---|---:|---:|---:|---:|",
    ]
    for case in result["cases"]:
        thermal = case["benchmark"]["thermal_5_kw_m2_distance_m"]
        blast = case["benchmark"]["overpressure_5_kpa_distance_m"]
        runtime = case["runtime"]
        flow = case["benchmark"]["jet_fire_mass_rate_kg_s"]
        blast_text = (
            f"{blast['minimum']:.1f}-{blast['maximum']:.1f} m"
            if blast else "not matched"
        )
        lines.append(
            f"| {case['equipment']} | {runtime['thermal_radius_5_kw_m2_m']:.1f} m | "
            f"{thermal['minimum']:.1f}-{thermal['maximum']:.1f} m | "
            f"{runtime['overpressure_radius_5_kpa_m']:.1f} m | "
            f"{blast_text} |"
        )
        lines.append(
            f"| ↳ mass rate | {runtime['modeled_mass_flow_kg_s']:.3f} kg/s | "
            f"{flow['minimum']:.3f}-{flow['maximum']:.3f} kg/s |  |  |"
        )
    lines += [
        "",
        f"- Thermal distance inside method envelope: **{result['aggregate']['thermal_within_method_envelope_count']}/{result['aggregate']['case_count']}**",
        f"- Overpressure distance inside method envelope: **{result['aggregate']['overpressure_within_method_envelope_count']}/{result['aggregate']['overpressure_comparable_case_count']}** comparable cases",
        "- No parameter was calibrated or changed from this comparison.",
        "",
        f"Claim boundary: {result['claim_boundary']}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("research/runtime_qra_envelope_comparison_2026_10_08.json"))
    parser.add_argument("--report", type=Path, default=Path("research/RUNTIME_QRA_ENVELOPE_COMPARISON_2026_10_08.md"))
    args = parser.parse_args()
    root = args.root.resolve()
    result = build(root)
    output = args.output if args.output.is_absolute() else root / args.output
    report = args.report if args.report.is_absolute() else root / args.report
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    with report.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown(result))
    print(json.dumps({"output": str(output), "report": str(report)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
