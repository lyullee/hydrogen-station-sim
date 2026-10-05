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
import json
from pathlib import Path
import sys

# Allow this script to be run directly from a source checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from h2station.controlled_station_replay import read_boundary_profile
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario

from calibrate_confidential_station_data import _mapping


def _positive(value: str) -> float:
    result = float(value)
    if result <= 0.0:
        raise argparse.ArgumentTypeError("value must be positive")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay a private measured station boundary without exporting raw data."
    )
    parser.add_argument("--input", type=Path, required=True, help="restricted raw trace")
    parser.add_argument("--mapping", type=Path, required=True, help="restricted custodian mapping JSON")
    parser.add_argument("--output", type=Path, required=True, help="aggregate replay report JSON")
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

    profile = read_boundary_profile(
        args.input,
        _mapping(args.mapping),
        stride=args.stride,
        max_rows=args.max_rows,
    )
    available_duration = float(profile.time_s[-1])
    duration_s = min(
        available_duration,
        args.duration_s if args.duration_s is not None else available_duration,
    )
    if duration_s <= 0.0:
        raise ValueError("the mapped boundary profile must span a positive duration")

    # Keep only the measured points inside the replay horizon.  Include the
    # first point after the horizon only when the profile has no earlier point;
    # _profile_value performs zero-order hold between supplied measurements.
    scenario_profile = tuple(
        (time_s, pressure_pa)
        for time_s, pressure_pa in zip(profile.time_s, profile.pressure_pa)
        if time_s <= duration_s
    )
    if len(scenario_profile) < 2:
        raise ValueError("the bounded replay needs at least two measured boundary points")
    temperature_profile = tuple(
        (time_s, temperature_k)
        for time_s, temperature_k in zip(profile.time_s, profile.temperature_k)
        if time_s <= duration_s
    ) if profile.temperature_k else ()

    config = ReferenceScenario(
        duration_s=duration_s,
        control_period_s=args.control_period_s,
        supply_pressure_profile_pa=scenario_profile,
        supply_temperature_profile_k=temperature_profile,
    )
    built = build_reference_scenario(config, UnavailableHyRAMBackend())
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
            "mapped_profile_points": len(profile.time_s),
            "profile_duration_s": round(available_duration, 3),
            "pressure_profile_used": True,
            "temperature_profile_used": bool(profile.temperature_k),
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
