"""Write a post-outcome effective-discharge-coefficient diagnostic.

This report is deliberately separate from the frozen HyTunnel-CS holdout.  It
uses the same synchronized samples and eligibility rule as the holdout, but
reports the coefficient implied by the measured mass flow.  It must never be
used to change the frozen ``Cd=0.8`` result or a runtime default.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from h2station.hytunnel_carpark_validation import (  # noqa: E402
    AMBIENT_PRESSURE_PA,
    BLOWDOWN_CASES,
    BLOWDOWN_DISCHARGE_COEFFICIENT,
    BLOWDOWN_NOZZLE_DIAMETER_M,
    _CoolPropHydrogen,
    _series_on_time,
    load_hytunnel_mat,
)


def _case(path: Path, experiment: int) -> dict[str, object]:
    trace = load_hytunnel_mat(path)
    time = np.asarray(trace.mass_flow_time_s, dtype=float)
    measured = np.asarray(trace.mass_flow_g_s, dtype=float)
    pressure = _series_on_time(
        trace.tank_pressure_bar, trace.tank_time_s, time, "Tank.p"
    )
    temperature = _series_on_time(
        trace.tank_temperature_c, trace.tank_time_s, time, "Tank.T"
    )
    valid = (
        np.isfinite(time)
        & np.isfinite(measured)
        & np.isfinite(pressure)
        & np.isfinite(temperature)
        & (time >= trace.release_start_s)
    )
    time = time[valid]
    measured = measured[valid]
    pressure = pressure[valid]
    temperature = temperature[valid]

    # Keep the holdout's one-second aggregation and measured-response
    # eligibility exactly.  This is not an alternate evaluator.
    bins = np.floor(time - trace.release_start_s).astype(np.int64)
    _, inverse = np.unique(bins, return_inverse=True)
    counts = np.bincount(inverse).astype(float)
    measured = np.bincount(inverse, weights=measured) / counts
    pressure = np.bincount(inverse, weights=pressure) / counts
    temperature = np.bincount(inverse, weights=temperature) / counts
    peak = float(np.nanmax(measured))
    eligible = (measured >= 0.1 * peak) & (
        pressure * 1.0e5 > AMBIENT_PRESSURE_PA * 1.01
    )
    measured = measured[eligible]
    pressure = pressure[eligible]
    temperature = temperature[eligible] + 273.15

    eos = _CoolPropHydrogen()
    area = np.pi * BLOWDOWN_NOZZLE_DIAMETER_M**2 / 4.0
    ideal = np.asarray(
        [
            area
            * eos.isentropic_mass_flux(
                p_bar * 1.0e5, temp_k, AMBIENT_PRESSURE_PA
            )
            * 1000.0
            for p_bar, temp_k in zip(pressure, temperature, strict=True)
        ]
    )
    effective = np.divide(
        measured,
        ideal,
        out=np.full_like(measured, np.nan),
        where=ideal > 0,
    )
    effective = effective[np.isfinite(effective)]
    measured_peak = float(np.max(measured))
    ideal_peak = float(np.max(ideal))
    return {
        "experiment": experiment,
        "eligible_points": int(measured.size),
        "measured_peak_g_s": measured_peak,
        "frozen_cd": BLOWDOWN_DISCHARGE_COEFFICIENT,
        "frozen_cd_peak_prediction_g_s": float(
            ideal_peak * BLOWDOWN_DISCHARGE_COEFFICIENT
        ),
        "effective_cd_peak_ratio": float(
            measured_peak / ideal_peak
        ),
        "effective_cd_median": float(np.median(effective)),
        "effective_cd_q10": float(np.quantile(effective, 0.10)),
        "effective_cd_q90": float(np.quantile(effective, 0.90)),
        "effective_cd_min": float(np.min(effective)),
        "effective_cd_max": float(np.max(effective)),
    }


def build_report(raw_dir: Path) -> dict[str, object]:
    cases = [_case(raw_dir / f"Exp{experiment:02d}.mat", experiment) for experiment in BLOWDOWN_CASES]
    peak_ratios = [item["effective_cd_peak_ratio"] for item in cases]
    medians = [item["effective_cd_median"] for item in cases]
    return {
        "schema_version": 1,
        "artifact_type": "hytunnel_carpark_post_outcome_effective_cd_diagnostic",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "post_outcome_diagnostic": True,
        "evidence_role": "development_diagnostic_only",
        "source": {
            "dataset_doi": "10.23642/USN.14405903",
            "article_doi": "10.3390/en14113008",
            "license": "CC BY 4.0",
            "raw_files_committed": False,
            "article_reported_mass_flow_uncertainty": "±0.2% of flow rate",
            "article_reported_flow_regime": "all experiments choked at the nozzle",
        },
        "protocol_reference": "research/hytunnel_carpark_holdout_protocol_2026_10_08.json",
        "holdout_result_reference": "research/hytunnel_carpark_holdout_result_2026_10_08.json",
        "model_lock": {
            "nozzle_diameter_m": BLOWDOWN_NOZZLE_DIAMETER_M,
            "frozen_discharge_coefficient": BLOWDOWN_DISCHARGE_COEFFICIENT,
            "downstream_pressure_pa": AMBIENT_PRESSURE_PA,
            "thermophysical_backend": "CoolProp hydrogen",
            "sample_and_eligibility_rule": "identical to frozen holdout",
        },
        "cases": cases,
        "aggregate": {
            "case_count": len(cases),
            "effective_cd_peak_ratio_median": float(np.median(peak_ratios)),
            "effective_cd_peak_ratio_min": float(np.min(peak_ratios)),
            "effective_cd_peak_ratio_max": float(np.max(peak_ratios)),
            "effective_cd_median_across_cases": float(np.median(medians)),
        },
        "findings": [
            "The frozen Cd=0.8 model preserves the mass-flow time ordering but underpredicts the measured peak in all five blowdown cases.",
            "The coefficient implied by the measured source rate is consistently near 0.98-1.00 at the case peak, while the frozen model uses 0.8.",
            "The source reports choked flow and a ±0.2% mass-flow uncertainty; these facts do not justify silently changing the frozen holdout parameter.",
            "A future pre-registered test may resolve the nozzle/line boundary with a documented coefficient or measured nozzle-upstream state. This artifact does not do that.",
        ],
        "runtime_parameter_changed": False,
        "frozen_validation_result_changed": False,
        "validation_gate_effect": "none",
        "claim_boundary": "This report diagnoses a post-outcome source-rate mismatch in five public blowdown cases. It does not support a new validation claim, station consequence distance, outdoor dispersion, detector placement, controls, or station-to-vehicle transfer.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir", type=Path, default=ROOT / "tmp/hytunnel_carpark_raw"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research/hytunnel_carpark_effective_cd_diagnostic_2026_10_12.json",
    )
    args = parser.parse_args()
    report = build_report(args.raw_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["aggregate"], indent=2))


if __name__ == "__main__":
    main()
