"""Run a bounded partial-station validation diagnostic on public H2Protocol traces.

The public J2601 validation workbooks expose vehicle-side traces, while the
repository's full-station experiment also simulates an illustrative cascade
and compressor.  This runner therefore evaluates only the PCV/precooler/
hose/vehicle-tank path and makes the missing upstream boundary explicit.  It
is deliberately a development diagnostic until a prospectively selected
holdout with an independently measured upstream pressure/temperature trace is
available; its output must not be presented as full-station validation.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import zipfile
from typing import Any

import numpy as np

from h2station.public_validation import compare_traces
from h2station.public_validation import read_mc_default_workbook
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario
from h2station.validation import OutputChannel


SCREENING_LIMITS = {
    "pressure_rmse_mpa": 5.0,
    "temperature_rmse_c": 10.0,
    "soc_final_abs_error_percentage_points": 5.0,
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _float(row: dict[str, str], name: str) -> float:
    value = row.get(name, "")
    if value in ("", None, "None"):
        raise ValueError(f"Missing required {name}")
    return float(value)


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _git_dirty() -> bool | None:
    try:
        return bool(subprocess.run(
            ["git", "status", "--porcelain"], check=True,
            capture_output=True, text=True,
        ).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def _tank_volume(capacity_kg: float) -> float:
    # Public summaries provide capacity but not a machine-readable vessel CAD
    # volume.  Preserve the repository's disclosed Type-IV scaling assumption.
    return 0.122 * capacity_kg / 4.7


def _profile(rows: list[dict[str, str]], value: str) -> tuple[tuple[float, float], ...]:
    return tuple((_float(row, "time_s"), _float(row, value)) for row in rows)


def _load_fit(path: Path) -> dict[str, float]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return {
        "effective_volume_multiplier": float(value["tank_fit"]["effective_volume_multiplier"]),
        "gas_liner_ua_multiplier": float(value["tank_fit"]["gas_liner_ua_multiplier"]),
        "dispenser_flow_area_multiplier": float(value["dispenser_flow_area_multiplier"]),
        "precooler_duty_multiplier": float(value["precooler_duty_multiplier"]),
    }


def run_case(
    summary: dict[str, str],
    rows: list[dict[str, str]],
    fit: dict[str, float],
    *,
    supply_pressure_mpa: float = 90.0,
    use_inlet_profile_for_supply_temperature: bool = True,
    maximum_gas_temperature_k: float = 358.15,
    supply_pressure_profile_mpa: tuple[tuple[float, float], ...] | None = None,
    pressure_reference_profile_mpa: tuple[tuple[float, float], ...] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    case_id = summary["case_id"]
    time_s = np.asarray([_float(row, "time_s") for row in rows], dtype=float)
    pressure_mpa = np.asarray([_float(row, "pressure_mpa") for row in rows], dtype=float)
    temperature_c = np.asarray([
        _float(row, "tank_temperature_mean_c") for row in rows
    ], dtype=float)
    soc_percent = np.asarray([_float(row, "soc_percent") for row in rows], dtype=float)
    inlet_c = np.asarray([
        _float(row, "inlet_gas_temperature_c") for row in rows
    ], dtype=float)
    flow_g_s = np.asarray([_float(row, "mass_flow_g_s") for row in rows], dtype=float)
    chamber_c = np.asarray([
        _float(row, "chamber_temperature_c") for row in rows
    ], dtype=float)
    dt = float(np.median(np.diff(time_s)))
    if dt <= 0.0:
        raise ValueError(f"{case_id} time values must be strictly increasing")

    # H2Protocol does not publish an upstream compressor/bank pressure trace.
    # A constant 90 MPa source is a declared boundary assumption, not a
    # recovered measurement.  The measured inlet-temperature profile is used
    # as the delivery/thermal boundary and is retained in the report.
    inlet_profile_k = tuple((float(t), float(value + 273.15)) for t, value in zip(time_s, inlet_c))
    supply_temperature_profile = inlet_profile_k if use_inlet_profile_for_supply_temperature else ()
    boundary_profile = supply_pressure_profile_mpa or ((0.0, supply_pressure_mpa),)
    config = ReferenceScenario(
        duration_s=float(time_s[-1]),
        control_period_s=dt,
        ambient_temperature_k=float(np.median(chamber_c) + 273.15),
        initial_vehicle_pressure_pa=float(pressure_mpa[0] * 1.0e6),
        initial_vehicle_temperature_k=float(temperature_c[0] + 273.15),
        vehicle_internal_volume_m3=_tank_volume(_float(summary, "tank_capacity_kg")),
        vehicle_nominal_working_pressure_pa=_float(summary, "nominal_pressure_mpa") * 1.0e6,
        vehicle_effective_volume_multiplier=fit["effective_volume_multiplier"],
        vehicle_gas_liner_ua_multiplier=fit["gas_liner_ua_multiplier"],
        dispenser_flow_area_multiplier=fit["dispenser_flow_area_multiplier"],
        precooler_duty_multiplier=fit["precooler_duty_multiplier"],
        target_vehicle_pressure_pa=float(pressure_mpa[-1] * 1.0e6),
        average_pressure_ramp_rate_pa_s=(
            _float(summary, "scheduled_aprr_mpa_min") * 1.0e6 / 60.0
        ),
        delivery_temperature_k=float(np.median(inlet_c) + 273.15),
        maximum_gas_temperature_k=maximum_gas_temperature_k,
        delivery_temperature_profile_k=inlet_profile_k,
        pressure_reference_profile_pa=(
            tuple((float(time), float(value * 1.0e6)) for time, value in pressure_reference_profile_mpa)
            if pressure_reference_profile_mpa is not None else ()
        ),
        supply_pressure_profile_pa=tuple(
            (float(time), float(value * 1.0e6)) for time, value in boundary_profile
        ),
        supply_temperature_profile_k=supply_temperature_profile,
        maximum_mass_flow_kg_s=0.060,
        risk_update_period_s=max(float(time_s[-1]) + 1.0, 3600.0),
    )
    built = build_reference_scenario(config, UnavailableHyRAMBackend())
    trajectory = built.station.partial_station.simulate(
        built.initial_state.partial_station,
        float(time_s[-1]),
        controller_period_s=dt,
    )
    predicted_pressure_mpa = trajectory.channels[OutputChannel.VEHICLE_GAS_PRESSURE] / 1.0e6
    predicted_temperature_c = trajectory.channels[OutputChannel.VEHICLE_GAS_TEMPERATURE] - 273.15
    predicted_soc_percent = 100.0 * trajectory.channels[OutputChannel.VEHICLE_SOC]
    agreement = compare_traces(
        experimental_time_s=time_s,
        experimental_pressure_mpa=pressure_mpa,
        experimental_temperature_c=temperature_c,
        experimental_soc_percent=soc_percent,
        predicted_time_s=trajectory.time_s,
        predicted_pressure_mpa=predicted_pressure_mpa,
        predicted_temperature_c=predicted_temperature_c,
        predicted_soc_percent=predicted_soc_percent,
    )
    flow_on_experimental_clock = 1000.0 * np.interp(
        time_s, trajectory.time_s,
        trajectory.channels[OutputChannel.DISPENSED_MASS_FLOW],
    )
    coverage = float(trajectory.time_s[-1] / time_s[-1]) if time_s[-1] > 0.0 else 0.0
    screen = (
        coverage >= 0.95
        and agreement.pressure_rmse_mpa <= SCREENING_LIMITS["pressure_rmse_mpa"]
        and agreement.temperature_rmse_c <= SCREENING_LIMITS["temperature_rmse_c"]
        and abs(agreement.soc_final_error_percentage_points)
        <= SCREENING_LIMITS["soc_final_abs_error_percentage_points"]
    )
    predicted_flow = flow_on_experimental_clock
    trace_rows = []
    for index, t in enumerate(time_s):
        model_index = min(index, len(trajectory.time_s) - 1)
        trace_rows.append({
            "time_s": float(t),
            "experimental_pressure_mpa": float(pressure_mpa[index]),
            "predicted_pressure_mpa": float(np.interp(t, trajectory.time_s, predicted_pressure_mpa)),
            "experimental_temperature_c": float(temperature_c[index]),
            "predicted_temperature_c": float(np.interp(t, trajectory.time_s, predicted_temperature_c)),
            "experimental_soc_percent": float(soc_percent[index]),
            "predicted_soc_percent": float(np.interp(t, trajectory.time_s, predicted_soc_percent)),
            "experimental_mass_flow_g_s": float(flow_g_s[index]),
            "predicted_mass_flow_g_s": float(predicted_flow[index]),
            "predicted_time_s": float(trajectory.time_s[model_index]),
        })
    row = {
        "case_id": case_id,
        "lab_test_number": int(float(summary["lab_test_number"])),
        "test_code": summary["test_code"],
        "tank_capacity_kg": _float(summary, "tank_capacity_kg"),
        "nominal_working_pressure_mpa": _float(summary, "nominal_pressure_mpa"),
        "tank_volume_assumed_m3": config.vehicle_internal_volume_m3,
        "experimental_duration_s": float(time_s[-1]),
        "simulated_duration_s": float(trajectory.time_s[-1]),
        "simulation_coverage_fraction": coverage,
        "experimental_final_pressure_mpa": float(pressure_mpa[-1]),
        "predicted_final_pressure_mpa": float(predicted_pressure_mpa[-1]),
        "experimental_peak_temperature_c": float(np.max(temperature_c)),
        "predicted_peak_temperature_c": float(np.max(predicted_temperature_c)),
        "experimental_final_soc_percent": float(soc_percent[-1]),
        "predicted_final_soc_percent": float(predicted_soc_percent[-1]),
        "predicted_peak_mass_flow_g_s": float(np.max(predicted_flow)),
        "flow_rmse_g_s": float(np.sqrt(np.mean((predicted_flow - flow_g_s) ** 2))),
        "stop_reason": trajectory.stop_reason,
        "maximum_gas_temperature_k": maximum_gas_temperature_k,
        "boundary_supply_pressure_mpa": float(boundary_profile[0][1]),
        "boundary_supply_pressure_profile_used": supply_pressure_profile_mpa is not None,
        "boundary_supply_pressure_final_mpa": float(boundary_profile[-1][1]),
        "pressure_reference_profile_used": pressure_reference_profile_mpa is not None,
        "delivery_temperature_profile_used": True,
        "supply_temperature_profile_used": use_inlet_profile_for_supply_temperature,
        "evidence_role": "development_diagnostic_only",
        "screening_pass": bool(screen),
        **agreement.to_dict(),
    }
    return row, trace_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=Path("data/public_validation/processed"))
    parser.add_argument("--fit", type=Path, default=Path("research/closed_loop_development_v2.json"))
    parser.add_argument("--output", type=Path, default=Path("data/public_validation/results/partial_station_profile_diagnostic"))
    parser.add_argument(
        "--raw-mc-archive", type=Path,
        default=Path("data/public_validation/raw/h2protocol_mc_default/SAE J2601 MC Default Bench Test Data.zip"),
    )
    parser.add_argument("--case-ids", nargs="*", default=None)
    parser.add_argument(
        "--dataset", choices=("h2protocol", "mc_default"), default="h2protocol",
        help="Use the Tables Method traces or the already-consumed MC Default traces.",
    )
    parser.add_argument("--supply-pressure-mpa", type=float, default=90.0)
    parser.add_argument(
        "--use-source-pressure-profile", action="store_true",
        help="For MC Default traces, use a published source pressure trace as the partial-station upstream boundary.",
    )
    parser.add_argument(
        "--source-pressure-column",
        choices=("source_pressure_1_mpa", "source_pressure_3_mpa"),
        default="source_pressure_1_mpa",
        help="MC Default source-pressure channel used when --use-source-pressure-profile is enabled.",
    )
    parser.add_argument("--constant-supply-temperature", action="store_true")
    parser.add_argument(
        "--use-protocol-pressure-profile", action="store_true",
        help="For MC Default traces, use the workbook's published pressure schedule as the controller reference.",
    )
    parser.add_argument(
        "--maximum-gas-temperature-c", type=float, default=85.0,
        help="Controller gas-temperature stop used for the diagnostic; use a high value only for a declared physics-only sensitivity.",
    )
    args = parser.parse_args()

    if args.dataset == "h2protocol":
        summary_name = "h2protocol_cases.csv"
        trace_dir_name = "h2protocol_traces"
        source_name = "Powertech Labs SAE J2601 Tables Method validation traces"
    else:
        summary_name = "mc_default_cases.csv"
        trace_dir_name = "mc_default_traces"
        source_name = "Powertech Labs SAE J2601 MC Default bench traces"
    summaries = _read_csv(args.processed / summary_name)
    if args.dataset == "mc_default":
        for index, summary in enumerate(summaries, start=1):
            summary["lab_test_number"] = str(index)
            summary["scheduled_aprr_mpa_min"] = summary["protocol_effective_aprr_mpa_min"]
            summary["target_vehicle_pressure_mpa"] = summary["protocol_target_pressure_mpa"]
    protocol_profiles: dict[str, tuple[tuple[float, float], ...]] = {}
    if args.use_protocol_pressure_profile:
        if args.dataset != "mc_default":
            raise SystemExit("--use-protocol-pressure-profile is available for --dataset mc_default only")
        if not args.raw_mc_archive.is_file():
            raise SystemExit(f"MC raw archive not found: {args.raw_mc_archive}")
        with zipfile.ZipFile(args.raw_mc_archive) as archive:
            for summary in summaries:
                member = summary.get("source_member", "")
                if not member or member not in archive.namelist():
                    raise SystemExit(f"MC raw archive is missing {member!r}")
                trace_object = read_mc_default_workbook(
                    archive.read(member),
                    source_archive=args.raw_mc_archive.name,
                    source_member=member,
                )
                if trace_object.protocol_pressure_time_s is None or trace_object.protocol_pressure_mpa is None:
                    raise SystemExit(f"MC workbook has no protocol pressure schedule: {member}")
                protocol_profiles[summary["case_id"]] = tuple(
                    (float(time), float(pressure))
                    for time, pressure in zip(
                        trace_object.protocol_pressure_time_s,
                        trace_object.protocol_pressure_mpa,
                    )
                )
    selected = set(args.case_ids or [row["case_id"] for row in summaries])
    summaries = [row for row in summaries if row["case_id"] in selected]
    if not summaries:
        raise SystemExit("No case IDs selected")
    fit = _load_fit(args.fit)
    rows: list[dict[str, Any]] = []
    args.output.mkdir(parents=True, exist_ok=True)
    trace_dir = args.output / "traces"
    trace_dir.mkdir(exist_ok=True)
    for summary in sorted(summaries, key=lambda value: int(float(value["lab_test_number"]))):
        trace = _read_csv(args.processed / trace_dir_name / f"{summary['case_id']}.csv")
        source_profile = None
        if args.use_source_pressure_profile:
            if not all(row.get(args.source_pressure_column, "") not in ("", None) for row in trace):
                raise SystemExit(
                    f"--use-source-pressure-profile requires {args.source_pressure_column} in every selected trace"
                )
            source_profile = tuple(
                (_float(row, "time_s"), _float(row, args.source_pressure_column))
                for row in trace
            )
        metric, trace_rows = run_case(
            summary, trace, fit,
            supply_pressure_mpa=args.supply_pressure_mpa,
            use_inlet_profile_for_supply_temperature=not args.constant_supply_temperature,
            maximum_gas_temperature_k=args.maximum_gas_temperature_c + 273.15,
            supply_pressure_profile_mpa=source_profile,
            pressure_reference_profile_mpa=protocol_profiles.get(summary["case_id"]),
        )
        rows.append(metric)
        with (trace_dir / f"{summary['case_id']}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(trace_rows[0]))
            writer.writeheader(); writer.writerows(trace_rows)
        print(f"evaluated {summary['case_id']} ({metric['screening_pass']})", flush=True)

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_role": "development_diagnostic_only",
        "claim_boundary": (
            "This is a bounded PCV/precooler/hose/vehicle-tank diagnostic. "
            "It is not independent external full-station validation and cannot "
            "support an IJHE full digital-twin performance claim."
        ),
        "protocol": {
            "source": source_name,
            "fresh_holdout": False,
            "outcomes_inspected_before_run": True,
            "upstream_pressure_trace_available": args.use_source_pressure_profile,
            "boundary_assumption": (
                f"published {args.source_pressure_column} trace used as upstream boundary; inlet gas temperature profile used as delivery thermal boundary"
                if args.use_source_pressure_profile else
                "constant 90 MPa upstream source pressure; inlet gas temperature profile used as delivery thermal boundary"
            ),
            "source_pressure_profile_used": args.use_source_pressure_profile,
            "source_pressure_column": (
                args.source_pressure_column if args.use_source_pressure_profile else None
            ),
            "source_temperature_profile_assumption": not args.constant_supply_temperature,
            "protocol_pressure_profile_used": args.use_protocol_pressure_profile,
            "raw_mc_archive": str(args.raw_mc_archive) if args.use_protocol_pressure_profile else None,
        "dataset": args.dataset,
            "maximum_gas_temperature_c": args.maximum_gas_temperature_c,
            "temperature_stop_mode": (
                "declared_physics_only_sensitivity"
                if args.maximum_gas_temperature_c > 150.0 else "safety_aware_controller"
            ),
        },
        "source_commit": _git_commit(),
        "source_worktree_dirty": _git_dirty(),
        "fit": fit,
        "screening_limits": SCREENING_LIMITS,
        "case_count": len(rows),
        "screening_pass_count": sum(bool(row["screening_pass"]) for row in rows),
        "aggregate": {
            name: float(np.mean([row[name] for row in rows]))
            for name in ("pressure_rmse_mpa", "temperature_rmse_c", "soc_rmse_percentage_points", "simulation_coverage_fraction")
        },
        "cases": rows,
    }
    (args.output / "validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (args.output / "case_metrics.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print(json.dumps({
        "case_count": len(rows),
        "screening_pass_count": report["screening_pass_count"],
        "output": str(args.output / "validation.json"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
