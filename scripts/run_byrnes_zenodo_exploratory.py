"""Run the post-access exploratory Byrnes/HydDown hydrogen release screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import yaml

from h2station.preslhy_nonadiabatic import (
    DischaVesselParameters,
    simulate_nonadiabatic_blowdown,
)
from h2station.preslhy_validation import PreslhyTrace


ARCHIVE_NAME = "blowdown_reproducibility_archive.zip"
CASE_FILES = ("Byrnes_run7.yml", "Byrnes_run8.yml", "Byrnes_run9.yml")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _crossing(time_s: np.ndarray, values_pa: np.ndarray, target_pa: float) -> float:
    for index in range(1, len(time_s)):
        if values_pa[index] <= target_pa < values_pa[index - 1]:
            fraction = (target_pa - values_pa[index - 1]) / (
                values_pa[index] - values_pa[index - 1]
            )
            return float(time_s[index - 1] + fraction * (time_s[index] - time_s[index - 1]))
    return float("nan")


def _run_case(path: Path) -> dict[str, object]:
    source = yaml.safe_load(path.read_text(encoding="utf-8"))
    vessel = source["vessel"]
    initial = source["initial"]
    pressure_validation = source["validation"]["pressure"]
    time_s = np.asarray(pressure_validation["time"], dtype=float)
    measured_pa = np.asarray(pressure_validation["pres"], dtype=float) * 1.0e5
    back_pressure_pa = float(source["valve"]["back_pressure"])
    trace = PreslhyTrace(
        case_id=path.stem,
        source_package="zenodo-20728325",
        source_member=path.name,
        nozzle_diameter_mm=float(source["valve"]["diameter"]) * 1.0e3,
        time_s=time_s,
        pressure_bar_abs=measured_pa / 1.0e5,
        initial_temperature_k=float(initial["temperature"]),
        ambient_pressure_pa=back_pressure_pa,
        pressure_unit_interpretation="source_yaml_reported_bar_absolute",
        temperature_substituted=False,
        ambient_pressure_substituted=False,
    )
    volume_m3 = math.pi * float(vessel["diameter"]) ** 2 * float(vessel["length"]) / 4.0
    shell_volume_m3 = (
        math.pi * float(vessel["diameter"]) * float(vessel["length"])
        + math.pi * float(vessel["diameter"]) ** 2 / 2.0
    ) * float(vessel["thickness"])
    wall_mass_kg = shell_volume_m3 * float(vessel["density"])
    parameters = DischaVesselParameters(
        internal_volume_m3=volume_m3,
        internal_diameter_m=float(vessel["diameter"]),
        internal_height_m=float(vessel["length"]),
        wall_mass_kg=wall_mass_kg,
        wall_specific_heat_j_kg_k=float(vessel["heat_capacity"]),
        external_heat_transfer_w_m2_k=float(source["heat_transfer"]["h_outer"]),
        ambient_temperature_k=float(initial["temperature"]),
        discharge_coefficient=float(source["valve"]["discharge_coef"]),
    )
    predicted = simulate_nonadiabatic_blowdown(trace, time_s, parameters=parameters)
    error_pa = predicted.pressure_pa - measured_pa
    pressure_rmse_bar = float(np.sqrt(np.mean(error_pa**2)) / 1.0e5)
    nrmse_percent = float(
        pressure_rmse_bar * 1.0e5 / trace.initial_pressure_pa * 100.0
    )
    half_target_pa = back_pressure_pa + 0.5 * (
        trace.initial_pressure_pa - back_pressure_pa
    )
    measured_half_s = _crossing(time_s, measured_pa, half_target_pa)
    predicted_half_s = _crossing(time_s, predicted.pressure_pa, half_target_pa)
    half_error_percent = float(
        abs(predicted_half_s - measured_half_s) / measured_half_s * 100.0
    ) if np.isfinite(measured_half_s) and np.isfinite(predicted_half_s) else float("inf")
    pressure_pass = nrmse_percent <= 10.0
    half_pass = half_error_percent <= 20.0
    return {
        "case_id": path.stem,
        "source_file": path.as_posix(),
        "volume_m3": volume_m3,
        "wall_mass_kg": wall_mass_kg,
        "pressure_rmse_bar": pressure_rmse_bar,
        "pressure_nrmse_percent_initial_pressure": nrmse_percent,
        "measured_half_pressure_s": float(measured_half_s),
        "predicted_half_pressure_s": float(predicted_half_s),
        "half_pressure_relative_error_percent": half_error_percent,
        "pressure_screen_pass": pressure_pass,
        "half_pressure_screen_pass": half_pass,
        "joint_screen_pass": pressure_pass and half_pass,
        "predicted_final_pressure_bar_abs": float(predicted.pressure_pa[-1] / 1.0e5),
        "measured_final_pressure_bar_abs": float(measured_pa[-1] / 1.0e5),
        "predicted_peak_mass_flow_kg_s": float(np.max(predicted.mass_flow_kg_s)),
    }


def run(source_dir: Path, archive_path: Path) -> dict[str, object]:
    cases = [_run_case(source_dir / case) for case in CASE_FILES]
    return {
        "schema_version": 1,
        "status": "completed_post_access_exploratory_screen",
        "evidence_role": "post_access_exploratory_screening",
        "protocol": "research/byrnes_zenodo_exploratory_protocol.json",
        "source": {
            "doi": "10.5281/zenodo.20728325",
            "landing_url": "https://zenodo.org/records/20728325",
            "archive": ARCHIVE_NAME,
            "archive_sha256": _sha256(archive_path),
            "license": "CC-BY-4.0",
        },
        "aggregate": {
            "case_count": len(cases),
            "joint_screen_pass_count": sum(bool(case["joint_screen_pass"]) for case in cases),
            "joint_screen_pass_fraction": sum(bool(case["joint_screen_pass"]) for case in cases) / len(cases),
            "claim_supported": False,
        },
        "claim_boundary": "Post-access exploratory screen only; not a prospective validation gate, not a station full-loop result, and not an emergency-consequence validation.",
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.source_dir, args.archive)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
