"""Replay the MC Default traces through the vehicle tank only.

The public MC Default workbooks expose measured mass flow, inlet gas
temperature and source-pressure channels.  This diagnostic supplies those
measurements as boundary conditions to the Type-IV tank model and deliberately
removes the station controller, cascade dispatch and dispenser hydraulics.
It is a development diagnostic: it cannot close the full-station validation
gate and it does not fit parameters to these eight cases.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from h2station.public_validation import compare_traces
from h2station.scenario import build_vehicle_tank
from h2station.tabulated import PropsSI
from h2station.vehicle import CompositeTankFitParameters, CompositeTankState, TankBoundaryFlow


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _f(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value in ("", None, "None"):
        raise ValueError(f"Missing {key}")
    return float(value)


def _git_commit() -> str:
    import subprocess
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def run_case(
    summary: dict[str, str], rows: list[dict[str, str]], fit: dict[str, float],
    *, source_pressure_column: str,
) -> dict:
    time_s = np.asarray([_f(row, "time_s") for row in rows], dtype=float)
    pressure = np.asarray([_f(row, "pressure_mpa") for row in rows], dtype=float)
    temperature = np.asarray([_f(row, "tank_temperature_mean_c") for row in rows], dtype=float)
    soc = np.asarray([_f(row, "soc_percent") for row in rows], dtype=float)
    flow = np.asarray([_f(row, "mass_flow_g_s") for row in rows], dtype=float)
    inlet_temperature = np.asarray([_f(row, "inlet_gas_temperature_c") for row in rows], dtype=float)
    source_pressure = np.asarray([_f(row, source_pressure_column) for row in rows], dtype=float)
    chamber = np.asarray([_f(row, "chamber_temperature_c") for row in rows], dtype=float)
    capacity = _f(summary, "tank_capacity_kg")
    tank = build_vehicle_tank(0.122 * capacity / 4.7, CompositeTankFitParameters(
        effective_volume_multiplier=float(fit["effective_volume_multiplier"]),
        gas_liner_ua_multiplier=float(fit["gas_liner_ua_multiplier"]),
    ))
    initial = tank.initial_state(pressure[0] * 1.0e6, temperature[0] + 273.15)
    ambient_k = float(np.median(chamber) + 273.15)

    def rhs(local_time_s: float, values: np.ndarray) -> np.ndarray:
        state = CompositeTankState.from_vector(values)
        mass_flow = max(0.0, float(np.interp(local_time_s, time_s, flow))) / 1000.0
        inlet_t = float(np.interp(local_time_s, time_s, inlet_temperature)) + 273.15
        inlet_p = max(0.2, float(np.interp(local_time_s, time_s, source_pressure))) * 1.0e6
        enthalpy = float(PropsSI("Hmass", "P", inlet_p, "T", inlet_t, "Hydrogen"))
        return tank.derivative(state, TankBoundaryFlow(
            inlet_mass_flow_kg_s=mass_flow,
            inlet_specific_enthalpy_j_kg=enthalpy,
            ambient_temperature_k=ambient_k,
        )).as_vector()

    solution = solve_ivp(
        rhs, (float(time_s[0]), float(time_s[-1])), initial.as_vector(),
        method="BDF", t_eval=time_s, rtol=5.0e-6, atol=5.0e-8,
    )
    if not solution.success:
        raise RuntimeError(f"{summary['case_id']}: {solution.message}")
    gases = [tank.gas_state(CompositeTankState.from_vector(v)) for v in solution.y.T]
    predicted_pressure = np.asarray([gas.pressure_pa / 1.0e6 for gas in gases])
    predicted_temperature = np.asarray([gas.temperature_k - 273.15 for gas in gases])
    reference_density = float(PropsSI("Dmass", "P", 70.0e6, "T", 288.15, "Hydrogen"))
    predicted_soc = np.asarray([100.0 * gas.density_kg_m3 / reference_density for gas in gases])
    agreement = compare_traces(
        experimental_time_s=time_s,
        experimental_pressure_mpa=pressure,
        experimental_temperature_c=temperature,
        experimental_soc_percent=soc,
        predicted_time_s=time_s,
        predicted_pressure_mpa=predicted_pressure,
        predicted_temperature_c=predicted_temperature,
        predicted_soc_percent=predicted_soc,
    )
    measured_mass = float(np.trapezoid(flow / 1000.0, time_s))
    return {
        "case_id": summary["case_id"],
        "tank_capacity_kg": capacity,
        "source_pressure_column": source_pressure_column,
        "experimental_duration_s": float(time_s[-1]),
        "experimental_final_pressure_mpa": float(pressure[-1]),
        "predicted_final_pressure_mpa": float(predicted_pressure[-1]),
        "experimental_peak_temperature_c": float(np.max(temperature)),
        "predicted_peak_temperature_c": float(np.max(predicted_temperature)),
        "experimental_final_soc_percent": float(soc[-1]),
        "predicted_final_soc_percent": float(predicted_soc[-1]),
        "measured_transferred_mass_kg": measured_mass,
        "fit": fit,
        **agreement.to_dict(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=Path("data/public_validation/processed"))
    parser.add_argument("--protocol", type=Path, default=Path("research/mc_default_external_holdout_protocol.json"))
    parser.add_argument("--output", type=Path, default=Path("research/mc_tank_boundary_diagnostic_2026_10_05.json"))
    parser.add_argument("--source-pressure-column", choices=("source_pressure_1_mpa", "source_pressure_3_mpa"), default="source_pressure_3_mpa")
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    fit = {
        "effective_volume_multiplier": float(protocol["frozen_model"]["effective_volume_multiplier"]),
        "gas_liner_ua_multiplier": float(protocol["frozen_model"]["gas_liner_ua_multiplier"]),
    }
    summaries = {row["case_id"]: row for row in _read_csv(args.processed / "mc_default_cases.csv")}
    selected = protocol["selected_workbooks"]
    rows = []
    for member in selected:
        summary = next(row for row in summaries.values() if row["source_member"] == member)
        trace = _read_csv(args.processed / "mc_default_traces" / f"{summary['case_id']}.csv")
        rows.append(run_case(summary, trace, fit, source_pressure_column=args.source_pressure_column))
    aggregate = {
        "case_count": len(rows),
        "pressure_rmse_mpa_mean": float(np.mean([row["pressure_rmse_mpa"] for row in rows])),
        "temperature_rmse_c_mean": float(np.mean([row["temperature_rmse_c"] for row in rows])),
        "soc_rmse_percentage_points_mean": float(np.mean([row["soc_rmse_percentage_points"] for row in rows])),
    }
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "diagnostic_type": "MC Default measured-boundary vehicle-tank replay",
        "evidence_role": "development_diagnostic_only",
        "post_outcome": True,
        "parameter_fitting": False,
        "protocol": str(args.protocol),
        "boundary_conditions": [
            "measured mass_flow_g_s",
            "measured inlet_gas_temperature_c",
            f"measured {args.source_pressure_column}",
        ],
        "claim_boundary": "This isolates the vehicle tank thermodynamic submodel. It does not validate the station controller, cascade dispatch, compressor, dispenser hydraulics, protocol schedule, safety PLC or field safety, and cannot close the full-loop gate.",
        "fit_source": "frozen MC Default model values; no case-specific fitting",
        "aggregate": aggregate,
        "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(aggregate, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
