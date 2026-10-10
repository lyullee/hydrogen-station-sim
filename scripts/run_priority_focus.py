"""Run the highest-impact software and physics checks in one fast lane.

The repository has two intentionally separate runners: one for focused
software/evidence checks and one for bounded post-outcome physics diagnostics.
This command composes them without changing either runner's claim boundary.
They start together, so a long diagnostic does not delay the P0 software
signal and a software collection problem does not leave the physics queue
unstarted.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

from run_priority_diagnostics import (
    DEFAULT_DIAGNOSTICS,
    run_priority_diagnostics,
)
from run_priority_validation import (
    DEFAULT_CHECKS,
    PriorityCheck,
    run_priority_checks,
)


ROOT = Path(__file__).resolve().parents[1]


def _select_checks(priority: str) -> tuple[PriorityCheck, ...]:
    if priority in {"critical", "all"}:
        return DEFAULT_CHECKS
    return tuple(check for check in DEFAULT_CHECKS if check.priority == priority)


def run_priority_focus(
    *,
    priority: str = "P0",
    timeout_s: float = 300.0,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Run software/evidence and physics tracks concurrently."""

    checks = _select_checks(priority)
    if not checks:
        raise ValueError(f"no software checks selected for priority {priority!r}")
    started = time.perf_counter()
    worker_count = max_workers or 2
    with ThreadPoolExecutor(max_workers=min(worker_count, 2)) as pool:
        software_future = pool.submit(
            run_priority_checks,
            checks,
            timeout_s=timeout_s,
            max_workers=min(len(checks), 3),
        )
        diagnostic_future = pool.submit(
            run_priority_diagnostics,
            priority=priority,
            timeout_s=timeout_s,
            # Keep the two process-level tracks from oversubscribing the
            # numerical solver on typical operator machines.  Callers can
            # still raise this explicitly when they have spare cores.
            max_workers=max_workers or 2,
        )
        software = software_future.result()
        diagnostics = diagnostic_future.result()

    status = "PASS" if software["status"] == "PASS" and diagnostics["status"] == "PASS" else "FAIL"
    return {
        "schema_version": 1,
        "artifact_type": "parallel_priority_focus_run",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parallel": True,
        "selected_priority": priority,
        "duration_s": round(time.perf_counter() - started, 3),
        "status": status,
        "software_checks": software,
        "physics_diagnostics": diagnostics,
        "claim_boundary": (
            "Fast-lane process status only. This report does not score external "
            "traces, change runtime parameters, or promote a validation gate."
        ),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--priority",
        choices=("P0", "P1", "critical", "all"),
        default="P0",
        help=(
            "Run one lane, or use 'critical' for P0 and P1 together; "
            "'all' is kept as an explicit alias for the complete queue."
        ),
    )
    parser.add_argument("--timeout-s", type=float, default=300.0)
    parser.add_argument("--max-workers", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_priority_focus(
        priority=args.priority,
        timeout_s=args.timeout_s,
        max_workers=args.max_workers,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
