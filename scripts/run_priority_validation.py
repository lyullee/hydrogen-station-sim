"""Run the highest-impact validation checks concurrently.

The complete regression suite is intentionally not a status command: it is
reserved for broad code changes and takes several minutes.  This runner starts
small, independent focused suites at the same time and returns a privacy-safe
summary with the current P0/P1/P2 evidence tracks.  It never promotes a
readiness gate or reads private measurement rows.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json
from pathlib import Path
import os
import re
import subprocess
import sys
import time
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "research" / "ijhe_readiness_audit.json"
TRIAGE = ROOT / "research" / "validation_gap_triage_2026_10_10.json"


def _test_python() -> str:
    """Return the repository's dependency-complete Python interpreter.

    The status command is often started from a global ``python`` on Windows,
    while this repository keeps its API/test dependencies in ``.venv``.  In
    that case launching pytest with ``sys.executable`` makes every focused
    check fail during collection (for example ``fastapi`` and ``fluids`` are
    missing) even though the project environment is healthy.  Prefer the
    checked-out virtual environment and fall back to the active interpreter
    when no local environment exists.
    """

    candidates = (
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / "venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "bin" / "python",
        ROOT / "venv" / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable


@dataclass(frozen=True)
class PriorityCheck:
    name: str
    priority: str
    command: tuple[str, ...]


DEFAULT_CHECKS: tuple[PriorityCheck, ...] = (
    PriorityCheck(
        "full_loop_intake",
        "P0",
        ("-m", "pytest", "tests/test_privacy_safe_full_loop_intake.py", "tests/test_privacy_safe_full_loop_cli.py", "-q"),
    ),
    PriorityCheck(
        "llm_evidence_boundary",
        "P0",
        ("-m", "pytest", "tests/test_llm_validation_gap_grounding.py", "tests/test_validation_evidence_api.py", "-q"),
    ),
    PriorityCheck(
        "virtual_safety_and_response",
        "P1",
        ("-m", "pytest", "tests/test_virtual_safety.py", "tests/test_emergency_response.py", "-q"),
    ),
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def priority_status() -> dict[str, Any]:
    """Return current gate counts and execution tracks without running tests."""

    readiness = _read_json(READINESS)
    triage = _read_json(TRIAGE)
    return {
        "readiness": {
            "gate_counts": readiness.get("gate_counts", {}),
            "bounded_ijhe_submission_ready": bool(
                readiness.get("bounded_ijhe_submission_ready")
            ),
            "full_user_objective_ready": bool(
                readiness.get("full_user_objective_ready")
            ),
        },
        "execution_tracks": triage.get("execution_tracks", []),
        "primary_blocker": (triage.get("interpretation") or {}).get(
            "primary_blocker", ""
        ),
        "data_volume_is_primary_blocker": bool(
            (triage.get("interpretation") or {}).get(
                "data_volume_is_primary_blocker", False
            )
        ),
    }


def _run_check(check: PriorityCheck, *, timeout_s: float) -> dict[str, Any]:
    started = time.perf_counter()
    environment = os.environ.copy()
    current_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        str(ROOT / "src")
        + (os.pathsep + current_pythonpath if current_pythonpath else "")
    )
    command = (_test_python(), *check.command)
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        output = _sanitize_output((completed.stdout + "\n" + completed.stderr).strip())
        return {
            "name": check.name,
            "priority": check.priority,
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "exit_code": completed.returncode,
            "duration_s": round(time.perf_counter() - started, 3),
            "output_tail": output[-1200:],
        }
    except subprocess.TimeoutExpired as exc:
        output = _sanitize_output(str(exc.stdout or "") + "\n" + str(exc.stderr or ""))
        return {
            "name": check.name,
            "priority": check.priority,
            "status": "TIMEOUT",
            "exit_code": None,
            "duration_s": round(time.perf_counter() - started, 3),
            "output_tail": output[-1200:],
        }


def run_priority_checks(
    checks: Sequence[PriorityCheck] = DEFAULT_CHECKS,
    *,
    timeout_s: float = 180.0,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Run independent focused checks in parallel and return aggregate output."""

    if not checks:
        raise ValueError("at least one priority check is required")
    worker_count = max_workers or min(len(checks), 3)
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(_run_check, check, timeout_s=timeout_s): check
            for check in checks
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: (item["priority"], item["name"]))
    return {
        "schema_version": 1,
        "artifact_type": "priority_validation_run",
        "parallel": True,
        "full_regression_run": False,
        "duration_s": round(time.perf_counter() - started, 3),
        "status": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL",
        "current_status": priority_status(),
        "checks": results,
        "claim_boundary": (
            "Focused software checks only. This report does not score external "
            "traces, change a frozen protocol, or promote a validation gate."
        ),
    }


def _sanitize_output(output: str) -> str:
    """Keep focused-test diagnostics from publishing local machine paths."""

    sanitized = output.replace(str(ROOT), "<repository>")
    # Tests should not print private input paths, but redact any Windows path
    # that a dependency may include in an exception before it reaches JSON.
    return re.sub(r"(?i)[A-Z]:\\[^\r\n]+", "<local-path>", sanitized)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--no-tests", action="store_true", help="Only print current P0/P1/P2 status")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    if args.no_tests:
        report = {
            "schema_version": 1,
            "artifact_type": "priority_validation_status",
            "parallel": False,
            "full_regression_run": False,
            "status": "STATUS_ONLY",
            "current_status": priority_status(),
            "claim_boundary": "Status only; no test or external evaluation was run.",
        }
    else:
        report = run_priority_checks(timeout_s=args.timeout_s)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    return 0 if report["status"] in {"PASS", "STATUS_ONLY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
