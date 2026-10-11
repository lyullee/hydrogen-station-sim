#!/usr/bin/env python3
"""Run a claim-bounded replay on the USN pressure-peaking MAT release.

The public Dataverse release 10.23642/USN.17932439 contains actual-hydrogen
time series for ten confined pressure-peaking experiments.  This runner uses
the same fixed perfect-mix enclosure balance as the older Zenodo screen.  The
release was inspected before this runner was written, so the output is a
post-access recheck and must not be promoted to a new confirmatory holdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
from scipy.io import loadmat


R = 8.314462618
M_H2 = 0.00201588
M_AIR = 0.028965
P0_PA = 101_325.0
V_M3 = 14.9
C_D = 0.7
VENT_AREA_M2 = {
    2: 0.0012, 3: 0.0020, 4: 0.0020, 5: 0.0014, 6: 0.0014,
    7: 0.0006, 8: 0.0006, 9: 0.0006, 10: 0.0006, 11: 0.0006,
}
T0_K = {
    2: 293.0, 3: 293.0, 4: 293.0, 5: 293.0, 6: 296.0,
    7: 292.34, 8: 291.94, 9: 293.12, 10: 289.71, 11: 293.57,
}
DOI = "10.23642/USN.17932439"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite_series(value: object, name: str) -> np.ndarray:
    result = np.asarray(value, dtype=float)
    if result.ndim != 2 or result.shape[1] < 2:
        raise ValueError(f"{name} must be an N x 2 numeric array")
    result = result[:, :2]
    finite = np.isfinite(result).all(axis=1)
    result = result[finite]
    if result.shape[0] < 30:
        raise ValueError(f"{name} has fewer than 30 finite rows")
    order = np.argsort(result[:, 0], kind="stable")
    result = result[order]
    unique = np.concatenate(([True], np.diff(result[:, 0]) > 0.0))
    result = result[unique]
    if result.shape[0] < 30:
        raise ValueError(f"{name} has fewer than 30 unique time rows")
    return result


def read_case(path: Path) -> tuple[int, np.ndarray, np.ndarray]:
    match = re.search(r"_(\d{5})_READ", path.stem)
    if match is None:
        raise ValueError(f"case number is missing from {path.name}")
    case = int(match.group(1))
    payload = loadmat(path, squeeze_me=True, struct_as_record=False)
    if "GEN3i" not in payload or "SIGMA" not in payload:
        raise ValueError("GEN3i and SIGMA channels are required")
    pressure = _finite_series(payload["GEN3i"], "GEN3i")
    sigma = np.asarray(payload["SIGMA"], dtype=float)
    if sigma.ndim != 2 or sigma.shape[1] < 2:
        raise ValueError("SIGMA must contain time and mass-flow columns")
    sigma = sigma[:, :2]
    finite = np.isfinite(sigma).all(axis=1)
    sigma = sigma[finite]
    order = np.argsort(sigma[:, 0], kind="stable")
    sigma = sigma[order]
    unique = np.concatenate(([True], np.diff(sigma[:, 0]) > 0.0))
    sigma = sigma[unique]
    if sigma.shape[0] < 30:
        raise ValueError("SIGMA has fewer than 30 finite unique rows")
    return case, pressure, sigma


def simulate_pmix(
    mass_flow_g_s: np.ndarray,
    *,
    vent_area_m2: float,
    temperature_k: float,
    time_step_s: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the fixed ideal-gas enclosure balance without fitting."""

    n_en = P0_PA * V_M3 / (R * temperature_k)
    n_h2 = 0.0
    overpressure = np.empty(mass_flow_g_s.size, dtype=float)
    time = np.arange(mass_flow_g_s.size, dtype=float) * time_step_s
    for index, flow_g_s in enumerate(mass_flow_g_s):
        n_in = max(float(flow_g_s), 0.0) / 1000.0 / M_H2
        x_h2 = min(max(n_h2 / max(n_en, 1.0e-18), 0.0), 0.999999)
        mixture_mass = x_h2 * M_H2 + (1.0 - x_h2) * M_AIR
        pressure_pa = n_en * R * temperature_k / V_M3
        delta_p = max(pressure_pa - P0_PA, 0.0)
        n_out = C_D * vent_area_m2 * math.sqrt(
            max(2.0 * delta_p * n_en / (V_M3 * mixture_mass), 0.0)
        )
        n_en = max(n_en + (n_in - n_out) * time_step_s, 1.0e-18)
        n_h2 = max(n_h2 + (n_in - x_h2 * n_out) * time_step_s, 0.0)
        overpressure[index] = max(
            n_en * R * temperature_k / V_M3 - P0_PA, 0.0
        ) / 1000.0
    return time, overpressure


