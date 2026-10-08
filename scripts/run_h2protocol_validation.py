"""Run a declared station-model configuration against normalized J2601 tests.

The experiment supplies initial/boundary conditions. The report records whether
global fitted parameters were loaded; no case-specific parameter is estimated
here. This is a research comparison and not a claim of SAE certification.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess

import numpy as np

from h2station.api import ProcessSettings
from h2station.operations import ProcessRuntime
from h2station.public_validation import compare_traces
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import (
    ReferenceScenario,
    build_reference_scenario,
    capacity_eos_volume_m3,
)


SCREENING_LIMITS = {
    "pressure_rmse_mpa": 5.0,
    "temperature_rmse_c": 10.0,
    "soc_final_abs_error_percentage_points": 5.0,
}


def _float(row: dict[str, str], name: str) -> float:
    value = row.get(name, "")
    if value in ("", "None", None):
        raise ValueError(f"Missing required {name}")
    return float(value)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _git_worktree_dirty() -> bool | None:
    try:
        output = subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return bool(output.strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def _tank_volume_from_nominal_capacity(capacity_kg: float) -> float:
    # The production demonstrator uses a 0.122 m3, 4.7 kg Type-IV surrogate.
    # Public files identify nominal capacity but not a machine-readable vessel
    # volume, so volume and thermal masses are scaled together.  The assumption
    # is emitted into every result row and must be replaced when exact geometry
    # becomes available.
    return 0.122 * capacity_kg / 4.7


def equivalent_capsule_geometry(
    volume_m3: float,
    cylindrical_length_to_diameter: float,
) -> tuple[float, float]:
    """Return a volume-preserving cylinder with two hemispherical ends.

    Public J2601 case tables declare nominal tank capacity but do not identify
    the physical vessel pack.  This helper therefore creates only a lumped
    research surrogate.  The aspect ratio must be declared before execution;
    the validation runner never estimates it from case outcomes.
    """

    if volume_m3 <= 0.0:
        raise ValueError("volume_m3 must be positive")
    if cylindrical_length_to_diameter <= 0.0:
        raise ValueError("cylindrical_length_to_diameter must be positive")
    coefficient = math.pi * (
        cylindrical_length_to_diameter / 4.0 + 1.0 / 6.0
    )
    diameter_m = (volume_m3 / coefficient) ** (1.0 / 3.0)
    return diameter_m, cylindrical_length_to_diameter * diameter_m


def run_case(
    summary: dict[str, str],
    trace_rows: list[dict[str, str]],
    tank_fit: dict[str, float] | None = None,
    dispenser_flow_area_multiplier: float = 1.0,
    precooler_duty_multiplier: float = 1.0,
    geometry_basis: str = "capacity_scaled",
    vehicle_tank_thermal_model: str = "constant_ua",
    vehicle_internal_diameter_m: float | None = None,
    vehicle_internal_length_m: float | None = None,
    vehicle_inlet_nozzle_diameter_m: float | None = None,
    vehicle_equivalent_capsule_aspect_ratio: float | None = None,
) -> dict:
    case_id = summary["case_id"]
    exp_time = np.asarray([_float(row, "time_s") for row in trace_rows])
    exp_pressure = np.asarray([_float(row, "pressure_mpa") for row in trace_rows])
    exp_temperature = np.asarray([
        _float(row, "tank_temperature_mean_c") for row in trace_rows
    ])
    exp_soc = np.asarray([_float(row, "soc_percent") for row in trace_rows])
    chamber = np.asarray([_float(row, "chamber_temperature_c") for row in trace_rows])
    inlet_temperature = np.asarray([
        _float(row, "inlet_gas_temperature_c") for row in trace_rows
    ])
    experimental_mass_flow_g_s = np.asarray([
        _float(row, "mass_flow_g_s") for row in trace_rows
    ])
    tank_capacity = _float(summary, "tank_capacity_kg")
    scheduled_aprr = _float(summary, "scheduled_aprr_mpa_min")
    nominal_pressure_mpa = _float(summary, "nominal_pressure_mpa")
    if geometry_basis == "capacity_scaled":
        tank_volume = _tank_volume_from_nominal_capacity(tank_capacity)
    elif geometry_basis == "capacity_eos":
        tank_volume = capacity_eos_volume_m3(
            tank_capacity,
            nominal_pressure_mpa * 1.0e6,
        )
    else:
        raise ValueError(
            "geometry_basis must be 'capacity_scaled' or 'capacity_eos'"
        )
    geometry_derivation = (
        "explicit_dimensions"
        if vehicle_tank_thermal_model == "mixed_convection"
        else "not_required"
    )
    if vehicle_tank_thermal_model == "mixed_convection":
        explicit_geometry = (
            vehicle_internal_diameter_m is not None
            or vehicle_internal_length_m is not None
        )
        if explicit_geometry and vehicle_equivalent_capsule_aspect_ratio is not None:
            raise ValueError(
                "Do not combine explicit tank dimensions with an equivalent-capsule "
                "aspect ratio"
            )
        if vehicle_equivalent_capsule_aspect_ratio is not None:
            vehicle_internal_diameter_m, vehicle_internal_length_m = (
                equivalent_capsule_geometry(
                    tank_volume,
                    vehicle_equivalent_capsule_aspect_ratio,
                )
            )
            geometry_derivation = "volume_preserving_equivalent_capsule"
        required = {
            "vehicle_internal_diameter_m": vehicle_internal_diameter_m,
            "vehicle_internal_length_m": vehicle_internal_length_m,
            "vehicle_inlet_nozzle_diameter_m": vehicle_inlet_nozzle_diameter_m,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise ValueError(
                "mixed_convection requires explicit geometry or a declared "
                "equivalent-capsule aspect ratio: " + ", ".join(missing)
            )
    elif any(value is not None for value in (
        vehicle_internal_diameter_m,
        vehicle_internal_length_m,
        vehicle_inlet_nozzle_diameter_m,
        vehicle_equivalent_capsule_aspect_ratio,
    )):
        raise ValueError(
            "Tank/nozzle geometry options require vehicle_tank_thermal_model="
            "'mixed_convection'"
        )
    tank_fit = tank_fit or {
        "effective_volume_multiplier": 1.0,
        "gas_liner_ua_multiplier": 1.0,
    }
    dt = float(np.median(np.diff(exp_time)))
    model_target_pressure_mpa = float(
        summary.get("target_vehicle_pressure_mpa") or exp_pressure[-1]
    )
    config = ReferenceScenario(
        duration_s=float(exp_time[-1]),
        control_period_s=dt,
        ambient_temperature_k=float(np.median(chamber) + 273.15),
        initial_vehicle_pressure_pa=float(exp_pressure[0] * 1.0e6),
        initial_vehicle_temperature_k=float(exp_temperature[0] + 273.15),
        vehicle_internal_volume_m3=tank_volume,
        vehicle_nominal_working_pressure_pa=nominal_pressure_mpa * 1.0e6,
        vehicle_effective_volume_multiplier=float(tank_fit["effective_volume_multiplier"]),
        vehicle_gas_liner_ua_multiplier=float(tank_fit["gas_liner_ua_multiplier"]),
        vehicle_tank_thermal_model=vehicle_tank_thermal_model,
        vehicle_internal_diameter_m=vehicle_internal_diameter_m,
        vehicle_internal_length_m=vehicle_internal_length_m,
        vehicle_inlet_nozzle_diameter_m=vehicle_inlet_nozzle_diameter_m,
        dispenser_flow_area_multiplier=dispenser_flow_area_multiplier,
        precooler_duty_multiplier=precooler_duty_multiplier,
        vehicle_2_internal_diameter_m=vehicle_internal_diameter_m,
        vehicle_2_internal_length_m=vehicle_internal_length_m,
        vehicle_2_inlet_nozzle_diameter_m=vehicle_inlet_nozzle_diameter_m,
        target_vehicle_pressure_pa=model_target_pressure_mpa * 1.0e6,
        average_pressure_ramp_rate_pa_s=scheduled_aprr * 1.0e6 / 60.0,
        delivery_temperature_k=float(np.median(inlet_temperature) + 273.15),
        maximum_mass_flow_kg_s=0.060,
        risk_update_period_s=max(float(exp_time[-1]) + 1.0, 3600.0),
    )
    built = build_reference_scenario(config, UnavailableHyRAMBackend())
    settings = ProcessSettings(
        vehicle_1=True,
        vehicle_1_auto_stop=True,
        vehicle_1_target_pressure_mpa=float(exp_pressure[-1]),
    ).model_dump()
    built.simulator.process_runtime = ProcessRuntime(settings)
    operation_samples = []
    trajectory = built.simulator.simulate(
        built.initial_state,
        float(exp_time[-1]),
        dt,
        pace_idle=False,
        sample_callback=operation_samples.append,
    )
    runtime_snapshot = built.simulator.process_runtime.snapshot()
    process_stop_reason = runtime_snapshot["stop_reason"]["vehicle_1"]
    reference_density = (
        built.station.partial_station.controller.soc_model.reference_density_kg_m3
    )
    predicted_soc = 100.0 * trajectory.vehicle_density_kg_m3 / reference_density
    agreement = compare_traces(
        experimental_time_s=exp_time,
        experimental_pressure_mpa=exp_pressure,
        experimental_temperature_c=exp_temperature,
        experimental_soc_percent=exp_soc,
        predicted_time_s=trajectory.time_s,
        predicted_pressure_mpa=trajectory.vehicle_pressure_pa / 1.0e6,
        predicted_temperature_c=trajectory.vehicle_temperature_k - 273.15,
        predicted_soc_percent=predicted_soc,
    )
    metrics = agreement.to_dict()
    predicted_flow_on_experimental_clock_g_s = 1000.0 * np.interp(
        exp_time, trajectory.time_s, trajectory.nozzle_mass_flow_kg_s
    )
    flow_error_g_s = (
        predicted_flow_on_experimental_clock_g_s - experimental_mass_flow_g_s
    )
    half_time = float(exp_time[0] + 0.5 * (exp_time[-1] - exp_time[0]))
    before_half = exp_time <= half_time
    if np.count_nonzero(before_half) < 2:
        raise RuntimeError(f"{case_id} has insufficient samples before half time")
    experimental_total_mass = float(np.trapezoid(
        experimental_mass_flow_g_s / 1000.0, exp_time
    ))
    predicted_total_mass = float(np.trapezoid(
        predicted_flow_on_experimental_clock_g_s / 1000.0, exp_time
    ))
    experimental_first_half_mass = float(np.trapezoid(
        experimental_mass_flow_g_s[before_half] / 1000.0,
        exp_time[before_half],
    ))
    predicted_first_half_mass = float(np.trapezoid(
        predicted_flow_on_experimental_clock_g_s[before_half] / 1000.0,
        exp_time[before_half],
    ))
    model_time = np.asarray([sample.time_s for sample in operation_samples])
    active_mask = np.asarray([
        command.phase.value == "filling" and command.stop_reason is None
        for command in trajectory.fueling_commands
    ])
    if not np.any(active_mask):
        raise RuntimeError(f"{case_id} produced no active fueling samples")
    active_time = model_time[active_mask]
    model_hose_temperature_c = np.asarray([
        sample.hose_temperature_k - 273.15 for sample in operation_samples
    ])[active_mask]
    model_precooler_temperature_c = np.asarray([
        sample.precooler_outlet_temperature_k - 273.15
        for sample in operation_samples
    ])[active_mask]
    experimental_inlet_on_model_clock = np.interp(
        active_time, exp_time, inlet_temperature
    )
    pressure_reference_mpa = np.asarray([
        command.reference_pressure_pa / 1.0e6
        for command in trajectory.fueling_commands
    ])[active_mask]
    vehicle_pressure_mpa = trajectory.vehicle_pressure_pa[active_mask] / 1.0e6
    reference_lag_mpa = pressure_reference_mpa - vehicle_pressure_mpa
    dispatch_counts = Counter(
        bank for bank, active in zip(trajectory.dispatch_bank, active_mask) if active
    )
    last_active_index = int(np.flatnonzero(active_mask)[-1])
    final_bank_pressures_mpa = {
        name: float(pressure_pa / 1.0e6)
        for name, pressure_pa in operation_samples[
            last_active_index
        ].bank_pressure_pa.items()
    }
    final_command = trajectory.fueling_commands[-1]
    first_stopped = next(
        (
            (float(time_s), command.stop_reason)
            for time_s, command in zip(trajectory.time_s, trajectory.fueling_commands)
            if command.stop_reason
        ),
        (None, None),
    )
    screening_pass = (
        metrics["pressure_rmse_mpa"] <= SCREENING_LIMITS["pressure_rmse_mpa"]
        and metrics["temperature_rmse_c"] <= SCREENING_LIMITS["temperature_rmse_c"]
        and abs(metrics["soc_final_error_percentage_points"])
        <= SCREENING_LIMITS["soc_final_abs_error_percentage_points"]
    )
    return {
        "case_id": case_id,
        "lab_test_number": int(float(summary["lab_test_number"])),
        "test_code": summary["test_code"],
        "tank_capacity_kg": tank_capacity,
        "nominal_working_pressure_mpa": nominal_pressure_mpa,
        "tank_volume_assumed_m3": tank_volume,
        "geometry_basis": geometry_basis,
        "effective_volume_multiplier": float(tank_fit["effective_volume_multiplier"]),
        "gas_liner_ua_multiplier": float(tank_fit["gas_liner_ua_multiplier"]),
        "vehicle_tank_thermal_model": vehicle_tank_thermal_model,
        "vehicle_internal_diameter_m": vehicle_internal_diameter_m,
        "vehicle_internal_length_m": vehicle_internal_length_m,
        "vehicle_inlet_nozzle_diameter_m": vehicle_inlet_nozzle_diameter_m,
        "vehicle_equivalent_capsule_aspect_ratio": (
            vehicle_equivalent_capsule_aspect_ratio
        ),
        "vehicle_geometry_derivation": geometry_derivation,
        "dispenser_flow_area_multiplier": dispenser_flow_area_multiplier,
        "precooler_duty_multiplier": precooler_duty_multiplier,
        "chamber_temperature_c": _float(summary, "chamber_temperature_c"),
        "scheduled_aprr_mpa_min": scheduled_aprr,
        "experimental_duration_s": float(exp_time[-1]),
        "experimental_final_pressure_mpa": float(exp_pressure[-1]),
        "model_target_pressure_mpa": model_target_pressure_mpa,
        "experimental_peak_temperature_c": float(np.max(exp_temperature)),
        "experimental_final_soc_percent": float(exp_soc[-1]),
        "predicted_final_pressure_mpa": float(trajectory.vehicle_pressure_pa[-1] / 1.0e6),
        "predicted_peak_temperature_c": float(np.max(trajectory.vehicle_temperature_k) - 273.15),
        "predicted_final_soc_percent": float(predicted_soc[-1]),
        "predicted_peak_mass_flow_g_s": float(1000.0 * np.max(trajectory.nozzle_mass_flow_kg_s)),
        "mass_flow_rmse_g_s": float(np.sqrt(np.mean(flow_error_g_s ** 2))),
        "mass_flow_peak_error_g_s": float(
            np.max(predicted_flow_on_experimental_clock_g_s)
            - np.max(experimental_mass_flow_g_s)
        ),
        "experimental_first_half_mass_fraction": (
            experimental_first_half_mass / experimental_total_mass
            if experimental_total_mass > 0.0 else None
        ),
        "predicted_first_half_mass_fraction": (
            predicted_first_half_mass / predicted_total_mass
            if predicted_total_mass > 0.0 else None
        ),
        "active_fueling_duration_s": float(active_time[-1] - active_time[0]),
        "active_pressure_reference_tracking_rmse_mpa": float(
            np.sqrt(np.mean(reference_lag_mpa ** 2))
        ),
        "active_pressure_reference_final_lag_mpa": float(reference_lag_mpa[-1]),
        "active_hose_inlet_temperature_rmse_c": float(np.sqrt(np.mean(
            (model_hose_temperature_c - experimental_inlet_on_model_clock) ** 2
        ))),
        "active_precooler_outlet_temperature_rmse_c": float(np.sqrt(np.mean(
            (model_precooler_temperature_c - experimental_inlet_on_model_clock) ** 2
        ))),
        "active_dispatch_sample_counts": {
            str(name or "none"): int(count) for name, count in dispatch_counts.items()
        },
        "bank_pressures_at_active_end_mpa": final_bank_pressures_mpa,
        "experimental_transferred_mass_kg": experimental_total_mass,
        "predicted_transferred_mass_kg": float(
            np.trapezoid(trajectory.nozzle_mass_flow_kg_s, trajectory.time_s)
        ),
        "final_fueling_phase": final_command.phase.value,
        "final_stop_reason": process_stop_reason,
        "controller_final_stop_reason": final_command.stop_reason,
        "first_stop_time_s": first_stopped[0],
        "first_stop_reason": first_stopped[1],
        **metrics,
        "screening_pass": screening_pass,
        "volume_assumption": (
            "hydrogen EOS density at declared nominal working pressure and 15 °C"
            if geometry_basis == "capacity_eos"
            else "0.122 m3 per 4.7 kg nominal capacity, linearly scaled"
        ),
    }


def _run_case_file(
    summary: dict[str, str],
    trace_path: Path,
    tank_fit: dict[str, float] | None,
    dispenser_flow_area_multiplier: float,
    precooler_duty_multiplier: float = 1.0,
    geometry_basis: str = "capacity_scaled",
    vehicle_tank_thermal_model: str = "constant_ua",
    vehicle_internal_diameter_m: float | None = None,
    vehicle_internal_length_m: float | None = None,
    vehicle_inlet_nozzle_diameter_m: float | None = None,
    vehicle_equivalent_capsule_aspect_ratio: float | None = None,
) -> dict:
    return run_case(
        summary,
        _read_csv(trace_path),
        tank_fit,
        dispenser_flow_area_multiplier,
        precooler_duty_multiplier,
        geometry_basis,
        vehicle_tank_thermal_model,
        vehicle_internal_diameter_m,
        vehicle_internal_length_m,
        vehicle_inlet_nozzle_diameter_m,
        vehicle_equivalent_capsule_aspect_ratio,
    )


def _bootstrap_ci(values: list[float], *, seed: int = 2601) -> list[float]:
    array = np.asarray(values, dtype=float)
    if len(array) == 1:
        return [float(array[0]), float(array[0])]
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(10000, len(array)))
    means = np.mean(array[indices], axis=1)
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def _aggregate(rows: list[dict]) -> dict:
    metric_names = (
        "pressure_rmse_mpa", "pressure_mae_mpa", "temperature_rmse_c",
        "temperature_mae_c", "soc_rmse_percentage_points",
    )
    metrics = {}
    for name in metric_names:
        values = [float(row[name]) for row in rows]
        metrics[name] = {
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "standard_deviation": (
                float(np.std(values, ddof=1)) if len(values) > 1 else None
            ),
            "mean_bootstrap_95_ci": _bootstrap_ci(values),
        }
    return {
        "case_count": len(rows),
        "screening_pass_count": sum(bool(row["screening_pass"]) for row in rows),
        "screening_pass_fraction": float(np.mean([row["screening_pass"] for row in rows])),
        "final_stop_reason_counts": dict(Counter(
            str(row["final_stop_reason"] or "none") for row in rows
        )),
        "metrics": metrics,
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(path: Path, report: dict) -> None:
    aggregate = report["aggregate"]
    calibrated = (
        report["tank_fit"] is not None
        or report["dispenser_flow_area_multiplier"] != 1.0
        or report["precooler_duty_multiplier"] != 1.0
    )
    title = (
        "SAE J2601 public-data closed-loop comparison"
        if calibrated else "SAE J2601 public-data uncalibrated baseline"
    )
    worktree_state = report.get("source_worktree_dirty")
    configuration_note = (
        "This run uses global parameters selected on separate development cases. "
        "It is an internal confirmation/iteration result, not a pristine external "
        "holdout, SAE certification, or field-safety validation."
        if calibrated else
        "This is an uncalibrated baseline comparison. It is not SAE certification "
        "or field-safety validation."
    )
    lines = [
        f"# {title}",
        "",
        f"Generated: {report['generated_at']}",
        f"Source commit: `{report['source_commit']}`",
        f"Source worktree dirty: `{worktree_state}`",
        f"Cases: {aggregate['case_count']}",
        "",
        f"> {configuration_note}",
        "",
        "## Model configuration",
        "",
        f"- Tank fit source: `{report['tank_fit_source'] or 'none'}`",
        f"- Tank fit: `{json.dumps(report['tank_fit'], sort_keys=True)}`",
        f"- Dispenser flow-area multiplier: `{report['dispenser_flow_area_multiplier']}`",
        f"- Flow calibration source: `{report['flow_calibration_source'] or 'none'}`",
        f"- Precooler duty multiplier: `{report['precooler_duty_multiplier']}`",
        f"- Thermal calibration source: `{report['thermal_calibration_source'] or 'none'}`",
        f"- Vehicle geometry basis: `{report.get('geometry_basis', 'capacity_scaled')}`",
        f"- Vehicle thermal model: `{report.get('vehicle_tank_thermal_model', 'constant_ua')}`",
        f"- Equivalent capsule aspect ratio: `{report.get('vehicle_equivalent_capsule_aspect_ratio')}`",
        f"- Inlet nozzle diameter: `{report.get('vehicle_inlet_nozzle_diameter_m')}` m",
        f"- Selected laboratory tests: `{report['selected_lab_test_numbers'] or 'all 36'}`",
        "",
        "## Aggregate agreement",
        "",
        "| Metric | Mean | Median | SD | Bootstrap 95% CI of mean |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, stats in aggregate["metrics"].items():
        standard_deviation = stats["standard_deviation"]
        standard_deviation_text = (
            f"{standard_deviation:.3f}"
            if standard_deviation is not None else "n/a"
        )
        lines.append(
            f"| {name} | {stats['mean']:.3f} | {stats['median']:.3f} | "
            f"{standard_deviation_text} | {stats['mean_bootstrap_95_ci'][0]:.3f}–"
            f"{stats['mean_bootstrap_95_ci'][1]:.3f} |"
        )
    lines.extend([
        "",
        f"Engineering-screening pass: {aggregate['screening_pass_count']}/"
        f"{aggregate['case_count']} ({100 * aggregate['screening_pass_fraction']:.1f}%).",
        "The screening limits are project criteria and are not an SAE acceptance rule: "
        f"pressure RMSE ≤ {SCREENING_LIMITS['pressure_rmse_mpa']} MPa, temperature RMSE ≤ "
        f"{SCREENING_LIMITS['temperature_rmse_c']} °C, and absolute final-SOC error ≤ "
        f"{SCREENING_LIMITS['soc_final_abs_error_percentage_points']} percentage points.",
        "Final stop reasons: " + ", ".join(
            f"{name}={count}" for name, count in aggregate["final_stop_reason_counts"].items()
        ) + ".",
        "",
        "## Condition strata",
        "",
        "| Variable | Value | Cases | P RMSE mean | T RMSE mean | SOC RMSE mean |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    labels = {
        "tank_capacity_kg": "Tank capacity (kg)",
        "chamber_temperature_c": "Chamber temperature (°C)",
        "scheduled_aprr_mpa_min": "Scheduled APRR (MPa/min)",
    }
    for field, groups in report["strata"].items():
        for value, group in groups.items():
            metrics = group["metrics"]
            lines.append(
                f"| {labels[field]} | {float(value):g} | {group['case_count']} | "
                f"{metrics['pressure_rmse_mpa']['mean']:.2f} | "
                f"{metrics['temperature_rmse_c']['mean']:.2f} | "
                f"{metrics['soc_rmse_percentage_points']['mean']:.2f} |"
            )
    lines.extend([
        "",
        "## Per-test results",
        "",
        "| Case | Tank | Chamber | APRR | P RMSE | T RMSE | SOC RMSE | Final SOC error | Screen |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in report["cases"]:
        lines.append(
            f"| {row['case_id']} | {row['tank_capacity_kg']:.1f} kg | "
            f"{row['chamber_temperature_c']:.1f} °C | {row['scheduled_aprr_mpa_min']:.1f} MPa/min | "
            f"{row['pressure_rmse_mpa']:.2f} MPa | {row['temperature_rmse_c']:.2f} °C | "
            f"{row['soc_rmse_percentage_points']:.2f}%p | "
            f"{row['soc_final_error_percentage_points']:.2f}%p | "
            f"{'PASS' if row['screening_pass'] else 'FAIL'} |"
        )
    lines.extend([
        "",
        "## Boundary assumptions",
        "",
        "- Initial pressure and gas temperature, chamber temperature, scheduled APRR, median inlet-gas temperature, and final comparison time come from each experiment.",
        "- Maximum flow remains fixed at the 60 g/s model setting; observed peak flow is not fitted.",
        (
            "- Vessel gas volume is calculated from declared capacity and hydrogen EOS "
            "density at nominal pressure and 15 °C."
            if report.get("geometry_basis") == "capacity_eos" else
            "- Vessel volume is scaled from the demonstrator's 0.122 m³ per 4.7 kg "
            "surrogate because the public overview does not provide machine-readable "
            "vessel geometry."
        ),
        (
            "- Mixed convection uses a volume-preserving capsule surrogate with the "
            "declared aspect ratio and nozzle diameter. It is a model-form diagnostic, "
            "not a reconstruction of the undisclosed physical vessel pack."
            if report.get("vehicle_tank_thermal_model") == "mixed_convection" else
            "- The constant-UA tank model does not require an assumed vessel aspect ratio."
        ),
        "- Predictions are interpolated to the experimental clock without dynamic time warping.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=Path("data/public_validation/processed"))
    parser.add_argument("--output", type=Path, default=Path("data/public_validation/results/h2protocol"))
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument(
        "--tank-validation-json", type=Path,
        help="Use the two global tank parameters fitted only on the frozen calibration set",
    )
    parser.add_argument("--dispenser-flow-area-multiplier", type=float, default=1.0)
    parser.add_argument(
        "--flow-calibration-json", type=Path,
        help="Load the frozen selected flow-area multiplier from calibration.json",
    )
    parser.add_argument("--precooler-duty-multiplier", type=float, default=1.0)
    parser.add_argument(
        "--geometry-basis",
        choices=("capacity_scaled", "capacity_eos"),
        default="capacity_scaled",
        help=(
            "Vehicle-volume rule. capacity_scaled preserves the historical "
            "0.122 m3/4.7 kg surrogate; capacity_eos derives volume from "
            "declared capacity and the tabulated H2 EOS at 15 °C."
        ),
    )
    parser.add_argument(
        "--thermal-calibration-json", type=Path,
        help="Load the selected global precooler-duty multiplier from calibration.json",
    )
    parser.add_argument(
        "--vehicle-tank-thermal-model",
        choices=("constant_ua", "mixed_convection"),
        default="constant_ua",
        help=(
            "Tank heat-transfer model. mixed_convection is a research path and "
            "requires a declared equivalent geometry and inlet-nozzle diameter."
        ),
    )
    parser.add_argument(
        "--vehicle-equivalent-capsule-aspect-ratio",
        type=float,
        help=(
            "Cylindrical length/diameter for a volume-preserving capsule surrogate; "
            "required with mixed_convection."
        ),
    )
    parser.add_argument(
        "--vehicle-inlet-nozzle-diameter-mm",
        type=float,
        help="Declared inlet-nozzle diameter in millimetres; required with mixed_convection.",
    )
    parser.add_argument(
        "--lab-test-numbers",
        help="Optional comma-separated frozen subset, for example 3,9,12",
    )
    args = parser.parse_args()
    if args.vehicle_tank_thermal_model == "mixed_convection":
        if (
            args.vehicle_equivalent_capsule_aspect_ratio is None
            or args.vehicle_inlet_nozzle_diameter_mm is None
        ):
            raise SystemExit(
                "mixed_convection requires --vehicle-equivalent-capsule-aspect-ratio "
                "and --vehicle-inlet-nozzle-diameter-mm"
            )
        if args.vehicle_equivalent_capsule_aspect_ratio <= 0.0:
            raise SystemExit(
                "--vehicle-equivalent-capsule-aspect-ratio must be positive"
            )
        if args.vehicle_inlet_nozzle_diameter_mm <= 0.0:
            raise SystemExit("--vehicle-inlet-nozzle-diameter-mm must be positive")
    elif (
        args.vehicle_equivalent_capsule_aspect_ratio is not None
        or args.vehicle_inlet_nozzle_diameter_mm is not None
    ):
        raise SystemExit(
            "Equivalent geometry options require --vehicle-tank-thermal-model "
            "mixed_convection"
        )
    inlet_nozzle_diameter_m = (
        None
        if args.vehicle_inlet_nozzle_diameter_mm is None
        else args.vehicle_inlet_nozzle_diameter_mm / 1000.0
    )
    flow_calibration_source = None
    if args.flow_calibration_json is not None:
        if args.dispenser_flow_area_multiplier != 1.0:
            raise SystemExit(
                "Do not combine --flow-calibration-json with an explicit flow multiplier"
            )
        flow_report = json.loads(args.flow_calibration_json.read_text(encoding="utf-8"))
        args.dispenser_flow_area_multiplier = float(
            flow_report["selected_dispenser_flow_area_multiplier"]
        )
        flow_calibration_source = str(args.flow_calibration_json)
    if args.dispenser_flow_area_multiplier <= 0.0:
        raise SystemExit("--dispenser-flow-area-multiplier must be positive")
    thermal_calibration_source = None
    if args.thermal_calibration_json is not None:
        if args.precooler_duty_multiplier != 1.0:
            raise SystemExit(
                "Do not combine --thermal-calibration-json with an explicit thermal multiplier"
            )
        thermal_report = json.loads(
            args.thermal_calibration_json.read_text(encoding="utf-8")
        )
        args.precooler_duty_multiplier = float(
            thermal_report["selected_precooler_duty_multiplier"]
        )
        thermal_calibration_source = str(args.thermal_calibration_json)
    if args.precooler_duty_multiplier <= 0.0:
        raise SystemExit("--precooler-duty-multiplier must be positive")
    tank_fit = None
    tank_fit_source = None
    if args.tank_validation_json is not None:
        tank_report = json.loads(args.tank_validation_json.read_text(encoding="utf-8"))
        tank_fit = {
            "effective_volume_multiplier": float(
                tank_report["fit"]["effective_volume_multiplier"]
            ),
            "gas_liner_ua_multiplier": float(
                tank_report["fit"]["gas_liner_ua_multiplier"]
            ),
        }
        tank_fit_source = str(args.tank_validation_json)
    summaries = _read_csv(args.processed / "h2protocol_cases.csv")
    if len(summaries) != 36:
        raise SystemExit(f"Expected 36 normalized J2601 cases, found {len(summaries)}")
    selected_lab_tests = None
    if args.lab_test_numbers:
        selected_lab_tests = {
            int(value.strip()) for value in args.lab_test_numbers.split(",") if value.strip()
        }
        summaries = [
            row for row in summaries
            if int(float(row["lab_test_number"])) in selected_lab_tests
        ]
        found = {int(float(row["lab_test_number"])) for row in summaries}
        if found != selected_lab_tests:
            raise SystemExit(
                f"Requested lab tests {sorted(selected_lab_tests)}, found {sorted(found)}"
            )
    ordered_summaries = sorted(
        summaries, key=lambda row: int(float(row["lab_test_number"]))
    )
    rows = []
    if args.jobs <= 1:
        for summary in ordered_summaries:
            result = _run_case_file(
                summary,
                args.processed / "h2protocol_traces" / f"{summary['case_id']}.csv",
                tank_fit,
                args.dispenser_flow_area_multiplier,
                args.precooler_duty_multiplier,
                args.geometry_basis,
                args.vehicle_tank_thermal_model,
                None,
                None,
                inlet_nozzle_diameter_m,
                args.vehicle_equivalent_capsule_aspect_ratio,
            )
            rows.append(result)
            print(f"validated {result['case_id']}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            futures = {
                pool.submit(
                    _run_case_file,
                    summary,
                    args.processed / "h2protocol_traces" / f"{summary['case_id']}.csv",
                    tank_fit,
                    args.dispenser_flow_area_multiplier,
                    args.precooler_duty_multiplier,
                    args.geometry_basis,
                    args.vehicle_tank_thermal_model,
                    None,
                    None,
                    inlet_nozzle_diameter_m,
                    args.vehicle_equivalent_capsule_aspect_ratio,
                ): summary["case_id"]
                for summary in ordered_summaries
            }
            for future in as_completed(futures):
                result = future.result()
                rows.append(result)
                print(f"validated {result['case_id']}", flush=True)
        rows.sort(key=lambda row: row["lab_test_number"])
    report = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "source_worktree_dirty": _git_worktree_dirty(),
        "protocol_source": "Powertech Labs SAE J2601 Tables Method validation data",
        "screening_limits": SCREENING_LIMITS,
        "tank_fit_source": tank_fit_source,
        "tank_fit": tank_fit,
        "dispenser_flow_area_multiplier": args.dispenser_flow_area_multiplier,
        "flow_calibration_source": flow_calibration_source,
        "precooler_duty_multiplier": args.precooler_duty_multiplier,
        "geometry_basis": args.geometry_basis,
        "vehicle_tank_thermal_model": args.vehicle_tank_thermal_model,
        "vehicle_equivalent_capsule_aspect_ratio": (
            args.vehicle_equivalent_capsule_aspect_ratio
        ),
        "vehicle_inlet_nozzle_diameter_m": inlet_nozzle_diameter_m,
        "thermal_calibration_source": thermal_calibration_source,
        "selected_lab_test_numbers": (
            sorted(selected_lab_tests) if selected_lab_tests is not None else None
        ),
        "aggregate": _aggregate(rows),
        "strata": {
            field: {
                value: _aggregate([row for row in rows if str(row[field]) == value])
                for value in sorted({str(row[field]) for row in rows}, key=float)
            }
            for field in (
                "tank_capacity_kg", "chamber_temperature_c", "scheduled_aprr_mpa_min"
            )
        },
        "cases": rows,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_csv(args.output / "case_metrics.csv", rows)
    _write_markdown(args.output / "report.md", report)
    print(args.output / "report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
