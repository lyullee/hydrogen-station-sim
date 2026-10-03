"""Analyze locked, blinded HIAD expert ratings after allocation is revealed."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon


SCORE_FIELDS = (
    "situation_accuracy_1_5",
    "immediate_action_correctness_1_5",
    "priority_order_1_5",
    "stabilization_restart_1_5",
    "prevention_quality_1_5",
    "evidence_grounding_1_5",
    "operator_usability_1_5",
)
BINARY_FIELDS = ("critical_omission_0_1", "unsafe_advice_0_1")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _quadratic_weighted_kappa(first: list[int], second: list[int]) -> float:
    categories = np.arange(1, 6)
    observed = np.zeros((5, 5), dtype=float)
    for a, b in zip(first, second):
        observed[a - 1, b - 1] += 1
    observed /= max(observed.sum(), 1.0)
    expected = np.outer(
        np.bincount(first, minlength=6)[1:] / len(first),
        np.bincount(second, minlength=6)[1:] / len(second),
    )
    weights = ((categories[:, None] - categories[None, :]) / 4.0) ** 2
    denominator = float(np.sum(weights * expected))
    return 1.0 - float(np.sum(weights * observed)) / denominator if denominator else 1.0


def _bootstrap_paired_ci(differences: np.ndarray, seed: int = 2601) -> list[float]:
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(differences), size=(10000, len(differences)))
    means = np.mean(differences[indices], axis=1)
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allocation", type=Path, required=True)
    parser.add_argument("--casebook", type=Path, required=True)
    parser.add_argument("--ratings", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=Path("data/public_validation/results/hiad_decision/analysis"))
    parser.add_argument("--allow-unapproved", action="store_true")
    parser.add_argument(
        "--primary-variant", default="saga-linked",
        help="Non-baseline variant used for the primary paired comparison",
    )
    args = parser.parse_args()

    casebook = json.loads(args.casebook.read_text(encoding="utf-8"))
    unapproved = [
        case["event_id"] for case in casebook["cases"]
        if str(case.get("expert_vignette_approved", "NO")).upper() != "YES"
    ]
    if unapproved and not args.allow_unapproved:
        raise SystemExit(
            "Expert vignette approval is incomplete for event IDs: " + ", ".join(unapproved)
        )
    allocation = {row["response_code"]: row for row in _read_csv(args.allocation)}
    ratings = []
    rater_ids = set()
    for path in args.ratings:
        for row in _read_csv(path):
            code = row["response_code"]
            if code not in allocation:
                raise SystemExit(f"Unknown response code {code} in {path}")
            rater_id = row.get("rater_id", "").strip()
            if not rater_id:
                raise SystemExit(f"Missing rater_id for {code} in {path}")
            parsed = {**allocation[code], "rater_id": rater_id}
            for field in SCORE_FIELDS:
                value = int(row[field])
                if not 1 <= value <= 5:
                    raise SystemExit(f"{field} outside 1..5 for {code}")
                parsed[field] = value
            for field in BINARY_FIELDS:
                value = int(row[field])
                if value not in (0, 1):
                    raise SystemExit(f"{field} outside 0..1 for {code}")
                parsed[field] = value
            parsed["composite_score"] = float(np.mean([parsed[field] for field in SCORE_FIELDS]))
            ratings.append(parsed)
            rater_ids.add(rater_id)
    review_keys = [(row["rater_id"], row["response_code"]) for row in ratings]
    if len(review_keys) != len(set(review_keys)):
        raise SystemExit("Duplicate (rater_id, response_code) rows are not allowed")
    if len(rater_ids) < 2:
        raise SystemExit("At least two independent raters are required")

    per_event: dict[tuple[str, str], list[float]] = {}
    for row in ratings:
        per_event.setdefault((row["event_id"], row["variant"]), []).append(row["composite_score"])
    event_ids = sorted({key[0] for key in per_event}, key=int)
    variants = sorted({key[1] for key in per_event})
    comparators = [variant for variant in variants if variant != "alarm-only"]
    if not comparators:
        raise SystemExit("At least one non-baseline response variant is required")
    if args.primary_variant not in comparators:
        raise SystemExit(
            f"Primary variant {args.primary_variant!r} is unavailable; choose one of "
            + ", ".join(comparators)
        )
    missing = [
        event_id for event_id in event_ids
        if any((event_id, variant) not in per_event for variant in variants)
    ]
    if missing:
        raise SystemExit("Missing paired variants for event IDs: " + ", ".join(missing))
    baseline = np.asarray([np.mean(per_event[(event_id, "alarm-only")]) for event_id in event_ids])
    paired_comparisons = {}
    for variant in comparators:
        candidate = np.asarray([
            np.mean(per_event[(event_id, variant)]) for event_id in event_ids
        ])
        differences = candidate - baseline
        test = wilcoxon(differences, alternative="two-sided", zero_method="zsplit")
        paired_comparisons[variant] = {
            "mean": float(np.mean(differences)),
            "median": float(np.median(differences)),
            "bootstrap_95_ci": _bootstrap_paired_ci(differences),
            "wilcoxon_statistic": float(test.statistic),
            "wilcoxon_p_value": float(test.pvalue),
        }

    agreement = {}
    ordered_raters = sorted(rater_ids)
    for field in SCORE_FIELDS:
        pair_values = []
        for left_index, left in enumerate(ordered_raters):
            for right in ordered_raters[left_index + 1:]:
                left_rows = {row["response_code"]: row for row in ratings if row["rater_id"] == left}
                right_rows = {row["response_code"]: row for row in ratings if row["rater_id"] == right}
                common = sorted(set(left_rows) & set(right_rows))
                if not common:
                    continue
                pair_values.append(_quadratic_weighted_kappa(
                    [left_rows[code][field] for code in common],
                    [right_rows[code][field] for code in common],
                ))
        agreement[field] = {
            "mean_pairwise_quadratic_weighted_kappa": float(np.mean(pair_values)),
            "pair_count": len(pair_values),
        }

    variant_summary = {}
    for variant in variants:
        rows = [row for row in ratings if row["variant"] == variant]
        variant_summary[variant] = {
            "rating_count": len(rows),
            "composite_mean": float(np.mean([row["composite_score"] for row in rows])),
            "critical_omission_rate": float(np.mean([row["critical_omission_0_1"] for row in rows])),
            "unsafe_advice_rate": float(np.mean([row["unsafe_advice_0_1"] for row in rows])),
        }
    report = {
        "event_count": len(event_ids),
        "rater_count": len(rater_ids),
        "variant_summary": variant_summary,
        "primary_variant": args.primary_variant,
        "paired_composite_differences_vs_alarm": paired_comparisons,
        "inter_rater_agreement": agreement,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "expert_review_analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# HIAD blinded expert-review analysis", "",
        f"Events: {len(event_ids)}; raters: {len(rater_ids)}", "",
        "| Variant | Composite mean | Critical omission | Unsafe advice |",
        "|---|---:|---:|---:|",
    ]
    for variant, summary in variant_summary.items():
        lines.append(
            f"| {variant} | {summary['composite_mean']:.3f} | "
            f"{100 * summary['critical_omission_rate']:.1f}% | "
            f"{100 * summary['unsafe_advice_rate']:.1f}% |"
        )
    lines.extend(["", "## Paired comparisons versus alarm-only", ""])
    for variant, paired in paired_comparisons.items():
        lines.append(
            f"- {variant}: mean {paired['mean']:.3f} "
            f"(bootstrap 95% CI {paired['bootstrap_95_ci'][0]:.3f} to "
            f"{paired['bootstrap_95_ci'][1]:.3f}); "
            f"Wilcoxon p={paired['wilcoxon_p_value']:.4g}."
        )
    lines.extend([
        "", "## Inter-rater agreement", "",
        "| Criterion | Mean pairwise quadratic-weighted kappa |",
        "|---|---:|",
    ])
    for field, result in agreement.items():
        lines.append(f"| {field} | {result['mean_pairwise_quadratic_weighted_kappa']:.3f} |")
    (args.output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output / "report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