def run(raw_directory: Path) -> dict[str, object]:
    files = sorted(raw_directory.glob("HTE242USN_*_READ190621.mat"))
    if not files:
        raise FileNotFoundError(f"no USN MAT files found under {raw_directory}")
    cases: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    manifest: list[dict[str, object]] = []
    for path in files:
        manifest.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
        try:
            case, pressure, sigma = read_case(path)
            if case not in VENT_AREA_M2:
                raise ValueError(f"case {case} has no frozen vent-area mapping")
            dt = float(np.median(np.diff(sigma[:, 0])))
            if not math.isfinite(dt) or dt <= 0.0:
                raise ValueError("SIGMA time base is invalid")
            model_time, predicted = simulate_pmix(
                sigma[:, 1],
                vent_area_m2=VENT_AREA_M2[case],
                temperature_k=T0_K[case],
                time_step_s=dt,
            )
            measured_peak_index = int(np.argmax(pressure[:, 1]))
            predicted_peak_index = int(np.argmax(predicted))
            measured_peak = float(pressure[measured_peak_index, 1])
            predicted_peak = float(predicted[predicted_peak_index])
            measured_peak_time = float(pressure[measured_peak_index, 0])
            predicted_peak_time = float(model_time[predicted_peak_index])
            pressure_error = abs(predicted_peak - measured_peak)
            time_error_pct = (
                abs(predicted_peak_time - measured_peak_time)
                / max(abs(measured_peak_time), 1.0e-12)
                * 100.0
            )
            pressure_pass = pressure_error <= 5.0
            time_pass = time_error_pct <= 20.0
            cases.append({
                "case": case,
                "source_file": path.name,
                "measured_peak_overpressure_kpa": measured_peak,
                "measured_peak_time_s": measured_peak_time,
                "predicted_peak_overpressure_kpa": predicted_peak,
                "predicted_peak_time_s": predicted_peak_time,
                "peak_overpressure_abs_error_kpa": pressure_error,
                "peak_time_relative_error_percent": time_error_pct,
                "primary_pressure_pass": pressure_pass,
                "primary_time_pass": time_pass,
                "joint_primary_pass": pressure_pass and time_pass,
                "mass_flow_samples": int(sigma.shape[0]),
                "mass_flow_peak_g_s": float(np.nanmax(sigma[:, 1])),
                "pressure_samples": int(pressure.shape[0]),
                "time_step_s": dt,
            })
        except (OSError, ValueError, KeyError, IndexError) as exc:
            excluded.append({"source_file": path.name, "reason": f"{type(exc).__name__}: {exc}"})

    cases.sort(key=lambda row: int(row["case"]))
    joint_count = sum(bool(row["joint_primary_pass"]) for row in cases)
    eligible_count = len(cases)
    return {
        "schema_version": 1,
        "status": "completed_post_access_pressure_peaking_recheck",
        "evidence_role": "post_access_public_actual_hydrogen_pressure_peaking_diagnostic",
        "source": {
            "doi": DOI,
            "license": "CC BY 4.0",
            "dataset_version": "1.1",
            "raw_files_committed": False,
            "raw_directory": raw_directory.as_posix(),
            "file_manifest": manifest,
        },
        "claim_boundary": (
            "This replay is limited to the unignited pressure-peaking response of a 14.9 m3 confined, vented enclosure. "
            "The public raw MAT files were accessed before this runner was created, so the result is not an independent confirmatory holdout. "
            "It does not validate the HRS fueling loop, outdoor dispersion, station control, vehicle fueling or emergency response."
        ),
        "model": {
            "enclosure_volume_m3": V_M3,
            "temperature_assumption": "fixed case temperatures carried from the earlier frozen pressure-peaking protocol; no raw temperature channel used",
            "discharge_coefficient": C_D,
            "vent_area_mapping_source": "research/zenodo_4106101_pressure_peaking_protocol.json",
            "mass_flow_input": "SIGMA[:,1] from each public MAT file",
            "pressure_observation": "GEN3i[:,1] peak, no filtering or case selection",
            "time_step_source": "median difference of each SIGMA time column",
            "parameter_fitting": False,
        },
        "aggregate": {
            "eligible_case_count": eligible_count,
            "excluded_case_count": len(excluded),
            "excluded_cases": excluded,
            "joint_primary_pass_count": joint_count,
            "joint_primary_pass_fraction": joint_count / eligible_count if eligible_count else 0.0,
            "screening_limits": {
                "peak_overpressure_abs_error_kpa_max": 5.0,
                "peak_time_relative_error_percent_max": 20.0,
            },
            "interpretation": "diagnostic_only",
        },
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-directory", type=Path, default=Path("data/public_validation/raw/usn_pressure_peaking"))
    parser.add_argument("--output", type=Path, default=Path("research/usn_17932439_pressure_peaking_recheck_2026_10_11.json"))
    args = parser.parse_args()
    result = run(args.raw_directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["aggregate"], ensure_ascii=False))


if __name__ == "__main__":
    main()
