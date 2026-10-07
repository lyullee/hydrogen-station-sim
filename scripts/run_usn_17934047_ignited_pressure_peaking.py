#!/usr/bin/env python3
"""Execute the frozen USN ignited pressure-peaking holdout.

Raw MAT files stay outside git.  The runner verifies every source identity,
applies the predeclared signal processing, and records both positive and
negative outcomes without fitting the model to a case.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat

from h2station.ignited_pressure_peaking import (
    simulate_ignited_pressure_peaking,
    vent_area_m2,
)


PROTOCOL = "research/usn_17934047_ignited_pressure_peaking_protocol_2026_10_08.json"
FILES: dict[int, tuple[int, int, str]] = {
    1: (266047, 42685282, "6f7b90c22d1ba4f34056e8dd14df4e98"),
    2: (266048, 42200980, "6b43f914eb31ec30c05b274da3a50089"),
    3: (266049, 41212810, "8911624132d23ffe14d8a6b99027479a"),
    4: (266050, 43094870, "43c2355ee9faea7581be25ce5ae20c46"),
    5: (266051, 41741953, "3881bdedfdecf69133f6e2fff339b6c9"),
    6: (266052, 41626433, "14638534b64675f2825c96211a99940e"),
    7: (266053, 41478900, "8a29f3dd0d5d1817589542c073a67fae"),
    8: (266054, 41937170, "a7eb1315d51de07f394eac874e13ecd3"),
    9: (266055, 41375928, "f5770155db92899b798db34615b2b6db"),
    10: (266056, 41775223, "28e83db74b9ebe2d4bccd105116d6059"),
    11: (266057, 41315811, "b51b98d892a86751fd30beb521b024d8"),
    12: (266058, 40877440, "816d754c3edb2ce82a39f1696ece14f7"),
    13: (266059, 41387557, "0df1add8f73ce0e8ebf9c4b3ddd7d6f7"),
    14: (266060, 42131019, "78a8d3589aa0c059bfde4353f3820538"),
    15: (266061, 40666968, "63880bdd5e17eab73918bb6889c038d6"),
    16: (266062, 40697671, "f718762c4243448f4e843cb43511c2ee"),
    17: (266063, 41678827, "08940689d1f84b6ef7f50108f2983513"),
    18: (266064, 41444716, "26f6508c05fa7df056153ba84491d933"),
    19: (266065, 42107531, "9e3a0d82694ce3f823e8849ba52dfafd"),
    20: (266066, 42273153, "0d9fc8875c9aae5c84f7134f1e02e305"),
    21: (266067, 41521647, "d788b0db68869b37121e142edd190a5b"),
    22: (266068, 41697746, "077f132a3f8459993c77a7d531fd2d69"),
    23: (266069, 42872038, "31bf7cf488d93ace66fff34c93b5b861"),
    24: (266070, 42991569, "c04fa994a1f322e01200130e5f71d1c1"),
    25: (266071, 42850620, "f97440140aa9569bc3107f2757a138ea"),
    26: (266072, 42086604, "1cced8c12babe466349c8f4320a08b14"),
    27: (266073, 42621247, "3e3f0f256263aa92ae01a9bdcceb86dd"),
    28: (266074, 42152718, "55994389aa6d6a60a6a736c8c79bee0e"),
    29: (266075, 42508034, "d93dab6ece1ea477825d35de4ff56344"),
    30: (266076, 43239997, "6012e3a7e92c43dced63312288f46425"),
    31: (266077, 43807775, "62d0637fe5ed0710589bb5b0482f82bd"),
}

# Experimental vent configurations reported in Table 3 of the associated
# publication.  Cases 29-31 are retained only for development diagnostics.
CASE_VENTS = {
    **{case: 1 for case in (1, 2, 3, 4, 19, 20, 30, 31)},
    **{case: 2 for case in (5, 6, 7, 8, 17, 18, 21, 22, 23, 28, 29)},
    **{case: 3 for case in (9, 10, 11, 12, 13, 14, 15, 16, 24, 25, 26, 27)},
}


def raw_name(case: int) -> str:
    return f"HTE341USN{case:04d}READ191111.mat"


def file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def block_mean(values: np.ndarray, block_size: int = 20) -> np.ndarray:
    usable = values.size - values.size % block_size
    if usable <= 0:
        raise ValueError("not enough mass-flow samples for frozen block mean")
    return values[:usable].reshape(-1, block_size).mean(axis=1)


def evaluate_case(path: Path, case: int) -> dict[str, Any]:
    datafile_id, expected_bytes, expected_md5 = FILES[case]
    observed_bytes = path.stat().st_size
    observed_md5 = file_md5(path)
    if observed_bytes != expected_bytes or observed_md5 != expected_md5:
        raise ValueError(
            f"source identity mismatch: bytes={observed_bytes}, md5={observed_md5}"
        )

    data = loadmat(path, squeeze_me=True, struct_as_record=False)
    sigma = np.asarray(data["SIGMA"], dtype=float)
    gen3i = np.asarray(data["GEN3i"], dtype=float)
    if sigma.ndim != 2 or sigma.shape[1] != 7 or gen3i.ndim != 2 or gen3i.shape[1] != 3:
        raise ValueError(f"unexpected channel shape: SIGMA={sigma.shape}, GEN3i={gen3i.shape}")
    if not np.isfinite(sigma).all() or not np.isfinite(gen3i).all():
        raise ValueError("non-finite raw channel values")
    if not np.all(np.diff(sigma[:, 0]) > 0.0) or not np.all(np.diff(gen3i[:, 0]) > 0.0):
        raise ValueError("non-monotonic raw time base")

    baseline_sigma = (sigma[:, 0] >= 0.2) & (sigma[:, 0] <= 1.2)
    baseline_gen3i = (gen3i[:, 0] >= 0.2) & (gen3i[:, 0] <= 1.2)
    initial_temperature_k = float(
        np.mean(np.median(sigma[baseline_sigma, 3:7], axis=0)) + 273.15
    )
    pressure_baseline_kpa = float(np.median(gen3i[baseline_gen3i, 2]))

    flow_time_s = block_mean(sigma[:, 0])
    flow_g_s = np.maximum(block_mean(sigma[:, 1]), 0.0)
    if flow_time_s[0] > 0.0:
        flow_time_s = np.concatenate(([0.0], flow_time_s))
        flow_g_s = np.concatenate(([0.0], flow_g_s))
    output_time_s = np.arange(0.0, 12.0001, 0.01)
    simulation = simulate_ignited_pressure_peaking(
        flow_time_s,
        flow_g_s,
        initial_temperature_k=initial_temperature_k,
        vent_area_m2_value=vent_area_m2(CASE_VENTS[case]),
        output_time_s=output_time_s,
    )

    measured_pressure_kpa = gen3i[:, 2] - pressure_baseline_kpa
    measured_peak_mask = (gen3i[:, 0] >= 1.0) & (gen3i[:, 0] <= 12.0)
    measured_peak_index_local = int(np.argmax(measured_pressure_kpa[measured_peak_mask]))
    measured_indices = np.flatnonzero(measured_peak_mask)
    measured_peak_index = int(measured_indices[measured_peak_index_local])
    measured_peak_kpa = float(measured_pressure_kpa[measured_peak_index])
    measured_peak_time_s = float(gen3i[measured_peak_index, 0])

    predicted_peak_mask = (simulation.time_s >= 1.0) & (simulation.time_s <= 12.0)
    predicted_indices = np.flatnonzero(predicted_peak_mask)
    predicted_peak_index_local = int(
        np.argmax(simulation.gauge_overpressure_kpa[predicted_peak_mask])
    )
    predicted_peak_index = int(predicted_indices[predicted_peak_index_local])
    predicted_peak_kpa = float(simulation.gauge_overpressure_kpa[predicted_peak_index])
    predicted_peak_time_s = float(simulation.time_s[predicted_peak_index])

    trace_time_s = np.arange(1.0, 12.0001, 0.01)
    measured_trace = np.interp(trace_time_s, gen3i[:, 0], measured_pressure_kpa)
    predicted_trace = np.interp(
        trace_time_s, simulation.time_s, simulation.gauge_overpressure_kpa
    )
    trace_span_kpa = float(np.ptp(measured_trace))
    trace_nrmse_percent = float(
        np.sqrt(np.mean(np.square(predicted_trace - measured_trace)))
        / max(trace_span_kpa, 1.0e-12)
        * 100.0
    )
    peak_error_kpa = abs(predicted_peak_kpa - measured_peak_kpa)
    peak_time_error_percent = (
        abs(predicted_peak_time_s - measured_peak_time_s)
        / max(measured_peak_time_s, 1.0e-12)
        * 100.0
    )
    return {
        "case": case,
        "datafile_id": datafile_id,
        "file": path.name,
        "bytes": observed_bytes,
        "md5": observed_md5,
        "open_vent_count": CASE_VENTS[case],
        "vent_area_m2": vent_area_m2(CASE_VENTS[case]),
        "initial_temperature_k": initial_temperature_k,
        "measured_peak_overpressure_kpa": measured_peak_kpa,
        "measured_peak_time_s": measured_peak_time_s,
        "predicted_peak_overpressure_kpa": predicted_peak_kpa,
        "predicted_peak_time_s": predicted_peak_time_s,
        "peak_overpressure_abs_error_kpa": peak_error_kpa,
        "peak_time_relative_error_percent": peak_time_error_percent,
        "pressure_trace_nrmse_percent": trace_nrmse_percent,
        "primary_pressure_pass": peak_error_kpa <= 2.0,
        "secondary_peak_time_pass": peak_time_error_percent <= 25.0,
        "secondary_trace_nrmse_pass": trace_nrmse_percent <= 25.0,
        "mass_flow_peak_g_s": float(np.max(flow_g_s)),
        "simulated_max_temperature_k": float(np.max(simulation.enclosure_temperature_k)),
    }


def run(raw_directory: Path, cases: list[int]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for case in cases:
        path = raw_directory / raw_name(case)
        try:
            results.append(evaluate_case(path, case))
        except (KeyError, OSError, ValueError, RuntimeError) as exc:
            excluded.append({"case": case, "file": path.name, "reason": str(exc)})

    pass_count = sum(item["primary_pressure_pass"] for item in results)
    pass_fraction = pass_count / len(results) if results else 0.0
    confirmatory = len(results) >= 20 and pass_fraction >= 0.8 and not excluded
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_prospective_protocol_execution",
        "evidence_role": "prospective_external_ignited_pressure_peaking_validation",
        "protocol": PROTOCOL,
        "source": {
            "dataset_doi": "10.23642/USN.17934047",
            "publication_doi": "10.1016/j.ijhydene.2020.12.015",
            "license": "CC BY 4.0",
            "raw_files_committed": False,
        },
        "aggregate": {
            "requested_case_count": len(cases),
            "eligible_case_count": len(results),
            "excluded_case_count": len(excluded),
            "excluded_cases": excluded,
            "primary_pass_count": pass_count,
            "primary_pass_fraction": pass_fraction,
            "peak_overpressure_mae_kpa": (
                float(np.mean([item["peak_overpressure_abs_error_kpa"] for item in results]))
                if results
                else None
            ),
            "median_trace_nrmse_percent": (
                float(np.median([item["pressure_trace_nrmse_percent"] for item in results]))
                if results
                else None
            ),
            "confirmatory_rule": ">=20 eligible cases, no identity/channel exclusions, and >=80% with peak absolute error <=2.0 kPa",
            "confirmatory_rule_met": confirmatory,
            "interpretation": (
                "confirmatory_component_validation_pass"
                if confirmatory
                else "negative_or_incomplete_component_validation"
            ),
        },
        "cases": results,
        "claim_boundary": "This result concerns only ignited pressure peaking in a vented enclosure. It does not validate an outdoor H70 station fueling loop, jet-flame radiation distance, emergency controls, operator response, or SAGA effectiveness.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-directory", type=Path, default=Path("tmp/usn_17934047"))
    parser.add_argument(
        "--cases",
        default="1-28",
        help="Inclusive range such as 1-28, or comma-separated cases.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/usn_17934047_ignited_pressure_peaking_result_2026_10_08.json"),
    )
    args = parser.parse_args()
    if "-" in args.cases and "," not in args.cases:
        first, last = (int(value) for value in args.cases.split("-", 1))
        cases = list(range(first, last + 1))
    else:
        cases = [int(value) for value in args.cases.split(",")]
    result = run(args.raw_directory, cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["aggregate"], indent=2))


if __name__ == "__main__":
    main()
