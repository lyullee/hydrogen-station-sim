"""Inspect one authorised event before requesting a multi-event holdout.

This command is intentionally a schema-only preview.  It emits aggregate
channel, time-axis and quality checks plus a file digest; it never emits raw
rows, source paths, filenames or facility identifiers.  A passing preview is
not a validation result and must not be used to tune the simulator.
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
    validate_privacy_safe_pilot_bundle,
)


def inspect_event(
    event_path: Path,
    *,
    require_vehicle_boundary: bool = False,
) -> dict[str, Any]:
    """Return a one-event, raw-row-free intake preview."""

    if not event_path.is_file():
        raise FileNotFoundError(event_path)
    report = validate_privacy_safe_pilot_bundle(
        [event_path],
        rules=PilotIntakeRules(
            minimum_event_count=1,
            require_vehicle_boundary=require_vehicle_boundary,
        ),
    )
    report["artifact_type"] = "privacy_safe_single_event_schema_preview"
    report["claim_boundary"] = (
        "Schema preview only; this event was not used for model fitting, "
        "parameter selection, accuracy scoring, safety limits or full-loop "
        "validation."
    )
    report["next_step"] = (
        "If the preview is acceptable, request at least three independent "
        "events and freeze the protocol, model and evaluator before outcomes "
        "are inspected."
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-vehicle-boundary", action="store_true")
    args = parser.parse_args()

    report = inspect_event(
        args.event,
        require_vehicle_boundary=args.require_vehicle_boundary,
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8", newline="\n")
        destination = output.name
    else:
        print(payload, end="")
        destination = "stdout"
    print(json.dumps({
        "status": report["status"],
        "output": destination,
        "claim_boundary": report["claim_boundary"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
