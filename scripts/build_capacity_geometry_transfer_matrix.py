"""Build a claim-bounded cross-dataset geometry-transfer matrix.

The MC Default and NREL H2FillS geometry diagnostics were run after their
numeric outcomes had already been accessed.  This script only synthesizes
those existing records.  It must never be interpreted as a new holdout or as
permission to change the runtime geometry default.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def build() -> dict:
    mc_path = "research/mc_geometry_transfer_diagnostic_2026_10_08.json"
    nrel_path = "research/nrel_h2fills_geometry_sensitivity_2026_10_12.json"
    mc = _read(mc_path)
    nrel = _read(nrel_path)
    mc_variants = []
    for run in mc["runs"]:
        mc_variants.append({
            "rule": run["geometry_rule"],
            "effective_volume_multiplier": run["effective_volume_multiplier"],
            "joint_pass_count": run["joint_screening_pass_count"],
            "case_count": run["case_count"],
            "aggregate": run["aggregate"],
            "source_provenance": run["rule_provenance"],
        })
    nrel_variants = []
    for name, variant in nrel["variants"].items():
        nrel_variants.append({
            "rule": name,
            "effective_volume_multiplier": variant["effective_volume_multiplier"],
            "joint_pass_count": variant["screening_pass_count"],
            "case_count": nrel["source"]["tank_count"],
            "aggregate": {
                "pressure_rmse_mpa": variant["pressure_rmse_mpa"],
                "temperature_rmse_c": variant["temperature_rmse_c"],
                "mass_final_abs_error_kg": variant["mass_final_error_kg"],
            },
            "source_provenance": variant.get("base_volume_m3"),
        })
    return {
        "schema_version": 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _commit(),
        "artifact_type": "cross_dataset_capacity_geometry_transfer_matrix",
        "evidence_role": "post_outcome_development_synthesis_only",
        "outcomes_accessed_before_synthesis": True,
        "parameter_fitting": False,
        "runtime_geometry_changed": False,
        "datasets": [
            {
                "dataset": "Powertech MC Default vehicle-tank boundary",
                "source_artifact": mc_path,
                "case_count": 8,
                "screening_limits": mc["screening_limits"],
                "variants": mc_variants,
            },
            {
                "dataset": "NREL H2FillS HDVS Type-IV tank boundary",
                "source_artifact": nrel_path,
                "case_count": nrel["source"]["tank_count"],
                "screening_limits": nrel["screening_limits"],
                "variants": nrel_variants,
            },
        ],
        "findings": [
            "The globally fitted tables-method multiplier does not transfer to the MC Default vessel set: 0/8 joint screens remained after the frozen rule, while two non-fitted geometry rules reached only 4/8.",
            "The NREL post-access sample is highly sensitive to the declared capacity/EOS geometry basis: both capacity-EOS variants reached 7/7, while the legacy nominal-volume rule reached 0/7.",
            "No single post-outcome variant may be selected as a universal production rule. The evidence supports requiring source-declared internal volume or a predeclared capacity/EOS rule before a new untouched holdout.",
        ],
        "next_required_evidence": [
            "At least one new untouched tank-and-hose cohort with declared capacity, internal volume or traceable geometry, inlet pressure/temperature, common time base and transferred mass.",
            "Freeze the geometry rule and screening limits before numeric outcomes are opened.",
            "Retain all cases and do not promote a post-outcome sensitivity to the validation gate.",
        ],
        "claim_boundary": "This matrix explains geometry-transfer risk and preserves negative evidence. It is not an external validation result, does not revise the frozen MC or NREL outcomes, does not select a runtime default and cannot establish station, vehicle-controller or field-safety validity.",
    }


def markdown(report: dict) -> str:
    lines = [
        "# Cross-dataset capacity/EOS geometry transfer matrix",
        "",
        "This is a post-outcome development synthesis. It does not promote a",
        "validation gate or change the runtime geometry rule.",
        "",
        "| Dataset | Variant | Effective-volume multiplier | Joint pass | Cases |",
        "|---|---|---:|---:|---:|",
    ]
    for dataset in report["datasets"]:
        for variant in dataset["variants"]:
            lines.append(
                f"| {dataset['dataset']} | {variant['rule']} | "
                f"{variant['effective_volume_multiplier']:.6f} | "
                f"{variant['joint_pass_count']} | {variant['case_count']} |"
            )
    lines.extend(["", "## Findings", ""])
    lines.extend(f"- {finding}" for finding in report["findings"])
    lines.extend(["", "## Required next evidence", ""])
    lines.extend(f"- {item}" for item in report["next_required_evidence"])
    lines.extend(["", report["claim_boundary"], ""])
    return "\n".join(lines)


def main() -> int:
    report = build()
    json_path = ROOT / "research/capacity_geometry_transfer_matrix_2026_10_12.json"
    md_path = ROOT / "research/CAPACITY_GEOMETRY_TRANSFER_MATRIX_2026_10_12.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    md_path.write_text(markdown(report), encoding="utf-8", newline="\n")
    print(json.dumps({
        "datasets": len(report["datasets"]),
        "variants": sum(len(item["variants"]) for item in report["datasets"]),
        "runtime_geometry_changed": report["runtime_geometry_changed"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
