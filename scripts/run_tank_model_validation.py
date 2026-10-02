"""Calibrate globally and validate the Type-IV tank model on public fills.

Measured mass flow and inlet-gas temperature are boundary conditions.  This
isolates tank thermodynamics from dispenser/controller errors.  Every third lab
test (3, 6, ..., 36) is a frozen external validation set; it is never used by
the optimizer.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares

from h2station.public_validation import compare_traces
from h2station.scenario import build_vehicle_tank
from h2station.tabulated import PropsSI
from h2station.vehicle import (
    CompositeTankFitParameters,
    CompositeTankState,
    CompositeVehicleTank,
    TankBoundaryFlow,
)


@dataclass(frozen=True)
class ExperimentalFill:
    case_id: str
    lab_test_number: int
    tank_capacity_kg: float
    chamber_temperature_c: float
    time_s: np.ndarray
    pressure_mpa: np.ndarray
    temperature_c: np.ndarray
    soc_percent: np.ndarray
    mass_flow_g_s: np.ndarray
    inlet_temperature_c: np.ndarray
    mass_closure_ratio: float


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_cases(root: Path) -> list[ExperimentalFill]:
    summaries = _read_csv(root / "h2protocol_cases.csv")
    cases = []
    for summary in summaries:
        rows = _read_csv(root / "h2protocol_traces" / f"{summary['case_id']}.csv")
        array = lambda name: np.asarray([float(row[name]) for row in rows])
        capacity = float(summary["tank_capacity_kg"])
        time = array("time_s")
        flow = array("mass_flow_g_s")
        soc = array("soc_percent")
        nominal_mass_change = capacity * (soc[-1] - soc[0]) / 100.0
        cases.append(ExperimentalFill(
            case_id=summary["case_id"],
            lab_test_number=int(float(summary["lab_test_number"])),
            tank_capacity_kg=capacity,
            chamber_temperature_c=float(summary["chamber_temperature_c"]),
            time_s=time, pressure_mpa=array("pressure_mpa"),
            temperature_c=array("tank_temperature_mean_c"),
            soc_percent=soc, mass_flow_g_s=flow,
            inlet_temperature_c=array("inlet_gas_temperature_c"),
            mass_closure_ratio=float(np.trapezoid(flow / 1000.0, time) / nominal_mass_change),
        ))
    if len(cases) != 36:
        raise ValueError(f"Expected 36 fills, found {len(cases)}")
    return sorted(cases, key=lambda case: case.lab_test_number)


def _tank(case: ExperimentalFill, volume_multiplier: float, gas_liner_ua_multiplier: float) -> CompositeVehicleTank:
    base_volume = 0.122 * case.tank_capacity_kg / 4.7
    base = build_vehicle_tank(base_volume)
    return CompositeVehicleTank(
        base.parameters,
        CompositeTankFitParameters(
            effective_volume_multiplier=volume_multiplier,
            gas_liner_ua_multiplier=gas_liner_ua_multiplier,
        ),
    )


def _simulate(
    case: ExperimentalFill,
    volume_multiplier: float,
    gas_liner_ua_multiplier: float,
    *, evaluation_indices: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    tank = _tank(case, volume_multiplier, gas_liner_ua_multiplier)
    initial = tank.initial_state(
        case.pressure_mpa[0] * 1.0e6, case.temperature_c[0] + 273.15
    )
    ambient_k = case.chamber_temperature_c + 273.15

    def rhs(time_s: float, values: np.ndarray) -> np.ndarray:
        state = CompositeTankState.from_vector(values)
        flow_kg_s = max(0.0, float(np.interp(
            time_s, case.time_s, case.mass_flow_g_s
        ))) / 1000.0
        inlet_temperature_k = float(np.interp(
            time_s, case.time_s, case.inlet_temperature_c
        )) + 273.15
        inlet_pressure_pa = max(0.2, float(np.interp(
            time_s, case.time_s, case.pressure_mpa
        ))) * 1.0e6
        inlet_enthalpy = float(PropsSI(
            "Hmass", "P", inlet_pressure_pa, "T", inlet_temperature_k, "Hydrogen"
        ))
        return tank.derivative(state, TankBoundaryFlow(
            inlet_mass_flow_kg_s=flow_kg_s,
            inlet_specific_enthalpy_j_kg=inlet_enthalpy,
            ambient_temperature_k=ambient_k,
        )).as_vector()

    indices = (
        np.arange(len(case.time_s), dtype=int)
        if evaluation_indices is None else np.unique(evaluation_indices.astype(int))
    )
    if indices[0] != 0:
        indices = np.insert(indices, 0, 0)
    if indices[-1] != len(case.time_s) - 1:
        indices = np.append(indices, len(case.time_s) - 1)
    target_times = case.time_s[indices]
    solution = solve_ivp(
        rhs, (float(case.time_s[0]), float(case.time_s[-1])), initial.as_vector(),
        method="BDF", t_eval=target_times,
        # A fixed tolerance keeps calibration and final evaluation consistent.
        rtol=5.0e-6,
        atol=5.0e-8,
    )
    if not solution.success:
        raise RuntimeError(f"{case.case_id} tank integration failed: {solution.message}")
    gas = [tank.gas_state(CompositeTankState.from_vector(values)) for values in solution.y.T]
    pressure = np.asarray([item.pressure_pa / 1.0e6 for item in gas])
    temperature = np.asarray([item.temperature_k - 273.15 for item in gas])
    reference_density = float(PropsSI(
        "Dmass", "P", 70.0e6, "T", 288.15, "Hydrogen"
    ))
    soc = np.asarray([100.0 * item.density_kg_m3 / reference_density for item in gas])
    return target_times, pressure, temperature, soc


def _calibration_residuals(log_parameters: np.ndarray, cases: list[ExperimentalFill]) -> np.ndarray:
    volume_multiplier, ua_multiplier = np.exp(log_parameters)
    residuals = []
    for case in cases:
        indices = np.linspace(0, len(case.time_s) - 1, min(30, len(case.time_s)), dtype=int)
        times, pressure, temperature, _ = _simulate(
            case, volume_multiplier, ua_multiplier, evaluation_indices=indices
        )
        experimental_pressure = np.interp(times, case.time_s, case.pressure_mpa)
        experimental_temperature = np.interp(times, case.time_s, case.temperature_c)
        residuals.extend((pressure - experimental_pressure) / 5.0)
        residuals.extend((temperature - experimental_temperature) / 10.0)
    return np.asarray(residuals)


def _metrics(case: ExperimentalFill, split: str, volume: float, ua: float) -> tuple[dict, list[dict]]:
    times, pressure, temperature, soc = _simulate(
        case, volume, ua
    )
    agreement = compare_traces(
        experimental_time_s=case.time_s,
        experimental_pressure_mpa=case.pressure_mpa,
        experimental_temperature_c=case.temperature_c,
        experimental_soc_percent=case.soc_percent,
        predicted_time_s=times,
        predicted_pressure_mpa=pressure,
        predicted_temperature_c=temperature,
        predicted_soc_percent=soc,
    )
    metric = {
        "case_id": case.case_id, "lab_test_number": case.lab_test_number,
        "split": split, "tank_capacity_kg": case.tank_capacity_kg,
        "chamber_temperature_c": case.chamber_temperature_c,
        "mass_closure_ratio": case.mass_closure_ratio,
        **agreement.to_dict(),
    }
    traces = [{
        "time_s": float(time_s),
        "experimental_pressure_mpa": float(exp_p),
        "predicted_pressure_mpa": float(pred_p),
        "pressure_residual_mpa": float(pred_p - exp_p),
        "experimental_temperature_c": float(exp_t),
        "predicted_temperature_c": float(pred_t),
        "temperature_residual_c": float(pred_t - exp_t),
        "experimental_soc_percent": float(exp_s),
        "predicted_soc_percent": float(pred_s),
        "soc_residual_percentage_points": float(pred_s - exp_s),
    } for time_s, exp_p, pred_p, exp_t, pred_t, exp_s, pred_s in zip(
        times, case.pressure_mpa, pressure, case.temperature_c, temperature,
        case.soc_percent, soc,
    )]
    return metric, traces


def _bootstrap_mean_ci(values: np.ndarray, *, seed: int, replicates: int = 10_000) -> list[float]:
    """Return a deterministic case-level percentile CI for the population mean."""
    if len(values) == 1:
        value = float(values[0])
        return [value, value]
    rng = np.random.default_rng(seed)
    sampled = rng.choice(values, size=(replicates, len(values)), replace=True)
    return [float(value) for value in np.percentile(np.mean(sampled, axis=1), [2.5, 97.5])]


def _summary(rows: list[dict], *, seed: int) -> dict:
    result = {"case_count": len(rows)}
    for name in (
        "pressure_rmse_mpa", "temperature_rmse_c", "soc_rmse_percentage_points",
        "pressure_final_error_mpa", "temperature_peak_error_c",
        "soc_final_error_percentage_points",
    ):
        values = np.asarray([row[name] for row in rows], dtype=float)
        result[name] = {
            "mean": float(np.mean(values)), "median": float(np.median(values)),
            "standard_deviation": (
                float(np.std(values, ddof=1)) if len(values) > 1 else None
            ),
            "case_bootstrap_mean_95_ci": _bootstrap_mean_ci(values, seed=seed),
        }
    return result


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def _grouped_summary(rows: list[dict], field: str, *, seed: int) -> dict[str, dict]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(str(row[field]), []).append(row)
    return {
        name: _summary(group, seed=seed + index)
        for index, (name, group) in enumerate(sorted(groups.items()))
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=Path("data/public_validation/processed"))
    parser.add_argument("--output", type=Path, default=Path("data/public_validation/results/tank_model"))
    parser.add_argument("--max-evaluations", type=int, default=20)
    parser.add_argument(
        "--include-mass-closure-outliers", action="store_true",
        help="Sensitivity analysis: retain experiments outside the predeclared mass-closure screen",
    )
    args = parser.parse_args()
    cases = _load_cases(args.processed)
    excluded = [] if args.include_mass_closure_outliers else [
        case for case in cases if not 0.8 <= case.mass_closure_ratio <= 1.2
    ]
    excluded_ids = {case.case_id for case in excluded}
    eligible = [case for case in cases if case.case_id not in excluded_ids]
    validation = [case for case in eligible if case.lab_test_number % 3 == 0]
    calibration = [case for case in eligible if case.lab_test_number % 3 != 0]
    validation_ids = {case.case_id for case in validation}
    fit = least_squares(
        _calibration_residuals,
        x0=np.log([1.05, 20.0]),
        bounds=(np.log([0.8, 0.2]), np.log([1.3, 100.0])),
        args=(calibration,), max_nfev=args.max_evaluations,
        loss="linear", jac="2-point", diff_step=0.01, x_scale="jac",
        ftol=1.0e-5, xtol=1.0e-5, gtol=1.0e-5, verbose=2,
    )
    volume_multiplier, ua_multiplier = np.exp(fit.x)
    args.output.mkdir(parents=True, exist_ok=True)
    trace_root = args.output / "traces"; trace_root.mkdir(exist_ok=True)
    rows = []
    for case in eligible:
        split = "validation" if case.case_id in validation_ids else "calibration"
        metric, traces = _metrics(case, split, volume_multiplier, ua_multiplier)
        rows.append(metric); _write_csv(trace_root / f"{case.case_id}.csv", traces)
        print(f"evaluated {case.case_id} ({split})", flush=True)
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Type-IV tank model with measured mass-flow and inlet-temperature boundaries",
        "split_rule": "validation when lab_test_number modulo 3 equals 0",
        "experimental_quality_rule": "0.8 <= integrated measured mass / nominal SOC-implied mass change <= 1.2",
        "experimental_quality_screen_applied": not args.include_mass_closure_outliers,
        "excluded_cases": [{
            "case_id": case.case_id,
            "reason": "experimental mass-closure ratio outside 0.8..1.2",
            "mass_closure_ratio": case.mass_closure_ratio,
        } for case in excluded],
        "calibration_case_ids": [case.case_id for case in calibration],
        "validation_case_ids": [case.case_id for case in validation],
        "fit": {
            "effective_volume_multiplier": float(volume_multiplier),
            "gas_liner_ua_multiplier": float(ua_multiplier),
            "method": "bounded nonlinear least squares in log-parameter space (forward finite differences)",
            "optimizer_success": bool(fit.success), "optimizer_message": fit.message,
            "function_evaluations": int(fit.nfev), "cost": float(fit.cost),
            "first_order_optimality": float(fit.optimality),
        },
        "uncertainty": {
            "method": "case-level nonparametric percentile bootstrap of the mean",
            "replicates": 10_000,
            "seed": 2601,
        },
        "calibration": _summary(
            [row for row in rows if row["split"] == "calibration"], seed=2601
        ),
        "validation": _summary(
            [row for row in rows if row["split"] == "validation"], seed=2602
        ),
        "validation_strata": {
            "tank_capacity_kg": _grouped_summary(
                [row for row in rows if row["split"] == "validation"],
                "tank_capacity_kg", seed=2700,
            ),
            "chamber_temperature_c": _grouped_summary(
                [row for row in rows if row["split"] == "validation"],
                "chamber_temperature_c", seed=2800,
            ),
        },
        "cases": rows,
    }
    (args.output / "validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_csv(args.output / "case_metrics.csv", rows)
    lines = [
        "# Type-IV tank external validation", "",
        f"Scope: {report['scope']}",
        f"Frozen split: {report['split_rule']}",
        f"Fitted effective-volume multiplier: {volume_multiplier:.5f}",
        f"Fitted gas-to-liner UA multiplier: {ua_multiplier:.5f}", "",
        "| Split | Cases | Pressure RMSE mean (95% CI) | Temperature RMSE mean (95% CI) | SOC RMSE mean (95% CI) |",
        "|---|---:|---:|---:|---:|",
    ]
    for split in ("calibration", "validation"):
        item = report[split]
        pressure = item["pressure_rmse_mpa"]
        temperature = item["temperature_rmse_c"]
        soc = item["soc_rmse_percentage_points"]
        lines.append(
            f"| {split} | {item['case_count']} | "
            f"{pressure['mean']:.3f} MPa ({pressure['case_bootstrap_mean_95_ci'][0]:.3f}–{pressure['case_bootstrap_mean_95_ci'][1]:.3f}) | "
            f"{temperature['mean']:.3f} °C ({temperature['case_bootstrap_mean_95_ci'][0]:.3f}–{temperature['case_bootstrap_mean_95_ci'][1]:.3f}) | "
            f"{soc['mean']:.3f}%p ({soc['case_bootstrap_mean_95_ci'][0]:.3f}–{soc['case_bootstrap_mean_95_ci'][1]:.3f}) |"
        )
    lines.extend([
        "", "Measured mass flow and inlet temperature are model boundary conditions. "
        "These results validate the tank submodel and do not validate the station controller, "
        "dispenser hydraulics, SAE table generation, or field safety.",
    ])
    (args.output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output / "report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
