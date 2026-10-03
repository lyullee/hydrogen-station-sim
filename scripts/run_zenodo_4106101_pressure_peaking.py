#!/usr/bin/env python3
"""Reproduce the frozen Zenodo 4106101 pressure-peaking screen.

The runner deliberately uses a fixed, source-documented enclosure model and
the measured mass-flow input.  It does not tune parameters per experiment or
select cases after inspecting agreement.  Raw archives are kept outside git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from zipfile import ZipFile

import numpy as np


R = 8.314462618
M_H2 = 0.00201588
M_AIR = 0.028965
P0_PA = 101_325.0
V_M3 = 14.9
C_D = 0.7
DT_S = 0.0002
VENT_AREA_M2 = {
    2: 0.0012,
    3: 0.0020,
    4: 0.0020,
    5: 0.0014,
    6: 0.0014,
    7: 0.0006,
    8: 0.0006,
    9: 0.0006,
    10: 0.0006,
    11: 0.0006,
}
T0_K = {
    2: 293.0,
    3: 293.0,
    4: 293.0,
    5: 293.0,
    6: 296.0,
    7: 292.34,
    8: 291.94,
    9: 293.12,
    10: 289.71,
    11: 293.57,
}
EXPECTED_ARCHIVE_MD5 = {
    "HTE242USN00011MFR.zip": "e210005525700347a43d9cf352e9a39b",
    "HTE242USN00011PRESS.zip": "85f590964f3dcefba1f4b2a59916a1a3",
}


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_mfr_g_s(archive: Path, case: int) -> np.ndarray:
    member = f"HTE242USN{case:05d}MFR190621/CH2_02h.TXT"
    with ZipFile(archive) as zf:
        with zf.open(member) as handle:
            rows: list[float] = []
            in_data = False
            for raw in handle:
                line = raw.decode("utf-8", errors="replace").strip()
                if not in_data:
                    if line == "DATA START":
                        in_data = True
                    continue
                if not line:
                    continue
                try:
                    volts = float(line.split("\t")[0])
                except (ValueError, IndexError):
                    continue
                rows.append((volts - 1.0) * 6.25)
    if not rows:
        raise ValueError(f"no mass-flow rows in {member}")
    return np.asarray(rows, dtype=float)


def read_pressure_peak(path: Path) -> tuple[float, float]:
    peak = -math.inf
    peak_time = math.nan
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for index, raw in enumerate(handle):
            if index < 8:
                continue
            fields = raw.strip().split("\t")
            if len(fields) < 2:
                continue
            try:
                time_s = float(fields[0])
                pressure_kpa = float(fields[1])
            except ValueError:
                continue
            if pressure_kpa > peak:
                peak = pressure_kpa
                peak_time = time_s
    if not math.isfinite(peak) or not math.isfinite(peak_time):
        raise ValueError(f"no pressure rows in {path}")
    return peak, peak_time


def simulate_pmix(mfr_g_s: np.ndarray, vent_area_m2: float, temperature_k: float) -> tuple[float, float]:
    """Integrate the fixed ideal-gas enclosure balance with measured MFR input."""
    n_en = P0_PA * V_M3 / (R * temperature_k)
    n_h2 = 0.0
    peak_kpa = 0.0
    peak_time = 0.0
    for index, flow_g_s in enumerate(mfr_g_s):
        n_in = max(float(flow_g_s), 0.0) / 1000.0 / M_H2
        x_h2 = min(max(n_h2 / max(n_en, 1e-18), 0.0), 0.999999)
        m_mix = x_h2 * M_H2 + (1.0 - x_h2) * M_AIR
        pressure_pa = n_en * R * temperature_k / V_M3
        delta_p = max(pressure_pa - P0_PA, 0.0)
        n_out = C_D * vent_area_m2 * math.sqrt(
            max(2.0 * delta_p * n_en / (V_M3 * m_mix), 0.0)
        )
        n_en = max(n_en + (n_in - n_out) * DT_S, 1e-18)
        n_h2 = max(n_h2 + (n_in - x_h2 * n_out) * DT_S, 0.0)
        pressure_kpa = max(n_en * R * temperature_k / V_M3 - P0_PA, 0.0) / 1000.0
        if pressure_kpa > peak_kpa:
            peak_kpa = pressure_kpa
            peak_time = (index + 1) * DT_S
    return peak_kpa, peak_time


def run(pressure_dir: Path, mfr_archive: Path) -> dict:
    archive_md5 = {path.name: md5(path) for path in (mfr_archive, pressure_dir.parent / "HTE242USN00011PRESS.zip")}
    for name, expected in EXPECTED_ARCHIVE_MD5.items():
        actual = archive_md5.get(name)
        if actual != expected:
            raise ValueError(f"archive hash mismatch for {name}: {actual} != {expected}")

    cases: list[dict] = []
    excluded: list[dict] = []
    for case in range(2, 12):
        pressure_path = pressure_dir / f"HTE242USN{case:05d}PRESS190621.txt"
        try:
            measured_peak, measured_peak_time = read_pressure_peak(pressure_path)
            mfr = read_mfr_g_s(mfr_archive, case)
            predicted_peak, predicted_peak_time = simulate_pmix(mfr, VENT_AREA_M2[case], T0_K[case])
        except (OSError, KeyError, ValueError) as exc:
            excluded.append({"case": case, "reason": str(exc)})
            continue
        pressure_error = abs(predicted_peak - measured_peak)
        time_error_pct = abs(predicted_peak_time - measured_peak_time) / max(measured_peak_time, 1e-12) * 100.0
        pressure_pass = pressure_error <= 5.0
        time_pass = time_error_pct <= 20.0
        cases.append(
            {
                "case": case,
                "pressure_file": pressure_path.name,
                "measured_peak_overpressure_kpa": measured_peak,
                "measured_peak_time_s": measured_peak_time,
                "predicted_peak_overpressure_kpa": predicted_peak,
                "predicted_peak_time_s": predicted_peak_time,
                "peak_overpressure_abs_error_kpa": pressure_error,
                "peak_time_relative_error_percent": time_error_pct,
                "primary_pressure_pass": pressure_pass,
                "primary_time_pass": time_pass,
                "joint_primary_pass": pressure_pass and time_pass,
                "mass_flow_samples": int(mfr.size),
                "mass_flow_peak_g_s": float(np.max(mfr)),
            }
        )

    joint_count = sum(1 for case in cases if case["joint_primary_pass"])
    eligible_count = len(cases)
    joint_fraction = joint_count / eligible_count if eligible_count else 0.0
    return {
        "schema_version": 1,
        "status": "completed_prospective_protocol_execution",
        "generated_at": "2026-10-04T00:00:00+09:00",
        "evidence_role": "prospective_external_consequence_validation_result",
        "claim_boundary": "This result validates only the unignited hydrogen pressure-peaking consequence submodel for a confined, vented enclosure. It is not validation of the full HRS fueling loop, cascade/compressor control, dispenser operation, outdoor dispersion, ignition, emergency response, or SAGA effectiveness.",
        "protocol": "research/zenodo_4106101_pressure_peaking_protocol.json",
        "source": {
            "doi": "10.5281/zenodo.4106101",
            "related_publication_doi": "10.1016/j.ijhydene.2020.08.221",
            "archive_md5": archive_md5,
            "raw_files_committed": False,
        },
        "model": {
            "enclosure_volume_m3": V_M3,
            "temperature_assumption": "case metadata T0 held constant",
            "discharge_coefficient": C_D,
            "coefficient_basis": "fixed value reported by the associated source publication; no per-case fitting",
            "mass_flow_input": "measured CH2 mass-flow channel from source MFR archive",
            "pressure_observation": "raw P1 peak; no per-case signal filtering or outcome selection",
            "time_step_s": DT_S,
        },
        "aggregate": {
            "eligible_case_count": eligible_count,
            "excluded_case_count": len(excluded),
            "excluded_cases": excluded,
            "joint_primary_pass_count": joint_count,
            "joint_primary_pass_fraction": joint_fraction,
            "confirmatory_rule": ">=6 eligible cases and >=80% joint primary pass",
            "confirmatory_rule_met": eligible_count >= 6 and joint_fraction >= 0.8 and not excluded,
            "interpretation": "exploratory_submodel_screen_only" if joint_fraction < 0.8 else "confirmatory_submodel_screen",
        },
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pressure-dir", type=Path, required=True)
    parser.add_argument("--mfr-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.pressure_dir, args.mfr_archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["aggregate"], ensure_ascii=False))


if __name__ == "__main__":
    main()
