"""Validate and pre-freeze a privacy-safe full-loop pilot bundle.

The source event CSVs stay with the custodian.  The generated JSON contains
only aggregate schema results, channel-role attestations and SHA-256 digests;
it must be created before any model outcome is inspected.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.privacy_safe_full_loop_intake import (  # noqa: E402
    PilotIntakeRules,
    build_privacy_safe_freeze_manifest,
    build_privacy_safe_split_freeze_manifest,
)


def _load_roles(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(role, str)
        for key, role in value.items()
    ):
        raise ValueError("channel roles JSON must be an object of string pairs")
    return value


def build_manifest(
    event_paths: list[Path],
    *,
    protocol_path: Path,
    model_path: Path,
    evaluator_path: Path,
    channel_roles_path: Path,
    minimum_event_count: int = 3,
    require_vehicle_boundary: bool = False,
) -> dict[str, Any]:
    """Build the pre-access manifest without exposing input paths."""

    return build_privacy_safe_freeze_manifest(
        event_paths,
        protocol_path=protocol_path,
        model_path=model_path,
        evaluator_path=evaluator_path,
        channel_roles=_load_roles(channel_roles_path),
        rules=PilotIntakeRules(
            minimum_event_count=minimum_event_count,
            require_vehicle_boundary=require_vehicle_boundary,
        ),
    )


def build_split_manifest(
    station_event_paths: list[Path],
    vehicle_event_paths: list[Path],
    *,
    protocol_path: Path,
    model_path: Path,
    evaluator_path: Path,
    channel_roles_path: Path,
    minimum_event_count: int = 3,
) -> dict[str, Any]:
    """Build a freeze manifest from paired station/vehicle exports."""

    if len(station_event_paths) != len(vehicle_event_paths):
        raise ValueError("station and vehicle event counts must match")
    if not station_event_paths:
        raise ValueError("at least one station/vehicle event pair is required")
    return build_privacy_safe_split_freeze_manifest(
        list(zip(station_event_paths, vehicle_event_paths)),
        protocol_path=protocol_path,
        model_path=model_path,
        evaluator_path=evaluator_path,
        channel_roles=_load_roles(channel_roles_path),
        rules=PilotIntakeRules(minimum_event_count=minimum_event_count),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    event_group = parser.add_mutually_exclusive_group(required=True)
    event_group.add_argument("--events", nargs="+", type=Path)
    event_group.add_argument("--station-events", nargs="+", type=Path)
    parser.add_argument(
        "--vehicle-events", nargs="+", type=Path,
        help="Vehicle CSVs paired by position with --station-events",
    )
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--channel-roles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-event-count", type=int, default=3)
    parser.add_argument(
        "--require-vehicle-boundary", action="store_true",
        help="Fail single-file intake unless every event contains vehicle channels",
    )
    args = parser.parse_args()

    if args.station_events is not None:
        if args.vehicle_events is None:
            parser.error("--vehicle-events is required with --station-events")
        manifest = build_split_manifest(
            args.station_events, args.vehicle_events,
            protocol_path=args.protocol,
            model_path=args.model,
            evaluator_path=args.evaluator,
            channel_roles_path=args.channel_roles,
            minimum_event_count=args.minimum_event_count,
        )
    else:
        if args.vehicle_events is not None:
            parser.error("--vehicle-events requires --station-events")
        manifest = build_manifest(
            args.events,
            protocol_path=args.protocol,
            model_path=args.model,
            evaluator_path=args.evaluator,
            channel_roles_path=args.channel_roles,
            minimum_event_count=args.minimum_event_count,
            require_vehicle_boundary=args.require_vehicle_boundary,
        )
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "status": manifest["status"],
        "event_count": manifest["bundle"]["event_count"],
        "full_loop_protocol_freeze_candidate": manifest["eligibility"][
            "full_loop_protocol_freeze_candidate"
        ],
        "output": output.name,
        "outcome_accessed_before_freeze": manifest["freeze"][
            "outcomes_accessed_before_freeze"
        ],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
