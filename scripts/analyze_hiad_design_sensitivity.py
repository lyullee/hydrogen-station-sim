"""Pre-outcome design sensitivity for the fixed 24-event HIAD holdout."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, wilcoxon


DEFAULT_EFFECTS = (0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0)


def simulate_power(
    *, event_count: int = 24, simulations: int = 20_000,
    effects: tuple[float, ...] = DEFAULT_EFFECTS, seed: int = 2601,
    alpha: float = 0.05,
) -> list[dict[str, float]]:
    if event_count < 5 or simulations < 1_000:
        raise ValueError("event_count must be >=5 and simulations >=1000")
    rng = np.random.default_rng(seed)
    rows = []
    for effect in effects:
        differences = rng.normal(
            loc=float(effect), scale=1.0, size=(simulations, event_count)
        )
        p_values = wilcoxon(
            differences, axis=1, alternative="two-sided", method="approx"
        ).pvalue
        power = float(np.mean(p_values < alpha))
        monte_carlo_se = float(np.sqrt(power * (1.0 - power) / simulations))
        rows.append({
            "standardized_paired_effect": float(effect),
            "estimated_power": power,
            "monte_carlo_se": monte_carlo_se,
        })
    return rows


def _minimum_effect_for_power(rows: list[dict[str, float]], target: float) -> float | None:
    qualifying = [
        row["standardized_paired_effect"]
        for row in rows if row["estimated_power"] >= target
    ]
    return min(qualifying) if qualifying else None


def build_report(event_count: int, simulations: int, seed: int) -> dict[str, object]:
    rows = simulate_power(
        event_count=event_count, simulations=simulations, seed=seed
    )
    zero_event_interval = binomtest(0, event_count).proportion_ci(
        confidence_level=0.95, method="exact"
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_timing": "before holdout response collection and expert rating",
        "event_count": event_count,
        "simulations_per_effect": simulations,
        "seed": seed,
        "alpha_two_sided": 0.05,
        "data_generating_assumption": (
            "independent normally distributed paired event differences with unit "
            "standard deviation; Wilcoxon signed-rank test using normal approximation"
        ),
        "power_by_standardized_paired_effect": rows,
        "smallest_grid_effect_with_at_least_80_percent_power": (
            _minimum_effect_for_power(rows, 0.80)
        ),
        "zero_unsafe_event_exact_two_sided_95_percent_upper_bound": float(
            zero_event_interval.high
        ),
        "zero_event_bound_unit": "event-level Bernoulli rate",
        "interpretation_limits": [
            "This is a design sensitivity analysis, not an observed effect estimate.",
            "The 24-event holdout is fixed by the eligible public incident population and frozen split.",
            "Normal paired differences are a transparent assumption; bounded and tied expert scores may yield different power.",
            "Repeated generations and reviewer scores are averaged within event; they do not increase the inferential event count.",
            "Even zero unsafe events cannot establish zero risk; the exact upper confidence bound must be reported.",
        ],
    }


def _markdown(report: dict[str, object]) -> str:
    lines = [
        "# HIAD expert-study design sensitivity", "",
        "This calculation was frozen before holdout response collection or expert rating.",
        "It quantifies limitations of the fixed 24-event design; it is not a study result.", "",
        "| Standardized paired effect | Estimated power | Monte Carlo SE |",
        "|---:|---:|---:|",
    ]
    for row in report["power_by_standardized_paired_effect"]:
        lines.append(
            f"| {row['standardized_paired_effect']:.2f} | "
            f"{100 * row['estimated_power']:.1f}% | "
            f"{100 * row['monte_carlo_se']:.2f}% |"
        )
    effect = report["smallest_grid_effect_with_at_least_80_percent_power"]
    lines.extend([
        "", "## Interpretation", "",
        f"On the prespecified grid, the smallest standardized paired effect reaching "
        f"at least 80% simulated power is **{effect if effect is not None else 'not reached'}**.",
        f"If zero of 24 events contain unsafe advice, the exact two-sided 95% upper "
        f"bound for the event-level rate remains **"
        f"{100 * report['zero_unsafe_event_exact_two_sided_95_percent_upper_bound']:.1f}%**.",
        "Repeated generations and multiple reviewers improve measurement stability but do "
        "not change the inferential event count of 24.", "", "## Assumptions and limits", "",
    ])
    lines.extend(f"- {item}" for item in report["interpretation_limits"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-count", type=int, default=24)
    parser.add_argument("--simulations", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=2601)
    parser.add_argument(
        "--json-output", type=Path,
        default=Path("research/hiad_design_sensitivity.json"),
    )
    parser.add_argument(
        "--report-output", type=Path,
        default=Path("research/HIAD_DESIGN_SENSITIVITY.md"),
    )
    args = parser.parse_args()
    report = build_report(args.event_count, args.simulations, args.seed)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    args.report_output.write_text(
        _markdown(report), encoding="utf-8", newline="\n"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
