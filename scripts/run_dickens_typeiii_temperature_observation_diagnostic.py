"""Replay Dickens Type-III temperatures with predefined observation operators.

This is a post-outcome semantic diagnostic.  It reuses the frozen, unfitted
Type-III protocol and the same tank/flow model as the prospective runner, then
compares the reported ``gas_mean`` channel with model gas, liner, shell, and
simple state-combination operators.  It never selects an operator, changes the
runtime temperature state, or revises the frozen validation result.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess

import numpy as np
from scipy.integrate import solve_ivp
import yaml

from h2station.tabulated import PropsSI
from h2station.vehicle import CompositeTankState, TankBoundaryFlow

from run_dickens_typeiii_prospective import (  # noqa: E402
    PROTOCOL_PATH,
    _build_tank,
    _sha256,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "research/dickens_typeiii_temperature_observation_diagnostic_2026_10_11.json"

OPERATORS = {
    "gas_temperature": "uniform gas state",
    "liner_temperature": "inner liner state",
    "shell_temperature": "outer composite shell state",
    "gas_liner_mean": "unweighted gas and liner state mean",
    "gas_shell_mean": "unweighted gas and shell state mean",
    "all_state_mean": "unweighted gas, liner, and shell state mean",
}


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _metrics(prediction: np.ndarray, observed: np.ndarray) -> dict[str, float]:
    error = prediction - observed
    return {
        "temperature_rmse_k": float(np.sqrt(np.mean(np.square(error)))),
        "temperature_mae_k": float(np.mean(np.abs(error))),
        "temperature_peak_error_k": float(np.max(prediction) - np.max(observed)),
        "temperature_max_absolute_error_k": float(np.max(np.abs(error))),
    }


def run() -> dict[str, object]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    source_info = protocol["source"]
    archive_path = ROOT / source_info["archive"]
    case_path = ROOT / source_info["case_file"]
    observed_hashes = {
        "archive_sha256": _sha256(archive_path),
        "case_file_sha256": _sha256(case_path),
    }
    expected_hashes = {
        "archive_sha256": source_info["archive_sha256"],
        "case_file_sha256": source_info["case_file_sha256"],
    }
    if observed_hashes != expected_hashes:
        raise RuntimeError("Frozen Dickens source hash mismatch")

    source = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    tank, derived_geometry = _build_tank(source)
    initial = source["initial"]
    initial_state = tank.initial_state(
        pressure_pa=float(initial["pressure"]),
        gas_temperature_k=float(initial["temperature"]),
    )
    valve = source["valve"]
    flow_time_s = np.asarray(valve["time"], dtype=float)
    flow_kg_s = np.asarray(valve["mdot"], dtype=float)
    inlet_enthalpy_j_kg = float(PropsSI(
        "Hmass", "P", float(valve["back_pressure"]), "T",
        float(initial["temperature"]), "Hydrogen",
    ))
    validation = source["validation"]
    pressure_time_s = np.asarray(validation["pressure"]["time"], dtype=float)
    temperature_time_s = np.asarray(
        validation["temperature"]["gas_mean"]["time"], dtype=float,
    )
    observed_temperature_k = np.asarray(
        validation["temperature"]["gas_mean"]["temp"], dtype=float,
    )
    evaluation_time_s = np.unique(np.concatenate((
        np.asarray([0.0]), pressure_time_s, temperature_time_s,
        np.asarray([max(pressure_time_s[-1], temperature_time_s[-1])]),
    )))
    p = tank.parameters

    def rhs(time_s: float, values: np.ndarray) -> np.ndarray:
        state = CompositeTankState.from_vector(values[:4])
        mass_flow_kg_s = float(np.interp(
            time_s, flow_time_s, flow_kg_s,
            left=flow_kg_s[0], right=flow_kg_s[-1],
        ))
        derivative = tank.derivative(state, TankBoundaryFlow(
            inlet_mass_flow_kg_s=mass_flow_kg_s,
            inlet_specific_enthalpy_j_kg=inlet_enthalpy_j_kg,
            ambient_temperature_k=float(source["heat_transfer"]["temp_ambient"]),
        ))
        shell_ambient_heat_w = (
            p.shell_ambient_ua_w_k
            * tank.fit.shell_ambient_ua_multiplier
            * (state.shell_temperature_k - float(source["heat_transfer"]["temp_ambient"]))
        )
        return np.concatenate((
            derivative.as_vector(),
            np.asarray([
                mass_flow_kg_s,
                mass_flow_kg_s * inlet_enthalpy_j_kg,
                shell_ambient_heat_w,
            ]),
        ))

    solution = solve_ivp(
        rhs,
        (0.0, float(evaluation_time_s[-1])),
        np.concatenate((initial_state.as_vector(), np.zeros(3))),
        method="BDF", rtol=1.0e-7, atol=1.0e-9, t_eval=evaluation_time_s,
    )
    if not solution.success:
        raise RuntimeError(f"Dickens integration failed: {solution.message}")

    gas_k = []
    for column in solution.y[:4].T:
        gas_k.append(tank.gas_state(CompositeTankState.from_vector(column)).temperature_k)
    gas_k = np.asarray(gas_k)
    liner_k = np.asarray(solution.y[2], dtype=float)
    shell_k = np.asarray(solution.y[3], dtype=float)
    predictions = {
        "gas_temperature": np.interp(temperature_time_s, solution.t, gas_k),
        "liner_temperature": np.interp(temperature_time_s, solution.t, liner_k),
        "shell_temperature": np.interp(temperature_time_s, solution.t, shell_k),
    }
    predictions["gas_liner_mean"] = (
        predictions["gas_temperature"] + predictions["liner_temperature"]
    ) / 2.0
    predictions["gas_shell_mean"] = (
        predictions["gas_temperature"] + predictions["shell_temperature"]
    ) / 2.0
    predictions["all_state_mean"] = (
        predictions["gas_temperature"] + predictions["liner_temperature"]
        + predictions["shell_temperature"]
    ) / 3.0
    metrics = {
        name: _metrics(values, observed_temperature_k)
        for name, values in predictions.items()
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "diagnostic_type": "Dickens Type-III temperature-observation semantic replay",
        "evidence_role": "post_outcome_semantic_diagnostic_only",
        "post_outcome": True,
        "parameter_fitting": False,
        "runtime_thermal_observation_changed": False,
        "observation_mapping_selection_prohibited": True,
        "promotion_to_validation_prohibited": True,
        "frozen_validation_result_revised": False,
        "raw_experimental_rows_persisted": False,
        "source_hashes_match": True,
        "protocol": str(PROTOCOL_PATH.relative_to(ROOT)).replace("\\", "/"),
        "case_id": source_info["case_id"],
        "dataset_doi": source_info["dataset_doi"],
        "candidate_observation_operators": OPERATORS,
        "derived_geometry": derived_geometry,
        "measurement_summary": {
            "reported_channel": "gas_mean",
            "temperature_points": int(temperature_time_s.size),
            "model_replay": "same unfitted layered gas-liner-shell model as frozen Dickens result",
        },
        "metrics": metrics,
        "interpretation": (
            "The reported gas_mean channel is not uniquely identified by its label. "
            "Predefined gas/liner/shell combinations can be compared to expose an "
            "observation-semantic ambiguity, but no operator is selected from these "
            "post-outcome errors and the frozen prospective result remains unchanged."
        ),
        "claim_boundary": (
            "This is a post-outcome diagnostic only. It does not validate the selected "
            "operator, change runtime thermal logic, or close the Dickens Type-III gate."
        ),
    }


def main() -> int:
    report = run()
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": report["metrics"], "output": str(OUTPUT_PATH)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
