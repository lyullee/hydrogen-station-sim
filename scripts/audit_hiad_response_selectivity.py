"""Audit action selectivity in retained HIAD machine-response outputs.

The original machine proxy rewards category recall and response-stage coverage.
This post-outcome robustness audit adds reference-category precision, F1 and
non-reference action burden without making another provider call.  HIAD action
fields are incomplete, so a non-reference category is not labelled unsafe or
incorrect.  The artifact is descriptive development evidence only.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "research/hiad_machine_response_benchmark_2026_10_08.json"
DEFAULT_GUARD = ROOT / "research/hiad_machine_response_guard_recheck_2026_10_08.json"
DEFAULT_OUTPUT = ROOT / "research/hiad_response_selectivity_audit_2026_10_08.json"
WORD = re.compile(r"\b[\w'-]+\b", re.UNICODE)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _case_metrics(row: dict[str, Any]) -> dict[str, Any] | None:
    expected = set(map(str, row.get("expected_categories") or []))
    if not expected:
        return None
    mentioned = set(map(str, row.get("mentioned_categories") or []))
    matched = expected.intersection(mentioned)
    precision = len(matched) / len(mentioned) if mentioned else 0.0
    recall = len(matched) / len(expected)
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "event_id": str(row["event_id"]),
        "reference_category_count": len(expected),
        "mentioned_category_count": len(mentioned),
        "matched_reference_category_count": len(matched),
        "non_reference_category_count": len(mentioned - expected),
        "reference_precision": precision,
        "reference_recall": recall,
        "reference_f1": f1,
        "stage_coverage": float(row.get("stage_coverage") or 0.0),
        "word_count": len(WORD.findall(str(row.get("answer") or ""))),
    }


def _bootstrap_difference(
    baseline: list[float], linked: list[float], *, seed: int, replicates: int,
) -> dict[str, Any]:
    differences = np.asarray(linked, dtype=float) - np.asarray(baseline, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(differences, size=(replicates, len(differences)), replace=True)
    means = samples.mean(axis=1)
    return {
        "mean_paired_difference": float(differences.mean()),
        "bootstrap_95_ci": [
            float(np.quantile(means, 0.025)),
            float(np.quantile(means, 0.975)),
        ],
        "improved_case_count": int(np.count_nonzero(differences > 0)),
        "unchanged_case_count": int(np.count_nonzero(differences == 0)),
        "worsened_case_count": int(np.count_nonzero(differences < 0)),
        "bootstrap_replicates": replicates,
        "bootstrap_seed": seed,
    }


def audit(
    benchmark: dict[str, Any], guard: dict[str, Any], *, seed: int = 20261008,
    replicates: int = 10_000,
) -> dict[str, Any]:
    baseline_rows = {
        str(row["event_id"]): row for row in benchmark.get("responses") or []
        if row.get("variant") == "alarm-only"
    }
    linked_rows = {
        str(row["event_id"]): row for row in guard.get("responses") or []
    }
    if set(baseline_rows) != set(linked_rows):
        raise ValueError("Baseline and guarded SAGA event IDs do not match")

    per_case: list[dict[str, Any]] = []
    for event_id in sorted(baseline_rows, key=int):
        baseline = _case_metrics(baseline_rows[event_id])
        linked = _case_metrics(linked_rows[event_id])
        if baseline is None or linked is None:
            continue
        if baseline["reference_category_count"] != linked["reference_category_count"]:
            raise ValueError(f"Reference categories changed for event {event_id}")
        per_case.append({
            "event_id": event_id,
            "alarm_only": baseline,
            "saga_linked_guarded": linked,
        })

    variants: dict[str, dict[str, float]] = {}
    for variant in ("alarm_only", "saga_linked_guarded"):
        values = [row[variant] for row in per_case]
        variants[variant] = {
            key: float(np.mean([float(row[key]) for row in values]))
            for key in (
                "reference_precision", "reference_recall", "reference_f1",
                "mentioned_category_count", "non_reference_category_count",
                "stage_coverage", "word_count",
            )
        }

    comparisons = {}
    for metric in (
        "reference_precision", "reference_recall", "reference_f1",
        "mentioned_category_count", "non_reference_category_count",
        "stage_coverage", "word_count",
    ):
        comparisons[metric] = _bootstrap_difference(
            [float(row["alarm_only"][metric]) for row in per_case],
            [float(row["saga_linked_guarded"][metric]) for row in per_case],
            seed=seed,
            replicates=replicates,
        )

    return {
        "schema_version": 1,
        "artifact_type": "hiad_post_outcome_response_selectivity_audit",
        "status": "COMPLETED_POST_OUTCOME_ROBUSTNESS_AUDIT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "alarm_only": "research/hiad_machine_response_benchmark_2026_10_08.json",
            "saga_linked_guarded": (
                "research/hiad_machine_response_guard_recheck_2026_10_08.json"
            ),
            "new_provider_calls": 0,
            "outcomes_known_before_analysis": True,
        },
        "cohort": {
            "retained_event_count": len(baseline_rows),
            "reference_evaluable_event_count": len(per_case),
            "excluded_without_public_action_categories": len(baseline_rows) - len(per_case),
        },
        "variant_summary": variants,
        "paired_differences_saga_minus_alarm_only": comparisons,
        "cases": per_case,
        "interpretation": {
            "f1_direction": (
                "Higher reference F1 means a better balance of matching the coarse "
                "public HIAD action categories and avoiding unreferenced categories."
            ),
            "burden_direction": (
                "Higher mentioned/non-reference category counts and word counts indicate "
                "more information for an operator to process."
            ),
        },
        "claim_boundary": (
            "This is a post-outcome keyword robustness audit on a consumed cohort. "
            "HIAD action prose may be incomplete, so non-reference categories are not "
            "necessarily wrong or unsafe. The result does not establish clinical-style "
            "precision, operator benefit, action correctness, or SAGA safety/effectiveness."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--guard", type=Path, default=DEFAULT_GUARD)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=20261008)
    parser.add_argument("--replicates", type=int, default=10_000)
    args = parser.parse_args()
    result = audit(
        _load(args.benchmark), _load(args.guard),
        seed=args.seed, replicates=args.replicates,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(json.dumps({
        "output": str(args.output),
        "cohort": result["cohort"],
        "variant_summary": result["variant_summary"],
        "f1_difference": result["paired_differences_saga_minus_alarm_only"][
            "reference_f1"
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
