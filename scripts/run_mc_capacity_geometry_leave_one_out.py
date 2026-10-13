"""Evaluate a transferable Type-IV volume rule by leave-one-case-out replay.

The eight public MC Default cases were inspected before this diagnostic was
created.  This is therefore a post-outcome, within-campaign development study,
not an external or prospective validation.  Each fold derives one global
effective-volume ratio from the other seven cases only, then replays the held
out case with the existing frozen thermal coefficient and measured boundaries.
No result is promoted to the runtime model.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import numpy as np

from h2station.tabulated import PropsSI
from run_mc_tank_boundary_diagnostic import _read_csv, run_case


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED = ROOT / "data/public_validation/processed"
DEFAULT_PROTOCOL = ROOT / "research/mc_default_external_holdout_protocol.json"
DEFAULT_BASELINE = ROOT / "research/mc_tank_boundary_diagnostic_2026_10_05.json"
DEFAULT_OUTPUT = ROOT / "research/mc_capacity_geometry_leave_one_out_2026_10_14.json"
DEFAULT_REPORT = ROOT / "research/MC_CAPACITY_GEOMETRY_LEAVE_ONE_OUT_2026_10_14.md"


def _git_commit() -> str:
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _inferred_volume_ratio(
    summary: dict[str, str], rows: list[dict[str, str]]
) -> dict[str, float]:
    time_s = np.asarray([float(row["time_s"]) for row in rows], dtype=float)
    flow_kg_s = np.asarray(
        [float(row["mass_flow_g_s"]) for row in rows], dtype=float
    ) / 1000.0
    pressure_pa = np.asarray(
        [float(row["pressure_mpa"]) for row in rows], dtype=float
    ) * 1.0e6
    temperature_k = np.asarray(
        [float(row["tank_temperature_mean_c"]) for row in rows], dtype=float
    ) + 273.15
    initial_density = float(
        PropsSI("Dmass", "P", pressure_pa[0], "T", temperature_k[0], "Hydrogen")
    )
    final_density = float(
        PropsSI("Dmass", "P", pressure_pa[-1], "T", temperature_k[-1], "Hydrogen")
    )
    density_change = final_density - initial_density
    if density_change <= 0.0:
        raise ValueError(f"{summary['case_id']}: non-positive density change")
    transferred_mass_kg = float(np.trapezoid(flow_kg_s, time_s))
    if transferred_mass_kg <= 0.0:
        raise ValueError(f"{summary['case_id']}: non-positive transferred mass")
    inferred_volume_m3 = transferred_mass_kg / density_change
    base_volume_m3 = 0.122 * float(summary["tank_capacity_kg"]) / 4.7
    return {
        "transferred_mass_kg": transferred_mass_kg,
        "inferred_volume_m3": inferred_volume_m3,
        "base_volume_m3": base_volume_m3,
        "inferred_volume_ratio": inferred_volume_m3 / base_volume_m3,
    }


def _mean(rows: list[dict[str, Any]], key: str, *, absolute: bool = False) -> float:
    values = [abs(float(row[key])) if absolute else float(row[key]) for row in rows]
    return float(np.mean(values))


def build_report(
    processed: Path = DEFAULT_PROCESSED,
    protocol_path: Path = DEFAULT_PROTOCOL,
    baseline_path: Path = DEFAULT_BASELINE,
) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    summaries = {
        row["source_member"]: row
        for row in _read_csv(processed / "mc_default_cases.csv")
    }
    selected = list(protocol["selected_workbooks"])
    if len(selected) != 8 or len(set(selected)) != len(selected):
        raise ValueError("MC grouped cross-validation requires eight unique cases")
    traces: dict[str, list[dict[str, str]]] = {}
    trace_paths: dict[str, Path] = {}
    volume_diagnostics: dict[str, dict[str, float]] = {}
    for source_member in selected:
        summary = summaries[source_member]
        trace_path = processed / "mc_default_traces" / f"{summary['case_id']}.csv"
        rows = _read_csv(trace_path)
        traces[source_member] = rows
        trace_paths[source_member] = trace_path
        volume_diagnostics[source_member] = _inferred_volume_ratio(summary, rows)

    fixed_ua = float(protocol["frozen_model"]["gas_liner_ua_multiplier"])
    folds: list[dict[str, Any]] = []
    for held_out_member in selected:
        training_members = [item for item in selected if item != held_out_member]
        training_ratios = [
            volume_diagnostics[item]["inferred_volume_ratio"]
            for item in training_members
        ]
        volume_multiplier = float(np.median(training_ratios))
        summary = summaries[held_out_member]
        replay = run_case(
            summary,
            traces[held_out_member],
            {
                "effective_volume_multiplier": volume_multiplier,
                "gas_liner_ua_multiplier": fixed_ua,
            },
            source_pressure_column="pressure_mpa",
        )
        folds.append(
            {
                "fold_id": f"holdout_{summary['case_id']}",
                "held_out_case_id": summary["case_id"],
                "training_case_ids": [summaries[item]["case_id"] for item in training_members],
                "training_case_count": len(training_members),
                "training_volume_ratio_median": volume_multiplier,
                "held_out_volume_ratio_for_scoring_only": volume_diagnostics[
                    held_out_member
                ]["inferred_volume_ratio"],
                "held_out_volume_ratio_used_for_training": False,
                "fixed_gas_liner_ua_multiplier": fixed_ua,
                "pressure_rmse_mpa": replay["pressure_rmse_mpa"],
                "temperature_rmse_c": replay["temperature_rmse_c"],
                "soc_rmse_percentage_points": replay[
                    "soc_rmse_percentage_points"
                ],
                "soc_final_error_percentage_points": replay[
                    "soc_final_error_percentage_points"
                ],
                "joint_screening_pass": replay["screening_pass"],
            }
        )

    aggregate = {
        "fold_count": len(folds),
        "joint_screening_pass_count": sum(
            bool(row["joint_screening_pass"]) for row in folds
        ),
        "joint_screening_pass_fraction": float(
            np.mean([row["joint_screening_pass"] for row in folds])
        ),
        "pressure_rmse_mpa_mean": _mean(folds, "pressure_rmse_mpa"),
        "temperature_rmse_c_mean": _mean(folds, "temperature_rmse_c"),
        "soc_rmse_percentage_points_mean": _mean(
            folds, "soc_rmse_percentage_points"
        ),
        "soc_final_abs_error_percentage_points_mean": _mean(
            folds, "soc_final_error_percentage_points", absolute=True
        ),
        "training_volume_ratio_median_min": min(
            row["training_volume_ratio_median"] for row in folds
        ),
        "training_volume_ratio_median_max": max(
            row["training_volume_ratio_median"] for row in folds
        ),
    }
    baseline_aggregate = baseline["aggregate"]
    baseline_final_abs = float(
        np.mean(
            [abs(float(row["soc_final_error_percentage_points"])) for row in baseline["cases"]]
        )
    )
    comparison = {
        "baseline_model": "prospectively frozen Tables Method effective-volume fit",
        "baseline_joint_screening_pass_count": baseline_aggregate[
            "joint_screening_pass_count"
        ],
        "baseline_pressure_rmse_mpa_mean": baseline_aggregate[
            "pressure_rmse_mpa_mean"
        ],
        "baseline_temperature_rmse_c_mean": baseline_aggregate[
            "temperature_rmse_c_mean"
        ],
        "baseline_soc_final_abs_error_percentage_points_mean": baseline_final_abs,
        "pressure_rmse_reduction_percent": 100.0
        * (
            float(baseline_aggregate["pressure_rmse_mpa_mean"])
            - aggregate["pressure_rmse_mpa_mean"]
        )
        / float(baseline_aggregate["pressure_rmse_mpa_mean"]),
        "temperature_rmse_reduction_percent": 100.0
        * (
            float(baseline_aggregate["temperature_rmse_c_mean"])
            - aggregate["temperature_rmse_c_mean"]
        )
        / float(baseline_aggregate["temperature_rmse_c_mean"]),
        "soc_final_abs_error_reduction_percent": 100.0
        * (baseline_final_abs - aggregate["soc_final_abs_error_percentage_points_mean"])
        / baseline_final_abs,
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "artifact_type": "mc_capacity_geometry_leave_one_case_out",
        "evidence_role": "post_outcome_within_campaign_development_cross_validation",
        "post_outcome": True,
        "external_validation": False,
        "prospective_validation": False,
        "parameter_fitting": True,
        "fit_scope": "training folds only; one median effective-volume ratio per fold",
        "runtime_parameter_changed": False,
        "validation_gate_changed": False,
        "method": {
            "split": "deterministic leave-one-case-out across eight public MC Default cases",
            "training_case_count_per_fold": 7,
            "held_out_case_count_per_fold": 1,
            "volume_estimator": (
                "median of training-case ratios: integrated signed mass flow divided "
                "by measured endpoint density change, normalized by declared capacity geometry"
            ),
            "held_out_outcomes_excluded_from_fit": True,
            "thermal_parameter_policy": "retain frozen public Type-IV gas-liner UA multiplier",
            "boundary_conditions": [
                "measured mass_flow_g_s",
                "measured inlet_gas_temperature_c",
                "co-located Pinlet pressure_mpa",
            ],
        },
        "screening_limits": baseline["screening_limits"],
        "aggregate": aggregate,
        "baseline_comparison": comparison,
        "folds": folds,
        "source_hashes": {
            _display(protocol_path): _sha256(protocol_path),
            _display(baseline_path): _sha256(baseline_path),
            _display(processed / "mc_default_cases.csv"): _sha256(
                processed / "mc_default_cases.csv"
            ),
            **{
                _display(trace_paths[item]): _sha256(trace_paths[item])
                for item in selected
            },
        },
        "interpretation": (
            "Training-only capacity/mass-closure geometry cuts mean pressure RMSE and "
            "final SOC error substantially, while the joint pass count reaches only "
            "four of eight because temperature remains the dominant unresolved boundary."
        ),
        "limitations": [
            "All folds belong to one already inspected public campaign.",
            "Manufacturer-certified internal volume is unavailable.",
            "The tank-temperature channel does not resolve gas, liner, shell or sensor weighting.",
            "The result cannot replace a prospectively frozen independent external holdout.",
        ],
        "claim_boundary": (
            "This is a leakage-controlled within-campaign development cross-validation. "
            "It may guide the next frozen candidate, but it does not validate a vehicle, "
            "station controller, dispenser, consequence model or field safety function."
        ),
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    agg = report["aggregate"]
    cmp = report["baseline_comparison"]
    lines = [
        "# MC capacity-geometry leave-one-case-out diagnostic",
        "",
        "This is a post-outcome within-campaign development cross-validation. It is not an independent validation and does not change the runtime model.",
        "",
        "## Result",
        "",
        f"- Held-out joint screen: **{agg['joint_screening_pass_count']}/{agg['fold_count']}** cases.",
        f"- Mean pressure RMSE: **{agg['pressure_rmse_mpa_mean']:.3f} MPa** ({cmp['pressure_rmse_reduction_percent']:.1f}% lower than the frozen baseline).",
        f"- Mean tank-temperature RMSE: **{agg['temperature_rmse_c_mean']:.3f} °C** ({cmp['temperature_rmse_reduction_percent']:.1f}% change; negative means worse).",
        f"- Mean final SOC absolute error: **{agg['soc_final_abs_error_percentage_points_mean']:.3f} percentage points** ({cmp['soc_final_abs_error_reduction_percent']:.1f}% lower).",
        "",
        "The geometry rule materially improves pressure and SOC transfer, but four cases still fail because the unresolved temperature boundary dominates the joint decision.",
        "",
        "## Claim boundary",
        "",
        report["claim_boundary"],
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=DEFAULT_PROCESSED)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = build_report(args.processed, args.protocol, args.baseline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_markdown(report, args.report)
    print(json.dumps(report["aggregate"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
