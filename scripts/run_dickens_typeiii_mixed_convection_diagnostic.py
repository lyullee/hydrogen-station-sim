"""Post-outcome sensitivity for inlet-jet heat transfer in the Dickens fill.

This diagnostic was designed after the frozen natural-convection result failed
its temperature screens.  It therefore cannot revise that result or select a
production parameter.  Only aggregate errors are persisted.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
import yaml

from h2station.tabulated import PropsSI
from h2station.vehicle import CompositeTankState, TankBoundaryFlow

from run_dickens_typeiii_prospective import (
    PROTOCOL_PATH,
    ROOT,
    _build_tank,
    _git_commit,
    _sha256,
)


RESULT_PATH = ROOT / "research/dickens_typeiii_mixed_convection_diagnostic_2026_10_08.json"
NOZZLE_DIAMETERS_M = (0.003, 0.005, 0.007)


def _evaluate(source: dict, nozzle_diameter_m: float) -> dict[str, object]:
    natural_tank, _ = _build_tank(source)
    tank = type(natural_tank)(replace(
        natural_tank.parameters,
        forced_convection_gas_liner=True,
    ))
    initial = source["initial"]
    initial_state = tank.initial_state(
        pressure_pa=float(initial["pressure"]),
        gas_temperature_k=float(initial["temperature"]),
    )
    valve = source["valve"]
    flow_time_s = np.asarray(valve["time"], dtype=float)
    flow_kg_s = np.asarray(valve["mdot"], dtype=float)
    inlet_pressure_pa = float(valve["back_pressure"])
    inlet_temperature_k = float(initial["temperature"])
    inlet_enthalpy_j_kg = float(PropsSI(
        "Hmass", "P", inlet_pressure_pa, "T", inlet_temperature_k, "Hydrogen",
    ))
    ambient_temperature_k = float(source["heat_transfer"]["temp_ambient"])
    validation = source["validation"]
    pressure_time_s = np.asarray(validation["pressure"]["time"], dtype=float)
    measured_pressure_pa = np.asarray(
        validation["pressure"]["pres"], dtype=float,
    ) * 1.0e5
    temperature_time_s = np.asarray(
        validation["temperature"]["gas_mean"]["time"], dtype=float,
    )
    measured_temperature_k = np.asarray(
        validation["temperature"]["gas_mean"]["temp"], dtype=float,
    )
    evaluation_time_s = np.unique(np.concatenate((
        np.asarray([0.0]), pressure_time_s, temperature_time_s,
    )))
    p = tank.parameters
    initial_total_energy_j = (
        initial_state.hydrogen_internal_energy_j
        + p.liner_mass_kg * p.liner_specific_heat_j_kg_k
        * initial_state.liner_temperature_k
        + p.shell_mass_kg * p.shell_specific_heat_j_kg_k
        * initial_state.shell_temperature_k
    )

    def rhs(time_s: float, values: np.ndarray) -> np.ndarray:
        state = CompositeTankState.from_vector(values[:4])
        mass_flow_kg_s = float(np.interp(
            time_s, flow_time_s, flow_kg_s,
            left=flow_kg_s[0], right=flow_kg_s[-1],
        ))
        boundary = TankBoundaryFlow(
            inlet_mass_flow_kg_s=mass_flow_kg_s,
            inlet_specific_enthalpy_j_kg=inlet_enthalpy_j_kg,
            ambient_temperature_k=ambient_temperature_k,
            inlet_pressure_pa=inlet_pressure_pa,
            inlet_temperature_k=inlet_temperature_k,
            inlet_nozzle_diameter_m=nozzle_diameter_m,
        )
        derivative = tank.derivative(state, boundary)
        ambient_heat_w = (
            p.shell_ambient_ua_w_k
            * (state.shell_temperature_k - ambient_temperature_k)
        )
        return np.concatenate((derivative.as_vector(), np.asarray([
            mass_flow_kg_s,
            mass_flow_kg_s * inlet_enthalpy_j_kg,
            ambient_heat_w,
        ])))

    solution = solve_ivp(
        rhs,
        (0.0, float(evaluation_time_s[-1])),
        np.concatenate((initial_state.as_vector(), np.zeros(3))),
        method="BDF",
        t_eval=evaluation_time_s,
        rtol=1.0e-7,
        atol=1.0e-9,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    pressure_pa = []
    temperature_k = []
    for column in solution.y[:4].T:
        gas = tank.gas_state(CompositeTankState.from_vector(column))
        pressure_pa.append(gas.pressure_pa)
        temperature_k.append(gas.temperature_k)
    pressure_prediction = np.interp(
        pressure_time_s, solution.t, np.asarray(pressure_pa),
    )
    temperature_prediction = np.interp(
        temperature_time_s, solution.t, np.asarray(temperature_k),
    )
    pressure_error_pa = pressure_prediction - measured_pressure_pa
    temperature_error_k = temperature_prediction - measured_temperature_k
    pressure_rmse_mpa = float(np.sqrt(np.mean(pressure_error_pa**2)) / 1.0e6)
    pressure_nrmse_percent_span = float(
        np.sqrt(np.mean(pressure_error_pa**2))
        / float(np.ptp(measured_pressure_pa)) * 100.0
    )
    temperature_rmse_k = float(np.sqrt(np.mean(temperature_error_k**2)))
    peak_temperature_error_k = float(
        abs(np.max(temperature_prediction) - np.max(measured_temperature_k))
    )
    final_state = CompositeTankState.from_vector(solution.y[:4, -1])
    final_total_energy_j = (
        final_state.hydrogen_internal_energy_j
        + p.liner_mass_kg * p.liner_specific_heat_j_kg_k
        * final_state.liner_temperature_k
        + p.shell_mass_kg * p.shell_specific_heat_j_kg_k
        * final_state.shell_temperature_k
    )
    mass_change_kg = final_state.hydrogen_mass_kg - initial_state.hydrogen_mass_kg
    mass_residual_relative = abs(
        mass_change_kg - float(solution.y[4, -1])
    ) / max(abs(mass_change_kg), 1.0e-12)
    energy_residual_relative = abs(
        final_total_energy_j - initial_total_energy_j
        - (float(solution.y[5, -1]) - float(solution.y[6, -1]))
    ) / max(abs(float(solution.y[5, -1])), 1.0)
    screens = {
        "pressure_nrmse_percent_measured_span": pressure_nrmse_percent_span <= 5.0,
        "pressure_rmse_mpa": pressure_rmse_mpa <= 2.0,
        "gas_temperature_rmse_k": temperature_rmse_k <= 10.0,
        "gas_temperature_peak_absolute_error_k": peak_temperature_error_k <= 15.0,
    }
    return {
        "nozzle_diameter_mm": nozzle_diameter_m * 1000.0,
        "metrics": {
            "pressure_rmse_mpa": pressure_rmse_mpa,
            "pressure_nrmse_percent_measured_span": pressure_nrmse_percent_span,
            "gas_temperature_rmse_k": temperature_rmse_k,
            "gas_temperature_peak_absolute_error_k": peak_temperature_error_k,
            "mass_residual_relative": mass_residual_relative,
            "energy_residual_relative": energy_residual_relative,
        },
        "screen_results": screens,
        "joint_primary_screen_pass": all(screens.values()),
    }


def run() -> dict[str, object]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    source_info = protocol["source"]
    archive_path = ROOT / source_info["archive"]
    case_path = ROOT / source_info["case_file"]
    if _sha256(archive_path) != source_info["archive_sha256"]:
        raise RuntimeError("Frozen source archive hash mismatch")
    if _sha256(case_path) != source_info["case_file_sha256"]:
        raise RuntimeError("Frozen source case hash mismatch")
    source = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    runs = [_evaluate(source, diameter) for diameter in NOZZLE_DIAMETERS_M]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "diagnostic_type": "post-outcome forced-mixing sensitivity",
        "evidence_role": "model-development diagnostic only",
        "post_outcome": True,
        "parameter_fitting": False,
        "runtime_parameter_updated": False,
        "frozen_validation_result_unchanged": True,
        "source_hashes_match": True,
        "correlation": {
            "form": "Nu_forced = 1.5 * sqrt(D_nozzle / D_tank) * Re^0.67",
            "empirical_factor_two_used": False,
            "coefficient_selected_from_case_outcome": False,
        },
        "method_sources": {
            "published_mechanism_doi": "10.1016/j.ijhydene.2025.04.015",
            "public_reference_implementation": "https://github.com/ArtCouteau/HyTF",
            "public_reference_commit": "f0e8f0446fe7638abe21734d14e654a8a79f95fc",
            "public_reference_license": "GPL-3.0",
            "source_code_copied": False,
            "implementation_note": (
                "The correlation was independently expressed in repository code. "
                "The public reference's separate fitted factor of two was omitted."
            ),
        },
        "unknown_source_metadata": [
            "experiment inlet nozzle internal diameter",
            "time-resolved inlet gas temperature",
        ],
        "runs": runs,
        "validation_gate_effect": "none",
        "claim_boundary": (
            "This post-outcome sensitivity identifies whether an omitted inlet-jet "
            "heat-transfer mechanism can explain the frozen temperature failure. "
            "It cannot select a nozzle diameter, revise the frozen Type-III result, "
            "change the runtime model, or support a validation claim."
        ),
    }


def main() -> int:
    report = run()
    with RESULT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
