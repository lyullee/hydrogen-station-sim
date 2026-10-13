"""Refresh hash-linked runtime and publication evidence in dependency order.

Several audit artifacts bind their decisions to source-file hashes.  Updating
the runtime without rebuilding every downstream projection can therefore make
the focused CI fail even when the implementation and its direct tests are
correct.  This command provides one deterministic entry point for that chain.

It does not promote a scientific gate.  Each child audit retains its own
acceptance rule, failed screens and claim boundary.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class RefreshStep:
    """One ordered evidence-generation command."""

    name: str
    script: str
    arguments: tuple[str, ...] = ()

    def command(self, python: str) -> tuple[str, ...]:
        return (python, str(ROOT / self.script), *self.arguments)


STEPS: tuple[RefreshStep, ...] = (
    RefreshStep(
        "hydelta_cabinet_runtime_grounding",
        "scripts/audit_hydelta_ventilation_runtime_grounding.py",
    ),
    RefreshStep(
        "public_type_iv_runtime_calibration",
        "scripts/audit_public_tank_runtime_calibration.py",
    ),
    RefreshStep(
        "public_accident_runtime_routing",
        "scripts/audit_runtime_public_accident_precedents.py",
    ),
    RefreshStep(
        "hiad_digital_twin_replay",
        "scripts/audit_hiad_digital_twin_replay_coverage.py",
    ),
    RefreshStep(
        "khk_digital_twin_replay",
        "scripts/audit_khk_digital_twin_replay_coverage.py",
    ),
    RefreshStep(
        "hiad_event_category_concordance",
        "scripts/build_hiad_event_category_concordance.py",
    ),
    RefreshStep(
        "incident_evidence_traceability",
        "scripts/build_incident_evidence_traceability.py",
    ),
    RefreshStep(
        "hiad_runtime_response_handoff",
        "scripts/audit_hiad_runtime_response_handoff.py",
    ),
    RefreshStep(
        "ijhe_readiness",
        "scripts/audit_ijhe_readiness.py",
    ),
    RefreshStep(
        "validation_gap_report",
        "scripts/build_validation_gap_report.py",
        (
            "--audit",
            "manuscript/ijhe_readiness_audit.json",
            "--json-output",
            "research/validation_gap_report_2026_10_13.json",
            "--markdown-output",
            "research/VALIDATION_GAP_REPORT_2026_10_13.md",
        ),
    ),
    RefreshStep(
        "ijhe_blocker_matrix",
        "scripts/build_ijhe_blocker_matrix.py",
        (
            "--json-output",
            "research/ijhe_submission_blocker_matrix_2026_10_13.json",
            "--report-output",
            "research/IJHE_SUBMISSION_BLOCKER_MATRIX_2026_10_13.md",
        ),
    ),
    RefreshStep(
        "data_coverage_summary",
        "scripts/build_data_coverage_summary.py",
        (
            "--json-output",
            "research/data_coverage_summary.json",
            "--markdown-output",
            "research/DATA_COVERAGE_SUMMARY.md",
        ),
    ),
    RefreshStep(
        "ijhe_claim_evidence_matrix",
        "scripts/build_ijhe_claim_evidence_matrix.py",
    ),
)


READINESS_MIRRORS: tuple[tuple[str, str], ...] = (
    (
        "manuscript/ijhe_readiness_audit.json",
        "research/ijhe_readiness_audit.json",
    ),
    (
        "manuscript/IJHE_READINESS_AUDIT.md",
        "research/ijhe_readiness_audit.md",
    ),
    (
        "manuscript/IJHE_READINESS_AUDIT.md",
        "research/IJHE_READINESS_REPORT.md",
    ),
)


def _display_command(step: RefreshStep) -> str:
    return " ".join(("python", step.script, *step.arguments))


def _copy_readiness_mirrors() -> list[str]:
    copied: list[str] = []
    for source_name, destination_name in READINESS_MIRRORS:
        source = ROOT / source_name
        destination = ROOT / destination_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        copied.append(destination_name)
    return copied


def _sanitize_output(value: str) -> str:
    """Remove workstation-specific repository paths from execution records."""

    root = str(ROOT)
    for representation in (
        root.replace("\\", "\\\\"),
        root.replace("\\", "/"),
        root,
    ):
        value = value.replace(representation, "<repository>")
    return value


def refresh(
    steps: Sequence[RefreshStep] = STEPS,
    *,
    python: str = sys.executable,
) -> dict[str, object]:
    """Execute the evidence chain and stop at the first failed generator."""

    started = time.perf_counter()
    results: list[dict[str, object]] = []
    mirrors_copied = False
    for step in steps:
        step_started = time.perf_counter()
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        completed = subprocess.run(
            step.command(python),
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        result = {
            "name": step.name,
            "command": _display_command(step),
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "exit_code": completed.returncode,
            "duration_s": round(time.perf_counter() - step_started, 3),
            "output_tail": _sanitize_output(
                (completed.stdout + completed.stderr).strip()
            )[-1200:],
        }
        results.append(result)
        if completed.returncode != 0:
            return {
                "schema_version": 1,
                "artifact_type": "runtime_evidence_chain_refresh",
                "status": "FAIL",
                "failed_step": step.name,
                "duration_s": round(time.perf_counter() - started, 3),
                "steps": results,
                "readiness_mirrors_copied": mirrors_copied,
                "scientific_gate_promotion": False,
            }
        if step.name == "ijhe_readiness":
            _copy_readiness_mirrors()
            mirrors_copied = True

    return {
        "schema_version": 1,
        "artifact_type": "runtime_evidence_chain_refresh",
        "status": "PASS",
        "failed_step": None,
        "duration_s": round(time.perf_counter() - started, 3),
        "steps": results,
        "readiness_mirrors_copied": mirrors_copied,
        "scientific_gate_promotion": False,
        "claim_boundary": (
            "This command refreshes deterministic evidence projections only. "
            "It does not change frozen scientific acceptance rules or turn a "
            "failed or pending validation gate into a pass."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the ordered refresh plan without changing files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON execution record; parent directories are created.",
    )
    args = parser.parse_args()

    if args.list:
        report: dict[str, object] = {
            "schema_version": 1,
            "artifact_type": "runtime_evidence_chain_plan",
            "status": "PLAN_ONLY",
            "steps": [
                {"name": step.name, "command": _display_command(step)}
                for step in STEPS
            ],
            "readiness_mirrors": [
                {"source": source, "destination": destination}
                for source, destination in READINESS_MIRRORS
            ],
        }
    else:
        report = refresh()

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    return 0 if report["status"] in {"PASS", "PLAN_ONLY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
