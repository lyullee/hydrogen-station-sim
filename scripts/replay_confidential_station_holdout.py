"""Run a time-ordered measured-boundary holdout replay.

The raw logger and custodian mappings are runtime-only inputs.  The prefix of
the measured profile is used to derive an aggregate restart margin; the later
suffix is then replayed through the protection-aware reference runtime.  The
report contains counts and protection outcomes only, so it is safe to review
without exporting the private trace.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from h2station.api import ProcessSettings
from h2station.controlled_station_replay import (
    StationBoundaryProfile,
    fit_station_boundary_profile,
    read_boundary_profile,
    synchronize_station_traces,
)
from h2station.operations import ProcessRuntime
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario

try:  # direct script execution
    from calibrate_confidential_station_data import _mapping
except ModuleNotFoundError:  # import from the repository test runner
    from scripts.calibrate_confidential_station_data import _mapping


def _positive(value: str) -> float:
    parsed = float(value)
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _split_profile(
    profile: StationBoundaryProfile,
    fraction: float,
) -> tuple[StationBoundaryProfile, StationBoundaryProfile]:
    if not 0.0 < fraction < 1.0:
        raise ValueError("calibration fraction must be between zero and one")
    if len(profile.time_s) < 4:
        raise ValueError("holdout replay requires at least four profile points")
    split_index = int(len(profile.time_s) * fraction)
    split_index = max(2, min(len(profile.time_s) - 2, split_index))
    calibration = StationBoundaryProfile(
        tuple(profile.time_s[:split_index]),
        tuple(profile.pressure_pa[:split_index]),
        tuple(profile.temperature_k[:split_index]) if profile.temperature_k else (),
    )
    origin = profile.time_s[split_index]
    holdout = StationBoundaryProfile(
        tuple(float(time_s - origin) for time_s in profile.time_s[split_index:]),
        tuple(profile.pressure_pa[split_index:]),
        tuple(profile.temperature_k[split_index:]) if profile.temperature_k else (),
    )
    return calibration, holdout


def _limit_profile(profile: StationBoundaryProfile, duration_s: float) -> StationBoundaryProfile:
    if duration_s >= profile.time_s[-1]:
        return profile
    points = [index for index, value in enumerate(profile.time_s) if value <= duration_s]
    if len(points) < 2:
        raise ValueError("holdout duration contains fewer than two measured points")
    end = points[-1]
    return StationBoundaryProfile(
        tuple(profile.time_s[: end + 1]),
        tuple(profile.pressure_pa[: end + 1]),
        tuple(profile.temperature_k[: end + 1]) if profile.temperature_k else (),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay an untouched private measured-boundary suffix")
    parser.add_argument("--input", type=Path, required=True, help="restricted raw pressure trace")
    parser.add_argument("--mapping", type=Path, required=True, help="restricted pressure mapping JSON")
    parser.add_argument("--output", type=Path, required=True, help="aggregate holdout report JSON")
    parser.add_argument("--equipment-input", type=Path, help="optional restricted equipment logger")
    parser.add_argument("--equipment-mapping", type=Path, help="mapping for --equipment-input")
    parser.add_argument("--max-match-gap-s", type=_positive, default=2.0)
    parser.add_argument("--calibration-fraction", type=float, default=0.70)
    parser.add_argument("--holdout-duration-s", type=_positive, default=300.0)
    parser.add_argument("--stride", type=int, default=60)
    parser.add_argument("--max-rows", type=int, default=25_000)
    parser.add_argument(
        "--active-vehicle", choices=("vehicle_1", "vehicle_2", "both"), default="vehicle_1"
    )
    parser.add_argument("--control-period-s", type=_positive, default=0.5)
    args = parser.parse_args()
    if args.stride < 1 or args.max_rows < 1:
        parser.error("--stride and --max-rows must be at least one")
    if bool(args.equipment_input) != bool(args.equipment_mapping):
        parser.error("--equipment-input and --equipment-mapping must be supplied together")
    if not 0.0 < args.calibration_fraction < 1.0:
        parser.error("--calibration-fraction must be between zero and one")

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
    calibration_profile, holdout_profile = _split_profile(profile, args.calibration_fraction)
    calibration = fit_station_boundary_profile(calibration_profile)
    holdout_profile = _limit_profile(holdout_profile, args.holdout_duration_s)
    duration_s = float(holdout_profile.time_s[-1])
    scenario_profile = tuple(zip(holdout_profile.time_s, holdout_profile.pressure_pa))
    temperature_profile = (
        tuple(zip(holdout_profile.time_s, holdout_profile.temperature_k))
        if holdout_profile.temperature_k else ()
    )
    config = ReferenceScenario(
        duration_s=duration_s,
        control_period_s=args.control_period_s,
        station_recharge_hysteresis_pa=calibration.recommended_recharge_restart_margin_pa,
        supply_pressure_profile_pa=scenario_profile,
        supply_temperature_profile_k=temperature_profile,
    )
    built = build_reference_scenario(config, UnavailableHyRAMBackend())
    if args.active_vehicle != "both":
        settings = ProcessSettings(**{args.active_vehicle: True}).model_dump()
        built.simulator.process_runtime = ProcessRuntime(settings)
    trajectory = built.simulator.simulate(
        built.initial_state,
        duration_s,
        control_period_s=args.control_period_s,
        pace_idle=False,
    )
    result = {
        "schema_version": 1,
        "artifact_type": "confidential_measured_boundary_holdout_replay",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "alignment": alignment,
        "split": {
            "calibration_fraction": args.calibration_fraction,
            "calibration_points": len(calibration_profile.time_s),
            "holdout_points": len(holdout_profile.time_s),
            "calibration_duration_s": round(calibration_profile.time_s[-1], 3),
            "holdout_duration_s": round(duration_s, 3),
            "fit_used_holdout": False,
            "outcome_used_for_fit": False,
        },
        "calibration": {
            "recharge_restart_margin_pa": round(
                float(calibration.recommended_recharge_restart_margin_pa or 0.0), 1
            ),
            "source_window": "chronological_prefix_only",
            "raw_rows_persisted": False,
            "source_identifiers_published": False,
        },
        "replay": {
            "active_vehicle": args.active_vehicle,
            "simulated_duration_s": round(float(trajectory.time_s[-1]), 3),
            "simulated_samples": int(len(trajectory.time_s)),
            "esd_triggered": trajectory.esd_time_s is not None,
            "control_period_s": args.control_period_s,
        },
        "claim_boundary": (
            "Time-ordered measured-boundary holdout replay only; it is not an "
            "independent station-to-vehicle accuracy result or safety certification."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
