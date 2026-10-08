"""Compare declared metal-tank heat-transfer models against Woodfield traces.

The embedded measurement rows are read from a pinned external HydDown checkout.
Only hashes and aggregate metrics are written to this repository because reuse
rights for the original paper measurements have not been independently confirmed.
"""

from __future__ import annotations

from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import subprocess
import yaml
import numpy as np
from fluids import TANK
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar
from CoolProp import AbstractState, CoolProp as CP

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SOURCE_COMMIT = "1040d758b819533451086baa5cf2a47b4292a22f"
EXPECTED_HASHES = {
    "fillingH2_woodfield.yml": "d2978ccbd9928ae8c8c363f9a7fc912ad3ba9e5d67b3c30ae8c30ddb2e14af54",
    "dischargeH2_woodfield.yml": "c0f5c3f96670f2e7063b9c99dcebb3871c758ad78f41253ca431ec3bf4a82f8b",
}
DEFAULT_SOURCE_ROOT = Path(
    os.environ.get(
        "HYDDOWN_ROOT",
        REPO_ROOT.parent / "HRS_sim" / "tmp" / "HydDown-public",
    )
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "research/woodfield_metal_tank_heat_transfer_development_2026_10_08.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit(path: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"

class EOS:
    def __init__(self):
        self.storage = AbstractState("HEOS", "Hydrogen")
        self.nozzle = AbstractState("HEOS", "Hydrogen")
    def pt(self, p, t):
        self.storage.update(CP.PT_INPUTS, p, t)
        return self.storage
    def ru(self, rho, u):
        self.storage.update(CP.DmassUmass_INPUTS, rho, u)
        return self.storage
    def flux(self, p, t, p2):
        self.nozzle.update(CP.PT_INPUTS, p, t)
        entropy = self.nozzle.smass()
        h0 = self.nozzle.hmass()
        lo, hi = max(p2, 1000.0), p * (1.0 - 1.0e-9)
        if lo >= hi:
            return 0.0
        def negative_flux(log_p):
            self.nozzle.update(CP.PSmass_INPUTS, math.exp(log_p), entropy)
            return -self.nozzle.rhomass() * math.sqrt(max(2.0 * (h0 - self.nozzle.hmass()), 0.0))
        optimum = minimize_scalar(negative_flux, bounds=(math.log(lo), math.log(hi)), method="bounded")
        return max(-negative_flux(math.log(lo)), -float(optimum.fun))

def simulate(
    source_root: Path,
    filename: str,
    mode: str,
    correlation: str,
) -> dict[str, float | str]:
    if mode not in {"fill", "discharge"}:
        raise ValueError("mode must be fill or discharge")
    if correlation not in {"natural", "ours"}:
        raise ValueError("correlation must be natural or ours")

    source = yaml.safe_load(
        (source_root / "validation" / filename).read_text(encoding="utf-8")
    )
    vessel = source["vessel"]
    initial = source["initial"]
    heat = source["heat_transfer"]
    valve = source["valve"]
    diameter = float(vessel["diameter"])
    length = float(vessel["length"])
    thickness = float(vessel["thickness"])
    horizontal = vessel.get("orientation", "horizontal") == "horizontal"
    inner_geometry = TANK(D=diameter, L=length, horizontal=horizontal)
    outer_geometry = inner_geometry.add_thickness(thickness)
    volume = float(inner_geometry.V_total)
    internal_area = float(inner_geometry.A)
    external_area = float(outer_geometry.A)
    wall_volume = float(outer_geometry.V_total - inner_geometry.V_total)
    wall_capacity = (
        wall_volume
        * float(vessel["density"])
        * float(vessel["heat_capacity"])
    )
    external_htc = float(heat["h_outer"])

    eos = EOS()
    state = eos.pt(float(initial["pressure"]), float(initial["temperature"]))
    mass0 = state.rhomass() * volume
    energy0 = mass0 * state.umass()
    wall0 = float(initial["temperature"])
    initial_total_energy = energy0 + wall_capacity * wall0
    ambient = float(heat["temp_ambient"])

    if mode == "fill":
        flow_time = np.asarray(valve["time"], dtype=float)
        flow = np.asarray(valve["mdot"], dtype=float)
        inlet_pressure = float(valve["back_pressure"])
        inlet_temperature = float(initial["temperature"])
        inlet = AbstractState("HEOS", "Hydrogen")
        inlet.update(CP.PT_INPUTS, inlet_pressure, inlet_temperature)
        inlet_enthalpy = float(inlet.hmass())
        nozzle_diameter = float(heat["D_throat"])
    else:
        nozzle_diameter = float(valve["diameter"])
        discharge_coefficient = float(valve["discharge_coef"])
        back_pressure = float(valve["back_pressure"])

    def quantities(vector: np.ndarray, time_s: float):
        mass = max(float(vector[0]), 1.0e-10)
        gas = eos.ru(mass / volume, float(vector[1]) / mass)
        gas_temperature = float(gas.T())
        pressure = float(gas.p())
        conductivity = float(gas.conductivity())
        viscosity = float(gas.viscosity())
        cp = float(gas.cpmass())
        density = float(gas.rhomass())
        prandtl = float(gas.Prandtl())
        beta = abs(float(gas.isobaric_expansion_coefficient()))
        kinematic_viscosity = viscosity / density
        thermal_diffusivity = conductivity / (density * cp)
        rayleigh = (
            9.80665
            * beta
            * abs(float(vector[2]) - gas_temperature)
            * diameter**3
            / max(
                kinematic_viscosity * thermal_diffusivity,
                1.0e-30,
            )
        )
        nusselt = (
            0.60
            + 0.387
            * rayleigh ** (1.0 / 6.0)
            / (1.0 + (0.559 / max(prandtl, 1.0e-12)) ** (9.0 / 16.0))
            ** (8.0 / 27.0)
        ) ** 2

        if mode == "fill":
            mass_flow = (
                float(np.interp(time_s, flow_time, flow))
                if time_s <= flow_time[-1]
                else 0.0
            )
        else:
            mass_flow = (
                discharge_coefficient
                * math.pi
                * nozzle_diameter**2
                / 4.0
                * eos.flux(pressure, gas_temperature, back_pressure)
                if pressure > back_pressure * 1.0001
                else 0.0
            )

        reynolds = (
            4.0
            * abs(mass_flow)
            / max(math.pi * nozzle_diameter * viscosity, 1.0e-30)
        )
        if correlation == "ours" and mode == "fill":
            nusselt += (
                1.5
                * math.sqrt(nozzle_diameter / diameter)
                * reynolds**0.67
            )
        h_inside = nusselt * conductivity / diameter
        heat_to_gas = (
            h_inside
            * internal_area
            * (float(vector[2]) - gas_temperature)
        )
        heat_to_wall = (
            external_htc
            * external_area
            * (ambient - float(vector[2]))
        )
        return gas, mass_flow, heat_to_gas, heat_to_wall

    def rhs(time_s: float, vector: np.ndarray) -> np.ndarray:
        gas, mass_flow, heat_to_gas, heat_to_wall = quantities(vector, time_s)
        if mode == "fill":
            mass_rate = mass_flow
            boundary_energy_rate = mass_flow * inlet_enthalpy
        else:
            mass_rate = -mass_flow
            boundary_energy_rate = -mass_flow * float(gas.hmass())
        return np.asarray(
            [
                mass_rate,
                boundary_energy_rate + heat_to_gas,
                (-heat_to_gas + heat_to_wall) / wall_capacity,
                mass_rate,
                boundary_energy_rate,
                heat_to_wall,
            ],
            dtype=float,
        )

    validation = source["validation"]
    end_time = float(source["calculation"]["end_time"])
    times = np.unique(
        np.r_[
            0.0,
            validation["pressure"]["time"],
            validation["temperature"]["gas_high"]["time"],
            validation["temperature"]["gas_low"]["time"],
            end_time,
        ]
    )
    solution = solve_ivp(
        rhs,
        (0.0, end_time),
        [mass0, energy0, wall0, 0.0, 0.0, 0.0],
        t_eval=times,
        method="LSODA",
        rtol=2.0e-6,
        atol=[1.0e-11, 1.0e-3, 1.0e-7, 1.0e-11, 1.0e-3, 1.0e-3],
        max_step=0.05,
    )
    if not solution.success:
        raise RuntimeError(
            f"Woodfield {mode} integration failed: {solution.message}"
        )

    pressure: list[float] = []
    temperature: list[float] = []
    for vector in solution.y.T:
        mass = max(float(vector[0]), 1.0e-10)
        gas = eos.ru(mass / volume, float(vector[1]) / mass)
        pressure.append(float(gas.p()) / 1.0e5)
        temperature.append(float(gas.T()))
    pressure_values = np.asarray(pressure)
    temperature_values = np.asarray(temperature)

    pressure_time = np.asarray(validation["pressure"]["time"], dtype=float)
    pressure_measured = np.asarray(
        validation["pressure"]["pres"],
        dtype=float,
    )
    pressure_predicted = np.interp(
        pressure_time,
        solution.t,
        pressure_values,
    )
    high_time = np.asarray(
        validation["temperature"]["gas_high"]["time"],
        dtype=float,
    )
    low_time = np.asarray(
        validation["temperature"]["gas_low"]["time"],
        dtype=float,
    )
    high_value = np.asarray(
        validation["temperature"]["gas_high"]["temp"],
        dtype=float,
    )
    low_value = np.asarray(
        validation["temperature"]["gas_low"]["temp"],
        dtype=float,
    )
    union_time = np.unique(np.r_[high_time, low_time])
    high = np.interp(union_time, high_time, high_value)
    low = np.interp(union_time, low_time, low_value)
    predicted = np.interp(
        union_time,
        solution.t,
        temperature_values,
    )
    lower = np.minimum(high, low)
    upper = np.maximum(high, low)
    outside = np.where(
        predicted < lower,
        lower - predicted,
        np.where(predicted > upper, predicted - upper, 0.0),
    )
    midpoint = 0.5 * (lower + upper)

    final_total_energy = (
        float(solution.y[1, -1])
        + wall_capacity * float(solution.y[2, -1])
    )
    mass_residual = (
        float(solution.y[0, -1]) - mass0 - float(solution.y[3, -1])
    )
    energy_residual = (
        final_total_energy
        - initial_total_energy
        - float(solution.y[4, -1])
        - float(solution.y[5, -1])
    )
    mass_change = float(solution.y[0, -1]) - mass0
    energy_throughput = (
        abs(float(solution.y[4, -1]))
        + abs(float(solution.y[5, -1]))
    )

    return {
        "mode": mode,
        "correlation": correlation,
        "volume_l": volume * 1000.0,
        "wall_volume_l": wall_volume * 1000.0,
        "wall_capacity_j_k": wall_capacity,
        "pressure_rmse_bar": float(
            np.sqrt(np.mean((pressure_predicted - pressure_measured) ** 2))
        ),
        "temperature_midpoint_rmse_k": float(
            np.sqrt(np.mean((predicted - midpoint) ** 2))
        ),
        "temperature_envelope_rmse_k": float(
            np.sqrt(np.mean(outside**2))
        ),
        "predicted_peak_temperature_k": float(
            np.max(temperature_values)
        ),
        "predicted_final_pressure_bar": float(pressure_values[-1]),
        "predicted_final_temperature_k": float(temperature_values[-1]),
        "mass_residual_relative": (
            abs(mass_residual) / max(abs(mass_change), 1.0e-12)
        ),
        "energy_residual_relative": (
            abs(energy_residual) / max(energy_throughput, 1.0)
        ),
    }

def run(source_root: Path) -> dict[str, object]:
    source_root = source_root.resolve()
    source_commit = _git_commit(source_root)
    if source_commit != EXPECTED_SOURCE_COMMIT:
        raise RuntimeError(
            f"HydDown commit mismatch: expected {EXPECTED_SOURCE_COMMIT}, got {source_commit}"
        )
    observed_hashes = {
        name: _sha256(source_root / "validation" / name)
        for name in EXPECTED_HASHES
    }
    if observed_hashes != EXPECTED_HASHES:
        raise RuntimeError("Woodfield source hash mismatch")

    experiments: dict[str, object] = {}
    for mode, filename in (
        ("fill", "fillingH2_woodfield.yml"),
        ("discharge", "dischargeH2_woodfield.yml"),
    ):
        experiments[mode] = {
            "natural_convection_only": simulate(
                source_root, filename, mode, "natural"
            ),
            "station_mixed_convection": simulate(
                source_root, filename, mode, "ours"
            ),
        }

    fill_natural = experiments["fill"]["natural_convection_only"]
    fill_mixed = experiments["fill"]["station_mixed_convection"]
    discharge_natural = experiments["discharge"]["natural_convection_only"]
    discharge_mixed = experiments["discharge"]["station_mixed_convection"]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_type": "post_access_woodfield_metal_tank_heat_transfer_development",
        "evidence_role": "model-development diagnostic only",
        "post_access": True,
        "parameter_fitting": False,
        "runtime_parameter_updated": False,
        "validation_gate_effect": "none",
        "source": {
            "repository": "https://github.com/andr1976/HydDown",
            "commit": source_commit,
            "license": "MIT",
            "case_ids": ["Woodfield filling H2", "Woodfield discharge H2"],
            "original_publication": {
                "title": (
                    "Measurement of Averaged Heat Transfer Coefficients in "
                    "High-Pressure Vessel during Charging with Hydrogen, "
                    "Nitrogen or Argon Gas"
                ),
                "doi": "10.1299/jtst.2.180",
                "year": 2007,
            },
            "source_hashes": observed_hashes,
            "source_hashes_match": True,
            "original_measurement_rights_independently_confirmed": False,
        },
        "privacy_and_rights": {
            "raw_measurement_rows_persisted": False,
            "raw_measurement_arrays_persisted": False,
            "absolute_local_source_path_persisted": False,
            "derived_metrics_only": True,
            "rights_boundary": (
                "The HydDown repository is MIT licensed, but the embedded "
                "measurement arrays are a secondary transcription. Only hashes, "
                "source metadata and aggregate errors are retained here."
            ),
        },
        "model": {
            "real_gas_eos": "CoolProp HEOS Hydrogen",
            "gas_control_volume": "uniform pressure and bulk temperature",
            "wall_control_volume": "single measured-geometry steel thermal mass",
            "natural_convection": "Churchill-Chu horizontal-cylinder form",
            "station_mixed_convection": (
                "existing Nu_forced = 1.5 sqrt(D_nozzle/D_tank) Re^0.67; "
                "forced term active during positive inlet flow only"
            ),
            "discharge_flow": "real-gas isentropic maximum-flux orifice",
            "formulation_source_commit": "91698f51",
            "formulation_changed_for_this_dataset": False,
        },
        "experiments": experiments,
        "comparisons": {
            "fill_pressure_rmse_reduction_percent": (
                100.0
                * (
                    fill_natural["pressure_rmse_bar"]
                    - fill_mixed["pressure_rmse_bar"]
                )
                / fill_natural["pressure_rmse_bar"]
            ),
            "fill_temperature_envelope_rmse_reduction_percent": (
                100.0
                * (
                    fill_natural["temperature_envelope_rmse_k"]
                    - fill_mixed["temperature_envelope_rmse_k"]
                )
                / fill_natural["temperature_envelope_rmse_k"]
            ),
            "discharge_pressure_rmse_difference_bar": (
                discharge_mixed["pressure_rmse_bar"]
                - discharge_natural["pressure_rmse_bar"]
            ),
            "discharge_temperature_envelope_rmse_difference_k": (
                discharge_mixed["temperature_envelope_rmse_k"]
                - discharge_natural["temperature_envelope_rmse_k"]
            ),
        },
        "interpretation": {
            "fill_mechanism_supported": (
                fill_mixed["temperature_envelope_rmse_k"]
                < fill_natural["temperature_envelope_rmse_k"]
                and fill_mixed["pressure_rmse_bar"]
                < fill_natural["pressure_rmse_bar"]
            ),
            "discharge_path_unchanged_by_inlet_forcing": (
                abs(
                    discharge_mixed["temperature_envelope_rmse_k"]
                    - discharge_natural["temperature_envelope_rmse_k"]
                )
                < 1.0e-9
            ),
            "production_default_change_supported": False,
            "prospective_validation_claim_supported": False,
            "next_evidence": (
                "Freeze the unchanged mixed-convection formulation and exact "
                "geometry before opening a new independent Type-III/IV fill."
            ),
        },
        "claim_boundary": (
            "The already inspected Woodfield traces support mechanism diagnosis "
            "only. They do not close the prospective tank-thermal validation gate, "
            "select a production parameter, or validate the full station loop."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hyddown-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.hyddown_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

