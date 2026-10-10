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
    Diagnostic(
        "nrel_h2fills_hdvs_tank",
        "P1",
        "scripts/run_nrel_h2fills_hdvs_validation.py",
        "NREL H2FillS HDVS Type-IV tank boundary screen",
    ),
)


def _sanitize(output: str) -> str:
    output = output.replace(str(ROOT), "<repository>")
    return re.sub(r"(?i)[A-Z]:\\[^\r\n]+", "<local-path>", output)


def _parse_stdout_payload(stdout: str) -> dict[str, object] | None:
    """Parse a diagnostic's machine-readable stdout when it is available.

    The child diagnostics intentionally keep their process exit code independent
    from a scientific screening result: a failed screen is useful negative
    evidence and should still produce a complete artifact.  The fast-lane
    runner therefore parses JSON separately instead of treating exit code 0 as
    a model pass.
    """

    candidate = stdout.strip()
    if not candidate:
        return None
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _scientific_screen(payload: dict[str, object] | None) -> dict[str, object]:
    """Extract an explicit screening outcome without inventing one.

    A diagnostic may report a joint pass fraction or a count of passing
    sub-screens.  When neither is present the result stays ``NOT_REPORTED``;
    process completion alone never becomes a scientific PASS.
    """

    if not payload:
        return {"status": "NOT_REPORTED"}
    aggregate = payload.get("aggregate")
    if isinstance(aggregate, dict):
        nested = _scientific_screen({**aggregate, "case_count": payload.get("case_count")})
        if nested["status"] != "NOT_REPORTED":
            return nested
    case_count = payload.get("case_count")
    joint_fraction = payload.get("joint_screening_pass_fraction")
    if isinstance(joint_fraction, (int, float)) and isinstance(case_count, int):
        status = "PASS" if float(joint_fraction) >= 0.8 else "FAIL"
        return {
            "status": status,
            "case_count": case_count,
            "joint_screening_pass_fraction": float(joint_fraction),
        }
    # Some bounded external screens report a tank/trace count rather than a
    # generic case_count.  Treat that explicit fraction as scientific evidence
    # too; otherwise a completed negative screen could incorrectly make an
    # entire priority lane look ready.
    screening_fraction = payload.get("screening_pass_fraction")
    screening_count = payload.get("screening_pass_count")
    screening_total = payload.get("tank_count") or payload.get("case_count")
    if isinstance(screening_fraction, (int, float)) and isinstance(screening_total, int):
        return {
            "status": "PASS" if float(screening_fraction) >= 0.8 else "FAIL",
            "case_count": screening_total,
            "screen_pass_count": (
                int(screening_count)
                if isinstance(screening_count, int)
                else round(float(screening_fraction) * screening_total)
            ),
            "screen_pass_fraction": float(screening_fraction),
        }
    if isinstance(screening_count, int) and isinstance(screening_total, int):
        fraction = screening_count / screening_total if screening_total else 0.0
        return {
            "status": "PASS" if fraction >= 0.8 else "FAIL",
            "case_count": screening_total,
            "screen_pass_count": screening_count,
            "screen_pass_fraction": fraction,
        }
    pass_count = payload.get("soc_definition_screen_pass_count")
    if isinstance(pass_count, int) and isinstance(case_count, int):
        fraction = pass_count / case_count if case_count else 0.0
        return {
            "status": "PASS" if fraction >= 0.8 else "FAIL",
            "case_count": case_count,
            "screen_pass_count": pass_count,
            "screen_pass_fraction": fraction,
        }
    flags: list[bool] = []

    def collect(value: object) -> None:
        if isinstance(value, dict):
            for key in ("joint_primary_screen_pass", "screening_pass"):
                flag = value.get(key)
                if isinstance(flag, bool):
                    flags.append(flag)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(payload)
    if flags:
        fraction = sum(flags) / len(flags)
        return {
            "status": "PASS" if fraction >= 0.8 else "FAIL",
            "screen_pass_count": sum(flags),
            "screen_case_count": len(flags),
            "screen_pass_fraction": fraction,
        }
    return {"status": "NOT_REPORTED"}


def _readiness_status(
    process_status: str, scientific_screen_status: str,
) -> str:
    """Summarize whether a diagnostic lane is usable for a readiness claim.

    ``status`` remains the child-process health signal for compatibility.  A
    completed process can still contain negative scientific evidence, so this
    separate field is deliberately conservative and never upgrades an
    unreported screen to PASS.
    """

    if process_status != "PASS":
        return "FAIL"
    if scientific_screen_status == "FAIL":
        return "BLOCKED"
    if scientific_screen_status != "PASS":
        return "NOT_ASSESSED"
    return "PASS"


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
        payload = _parse_stdout_payload(completed.stdout)
        output = _sanitize((completed.stdout + "\n" + completed.stderr).strip())
        return {
            "name": diagnostic.name,
            "priority": diagnostic.priority,
            "description": diagnostic.description,
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "exit_code": completed.returncode,
            "duration_s": round(time.perf_counter() - started, 3),
            "scientific_screen": _scientific_screen(payload),
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
            "scientific_screen": {"status": "TIMEOUT"},
            "output_tail": output[-1600:],
        }


def select_diagnostics(
    diagnostics: Sequence[Diagnostic], priority: str,
) -> tuple[Diagnostic, ...]:
    if priority in {"critical", "all"}:
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
    scientific_failures = [
        str(item["name"])
        for item in results
        if (item.get("scientific_screen") or {}).get("status") == "FAIL"
    ]
    reported_screens = [
        (item.get("scientific_screen") or {}).get("status")
        for item in results
        if (item.get("scientific_screen") or {}).get("status") in {"PASS", "FAIL"}
    ]
    process_status = "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL"
    scientific_screen_status = (
        "FAIL" if scientific_failures else "PASS" if reported_screens else "NOT_REPORTED"
    )
    return {
        "schema_version": 1,
        "artifact_type": "parallel_priority_diagnostic_run",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parallel": True,
        "selected_priority": priority,
        "diagnostic_count": len(selected),
        "duration_s": round(time.perf_counter() - started, 3),
        "status": process_status,
        "scientific_screen_status": scientific_screen_status,
        "readiness_status": _readiness_status(
            process_status, scientific_screen_status
        ),
        "scientific_screen_failures": scientific_failures,
        "results": results,
        "claim_boundary": (
            "Process status only. These are bounded development diagnostics; "
            "the runner does not promote validation gates, change runtime "
            "parameters, or publish raw measurements."
        ),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--priority",
        choices=("P0", "P1", "critical", "all"),
        default="all",
        help="Use 'critical' to run the P0/P1 tracks together; 'all' is an alias.",
    )
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
