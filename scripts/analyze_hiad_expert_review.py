"""Analyze locked, blinded HIAD expert ratings after allocation is revealed."""

from __future__ import annotations

import argparse
import csv
import hashlib
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


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
    parser.add_argument("--reviewer-qualifications", type=Path, required=True)
    parser.add_argument(
        "--manifest", type=Path,
        help="Collection manifest; defaults to collection_manifest.json beside allocation",
    )
    parser.add_argument(
        "--blind-template", type=Path,
        help="Locked blank rating form; defaults to blind_expert_review.csv beside allocation",
    )
    parser.add_argument("--output", type=Path, default=Path("data/public_validation/results/hiad_decision/analysis"))
    parser.add_argument("--allow-unapproved", action="store_true")
    parser.add_argument(
        "--primary-variant", default="saga-linked",
        help="Non-baseline variant used for the primary paired comparison",
    )
    args = parser.parse_args()

    casebook = json.loads(args.casebook.read_text(encoding="utf-8"))
    unapproved = [
        str(case["event_id"]) for case in casebook["cases"]
        if str(case.get("expert_vignette_approved", "NO")).upper() != "YES"
        or str(case.get("narrative_action_leakage_review", "")).upper() != "PASS"
    ]
    if unapproved and not args.allow_unapproved:
        raise SystemExit(
            "Expert vignette approval is incomplete for event IDs: " + ", ".join(unapproved)
        )
    allocation_rows = _read_csv(args.allocation)
    allocation_codes = [row["response_code"] for row in allocation_rows]
    if len(allocation_codes) != len(set(allocation_codes)):
        raise SystemExit("Duplicate response_code rows are not allowed in allocation")
    allocation = {row["response_code"]: row for row in allocation_rows}
    casebook_ids = {str(case["event_id"]) for case in casebook["cases"]}
    allocation_event_ids = {str(row["event_id"]) for row in allocation_rows}
    if allocation_event_ids != casebook_ids:
        missing = sorted(casebook_ids - allocation_event_ids, key=int)
        extra = sorted(allocation_event_ids - casebook_ids, key=int)
        raise SystemExit(
            f"Allocation/casebook event mismatch; missing={missing}, extra={extra}"
        )

    manifest_path = args.manifest or args.allocation.with_name("collection_manifest.json")
    manifest = None
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_hashes = manifest.get("file_sha256") or {}
        for name, path in (
            ("allocation_key.csv", args.allocation),
            ("casebook_snapshot.json", args.casebook),
        ):
            expected = expected_hashes.get(name)
            if expected and _sha256_file(path) != expected:
                raise SystemExit(f"Locked file hash mismatch: {name}")
        if int(manifest.get("response_count", len(allocation_rows))) != len(allocation_rows):
            raise SystemExit("Allocation row count differs from collection manifest")

    blind_path = args.blind_template or args.allocation.with_name("blind_expert_review.csv")
    blind_template = None
    if blind_path.exists():
        blind_rows = _read_csv(blind_path)
        blind_template = {row["response_code"]: row for row in blind_rows}
        if len(blind_template) != len(blind_rows) or set(blind_template) != set(allocation):
            raise SystemExit("Blind template does not match allocation response codes")
        expected = (manifest or {}).get("file_sha256", {}).get("blind_expert_review.csv")
        if expected and _sha256_file(blind_path) != expected:
            raise SystemExit("Locked file hash mismatch: blind_expert_review.csv")

    ratings = []
    rater_ids = set()
    rating_file_hashes = []
    for path in args.ratings:
        file_rows = _read_csv(path)
        if not file_rows:
            raise SystemExit(f"Rating file is empty: {path}")
        file_rater_ids = {row.get("rater_id", "").strip() for row in file_rows}
        if "" in file_rater_ids or len(file_rater_ids) != 1:
            raise SystemExit(
                f"Each rating file must contain exactly one non-empty rater_id: {path}"
            )
        file_codes = [row.get("response_code", "").strip() for row in file_rows]
        if len(file_codes) != len(set(file_codes)):
            raise SystemExit(f"Duplicate response_code rows in {path}")
        missing_codes = sorted(set(allocation) - set(file_codes))
        extra_codes = sorted(set(file_codes) - set(allocation))
        if missing_codes or extra_codes:
            raise SystemExit(
                f"Incomplete rating file {path}; missing={missing_codes}, extra={extra_codes}"
            )
        rating_file_hashes.append({"file": path.name, "sha256": _sha256_file(path)})
        for row in file_rows:
            code = row["response_code"]
            if code not in allocation:
                raise SystemExit(f"Unknown response code {code} in {path}")
            if blind_template is not None:
                locked = blind_template[code]
                for field in ("event_id", "response_text"):
                    if row.get(field, "") != locked.get(field, ""):
                        raise SystemExit(
                            f"Locked {field} was changed for {code} in {path}"
                        )
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
            if any(parsed[field] == 1 for field in BINARY_FIELDS) and not row.get(
                "comments", ""
            ).strip():
                raise SystemExit(
                    f"A comment is required for omission/unsafe mark on {code}"
                )
            parsed["composite_score"] = float(np.mean([parsed[field] for field in SCORE_FIELDS]))
            ratings.append(parsed)
            rater_ids.add(rater_id)
    review_keys = [(row["rater_id"], row["response_code"]) for row in ratings]
    if len(review_keys) != len(set(review_keys)):
        raise SystemExit("Duplicate (rater_id, response_code) rows are not allowed")
    if len(rater_ids) < 3:
        raise SystemExit("At least three independent raters are required")

    qualification_rows = _read_csv(args.reviewer_qualifications)
    qualification_codes = [row.get("reviewer_code", "").strip() for row in qualification_rows]
    if len(qualification_codes) != len(set(qualification_codes)) or "" in qualification_codes:
        raise SystemExit("Reviewer qualification codes must be non-empty and unique")
    if set(qualification_codes) != rater_ids:
        raise SystemExit(
            "Reviewer qualification codes do not match completed rating files"
        )
    experience_fields = (
        "hydrogen_safety_experience", "hazop_experience",
        "emergency_response_experience", "hrs_operating_experience",
    )
    parsed_qualifications = []
    for row in qualification_rows:
        code = row["reviewer_code"].strip()
        role = row.get("professional_role", "").strip()
        if not role:
            raise SystemExit(f"Reviewer {code} has no professional role")
        try:
            years = float(row.get("relevant_years_experience", ""))
        except ValueError as exc:
            raise SystemExit(f"Reviewer {code} has invalid relevant experience years") from exc
        documented_qualification = bool(row.get("qualifications", "").strip())
        if years < 3 and not documented_qualification:
            raise SystemExit(
                f"Reviewer {code} needs at least three years of relevant experience "
                "or a documented relevant qualification"
            )
        meaningful_experience = [
            field for field in experience_fields
            if row.get(field, "").strip().lower() not in {"", "no", "none", "0", "n/a"}
        ]
        if not meaningful_experience:
            raise SystemExit(f"Reviewer {code} has no documented relevant experience category")
        for field in (
            "prior_system_familiarity", "conflict_of_interest",
            "conflict_management_or_none", "rating_completed_utc",
        ):
            if not row.get(field, "").strip():
                raise SystemExit(f"Reviewer {code} has no value for {field}")
        if row.get("independence_confirmed_yes_no", "").strip().lower() != "yes":
            raise SystemExit(f"Reviewer {code} independence is not confirmed")
        if row.get("ethics_information_provided_yes_no", "").strip().lower() != "yes":
            raise SystemExit(f"Reviewer {code} ethics information receipt is not confirmed")
        parsed_qualifications.append({
            "reviewer_code": code,
            "years": years,
            "documented_qualification": documented_qualification,
            "experience_fields": meaningful_experience,
            "prior_system_familiarity": row["prior_system_familiarity"].strip(),
        })

    design_counts: dict[tuple[str, str], int] = {}
    for row in allocation_rows:
        design_counts[(str(row["event_id"]), row["variant"])] = (
            design_counts.get((str(row["event_id"]), row["variant"]), 0) + 1
        )
    design_variants = sorted({variant for _, variant in design_counts})
    for event_id in sorted(casebook_ids, key=int):
        for variant in design_variants:
            count = design_counts.get((event_id, variant), 0)
            expected = 1 if variant == "alarm-only" else None
            if expected is not None and count != expected:
                raise SystemExit(
                    f"Expected one alarm-only response for event {event_id}; got {count}"
                )
    for variant in (item for item in design_variants if item != "alarm-only"):
        counts = {design_counts.get((event_id, variant), 0) for event_id in casebook_ids}
        if len(counts) != 1 or next(iter(counts)) < 1:
            raise SystemExit(f"Inconsistent repeat count for variant {variant}: {sorted(counts)}")

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
        calls = [row for row in allocation_rows if row["variant"] == variant]
        latencies = [
            float(row.get("latency_ms") or 0.0) for row in calls
        ]
        variant_summary[variant] = {
            "rating_count": len(rows),
            "response_call_count": len(calls),
            "composite_mean": float(np.mean([row["composite_score"] for row in rows])),
            "critical_omission_rate": float(np.mean([row["critical_omission_0_1"] for row in rows])),
            "unsafe_advice_rate": float(np.mean([row["unsafe_advice_0_1"] for row in rows])),
            "failed_call_rate": float(np.mean([
                _as_bool(row.get("call_failed", False)) for row in calls
            ])),
            "latency_ms_mean": float(np.mean(latencies)),
        }
    report = {
        "event_count": len(event_ids),
        "rater_count": len(rater_ids),
        "variant_summary": variant_summary,
        "primary_variant": args.primary_variant,
        "paired_composite_differences_vs_alarm": paired_comparisons,
        "inter_rater_agreement": agreement,
        "reviewer_qualification_summary": {
            "reviewer_count": len(parsed_qualifications),
            "relevant_years_min": float(min(item["years"] for item in parsed_qualifications)),
            "relevant_years_median": float(np.median([
                item["years"] for item in parsed_qualifications
            ])),
            "relevant_years_max": float(max(item["years"] for item in parsed_qualifications)),
            "documented_qualification_count": sum(
                item["documented_qualification"] for item in parsed_qualifications
            ),
            "experience_category_counts": {
                field: sum(
                    field in item["experience_fields"] for item in parsed_qualifications
                )
                for field in experience_fields
            },
        },
        "lock": {
            "allocation_sha256": _sha256_file(args.allocation),
            "casebook_sha256": _sha256_file(args.casebook),
            "blind_template_sha256": (
                _sha256_file(blind_path) if blind_template is not None else None
            ),
            "manifest": manifest_path.name if manifest is not None else None,
            "rating_files": rating_file_hashes,
            "reviewer_qualifications_sha256": _sha256_file(
                args.reviewer_qualifications
            ),
        },
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "expert_review_analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# HIAD blinded expert-review analysis", "",
        f"Events: {len(event_ids)}; raters: {len(rater_ids)}", "",
        "| Variant | Composite mean | Critical omission | Unsafe advice | Failed calls | Mean latency (ms) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for variant, summary in variant_summary.items():
        lines.append(
            f"| {variant} | {summary['composite_mean']:.3f} | "
            f"{100 * summary['critical_omission_rate']:.1f}% | "
            f"{100 * summary['unsafe_advice_rate']:.1f}% | "
            f"{100 * summary['failed_call_rate']:.1f}% | "
            f"{summary['latency_ms_mean']:.1f} |"
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
