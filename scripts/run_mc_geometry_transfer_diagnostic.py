"""Diagnose transfer of the public Type-IV effective-volume calibration.

The eight MC Default outcomes have already been inspected.  This script therefore
compares three pre-existing geometry rules only as a post-outcome development
diagnostic.  It cannot select a production rule or revise the frozen holdout.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import numpy as np

from h2station.scenario import capacity_eos_volume_m3
from h2station.tabulated import PropsSI

from run_mc_tank_boundary_diagnostic import SCREENING_LIMITS, _read_csv, run_case


ROOT = Path(__file__).resolve().parents[1]


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _run_geometry(
    protocol: dict,
    summaries: dict[str, dict[str, str]],
    processed: Path,
    *,
    name: str,
    volume_multiplier: float,
    ua_multiplier: float,
    provenance: str,
) -> dict:
    cases = []
    for member in protocol["selected_workbooks"]:
        summary = next(
            row for row in summaries.values() if row["source_member"] == member
        )
        trace = _read_csv(
            processed / "mc_default_traces" / f"{summary['case_id']}.csv"
        )
        cases.append(run_case(
            summary,
            trace,
            {
                "effective_volume_multiplier": volume_multiplier,
                "gas_liner_ua_multiplier": ua_multiplier,
            },
            source_pressure_column="pressure_mpa",
        ))
    return {
        "geometry_rule": name,
        "rule_provenance": provenance,
        "effective_volume_multiplier": volume_multiplier,
        "gas_liner_ua_multiplier": ua_multiplier,
        "case_count": len(cases),
        "joint_screening_pass_count": sum(row["screening_pass"] for row in cases),
        "aggregate": {
            "pressure_rmse_mpa_mean": float(np.mean([
                row["pressure_rmse_mpa"] for row in cases
            ])),
            "temperature_rmse_c_mean": float(np.mean([
                row["temperature_rmse_c"] for row in cases
            ])),
            "soc_rmse_percentage_points_mean": float(np.mean([
                row["soc_rmse_percentage_points"] for row in cases
            ])),
            "soc_final_abs_error_percentage_points_mean": float(np.mean([
                abs(row["soc_final_error_percentage_points"]) for row in cases
            ])),
        },
        "cases": cases,
    }


def _outcome_derived_volume_range(
    summaries: dict[str, dict[str, str]], processed: Path
) -> dict:
    ratios = []
    for summary in summaries.values():
        rows = _read_csv(
            processed / "mc_default_traces" / f"{summary['case_id']}.csv"
        )
        time_s = np.asarray([float(row["time_s"]) for row in rows])
        flow_kg_s = np.asarray([float(row["mass_flow_g_s"]) for row in rows]) / 1000.0
        pressure_pa = np.asarray([float(row["pressure_mpa"]) for row in rows]) * 1.0e6
        temperature_k = np.asarray([
            float(row["tank_temperature_mean_c"]) for row in rows
        ]) + 273.15
        initial_density = float(PropsSI(
            "Dmass", "P", pressure_pa[0], "T", temperature_k[0], "Hydrogen"
        ))
        final_density = float(PropsSI(
            "Dmass", "P", pressure_pa[-1], "T", temperature_k[-1], "Hydrogen"
        ))
        transferred_mass_kg = float(np.trapezoid(flow_kg_s, time_s))
        inferred_volume_m3 = transferred_mass_kg / (final_density - initial_density)
        base_volume_m3 = 0.122 * float(summary["tank_capacity_kg"]) / 4.7
        ratios.append(inferred_volume_m3 / base_volume_m3)
    return {
        "method": (
            "integrated measured mass divided by measured final-minus-initial "
            "hydrogen density; outcome-derived diagnostic only"
        ),
        "case_count": len(ratios),
        "effective_volume_ratio_min": float(np.min(ratios)),
        "effective_volume_ratio_median": float(np.median(ratios)),
        "effective_volume_ratio_max": float(np.max(ratios)),
        "use_for_parameter_selection_prohibited": True,
    }


def main() -> int:
    processed = ROOT / "data/public_validation/processed"
    protocol_path = ROOT / "research/mc_default_external_holdout_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    summaries = {
        row["case_id"]: row
        for row in _read_csv(processed / "mc_default_cases.csv")
    }
    frozen = protocol["frozen_model"]
    ua_multiplier = float(frozen["gas_liner_ua_multiplier"])
    capacity_ratio = capacity_eos_volume_m3(4.7, 70.0e6) / 0.122
    runs = [
        _run_geometry(
            protocol, summaries, processed,
            name="frozen_tables_method_effective_volume",
            volume_multiplier=float(frozen["effective_volume_multiplier"]),
            ua_multiplier=ua_multiplier,
            provenance="prospectively frozen MC Default model",
        ),
        _run_geometry(
            protocol, summaries, processed,
            name="unadjusted_reference_volume",
            volume_multiplier=1.0,
            ua_multiplier=ua_multiplier,
            provenance="pre-existing 0.122 m3 per 4.7 kg reference geometry",
        ),
        _run_geometry(
            protocol, summaries, processed,
            name="capacity_eos_volume",
            volume_multiplier=capacity_ratio,
            ua_multiplier=ua_multiplier,
            provenance=(
                "pre-existing capacity divided by hydrogen density at nominal "
                "working pressure and 15 degC"
            ),
        ),
    ]
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "diagnostic_type": "MC Default Type-IV geometry-transfer sensitivity",
        "evidence_role": "post_outcome_development_diagnostic_only",
        "post_outcome": True,
        "parameter_fitting": False,
        "runtime_geometry_changed": False,
        "geometry_rule_selection_prohibited": True,
        "screening_limits": SCREENING_LIMITS,
        "fixed_boundaries": [
            "measured mass_flow_g_s",
            "co-located Pinlet/Tinlet_G enthalpy boundary",
            "frozen gas_liner_ua_multiplier",
        ],
        "runs": runs,
        "outcome_derived_identifiability": _outcome_derived_volume_range(
            summaries, processed
        ),
        "interpretation": (
            "The globally fitted Tables Method effective-volume multiplier does "
            "not transfer cleanly to the different MC Default vessel set. Two "
            "pre-existing non-fitted geometry rules improve pressure and SOC, "
            "but neither can be selected after outcomes were inspected. Future "
            "full-loop validation must provide exact internal volume and vessel "
            "configuration before outcome access."
        ),
        "claim_boundary": (
            "This diagnostic cannot revise the frozen 0/8 holdout, select a "
            "production geometry, validate the complete station, or close an "
            "IJHE readiness gate."
        ),
    }
    output = ROOT / "research/mc_geometry_transfer_diagnostic_2026_10_08.json"
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        run["geometry_rule"]: {
            "joint_passes": run["joint_screening_pass_count"],
            **run["aggregate"],
        }
        for run in runs
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
