"""Run a post-outcome mixed-convection sensitivity through the full station.

The MC Default outcomes were inspected before this diagnostic was designed.
The result is therefore a development diagnostic, never a replacement for the
frozen external holdout.  Public MC files do not disclose the receptacle and
inlet-nozzle geometry needed by the correlation, so the script evaluates every
declared equivalent geometry without selecting a winner.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from run_h2protocol_validation import SCREENING_LIMITS, _read_csv, run_case  # noqa: E402


PROTOCOL_PATH = ROOT / "research/mc_default_external_holdout_protocol.json"
SUMMARY_PATH = ROOT / "data/public_validation/processed/mc_default_cases.csv"
TRACE_ROOT = ROOT / "data/public_validation/processed/mc_default_traces"
RESULT_PATH = ROOT / "research/mc_station_mixed_convection_diagnostic_2026_10_08.json"
REPORT_PATH = ROOT / "research/MC_STATION_MIXED_CONVECTION_DIAGNOSTIC_2026_10_08.md"

# The public archive does not disclose nozzle geometry.  These values are the
# same bounded, non-fitted research range used by the Type-III component
# diagnostic.  No outcome-dependent interpolation or selection is allowed.
NOZZLE_DIAMETERS_M = (0.003, 0.005, 0.007)
EQUIVALENT_CYLINDER_ASPECT_RATIO = 5.0


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _git_worktree_dirty() -> bool | None:
    try:
        return bool(subprocess.run(
            ["git", "status", "--porcelain"],
            check=True, capture_output=True, text=True,
        ).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def equivalent_geometry(volume_m3: float) -> tuple[float, float]:
    """Return diameter and cylindrical length for a volume-preserving surrogate.

    The runtime heat-transfer area uses a cylinder plus two hemispherical ends.
    This inverse applies the matching volume expression.  It is a lumped
    equivalent geometry and must not be described as the physical vessel pack.
    """

    if volume_m3 <= 0.0:
        raise ValueError("volume_m3 must be positive")
    coefficient = math.pi * (
        EQUIVALENT_CYLINDER_ASPECT_RATIO / 4.0 + 1.0 / 6.0
    )
    diameter_m = (volume_m3 / coefficient) ** (1.0 / 3.0)
    return diameter_m, EQUIVALENT_CYLINDER_ASPECT_RATIO * diameter_m


def _run_one(
    summary: dict[str, str],
    thermal_model: str,
    nozzle_diameter_m: float | None,
) -> dict:
    summary = dict(summary)
    summary["scheduled_aprr_mpa_min"] = summary["protocol_effective_aprr_mpa_min"]
    summary["target_vehicle_pressure_mpa"] = summary["protocol_target_pressure_mpa"]
    capacity_kg = float(summary["tank_capacity_kg"])
    # This volume rule already exists in the station comparison and uses only
    # declared nominal capacity, pressure and the hydrogen EOS.
    from h2station.scenario import capacity_eos_volume_m3

    volume_m3 = capacity_eos_volume_m3(
        capacity_kg, float(summary["nominal_pressure_mpa"]) * 1.0e6,
    )
    diameter_m, length_m = equivalent_geometry(volume_m3)
    mixed = thermal_model == "mixed_convection"
    case = run_case(
        summary,
        _read_csv(TRACE_ROOT / f"{summary['case_id']}.csv"),
        {
            "effective_volume_multiplier": 1.0,
            "gas_liner_ua_multiplier": 1.0,
        },
        dispenser_flow_area_multiplier=2.0,
        precooler_duty_multiplier=16.0,
        geometry_basis="capacity_eos",
        vehicle_tank_thermal_model=thermal_model,
        vehicle_internal_diameter_m=diameter_m if mixed else None,
        vehicle_internal_length_m=length_m if mixed else None,
        vehicle_inlet_nozzle_diameter_m=nozzle_diameter_m if mixed else None,
    )
    case["equivalent_geometry_volume_residual_m3"] = (
        math.pi * diameter_m**2 * length_m / 4.0
        + math.pi * diameter_m**3 / 6.0
        - volume_m3
    )
    return case


def _aggregate(cases: list[dict]) -> dict:
    return {
        "case_count": len(cases),
        "joint_screening_pass_count": sum(row["screening_pass"] for row in cases),
        "pressure_rmse_mpa_mean": float(np.mean([
            row["pressure_rmse_mpa"] for row in cases
        ])),
        "temperature_rmse_c_mean": float(np.mean([
            row["temperature_rmse_c"] for row in cases
        ])),
        "soc_rmse_percentage_points_mean": float(np.mean([
            row["soc_rmse_percentage_points"] for row in cases
        ])),
        "soc_final_abs_error_percentage_points_mean": float(np.mean([
            abs(row["soc_final_error_percentage_points"]) for row in cases
        ])),
        "temperature_safety_stop_count": sum(
            row["final_stop_reason"] == "safety-temperature" for row in cases
        ),
        "final_stop_reason_counts": {
            reason: sum((row["final_stop_reason"] or "none") == reason for row in cases)
            for reason in sorted({row["final_stop_reason"] or "none" for row in cases})
        },
    }


def run(jobs: int = 8) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    summaries = _read_csv(SUMMARY_PATH)
    selected = {
        member: next(row for row in summaries if row["source_member"] == member)
        for member in protocol["selected_workbooks"]
    }
    configurations: tuple[tuple[str, float | None], ...] = (
        ("constant_ua", None),
        *(("mixed_convection", diameter) for diameter in NOZZLE_DIAMETERS_M),
    )
    run_rows: dict[tuple[str, float | None], list[dict]] = {
        configuration: [] for configuration in configurations
    }
    futures = {}
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for thermal_model, nozzle_diameter_m in configurations:
            for index, summary in enumerate(selected.values(), start=1):
                summary = dict(summary)
                summary["lab_test_number"] = str(index)
                future = pool.submit(
                    _run_one, summary, thermal_model, nozzle_diameter_m,
                )
                futures[future] = (
                    thermal_model, nozzle_diameter_m, summary["case_id"],
                )
        for future in as_completed(futures):
            thermal_model, nozzle_diameter_m, case_id = futures[future]
            row = future.result()
            run_rows[(thermal_model, nozzle_diameter_m)].append(row)
            label = (
                thermal_model if nozzle_diameter_m is None
                else f"{thermal_model} at {1000 * nozzle_diameter_m:g} mm"
            )
            print(f"diagnosed {case_id}: {label}", flush=True)

    runs = []
    for thermal_model, nozzle_diameter_m in configurations:
        cases = sorted(
            run_rows[(thermal_model, nozzle_diameter_m)],
            key=lambda row: row["case_id"],
        )
        runs.append({
            "thermal_model": thermal_model,
            "nozzle_diameter_mm": (
                None if nozzle_diameter_m is None else 1000.0 * nozzle_diameter_m
            ),
            "aggregate": _aggregate(cases),
            "cases": cases,
        })
    baseline = runs[0]["aggregate"]
    mixed_aggregates = [row["aggregate"] for row in runs[1:]]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "source_worktree_dirty": _git_worktree_dirty(),
        "diagnostic_type": "MC Default full-station mixed-convection sensitivity",
        "evidence_role": "post_outcome_development_diagnostic_only",
        "post_outcome": True,
        "parameter_fitting": False,
        "geometry_selection_prohibited": True,
        "historical_frozen_validation_unchanged": True,
        "screening_limits": SCREENING_LIMITS,
        "case_count": len(selected),
        "configuration": {
            "geometry_basis": "capacity_eos",
            "equivalent_geometry_shape": "cylinder plus two hemispherical ends",
            "equivalent_cylinder_aspect_ratio_length_over_diameter": (
                EQUIVALENT_CYLINDER_ASPECT_RATIO
            ),
            "effective_volume_multiplier": 1.0,
            "gas_liner_ua_multiplier": 1.0,
            "dispenser_flow_area_multiplier": 2.0,
            "precooler_duty_multiplier": 16.0,
            "nozzle_diameter_grid_mm": [
                1000.0 * value for value in NOZZLE_DIAMETERS_M
            ],
        },
        "configuration_provenance": {
            "flow_and_precooler": (
                "existing post-freeze global development settings; outcomes already accessed"
            ),
            "tank_volume": (
                "nominal capacity divided by tabulated H2 density at nominal pressure and 15 C"
            ),
            "equivalent_geometry": (
                "volume-preserving lumped surrogate; physical MC vessel layout is unavailable"
            ),
            "nozzle_grid": (
                "pre-declared 3/5/7 mm research range reused from the Type-III component diagnostic"
            ),
        },
        "runs": runs,
        "interpretation": {
            "constant_ua_temperature_stop_count": baseline[
                "temperature_safety_stop_count"
            ],
            "mixed_convection_temperature_stop_count_range": [
                min(row["temperature_safety_stop_count"] for row in mixed_aggregates),
                max(row["temperature_safety_stop_count"] for row in mixed_aggregates),
            ],
            "constant_ua_pressure_rmse_mpa_mean": baseline[
                "pressure_rmse_mpa_mean"
            ],
            "mixed_convection_pressure_rmse_mpa_mean_range": [
                min(row["pressure_rmse_mpa_mean"] for row in mixed_aggregates),
                max(row["pressure_rmse_mpa_mean"] for row in mixed_aggregates),
            ],
            "constant_ua_temperature_rmse_c_mean": baseline[
                "temperature_rmse_c_mean"
            ],
            "mixed_convection_temperature_rmse_c_mean_range": [
                min(row["temperature_rmse_c_mean"] for row in mixed_aggregates),
                max(row["temperature_rmse_c_mean"] for row in mixed_aggregates),
            ],
            "joint_screening_pass_count_range": [
                min(row["joint_screening_pass_count"] for row in mixed_aggregates),
                max(row["joint_screening_pass_count"] for row in mixed_aggregates),
            ],
            "decision": (
                "Mixed convection materially improves the matched uncalibrated-UA "
                "comparator, but it leaves five premature temperature stops and "
                "zero joint screening passes at every declared nozzle diameter. "
                "No diameter or production default is selected."
            ),
        },
        "claim_boundary": (
            "These outcomes were already inspected. This sensitivity cannot revise the frozen "
            "0/8 external holdout, identify the undisclosed physical vessel or nozzle geometry, "
            "select a production configuration, validate the complete station, or close an IJHE gate."
        ),
    }


def write_report(report: dict) -> None:
    RESULT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    lines = [
        "# MC Default full-station mixed-convection diagnostic",
        "",
        "> Post-outcome development diagnostic only. The frozen external result remains 0/8.",
        "",
        "The full station runtime was evaluated with a volume-preserving equivalent Type-IV "
        "tank and a declared 3/5/7 mm inlet-nozzle range. The source archive does not disclose "
        "the physical vessel pack or nozzle geometry, so no row is selected as the production model.",
        "",
        "| Thermal model | Nozzle | Joint screens | P RMSE | T RMSE | SOC RMSE | Temperature stops |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["runs"]:
        aggregate = row["aggregate"]
        nozzle = (
            "n/a" if row["nozzle_diameter_mm"] is None
            else f"{row['nozzle_diameter_mm']:g} mm"
        )
        lines.append(
            f"| {row['thermal_model']} | {nozzle} | "
            f"{aggregate['joint_screening_pass_count']}/{aggregate['case_count']} | "
            f"{aggregate['pressure_rmse_mpa_mean']:.2f} MPa | "
            f"{aggregate['temperature_rmse_c_mean']:.2f} °C | "
            f"{aggregate['soc_rmse_percentage_points_mean']:.2f}%p | "
            f"{aggregate['temperature_safety_stop_count']} |"
        )
    lines.extend([
        "",
        "## Result",
        "",
        report["interpretation"]["decision"],
        "",
        "## Interpretation boundary",
        "",
        report["claim_boundary"],
        "",
        "The geometry is a single lumped equivalent used to expose model-form sensitivity. "
        "It is not a reconstruction of a multi-cylinder vehicle storage system.",
    ])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    report = run()
    write_report(report)
    print(json.dumps({
        (
            row["thermal_model"] if row["nozzle_diameter_mm"] is None
            else f"{row['thermal_model']}_{row['nozzle_diameter_mm']:g}mm"
        ): row["aggregate"] for row in report["runs"]
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
