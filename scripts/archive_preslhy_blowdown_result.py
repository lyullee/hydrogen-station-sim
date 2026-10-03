"""Archive the frozen PRESLHY result as reviewable research evidence."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path


EXPECTED_PACKAGES = {
    "PRE3P1A_KIT_D05_300K_DATA.zip",
    "PRE3P1A_KIT_D1_300K_DATA.zip",
    "PRE3P1A_KIT_D2_300K_DATA.zip",
    "PRE3P1A_KIT_D4_300K_DATA.zip",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _group_summary(cases: list[dict], key: str) -> dict[str, dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for case in cases:
        groups[str(case[key])].append(case)
    return {
        name: {
            "case_count": len(items),
            "pressure_screen_pass_count": sum(
                bool(item["pressure_screen_pass"]) for item in items
            ),
            "half_time_screen_pass_count": sum(
                bool(item["half_time_screen_pass"]) for item in items
            ),
            "joint_primary_pass_count": sum(
                bool(item["joint_primary_screen_pass"]) for item in items
            ),
            "joint_primary_pass_fraction": sum(
                bool(item["joint_primary_screen_pass"]) for item in items
            ) / len(items),
            "evaluation_error_count": sum(
                bool(item.get("evaluation_error")) for item in items
            ),
        }
        for name, items in sorted(groups.items())
    }


def archive_result(validation: dict, protocol: dict, protocol_sha256: str) -> dict:
    packages = {item["name"] for item in validation["packages"]}
    if packages != EXPECTED_PACKAGES:
        raise RuntimeError(f"unexpected PRESLHY package set: {sorted(packages)}")
    if validation["protocol_sha256"] != protocol_sha256:
        raise RuntimeError("validation result does not match the current frozen protocol")
    if protocol["source"]["outcomes_accessed_before_freeze"] is not False:
        raise RuntimeError("protocol was not frozen before numerical outcome access")

    cases = validation["cases"]
    errors = Counter(
        item["evaluation_error"] for item in cases if item.get("evaluation_error")
    )
    numerical = [item for item in cases if not item.get("evaluation_error")]
    numerical_pass_fraction = (
        sum(bool(item["joint_primary_screen_pass"]) for item in numerical)
        / len(numerical)
        if numerical
        else math.nan
    )
    aggregate = validation["aggregate"]
    claim_supported = aggregate[
        "ambient_direct_aperture_blowdown_claim_supported"
    ]
    return {
        "schema_version": 1,
        "evidence_type": "prospectively specified independent external validation",
        "source": protocol["source"],
        "claim_boundary": validation["claim_boundary"],
        "protocol_path": validation["protocol_path"],
        "protocol_sha256": validation["protocol_sha256"],
        "runner_git_commit": validation["runner_git_commit"],
        "generated_at": validation["generated_at"],
        "packages": validation["packages"],
        "eligibility": validation["eligibility"],
        "aggregate": aggregate,
        "decision": {
            "status": "PASS" if claim_supported else "FAIL",
            "predeclared_threshold": aggregate["claim_threshold"],
            "claim_supported": claim_supported,
            "interpretation": (
                "The frozen ambient direct-aperture source-depletion model met "
                "the predeclared external-validation decision rule."
                if claim_supported
                else "The frozen ambient direct-aperture source-depletion model "
                "did not meet the predeclared external-validation decision rule; "
                "the validated-blowdown claim is prohibited for this revision."
            ),
        },
        "failure_accounting": {
            "eligible_case_count": len(cases),
            "evaluation_error_count": sum(errors.values()),
            "evaluation_errors_by_message": dict(sorted(errors.items())),
            "numerically_evaluated_case_count": len(numerical),
            "descriptive_numerical_only_joint_pass_fraction": numerical_pass_fraction,
            "decision_uses_all_eligible_cases": True,
        },
        "stratified": {
            "by_nozzle_diameter_mm": _group_summary(cases, "nozzle_diameter_mm"),
            "by_initial_pressure_group": _group_summary(cases, "pressure_group"),
        },
        "cases": cases,
        "exclusions": validation["exclusions"],
        "development_note": (
            "Post-outcome model development must preserve this negative result. "
            "Any revised thermophysical domain, heat-transfer model, valve/line "
            "model or coefficient requires a new version and independent holdout; "
            "the present cases cannot become an undisclosed validation set."
        ),
    }


def _format(value, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def markdown_report(report: dict) -> str:
    aggregate = report["aggregate"]
    eligibility = report["eligibility"]
    failures = report["failure_accounting"]
    ci = aggregate["bootstrap_95_percent_ci"]
    lines = [
        "# PRESLHY ambient blowdown external validation", "",
        f"- Decision: **{report['decision']['status']}**",
        f"- Eligible cases: **{eligibility['eligible_cases']}**; excluded: "
        f"**{eligibility['excluded_workbooks']}**",
        f"- Joint primary pass fraction: **{aggregate['joint_primary_pass_fraction']:.1%}** "
        f"(case-bootstrap 95% CI {ci[0]:.1%}–{ci[1]:.1%})",
        f"- Predeclared threshold: **{aggregate['claim_threshold']:.0%}**",
        f"- Evaluation errors retained as failures: **{failures['evaluation_error_count']}**",
        f"- Protocol SHA-256: `{report['protocol_sha256']}`",
        f"- Runner commit: `{report['runner_git_commit']}`", "",
        report["decision"]["interpretation"], "",
        "## Stratified result", "",
        "| Stratum | Cases | Pressure pass | Half-time pass | Joint pass | Errors |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for dimension, groups in report["stratified"].items():
        for name, item in groups.items():
            lines.append(
                f"| {dimension}: {name} | {item['case_count']} | "
                f"{item['pressure_screen_pass_count']} | "
                f"{item['half_time_screen_pass_count']} | "
                f"{item['joint_primary_pass_count']} | "
                f"{item['evaluation_error_count']} |"
            )
    lines.extend([
        "", "## Case-level result", "",
        "| Case | d (mm) | P0 (bar abs) | Group | P NRMSE (%) | t50 error (%) | Joint | Error |",
        "|---|---:|---:|---|---:|---:|---|---|",
    ])
    for item in report["cases"]:
        lines.append(
            f"| {item['case_id']} | {item['nozzle_diameter_mm']:g} | "
            f"{item['initial_pressure_bar_abs']:.3f} | {item['pressure_group']} | "
            f"{_format(item['pressure_nrmse_percent_initial_absolute_pressure'])} | "
            f"{_format(item['time_to_50_percent_gauge_relative_error_percent'])} | "
            f"{'PASS' if item['joint_primary_screen_pass'] else 'FAIL'} | "
            f"{item.get('evaluation_error', '')} |"
        )
    lines.extend([
        "", "## Scope and interpretation", "",
        report["claim_boundary"], "",
        report["development_note"], "",
        "The numerical-only pass fraction is descriptive and does not replace "
        "the predeclared decision, which includes every eligible model failure.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validation",
        type=Path,
        default=Path("data/public_validation/results/preslhy_blowdown/validation.json"),
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("research/preslhy_blowdown_validation_protocol.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("research/preslhy_blowdown_external_validation.json"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("research/PRESLHY_BLOWDOWN_EXTERNAL_VALIDATION.md"),
    )
    args = parser.parse_args()
    validation = json.loads(args.validation.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    report = archive_result(validation, protocol, _sha256(args.protocol))
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.report_output.write_text(
        markdown_report(report), encoding="utf-8", newline="\n"
    )
    print(args.json_output)
    print(args.report_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
