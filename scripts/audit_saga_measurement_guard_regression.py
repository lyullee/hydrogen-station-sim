"""Audit SAGA direct-answer measurement grounding without provider calls.

The retained HIAD benchmark exposed a weakness in the first lexical detector:
equivalent forms such as ``10 min``/``10 minutes`` and
``-33oC``/``-33 °C`` could be classified differently.  This deterministic
regression exercises the current SAGA API guard and records the exact source
revision.  It is a software-safety check, not an LLM effectiveness result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "research/saga_measurement_guard_regression_2026_10_08.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()


def run(saga_repo: Path) -> dict[str, Any]:
    api_path = saga_repo / "python/saga/api.py"
    if not api_path.is_file():
        raise FileNotFoundError(f"SAGA API not found: {api_path}")
    sys.path.insert(0, str((saga_repo / "python").resolve()))
    from saga.api import _direct_measurement_evidence, _guard_direct_measurements

    cases = [
        {
            "id": "temperature_notation_equivalence",
            "allowed": "Hydrogen was pre-chilled between -33oC and -40oC.",
            "answer": "The test range was -33 °C to -40 °C.",
            "language": "en",
            "must_keep": ["-33 °C", "-40 °C"],
            "must_remove": [],
            "notice_expected": False,
        },
        {
            "id": "time_unit_equivalence",
            "allowed": "Responders arrived within 10 min.",
            "answer": "Responders arrived within 10 minutes.",
            "language": "en",
            "must_keep": ["10 minutes"],
            "must_remove": [],
            "notice_expected": False,
        },
        {
            "id": "shared_unit_range_expansion",
            "allowed": "The documented interval is 5-10 MPa.",
            "answer": "The interval is 5 MPa to 10 MPa.",
            "language": "en",
            "must_keep": ["5 MPa", "10 MPa"],
            "must_remove": [],
            "notice_expected": False,
        },
        {
            "id": "structured_context_projection",
            "allowed": _direct_measurement_evidence({
                "pressure_mpa": 69.4,
                "temperature_c": 25.0,
                "effect_distance_m": 5.5,
            }),
            "answer": "Pressure is 69.4 MPa, temperature is 25 °C, and distance is 5.5 m.",
            "language": "en",
            "must_keep": ["69.4 MPa", "25 °C", "5.5 m"],
            "must_remove": [],
            "notice_expected": False,
        },
        {
            "id": "unsupported_value_removed",
            "allowed": "The supplied pressure is 69.4 MPa.",
            "answer": "The supplied pressure is 69.4 MPa. An inferred pressure is 12 bar.",
            "language": "en",
            "must_keep": ["69.4 MPa"],
            "must_remove": ["12 bar"],
            "notice_expected": True,
        },
    ]
    rows: list[dict[str, Any]] = []
    for case in cases:
        guarded = _guard_direct_measurements(
            case["answer"], case["allowed"], case["language"],
        )
        retained = all(item in guarded for item in case["must_keep"])
        removed = all(item not in guarded for item in case["must_remove"])
        notice = "No precise value was supplied" in guarded
        passed = retained and removed and notice is case["notice_expected"]
        rows.append({
            "id": case["id"],
            "passed": passed,
            "grounded_values_retained": retained,
            "unsupported_values_removed": removed,
            "notice_observed": notice,
        })

    return {
        "schema_version": 1,
        "artifact_type": "saga_direct_measurement_guard_regression",
        "status": "PASS" if all(row["passed"] for row in rows) else "FAIL",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "saga_commit": _git(saga_repo, "rev-parse", "HEAD"),
            "saga_remote": _git(saga_repo, "remote", "get-url", "origin"),
            "api_path": "python/saga/api.py",
            "api_sha256": _sha256(api_path),
            "provider_calls": 0,
        },
        "aggregate": {
            "case_count": len(rows),
            "pass_count": sum(row["passed"] for row in rows),
            "equivalent_grounded_case_count": 4,
            "unsupported_rejection_case_count": 1,
        },
        "cases": rows,
        "claim_boundary": (
            "Deterministic software regression of measurement-token normalization and "
            "output filtering only. It does not establish factual completeness, action "
            "correctness, operator benefit, field safety or SAGA effectiveness."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saga-repo", type=Path, default=ROOT.parent / "saga-system")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.saga_repo.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["aggregate"], ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
