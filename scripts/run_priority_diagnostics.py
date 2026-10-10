"""Run independent development diagnostics concurrently.

This runner is deliberately separate from the readiness audit and production
runtime.  It starts bounded, post-outcome diagnostics in parallel so a slow
component investigation does not block unrelated P0/P1 work.  The runner
records process status only; it never promotes a gate or copies raw rows.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]


def _test_python() -> str:
    for candidate in (
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / "venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "bin" / "python",
        ROOT / "venv" / "bin" / "python",
    ):
        if candidate.is_file():
            return str(candidate)
    return sys.executable


@dataclass(frozen=True)
class Diagnostic:
    name: str
    priority: str
    script: str
    description: str
    output_argument: bool = True


DEFAULT_DIAGNOSTICS: tuple[Diagnostic, ...] = (
    Diagnostic(
        "mc_tank_boundary",
        "P0",
        "scripts/run_mc_tank_boundary_diagnostic.py",
        "MC measured-boundary vehicle-tank replay",
    ),
    Diagnostic(
        "mc_soc_boundary",
        "P0",
        "scripts/run_mc_soc_boundary_diagnostic.py",
        "MC SOC/EOS and mass-closure boundary consistency",
    ),
    Diagnostic(
        "dickens_mixed_convection",
        "P1",
        "scripts/run_dickens_typeiii_mixed_convection_diagnostic.py",
        "Type-III inlet-jet heat-transfer sensitivity",
    ),
    Diagnostic(
        "schefer_line_transient",
        "P1",
        "scripts/run_schefer_2006_line_transient_diagnostic.py",
        "Source-line inventory and valve-opening sensitivity",
    ),
    Diagnostic(
        "h2safe_spatial_response",
        "P1",
        "scripts/run_h2safe_spatial_response_diagnostic.py",
        "Hydrogen detector spatial-response diagnostic",
    ),
)


def _sanitize(output: str) -> str:
    output = output.replace(str(ROOT), "<repository>")
    return re.sub(r"(?i)[A-Z]:\\[^\r\n]+", "<local-path>", output)


def _run_one(diagnostic: Diagnostic, timeout_s: float) -> dict[str, object]:
    started = time.perf_counter()
    environment = os.environ.copy()
    current = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = str(ROOT / "src") + (
        os.pathsep + current if current else ""
    )
    try:
        # The child scripts default to tracked research artifacts.  A status
        # run must not rewrite those artifacts, so isolate output in a
        # temporary directory and discard it after the child exits.
        with tempfile.TemporaryDirectory(prefix="h2station-priority-") as temp_dir:
            command = [_test_python(), diagnostic.script]
            if diagnostic.output_argument:
                command.extend(("--output", str(Path(temp_dir) / "diagnostic.json")))
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        output = _sanitize((completed.stdout + "\n" + completed.stderr).strip())
        return {
            "name": diagnostic.name,
            "priority": diagnostic.priority,
            "description": diagnostic.description,
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "exit_code": completed.returncode,
            "duration_s": round(time.perf_counter() - started, 3),
            "output_tail": output[-1600:],
        }
    except subprocess.TimeoutExpired as exc:
        output = _sanitize(str(exc.stdout or "") + "\n" + str(exc.stderr or ""))
        return {
            "name": diagnostic.name,
            "priority": diagnostic.priority,
            "description": diagnostic.description,
            "status": "TIMEOUT",
            "exit_code": None,
            "duration_s": round(time.perf_counter() - started, 3),
            "output_tail": output[-1600:],
        }


def select_diagnostics(
    diagnostics: Sequence[Diagnostic], priority: str,
) -> tuple[Diagnostic, ...]:
    if priority == "all":
        return tuple(diagnostics)
    return tuple(item for item in diagnostics if item.priority == priority)


def run_priority_diagnostics(
    diagnostics: Sequence[Diagnostic] = DEFAULT_DIAGNOSTICS,
    *,
    priority: str = "all",
    timeout_s: float = 300.0,
    max_workers: int | None = None,
) -> dict[str, object]:
    selected = select_diagnostics(diagnostics, priority)
    if not selected:
        raise ValueError(f"no diagnostics selected for priority {priority!r}")
    workers = max_workers or len(selected)
    started = time.perf_counter()
    results: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(selected))) as pool:
        futures = {
            pool.submit(_run_one, item, timeout_s): item for item in selected
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: (str(item["priority"]), str(item["name"])))
    return {
        "schema_version": 1,
        "artifact_type": "parallel_priority_diagnostic_run",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parallel": True,
        "selected_priority": priority,
        "diagnostic_count": len(selected),
        "duration_s": round(time.perf_counter() - started, 3),
        "status": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL",
        "results": results,
        "claim_boundary": (
            "Process status only. These are bounded development diagnostics; "
            "the runner does not promote validation gates, change runtime "
            "parameters, or publish raw measurements."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--priority", choices=("P0", "P1", "all"), default="all")
    parser.add_argument("--timeout-s", type=float, default=300.0)
    parser.add_argument("--max-workers", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--list", action="store_true", help="List diagnostics without running them")
    args = parser.parse_args()
    if args.list:
        print(json.dumps([item.__dict__ for item in DEFAULT_DIAGNOSTICS], ensure_ascii=False, indent=2))
        return 0
    report = run_priority_diagnostics(
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
