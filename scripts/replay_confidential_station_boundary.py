"""Replay an owner-approved measured station boundary through the reference model.

This runner is intentionally a controlled partial replay.  It accepts a
private trace and a custodian mapping at runtime, injects the mapped pressure
(and optional temperature) boundary into the reference station, and writes a
small aggregate outcome report.  Raw rows, timestamps, source paths, and
source column names never enter the report.  The result is therefore evidence
that a measured boundary can be exercised by the model, not independent
full-station validation.
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
import json
from pathlib import Path
import sys

# Allow this script to be run directly from a source checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from h2station.controlled_station_replay import (
    StationBoundaryProfile,
    read_boundary_profile,
    synchronize_station_traces,
)
from h2station.api import ProcessSettings
from h2station.operations import ProcessRuntime
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario

from calibrate_confidential_station_data import _mapping


def _positive(value: str) -> float:
    result = float(value)
    if result <= 0.0:
        raise argparse.ArgumentTypeError("value must be positive")
    return result


def _slice_profile(
    profile: StationBoundaryProfile,
    start_s: float,
    duration_s: float,
) -> StationBoundaryProfile:
    """Return a relative window, carrying the last measured boundary into t=0."""

    if start_s < 0.0 or duration_s <= 0.0:
        raise ValueError("profile window must have a non-negative start and positive duration")
    end_s = start_s + duration_s
    if end_s > profile.time_s[-1]:
        raise ValueError("profile window exceeds the available measured boundary")
    anchor = max(
        (index for index, time_s in enumerate(profile.time_s) if time_s <= start_s),
        default=0,
    )
    points = [(0.0, profile.pressure_pa[anchor])]
    for time_s, pressure_pa in zip(profile.time_s, profile.pressure_pa):
        if start_s < time_s <= end_s:
            points.append((float(time_s - start_s), float(pressure_pa)))
    if len(points) < 2:
        raise ValueError("profile window must contain at least two measured boundary points")
    temperature = ()
    if profile.temperature_k:
        temperature_points = [(0.0, profile.temperature_k[anchor])]
        for time_s, temperature_k in zip(profile.time_s, profile.temperature_k):
            if start_s < time_s <= end_s:
                temperature_points.append((float(time_s - start_s), float(temperature_k)))
        if len(temperature_points) == len(points):
            temperature = tuple(value for _, value in temperature_points)
    return StationBoundaryProfile(
        tuple(time_s for time_s, _ in points),
        tuple(value for _, value in points),
        temperature,
    )


def _max_ramp_start(profile: StationBoundaryProfile, duration_s: float) -> float:
    """Select a deterministic high-ramp window without inspecting outcomes."""

    best_rate = -1.0
    best_start = 0.0
    for index, start_s in enumerate(profile.time_s):
        end_index = bisect_right(profile.time_s, start_s + duration_s) - 1
        if end_index <= index:
            continue
        elapsed = profile.time_s[end_index] - start_s
        if elapsed <= 0.0:
            continue
        rate = abs(profile.pressure_pa[end_index] - profile.pressure_pa[index]) / elapsed
        # Retain the earliest window on ties for deterministic replay.
        if rate > best_rate:
            best_rate = rate
            best_start = float(start_s)
    if best_rate < 0.0:
        raise ValueError("the measured boundary has no complete pressure-ramp window")
    return best_start


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay a private measured station boundary without exporting raw data."
    )
    parser.add_argument("--input", type=Path, required=True, help="restricted raw trace")
    parser.add_argument("--mapping", type=Path, required=True, help="restricted custodian mapping JSON")
    parser.add_argument("--output", type=Path, required=True, help="aggregate replay report JSON")
    parser.add_argument(
        "--calibration", type=Path,
        help="optional owner-approved aggregate calibration JSON; no raw trace is read from it",
    )
    parser.add_argument(
        "--equipment-input", type=Path,
        help="optional second private logger to require an absolute-time alignment check",
    )
    parser.add_argument(
        "--equipment-mapping", type=Path,
        help="mapping for --equipment-input",
    )
    parser.add_argument("--max-match-gap-s", type=_positive, default=2.0)
    parser.add_argument("--window-start-s", type=float, default=0.0)
    parser.add_argument(
        "--window-selection", choices=("fixed", "max_abs_pressure_ramp"), default="fixed",
        help="fixed uses --window-start-s; max_abs_pressure_ramp selects a deterministic signal-only window",
    )
    parser.add_argument(
        "--active-vehicle", choices=("vehicle_1", "vehicle_2", "both"),
        default="vehicle_1",
        help="which virtual dispenser circuit is active during the boundary replay",
    )
    parser.add_argument("--stride", type=int, default=60)
    parser.add_argument("--max-rows", type=int, default=25_000)
    parser.add_argument(
        "--duration-s", type=_positive, default=None,
        help="bounded replay duration; defaults to the available measured profile duration",
    )
    parser.add_argument("--control-period-s", type=_positive, default=0.2)
    args = parser.parse_args()
    if args.stride < 1 or args.max_rows < 1:
        parser.error("--stride and --max-rows must be at least one")
    if bool(args.equipment_input) != bool(args.equipment_mapping):
        parser.error("--equipment-input and --equipment-mapping must be supplied together")
    if args.window_start_s < 0.0:
        parser.error("--window-start-s cannot be negative")

    pressure_mapping = _mapping(args.mapping)
    alignment = None
    if args.equipment_input:
        synchronized = synchronize_station_traces(
            args.input,
            pressure_mapping,
            args.equipment_input,
            _mapping(args.equipment_mapping),
            stride=args.stride,
            max_rows=args.max_rows,
            max_match_gap_s=args.max_match_gap_s,
        )
        profile = synchronized.boundary
        alignment = synchronized.alignment.to_public_dict()
    else:
        profile = read_boundary_profile(
            args.input,
            pressure_mapping,
            stride=args.stride,
            max_rows=args.max_rows,
        )
    available_duration = float(profile.time_s[-1])
    if args.window_start_s >= available_duration:
        raise ValueError("--window-start-s must precede the available measured boundary")
    requested_duration = (
        args.duration_s if args.duration_s is not None else min(300.0, available_duration - args.window_start_s)
    )
    if requested_duration <= 0.0:
        raise ValueError("requested replay duration must be positive")
    selected_start_s = (
        _max_ramp_start(profile, requested_duration)
        if args.window_selection == "max_abs_pressure_ramp"
        else args.window_start_s
    )
    if selected_start_s >= available_duration:
        raise ValueError("selected replay window starts beyond the measured boundary")
    duration_s = min(requested_duration, available_duration - selected_start_s)
    window_profile = _slice_profile(profile, selected_start_s, duration_s)
    scenario_profile = tuple(zip(window_profile.time_s, window_profile.pressure_pa))
    temperature_profile = (
        tuple(zip(window_profile.time_s, window_profile.temperature_k))
        if window_profile.temperature_k else ()
    )

    calibrated_hysteresis_pa: float | None = None
    if args.calibration is not None:
        calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
        if calibration.get("artifact_type") != "confidential_station_boundary_calibration":
            raise ValueError("--calibration is not a station boundary calibration artifact")
        value = calibration.get("calibration", {}).get("recharge_restart_margin_pa")
        if value is not None:
            calibrated_hysteresis_pa = float(value)
            if calibrated_hysteresis_pa <= 0.0:
                raise ValueError("calibration recharge margin must be positive")

    config = ReferenceScenario(
        duration_s=duration_s,
        control_period_s=args.control_period_s,
        station_recharge_hysteresis_pa=calibrated_hysteresis_pa,
        supply_pressure_profile_pa=scenario_profile,
        supply_temperature_profile_k=temperature_profile,
    )
    built = build_reference_scenario(config, UnavailableHyRAMBackend())
    process_runtime = None
    if args.active_vehicle != "both":
        settings = ProcessSettings(
            **{args.active_vehicle: True},
        ).model_dump()
        process_runtime = ProcessRuntime(settings)
        built.simulator.process_runtime = process_runtime
    trajectory = built.simulator.simulate(
        built.initial_state,
        duration_s,
        control_period_s=args.control_period_s,
        pace_idle=False,
    )
    result = {
        "schema_version": 1,
        "artifact_type": "confidential_station_boundary_replay",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "input_boundary": {
            "source_mode": "synchronized_logger_boundary" if alignment is not None else "pressure_boundary_only",
            "mapped_profile_points": len(profile.time_s),
            "profile_duration_s": round(available_duration, 3),
            "pressure_profile_used": True,
            "temperature_profile_used": bool(profile.temperature_k),
        },
        "alignment": alignment,
        "window": {
            "start_s": round(selected_start_s, 3),
            "duration_s": round(duration_s, 3),
            "replayed_profile_points": len(window_profile.time_s),
            "active_vehicle": args.active_vehicle,
            "selection_method": args.window_selection,
        },
        "calibration": {
            "aggregate_margin_applied": calibrated_hysteresis_pa is not None,
            "raw_rows_persisted": False,
            "source_identifiers_published": False,
        },
        "replay": {
            "requested_duration_s": round(duration_s, 3),
            "simulated_duration_s": round(float(trajectory.time_s[-1]), 3),
            "simulated_samples": int(len(trajectory.time_s)),
            "esd_triggered": trajectory.esd_time_s is not None,
            "control_period_s": args.control_period_s,
        },
        "claim_boundary": (
            "Controlled measured-boundary replay only; this is not independent "
            "full station-to-vehicle validation."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
