"""Run a post-outcome, geometry-only line-inventory diagnostic.

The frozen HyTunnel mass-flow holdout uses measured tank pressure and
temperature directly at a local 0.5 mm aperture.  The published apparatus
also declares a 3.86 m, 3 mm blowdown line.  This runner exercises the
development-only two-volume model to expose the difference between flow
leaving the source and flow leaving the nozzle.  It deliberately does not
select a source volume from the measured outcome, change the frozen holdout,
or write runtime calibration.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from h2station.hytunnel_carpark_validation import BLOWDOWN_CASES, load_hytunnel_mat
from h2station.line_transient_development import (
    LineTransientParameters,
    simulate_line_transient,
)


LINE_LENGTH_M = 3.86
LINE_INNER_DIAMETER_M = 0.003
NOZZLE_INNER_DIAMETER_M = 0.0005
DEFAULT_SOURCE_VOLUMES_L = (5.0, 10.0, 20.0)
DEFAULT_WINDOW_S = 30.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _initial_tank_state(trace) -> tuple[float, float]:
    """Return the measured initial tank state in Pa and K."""

    if trace.tank_time_s is None or trace.tank_pressure_bar is None or trace.tank_temperature_c is None:
        raise ValueError("Tank.time, Tank.p and Tank.T are required")
    pressure_bar = float(
        np.interp(trace.release_start_s, trace.tank_time_s, trace.tank_pressure_bar)
    )
    temperature_c = float(
        np.interp(trace.release_start_s, trace.tank_time_s, trace.tank_temperature_c)
    )
    if not np.isfinite(pressure_bar) or not np.isfinite(temperature_c):
        raise ValueError("initial tank boundary is not finite")
    return pressure_bar * 1.0e5, temperature_c + 273.15


def _result_summary(result, times: np.ndarray, measured_flow_g_s: np.ndarray) -> dict[str, float]:
    source_peak_index = int(np.argmax(result.source_flow_kg_s))
    outlet_peak_index = int(np.argmax(result.outlet_flow_kg_s))
    measured_peak = float(np.nanmax(measured_flow_g_s))
    source_peak = float(np.max(result.source_flow_kg_s) * 1000.0)
    outlet_peak = float(np.max(result.outlet_flow_kg_s) * 1000.0)
    return {
        "measured_peak_mass_flow_g_s": measured_peak,
        "source_peak_mass_flow_g_s": source_peak,
        "outlet_peak_mass_flow_g_s": outlet_peak,
        "outlet_to_source_peak_ratio": outlet_peak / source_peak if source_peak > 0.0 else 0.0,
        "source_peak_time_from_release_s": float(times[source_peak_index] - times[0]),
        "outlet_peak_time_from_release_s": float(times[outlet_peak_index] - times[0]),
        "outlet_peak_delay_s": float(times[outlet_peak_index] - times[source_peak_index]),
        "initial_line_inventory_g": float(result.line_mass_kg[0] * 1000.0),
        "peak_line_inventory_g": float(np.max(result.line_mass_kg) * 1000.0),
        "source_pressure_end_mpa_abs": float(result.source_pressure_pa[-1] / 1.0e6),
        "line_pressure_peak_mpa_abs": float(np.max(result.line_pressure_pa) / 1.0e6),
    }


def evaluate_case(path: Path, source_volume_l: float, window_s: float) -> dict[str, object]:
    trace = load_hytunnel_mat(path)
    source_pressure_pa, source_temperature_k = _initial_tank_state(trace)
    source_time = np.asarray(trace.mass_flow_time_s, dtype=float)
    source_flow = np.asarray(trace.mass_flow_g_s, dtype=float)
    finite = np.isfinite(source_time) & np.isfinite(source_flow)
    post = finite & (source_time >= trace.release_start_s)
    if np.count_nonzero(post) < 2:
        raise ValueError("fewer than two post-release mass-flow samples")
    end_s = min(float(np.max(source_time[post])), trace.release_start_s + window_s)
    if end_s <= trace.release_start_s:
        raise ValueError("empty diagnostic window")
    times = np.linspace(trace.release_start_s, end_s, 31)
    measured_flow = np.interp(times, source_time[finite], source_flow[finite])
    parameters = LineTransientParameters(
        source_volume_m3=source_volume_l / 1000.0,
        source_pressure_pa_abs=source_pressure_pa,
        source_temperature_k=source_temperature_k,
        line_length_m=LINE_LENGTH_M,
        line_inner_diameter_m=LINE_INNER_DIAMETER_M,
        outlet_inner_diameter_m=NOZZLE_INNER_DIAMETER_M,
        line_initial_pressure_pa_abs=101_325.0,
        line_initial_temperature_k=293.15,
    )
    result = simulate_line_transient(times, parameters=parameters, solver_max_step=0.1)
    return {
        "experiment": trace.experiment,
        "source_volume_l": source_volume_l,
        "diagnostic_window_s": float(end_s - trace.release_start_s),
        "initial_source_pressure_mpa_abs": source_pressure_pa / 1.0e6,
        "initial_source_temperature_c": source_temperature_k - 273.15,
        "line_volume_cm3": parameters.line_volume_m3 * 1.0e6,
        "summary": _result_summary(result, times, measured_flow),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-directory", type=Path, required=True)
    parser.add_argument("--window-s", type=float, default=DEFAULT_WINDOW_S)
    parser.add_argument(
        "--source-volume-l",
        type=float,
        nargs="+",
        default=list(DEFAULT_SOURCE_VOLUMES_L),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/hytunnel_line_inventory_diagnostic_2026_10_11.json"),
    )
    args = parser.parse_args()
    if args.window_s <= 0.0 or any(value <= 0.0 for value in args.source_volume_l):
        raise SystemExit("window and source volumes must be positive")

    source_files = [args.data_directory / f"Exp{case:02d}.mat" for case in BLOWDOWN_CASES]
    missing = [str(path) for path in source_files if not path.exists()]
    if missing:
        raise SystemExit("missing blowdown files: " + ", ".join(missing))
    cases: list[dict[str, object]] = []
    for path in source_files:
        for source_volume_l in args.source_volume_l:
            cases.append(evaluate_case(path, float(source_volume_l), args.window_s))

    payload = {
        "schema_version": 1,
        "artifact_type": "hytunnel_post_outcome_line_inventory_diagnostic",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "post_outcome_diagnostic": True,
        "source": {
            "dataset_doi": "10.23642/USN.14405903",
            "article_doi": "10.3390/en14113008",
            "license": "CC BY 4.0",
            "raw_files_committed": False,
            "files": [
                {"name": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}
                for path in source_files
            ],
        },
        "protocol_reference": "research/hytunnel_carpark_holdout_protocol_2026_10_08.json",
        "model_boundary": {
            "name": "source_vessel_plus_3.86_m_line_plus_0.5_mm_nozzle",
            "line_length_m": LINE_LENGTH_M,
            "line_inner_diameter_m": LINE_INNER_DIAMETER_M,
            "nozzle_inner_diameter_m": NOZZLE_INNER_DIAMETER_M,
            "source_volume_sensitivity_l": list(args.source_volume_l),
            "source_volume_selection": "declared sensitivity envelope; not selected from measured outcomes",
            "initial_source_state": "measured Tank.p and Tank.T interpolated at MFM.t0",
            "line_initial_state": "ambient pressure and temperature",
            "case_specific_fitting": False,
            "time_shift": False,
            "runtime_parameter_application": False,
            "frozen_gate_effect": "none",
        },
        "cases": cases,
        "claim_boundary": (
            "Post-outcome development diagnostic only. It separates source-side and nozzle-side "
            "flows and reports line inventory; it does not replace the frozen mass-flow holdout, "
            "prove a source volume, validate station controls, or authorize a runtime change."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
