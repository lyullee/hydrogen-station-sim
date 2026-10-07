"""Run the frozen Dickens Type-III hydrogen filling validation.

The protocol was committed before numerical measurement values were printed or
reviewed.  The runner verifies the frozen source hashes, uses only source-declared
geometry/material/boundary fields, and emits metrics rather than measurement rows.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np
from scipy.integrate import solve_ivp
import yaml

from h2station.tabulated import PropsSI
from h2station.vehicle import (
    CompositeTankParameters,
    CompositeTankState,
    CompositeVehicleTank,
    TankBoundaryFlow,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "research/dickens_typeiii_prospective_protocol_2026_10_08.json"
RESULT_PATH = ROOT / "research/dickens_typeiii_prospective_result_2026_10_08.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _wall_area(diameter_m: float, length_m: float) -> float:
    return math.pi * diameter_m * length_m + 0.5 * math.pi * diameter_m**2


def _build_tank(source: dict) -> tuple[CompositeVehicleTank, dict[str, float]]:
    vessel = source["vessel"]
    heat = source["heat_transfer"]
    diameter_m = float(vessel["diameter"])
    length_m = float(vessel["length"])
    area_m2 = _wall_area(diameter_m, length_m)
    liner_thickness_m = float(vessel["liner_thickness"])
    shell_thickness_m = float(vessel["thickness"])
    liner_k = float(vessel["liner_thermal_conductivity"])
    shell_k = float(vessel["thermal_conductivity"])
    liner_shell_ua_w_k = area_m2 / (
        0.5 * liner_thickness_m / liner_k
        + 0.5 * shell_thickness_m / shell_k
    )
    parameters = CompositeTankParameters(
        internal_volume_m3=math.pi * diameter_m**2 * length_m / 4.0,
        liner_mass_kg=area_m2 * liner_thickness_m * float(vessel["liner_density"]),
        liner_specific_heat_j_kg_k=float(vessel["liner_heat_capacity"]),
        shell_mass_kg=area_m2 * shell_thickness_m * float(vessel["density"]),
        shell_specific_heat_j_kg_k=float(vessel["heat_capacity"]),
        gas_liner_ua_w_k=0.0,
        liner_shell_ua_w_k=liner_shell_ua_w_k,
        shell_ambient_ua_w_k=float(heat["h_outer"]) * area_m2,
        internal_diameter_m=diameter_m,
        internal_length_m=length_m,
        natural_convection_gas_liner=True,
    )
    return CompositeVehicleTank(parameters), {
        "internal_volume_m3": parameters.internal_volume_m3,
        "wall_area_m2": area_m2,
        "liner_mass_kg": parameters.liner_mass_kg,
        "shell_mass_kg": parameters.shell_mass_kg,
        "liner_shell_ua_w_k": parameters.liner_shell_ua_w_k,
        "shell_ambient_ua_w_k": parameters.shell_ambient_ua_w_k,
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
        np.asarray([max(pressure_time_s[-1], temperature_time_s[-1])]),
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
        method="BDF",
        t_eval=evaluation_time_s,
        rtol=1.0e-7,
        atol=1.0e-9,
    )
    if not solution.success:
        raise RuntimeError(f"Dickens integration failed: {solution.message}")

    predicted_pressure_pa = []
    predicted_temperature_k = []
    for column in solution.y[:4].T:
        gas = tank.gas_state(CompositeTankState.from_vector(column))
        predicted_pressure_pa.append(gas.pressure_pa)
        predicted_temperature_k.append(gas.temperature_k)
    predicted_pressure_pa = np.asarray(predicted_pressure_pa)
    predicted_temperature_k = np.asarray(predicted_temperature_k)
    pressure_prediction = np.interp(
        pressure_time_s, solution.t, predicted_pressure_pa,
    )
    temperature_prediction = np.interp(
        temperature_time_s, solution.t, predicted_temperature_k,
    )
    pressure_error_pa = pressure_prediction - measured_pressure_pa
    temperature_error_k = temperature_prediction - measured_temperature_k
    pressure_rmse_mpa = float(np.sqrt(np.mean(pressure_error_pa**2)) / 1.0e6)
    pressure_span_pa = float(np.ptp(measured_pressure_pa))
    pressure_nrmse_percent_span = float(
        np.sqrt(np.mean(pressure_error_pa**2)) / pressure_span_pa * 100.0
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
    mass_residual_kg = mass_change_kg - float(solution.y[4, -1])
    energy_residual_j = (
        final_total_energy_j - initial_total_energy_j
        - (float(solution.y[5, -1]) - float(solution.y[6, -1]))
    )
    mass_residual_relative = abs(mass_residual_kg) / max(abs(mass_change_kg), 1.0e-12)
    energy_residual_relative = abs(energy_residual_j) / max(
        abs(float(solution.y[5, -1])), 1.0,
    )
    limits = protocol["primary_screens"]
    screens = {
        "pressure_nrmse_percent_measured_span": (
            pressure_nrmse_percent_span
            <= float(limits["pressure_nrmse_percent_measured_span_max"])
        ),
        "pressure_rmse_mpa": (
            pressure_rmse_mpa <= float(limits["pressure_rmse_mpa_max"])
        ),
        "gas_temperature_rmse_k": (
            temperature_rmse_k <= float(limits["gas_temperature_rmse_k_max"])
        ),
        "gas_temperature_peak_absolute_error_k": (
            peak_temperature_error_k
            <= float(limits["gas_temperature_peak_absolute_error_k_max"])
        ),
    }
    integrity_limits = protocol["integrity_requirements"]
    integrity_pass = (
        mass_residual_relative
        <= float(integrity_limits["mass_residual_relative_max"])
        and energy_residual_relative
        <= float(integrity_limits["energy_residual_relative_max"])
    )
    joint_pass = all(screens.values()) and integrity_pass
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "status": "completed_prospective_external_component_validation",
        "protocol": str(PROTOCOL_PATH.relative_to(ROOT)).replace("\\", "/"),
        "source_hashes_match": True,
        "parameter_fitting": False,
        "post_outcome_parameter_change": False,
        "case_id": source_info["case_id"],
        "fluid": initial["fluid"],
        "derived_geometry": derived_geometry,
        "boundary_summary": {
            "mass_flow_points": int(flow_time_s.size),
            "mass_flow_min_kg_s": float(np.min(flow_kg_s)),
            "mass_flow_max_kg_s": float(np.max(flow_kg_s)),
            "source_pressure_mpa": float(valve["back_pressure"]) / 1.0e6,
            "source_temperature_k": float(initial["temperature"]),
        },
        "measurement_summary": {
            "pressure_points": int(pressure_time_s.size),
            "mean_gas_temperature_points": int(temperature_time_s.size),
        },
        "metrics": {
            "pressure_rmse_mpa": pressure_rmse_mpa,
            "pressure_nrmse_percent_measured_span": pressure_nrmse_percent_span,
            "gas_temperature_rmse_k": temperature_rmse_k,
            "gas_temperature_peak_absolute_error_k": peak_temperature_error_k,
            "mass_residual_relative": mass_residual_relative,
            "energy_residual_relative": energy_residual_relative,
            "predicted_final_pressure_mpa": float(pressure_prediction[-1] / 1.0e6),
            "measured_final_pressure_mpa": float(measured_pressure_pa[-1] / 1.0e6),
            "predicted_peak_temperature_k": float(np.max(temperature_prediction)),
            "measured_peak_temperature_k": float(np.max(measured_temperature_k)),
        },
        "screen_results": screens,
        "integrity_pass": integrity_pass,
        "joint_primary_screen_pass": joint_pass,
        "claim_supported": joint_pass,
        "claim_boundary": protocol["claim_boundary"],
    }


def main() -> int:
    report = run()
    with RESULT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
