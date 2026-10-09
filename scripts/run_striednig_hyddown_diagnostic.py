"""Run a claim-bounded Type-I filling diagnostic on the public HydDown cases.

The HydDown repository transcribes three Striednig et al. Type-I hydrogen
filling experiments.  The source is useful for an independent vessel thermal
check, but it does not contain a station controller or vehicle-side trace.
This runner therefore emits aggregate metrics only and can never change the
runtime fit or an external full-loop gate.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import yaml
from scipy.integrate import solve_ivp

from h2station.dispenser import IsentropicRealGasRestriction, RestrictionParameters
from h2station.tabulated import PropsSI


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "research/striednig_hyddown_screening.json"
SOURCE_ROOT = ROOT / "data/public_validation/raw/zenodo_20728325/unpacked/zenodo_archive/inputs/hyddown_validation"
RESULT_PATH = ROOT / "research/striednig_hyddown_diagnostic_result_2026_10_10.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _sha256_lf_normalized(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest().upper()


def _wall_area(diameter_m: float, length_m: float) -> float:
    return math.pi * diameter_m * length_m + 0.5 * math.pi * diameter_m**2


def _case_result(case: dict[str, object], expected_hash: str, expected_lf_hash: str) -> dict[str, object]:
    relative = Path(str(case["file"])).name
    source_path = SOURCE_ROOT / relative
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    observed_hash = _sha256(source_path)
    observed_lf_hash = _sha256_lf_normalized(source_path)
    if observed_lf_hash != expected_lf_hash:
        raise RuntimeError(f"Striednig source content mismatch: {relative}")

    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    vessel = source["vessel"]
    diameter_m = float(vessel["diameter"])
    length_m = float(vessel["length"])
    area_m2 = _wall_area(diameter_m, length_m)
    volume_m3 = math.pi * diameter_m**2 * length_m / 4.0
    wall_mass_kg = (
        area_m2 * float(vessel["thickness"]) * float(vessel["density"])
    )
    wall_cp_j_kg_k = float(vessel["heat_capacity"])
    initial = source["initial"]
    initial_temperature_k = float(initial["temperature"])
    initial_pressure_pa = float(initial["pressure"])
    upstream_pressure_pa = float(source["valve"]["back_pressure"])
    ambient_temperature_k = float(source["heat_transfer"]["temp_ambient"])
    orifice_diameter_m = float(source["valve"]["diameter"])
    discharge_coefficient = float(source["valve"]["discharge_coef"])
    restriction = IsentropicRealGasRestriction(
        RestrictionParameters(
            flow_area_m2=math.pi * orifice_diameter_m**2 / 4.0,
            discharge_coefficient=discharge_coefficient,
        )
    )

    initial_density = float(
        PropsSI(
            "Dmass", "P", initial_pressure_pa, "T", initial_temperature_k,
            "Hydrogen",
        )
    )
    initial_mass_kg = initial_density * volume_m3
    initial_internal_energy_j = initial_mass_kg * float(
        PropsSI(
            "Umass", "P", initial_pressure_pa, "T", initial_temperature_k,
            "Hydrogen",
        )
    )
    inlet_enthalpy_j_kg = float(
        PropsSI(
            "Hmass", "P", upstream_pressure_pa, "T", ambient_temperature_k,
            "Hydrogen",
        )
    )

    def rhs(_time_s: float, values: np.ndarray) -> np.ndarray:
        mass_kg, internal_energy_j, wall_temperature_k = values
        density = mass_kg / volume_m3
        specific_internal_energy = internal_energy_j / mass_kg
        pressure_pa = float(
            PropsSI(
                "P", "Dmass", density, "Umass", specific_internal_energy,
                "Hydrogen",
            )
        )
        gas_temperature_k = float(
            PropsSI(
                "T", "Dmass", density, "Umass", specific_internal_energy,
                "Hydrogen",
            )
        )
        mass_flow_kg_s = (
            restriction.mass_flow_kg_s(
                upstream_pressure_pa, ambient_temperature_k, pressure_pa,
            )
            if pressure_pa < upstream_pressure_pa else 0.0
        )

        # HydDown's filling path uses a mixed natural/forced-convection
        # correlation.  Transport properties are evaluated at the gas/wall
        # film state; no experiment-specific fitting is applied here.
        film_temperature_k = 0.5 * (gas_temperature_k + wall_temperature_k)
        conductivity_w_m_k = float(
            PropsSI("CONDUCTIVITY", "P", pressure_pa, "T", film_temperature_k, "Hydrogen")
        )
        viscosity_pa_s = float(
            PropsSI("VISCOSITY", "P", pressure_pa, "T", film_temperature_k, "Hydrogen")
        )
        heat_capacity_j_kg_k = float(
            PropsSI("CPMASS", "P", pressure_pa, "T", film_temperature_k, "Hydrogen")
        )
        film_density_kg_m3 = float(
            PropsSI("Dmass", "P", pressure_pa, "T", film_temperature_k, "Hydrogen")
        )
        kinematic_viscosity_m2_s = viscosity_pa_s / film_density_kg_m3
        thermal_diffusivity_m2_s = conductivity_w_m_k / (
            film_density_kg_m3 * heat_capacity_j_kg_k
        )
        prandtl = kinematic_viscosity_m2_s / thermal_diffusivity_m2_s
        rayleigh = (
            9.80665
            * (1.0 / film_temperature_k)
            * max(abs(wall_temperature_k - gas_temperature_k), 1.0e-9)
            * diameter_m**3
            / (kinematic_viscosity_m2_s**2)
        )
        nusselt_free = (
            0.60
            + 0.387 * rayleigh ** (1.0 / 6.0)
            / (1.0 + (0.559 / prandtl) ** (9.0 / 16.0)) ** (8.0 / 27.0)
        ) ** 2
        reynolds = 4.0 * abs(mass_flow_kg_s) / (
            viscosity_pa_s * math.pi * diameter_m
        )
        nusselt = nusselt_free + 0.56 * reynolds**0.67
        gas_wall_ua_w_k = nusselt * conductivity_w_m_k / diameter_m * area_m2
        gas_wall_heat_w = gas_wall_ua_w_k * (
            gas_temperature_k - wall_temperature_k
        )
        wall_ambient_heat_w = float(source["heat_transfer"]["h_outer"]) * area_m2 * (
            wall_temperature_k - ambient_temperature_k
        )
        return np.asarray(
            [
                mass_flow_kg_s,
                mass_flow_kg_s * inlet_enthalpy_j_kg - gas_wall_heat_w,
                (gas_wall_heat_w - wall_ambient_heat_w)
                / (wall_mass_kg * wall_cp_j_kg_k),
            ],
            dtype=float,
        )

    end_time_s = float(source["calculation"]["end_time"])
    measurement = source["validation"]["temperature"]["gas_mean"]
    measurement_time_s = np.asarray(measurement["time"], dtype=float)
    measured_temperature_k = np.asarray(measurement["temp"], dtype=float)
    evaluation_time_s = np.unique(
        np.concatenate(([0.0], measurement_time_s, [end_time_s]))
    )
    initial_state = np.asarray(
        [initial_mass_kg, initial_internal_energy_j, initial_temperature_k],
        dtype=float,
    )
    solution = solve_ivp(
        rhs,
        (0.0, end_time_s),
        initial_state,
        method="BDF",
        t_eval=evaluation_time_s,
        rtol=1.0e-6,
        atol=1.0e-8,
    )
    if not solution.success:
        raise RuntimeError(f"Striednig integration failed: {solution.message}")

    predicted_temperature_k: list[float] = []
    predicted_pressure_pa: list[float] = []
    for mass_kg, internal_energy_j, _wall_temperature_k in solution.y.T:
        density = mass_kg / volume_m3
        specific_internal_energy = internal_energy_j / mass_kg
        predicted_temperature_k.append(
            float(
                PropsSI(
                    "T", "Dmass", density, "Umass", specific_internal_energy,
                    "Hydrogen",
                )
            )
        )
        predicted_pressure_pa.append(
            float(
                PropsSI(
                    "P", "Dmass", density, "Umass", specific_internal_energy,
                    "Hydrogen",
                )
            )
        )
    predicted_temperature = np.interp(
        measurement_time_s, solution.t, predicted_temperature_k,
    )
    temperature_error = predicted_temperature - measured_temperature_k
    final_state = solution.y[:, -1]
    mass_added_kg = float(final_state[0] - initial_mass_kg)
    integrated_mass_kg = float(
        np.trapezoid([rhs(t, y)[0] for t, y in zip(solution.t, solution.y.T)], solution.t)
    )
    mass_residual_kg = mass_added_kg - integrated_mass_kg
    return {
        "case": str(case["case"]),
        "source_file": str(case["file"]),
        "source_sha256": observed_hash,
        "source_sha256_lf_normalized": observed_lf_hash,
        "source_sha256_raw_reference": expected_hash,
        "measurement_count": int(len(measured_temperature_k)),
        "duration_s": end_time_s,
        "model": {
            "volume_m3": volume_m3,
            "wall_mass_kg": wall_mass_kg,
            "orifice_diameter_mm": orifice_diameter_m * 1000.0,
            "upstream_pressure_mpa_abs": upstream_pressure_pa / 1.0e6,
            "mixed_convection": True,
            "case_specific_fitting": False,
        },
        "metrics": {
            "gas_temperature_rmse_k": float(np.sqrt(np.mean(temperature_error**2))),
            "gas_temperature_peak_absolute_error_k": float(
                abs(np.max(predicted_temperature) - np.max(measured_temperature_k))
            ),
            "measured_peak_temperature_k": float(np.max(measured_temperature_k)),
            "predicted_peak_temperature_k": float(np.max(predicted_temperature)),
            "predicted_final_pressure_mpa_abs": float(predicted_pressure_pa[-1] / 1.0e6),
            "mass_residual_relative": float(
                abs(mass_residual_kg) / max(abs(mass_added_kg), 1.0e-12)
            ),
        },
    }


def run() -> dict[str, object]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    hashes = {
        Path(item["path"]).name: (
            str(item["sha256"]).upper(),
            str(item["sha256_lf_normalized"]).upper(),
        )
        for item in protocol["source"]["source_files"]
    }
    cases = [
        _case_result(case, *hashes[Path(str(case["file"])).name])
        for case in protocol["embedded_measurement_series"]
    ]
    return {
        "schema_version": 1,
        "artifact_type": "public_type_i_filling_thermal_diagnostic",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_role": "post_access_public_component_diagnostic",
        "source": {
            "protocol": str(PROTOCOL_PATH.relative_to(ROOT)).replace("\\", "/"),
            "repository": protocol["source"]["repository"],
            "repository_commit": protocol["source"]["commit"],
            "paper_doi": protocol["source"]["paper"]["doi"],
            "case_count": len(cases),
        },
        "cases": cases,
        "eligibility": {
            "physical_experiment": True,
            "common_time_base": True,
            "full_loop_station_vehicle_validation_eligible": False,
            "runtime_parameter_application": False,
            "validation_gate_changed": False,
            "raw_measurement_arrays_persisted": False,
        },
        "claim_boundary": (
            "This is an aggregate-only diagnostic of the vessel thermal submodel "
            "against three public Type-I filling experiments. It does not validate "
            "station control, cascade dispatch, dispenser metering, vehicle filling, "
            "safety response or consequence distances, and it does not change any "
            "runtime parameter or validation gate."
        ),
        "rights_boundary": protocol["eligibility_decision"]["rights_boundary"],
    }


def main() -> int:
    result = run()
    RESULT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "artifact_type": result["artifact_type"],
                "case_count": len(result["cases"]),
                "temperature_rmse_k": [
                    round(item["metrics"]["gas_temperature_rmse_k"], 4)
                    for item in result["cases"]
                ],
                "runtime_parameter_application": result["eligibility"]["runtime_parameter_application"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
