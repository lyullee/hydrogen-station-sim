"""Run the paper's reproducibility and integrity checks.

This entry point deliberately separates three results that are often confused
in a manuscript review:

* artifact integrity (the committed source, PDF and audit files are readable),
* software checks (focused tests, and optionally the complete regression suite),
* scientific readiness (the frozen external-validation gates in the audit).

An open scientific gate is reported as ``SCIENTIFIC_GATES_OPEN``; it is not
silently converted into a passing result and it does not make this command
fail.  Use ``--require-bounded`` when a release workflow must stop unless the
bounded paper gate is closed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
FOCUSED_TESTS = (
    "tests/test_ijhe_readiness_audit.py",
    "tests/test_ijhe_audit_snapshot_consistency.py",
    "tests/test_ijhe_manuscript_format.py",
    "tests/test_ijhe_compile_artifact.py",
    "tests/test_goal_progress_snapshot.py",
    "tests/test_ijhe_reproduction.py",
)


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _test_python() -> str:
    candidates = (
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "bin" / "python",
        ROOT / "venv" / "Scripts" / "python.exe",
        ROOT / "venv" / "bin" / "python",
    )
    return str(next((item for item in candidates if item.is_file()), Path(sys.executable)))


def _run_tests(test_paths: Sequence[str], *, timeout_s: float) -> dict[str, Any]:
    command = [_test_python(), "-m", "pytest", *test_paths, "-q"]
    environment = dict(os.environ)
    source_path = str(ROOT / "src")
    environment["PYTHONPATH"] = source_path + (
        os.pathsep + environment["PYTHONPATH"]
        if environment.get("PYTHONPATH") else ""
    )
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
        output = (completed.stdout + "\n" + completed.stderr).strip()
        return {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "exit_code": completed.returncode,
            "command": " ".join(command[1:]),
            "tests": list(test_paths),
            "output_tail": output[-2000:],
        }
    except subprocess.TimeoutExpired as exc:
        output = f"{exc.stdout or ''}\n{exc.stderr or ''}".strip()
        return {
            "status": "TIMEOUT",
            "exit_code": None,
            "command": " ".join(command[1:]),
            "tests": list(test_paths),
            "output_tail": output[-2000:],
        }


def _decision_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "bounded_ijhe_submission_ready": report.get("bounded_ijhe_submission_ready"),
        "full_user_objective_ready": report.get("full_user_objective_ready"),
        "goal_completion_permitted": report.get("goal_completion_permitted"),
        "gate_counts": report.get("gate_counts", {}),
        "blocking_bounded_submission_gates": report.get(
            "blocking_bounded_submission_gates", []
        ),
    }


def build_report(*, root: Path = ROOT, run_focused_tests: bool = False,
                 run_full_regression: bool = False,
                 timeout_s: float = 900.0) -> dict[str, Any]:
    # Imports are delayed so ``--help`` works even in a minimal environment.
    sys.path.insert(0, str(root / "scripts"))
    from audit_ijhe_readiness import audit  # noqa: PLC0415
    from check_ijhe_manuscript import check as check_manuscript  # noqa: PLC0415
    from record_ijhe_compile_status import build_status  # noqa: PLC0415

    readiness = audit(root)
    format_result = check_manuscript(
        root / "manuscript/ijhe_manuscript_draft.tex",
        root / "manuscript/Highlights.txt",
    )
    stored_compile = json.loads(
        (root / "manuscript/ijhe_compile_status.json").read_text(encoding="utf-8")
    )
    source = root / stored_compile["source"]["path"]
    pdf = root / stored_compile["pdf"]["path"]
    log = root / stored_compile["compile_log"]["path"]
    compile_result = build_status(
        source=source,
        pdf=pdf,
        log=log,
        compiler=stored_compile["compiler"]["name"],
        compiler_version=stored_compile["compiler"]["version"],
        compiler_url=stored_compile["compiler"]["official_release_url"],
        compiler_archive_sha256=stored_compile["compiler"]["archive_sha256"],
        visual_pages_inspected=stored_compile["visual_qa"]["pages_inspected"],
    )

    audit_mirror = json.loads(
        (root / "research/ijhe_readiness_audit.json").read_text(encoding="utf-8")
    )
    integrity_passed = (
        format_result["format_gate_passed"]
        and compile_result["success"]
        and _decision_snapshot(readiness) == _decision_snapshot(audit_mirror)
    )
    checks: list[dict[str, Any]] = []
    if run_focused_tests:
        checks.append(_run_tests(FOCUSED_TESTS, timeout_s=timeout_s))
    if run_full_regression:
        checks.append(_run_tests(("tests",), timeout_s=timeout_s))

    science_ready = bool(readiness.get("bounded_ijhe_submission_ready"))
    software_passed = all(item["status"] == "PASS" for item in checks)
    if not integrity_passed or any(item["status"] != "PASS" for item in checks):
        status = "FAIL"
    elif science_ready:
        status = "READY"
    else:
        status = "SCIENTIFIC_GATES_OPEN"
    return {
        "schema_version": 1,
        "artifact_type": "ijhe_reproducibility_run",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "repository": {
            "root": _relative(root),
            "commit": subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True,
                capture_output=True, text=True,
            ).stdout.strip(),
            "dirty": bool(subprocess.run(
                ["git", "status", "--porcelain"], cwd=root, check=True,
                capture_output=True, text=True,
            ).stdout.strip()),
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "interpreter": _relative(Path(_test_python())),
        },
        "artifact_integrity": {
            "passed": integrity_passed,
            "manuscript_format": format_result,
            "compile_status_rebuilt": compile_result,
            "audit_snapshot_matches_research_mirror": (
                _decision_snapshot(readiness) == _decision_snapshot(audit_mirror)
            ),
        },
        "scientific_readiness": {
            "bounded_submission_ready": science_ready,
            "decision": _decision_snapshot(readiness),
            "claim_boundary": (
                "This is an evidence-readiness result, not a guarantee of peer-review "
                "acceptance, field safety, or regulatory compliance."
            ),
        },
        "software_checks": {
            "requested": bool(checks),
            "passed": software_passed if checks else None,
            "runs": checks,
        },
        "reproduction_commands": {
            "focused": ".venv/Scripts/python -m pytest " + " ".join(FOCUSED_TESTS) + " -q",
            "full": ".venv/Scripts/python -m pytest -q",
            "audit": ".venv/Scripts/python scripts/audit_ijhe_readiness.py",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("tmp/ijhe_reproduction_report.json"))
    parser.add_argument("--run-focused-tests", action="store_true")
    parser.add_argument("--run-full-regression", action="store_true")
    parser.add_argument("--timeout-s", type=float, default=900.0)
    parser.add_argument("--require-bounded", action="store_true")
    args = parser.parse_args()
    report = build_report(
        root=ROOT,
        run_focused_tests=args.run_focused_tests,
        run_full_regression=args.run_full_regression,
        timeout_s=args.timeout_s,
    )
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.require_bounded and not report["scientific_readiness"]["bounded_submission_ready"]:
        return 2
    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
