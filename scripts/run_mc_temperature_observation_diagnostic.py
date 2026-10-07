"""Audit the thermal observation semantics of the MC Default replay.

The MC Default workbook calls its thermal channel a tank mean temperature.
That label alone does not establish whether it represents the gas, liner, shell,
or a sensor-weighted combination.  The Type-IV model has separate gas, liner,
and shell states, so this diagnostic reports several *predefined* observation
operators without fitting or selecting one from the benchmark outcomes.

It is a post-outcome semantic diagnostic.  It is deliberately not a new
validation result and cannot change the frozen full-loop result or runtime
thermal observation used by the digital twin.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

from h2station.public_tank_calibration import load_public_type_iv_tank_calibration
from h2station.scenario import build_vehicle_tank
from h2station.tabulated import PropsSI
from h2station.vehicle import CompositeTankFitParameters, CompositeTankState, TankBoundaryFlow


TEMPERATURE_OBSERVATIONS: dict[str, str] = {
    "gas_temperature": "uniform gas state",
    "liner_temperature": "inner polymer liner state",
    "shell_temperature": "outer composite shell state",
    "liner_shell_mean": "unweighted liner and shell state mean",
}


@dataclass(frozen=True)
class Replay:
    time_s: np.ndarray
    observed_temperature_c: np.ndarray
    gas_temperature_c: np.ndarray
    liner_temperature_c: np.ndarray
    shell_temperature_c: np.ndarray


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_float(rows: list[dict[str, str]], column: str) -> np.ndarray:
    return np.asarray([float(row[column]) for row in rows], dtype=float)


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _thermal_observations(replay: Replay) -> dict[str, np.ndarray]:
    """Return predefined model-state observation operators without fitting."""

    return {
        "gas_temperature": replay.gas_temperature_c,
        "liner_temperature": replay.liner_temperature_c,
        "shell_temperature": replay.shell_temperature_c,
        "liner_shell_mean": (replay.liner_temperature_c + replay.shell_temperature_c) / 2.0,
    }


def _replay_case(
    summary: dict[str, str],
    rows: list[dict[str, str]],
    *,
    fit: CompositeTankFitParameters,
    source_pressure_column: str,
) -> Replay:
    time_s = _as_float(rows, "time_s")
    pressure_mpa = _as_float(rows, "pressure_mpa")
    observed_temperature_c = _as_float(rows, "tank_temperature_mean_c")
    mass_flow_g_s = _as_float(rows, "mass_flow_g_s")
    inlet_temperature_c = _as_float(rows, "inlet_gas_temperature_c")
    source_pressure_mpa = _as_float(rows, source_pressure_column)
    tank = build_vehicle_tank(0.122 * float(summary["tank_capacity_kg"]) / 4.7, fit)
    initial = tank.initial_state(
        pressure_mpa[0] * 1.0e6,
        observed_temperature_c[0] + 273.15,
    )
    ambient_temperature_k = float(summary["chamber_temperature_c"]) + 273.15

    def rhs(local_time_s: float, values: np.ndarray) -> np.ndarray:
        state = CompositeTankState.from_vector(values)
        inlet_mass_flow_kg_s = max(0.0, float(np.interp(local_time_s, time_s, mass_flow_g_s))) / 1000.0
        inlet_temperature_k = float(np.interp(local_time_s, time_s, inlet_temperature_c)) + 273.15
        inlet_pressure_pa = max(0.2, float(np.interp(local_time_s, time_s, source_pressure_mpa))) * 1.0e6
        inlet_enthalpy = float(PropsSI("Hmass", "P", inlet_pressure_pa, "T", inlet_temperature_k, "Hydrogen"))
        return tank.derivative(
            state,
            TankBoundaryFlow(
                inlet_mass_flow_kg_s=inlet_mass_flow_kg_s,
                inlet_specific_enthalpy_j_kg=inlet_enthalpy,
                ambient_temperature_k=ambient_temperature_k,
            ),
        ).as_vector()

    solution = solve_ivp(
        rhs,
        (float(time_s[0]), float(time_s[-1])),
        initial.as_vector(),
        method="BDF",
        t_eval=time_s,
        rtol=5.0e-6,
        atol=5.0e-8,
    )
    if not solution.success:
        raise RuntimeError(f"{summary['case_id']}: {solution.message}")
    gas_temperature_c = np.asarray(
        [tank.gas_state(CompositeTankState.from_vector(values)).temperature_k - 273.15 for values in solution.y.T],
        dtype=float,
    )
    return Replay(
        time_s=time_s,
        observed_temperature_c=observed_temperature_c,
        gas_temperature_c=gas_temperature_c,
        liner_temperature_c=np.asarray(solution.y[2] - 273.15, dtype=float),
        shell_temperature_c=np.asarray(solution.y[3] - 273.15, dtype=float),
    )


def _metrics(replay: Replay) -> dict[str, dict[str, float]]:
    values: dict[str, dict[str, float]] = {}
    for name, prediction in _thermal_observations(replay).items():
        error = prediction - replay.observed_temperature_c
        values[name] = {
            "temperature_rmse_c": float(np.sqrt(np.mean(np.square(error)))),
            "temperature_mae_c": float(np.mean(np.abs(error))),
            "temperature_peak_error_c": float(np.max(prediction) - np.max(replay.observed_temperature_c)),
        }
    return values


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    aggregate: dict[str, dict[str, float]] = {}
    for observation in TEMPERATURE_OBSERVATIONS:
        aggregate[observation] = {
            metric: float(np.mean([row["observations"][observation][metric] for row in rows]))
            for metric in ("temperature_rmse_c", "temperature_mae_c", "temperature_peak_error_c")
        }
    return aggregate


def build_report(processed: Path, protocol_path: Path, *, source_pressure_column: str) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    profile = load_public_type_iv_tank_calibration()
    fit = CompositeTankFitParameters(
        effective_volume_multiplier=profile.effective_volume_multiplier,
        gas_liner_ua_multiplier=profile.gas_liner_ua_multiplier,
    )
    summaries = {row["source_member"]: row for row in _read_csv(processed / "mc_default_cases.csv")}
    cases: list[dict[str, Any]] = []
    for source_member in protocol["selected_workbooks"]:
        summary = summaries[source_member]
        trace_rows = _read_csv(processed / "mc_default_traces" / f"{summary['case_id']}.csv")
        replay = _replay_case(
            summary,
            trace_rows,
            fit=fit,
            source_pressure_column=source_pressure_column,
        )
        cases.append({"case_id": summary["case_id"], "observations": _metrics(replay)})
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "diagnostic_type": "MC Default temperature-observation semantic replay",
        "evidence_role": "post_outcome_semantic_diagnostic_only",
        "post_outcome": True,
        "parameter_fitting": False,
        "runtime_thermal_observation_changed": False,
        "observation_mapping_selection_prohibited": True,
        "promotion_to_validation_prohibited": True,
        "raw_experimental_rows_persisted": False,
        "source_workbook_names_persisted": False,
        "protocol": str(protocol_path),
        "boundary_conditions": [
            "measured mass_flow_g_s",
            "measured inlet_gas_temperature_c",
            f"measured {source_pressure_column}",
        ],
        "candidate_observation_operators": TEMPERATURE_OBSERVATIONS,
        "aggregate": _aggregate(cases),
        "cases": cases,
        "interpretation": (
            "Different predefined tank-state observation operators yield materially different thermal errors. "
            "The source label alone does not identify the physical measurement location or weighting. "
            "This report does not select an operator, change the runtime gas-temperature observation, "
            "or revise any frozen validation outcome."
        ),
        "claim_boundary": (
            "This is a post-outcome semantic diagnostic for one public vehicle-tank replay. "
            "It is not a tank, full-station, release, consequence, or safety validation result."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=Path("data/public_validation/processed"))
    parser.add_argument("--protocol", type=Path, default=Path("research/mc_default_external_holdout_protocol.json"))
    parser.add_argument("--source-pressure-column", choices=("source_pressure_1_mpa", "source_pressure_3_mpa"), default="source_pressure_3_mpa")
    parser.add_argument("--output", type=Path, default=Path("research/mc_temperature_observation_diagnostic_2026_10_07.json"))
    args = parser.parse_args()
    report = build_report(args.processed, args.protocol, source_pressure_column=args.source_pressure_column)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"case_count": len(report["cases"]), "aggregate": report["aggregate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
