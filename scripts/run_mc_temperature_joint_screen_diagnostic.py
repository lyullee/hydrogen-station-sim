"""Combine MC temperature-observation candidates with the frozen pressure/SOC screen.

This is a post-outcome diagnostic only.  The MC boundary replay already records
pressure and final-SOC errors for the frozen model, while the companion semantic
replay reports several possible interpretations of ``tank_temperature_mean_c``.
This script joins those two *predefined* views under the same Pinlet boundary
condition so that a temperature-label ambiguity cannot hide a pressure or SOC
failure.  It never selects an operator, changes runtime parameters, or revises
the frozen validation result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any

import numpy as np

from run_mc_tank_boundary_diagnostic import SCREENING_LIMITS
from run_mc_temperature_observation_diagnostic import (
    TEMPERATURE_OBSERVATIONS,
    _metrics,
    _read_csv,
    _replay_case,
)
from h2station.public_tank_calibration import load_public_type_iv_tank_calibration
from h2station.vehicle import CompositeTankFitParameters


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _fit(protocol: dict[str, Any]) -> CompositeTankFitParameters:
    frozen = protocol["frozen_model"]
    return CompositeTankFitParameters(
        effective_volume_multiplier=float(frozen["effective_volume_multiplier"]),
        gas_liner_ua_multiplier=float(frozen["gas_liner_ua_multiplier"]),
    )


def _operator_screen(
    thermal: dict[str, float], boundary_case: dict[str, Any]
) -> bool:
    """Apply the frozen three-channel screen without changing its thresholds."""

    return bool(
        float(boundary_case["pressure_rmse_mpa"])
        <= SCREENING_LIMITS["pressure_rmse_mpa"]
        and thermal["temperature_rmse_c"] <= SCREENING_LIMITS["temperature_rmse_c"]
        and abs(float(boundary_case["soc_final_error_percentage_points"]))
        <= SCREENING_LIMITS["soc_final_abs_error_percentage_points"]
    )


def build_report(
    processed: Path,
    protocol_path: Path,
    boundary_report_path: Path,
) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    boundary_report = json.loads(boundary_report_path.read_text(encoding="utf-8"))
    boundary_cases = {row["case_id"]: row for row in boundary_report["cases"]}
    if boundary_report.get("boundary_semantics", {}).get("pressure_channel") != "Pinlet":
        raise ValueError("joint diagnostic requires the frozen co-located Pinlet boundary report")

    profile = load_public_type_iv_tank_calibration()
    fit = _fit(protocol)
    summaries = {
        row["source_member"]: row
        for row in _read_csv(processed / "mc_default_cases.csv")
    }
    cases: list[dict[str, Any]] = []
    for source_member in protocol["selected_workbooks"]:
        summary = summaries[source_member]
        case_id = summary["case_id"]
        if case_id not in boundary_cases:
            raise ValueError(f"boundary report is missing {case_id}")
        trace_rows = _read_csv(processed / "mc_default_traces" / f"{case_id}.csv")
        replay = _replay_case(
            summary,
            trace_rows,
            fit=fit,
            source_pressure_column="pressure_mpa",
        )
        thermal = _metrics(replay)
        boundary = boundary_cases[case_id]
        cases.append(
            {
                "case_id": case_id,
                "pressure_rmse_mpa": float(boundary["pressure_rmse_mpa"]),
                "soc_final_error_percentage_points": float(
                    boundary["soc_final_error_percentage_points"]
                ),
                "temperature_observations": {
                    name: {
                        **metrics,
                        "joint_screening_pass": _operator_screen(metrics, boundary),
                    }
                    for name, metrics in thermal.items()
                },
            }
        )

    aggregate: dict[str, Any] = {}
    for name in TEMPERATURE_OBSERVATIONS:
        rows = [case["temperature_observations"][name] for case in cases]
        aggregate[name] = {
            "case_count": len(rows),
            "joint_screening_pass_count": sum(row["joint_screening_pass"] for row in rows),
            "joint_screening_pass_fraction": float(
                np.mean([row["joint_screening_pass"] for row in rows])
            ),
            "temperature_rmse_c_mean": float(
                np.mean([row["temperature_rmse_c"] for row in rows])
            ),
            "pressure_rmse_mpa_mean": float(
                np.mean([case["pressure_rmse_mpa"] for case in cases])
            ),
            "soc_final_abs_error_percentage_points_mean": float(
                np.mean(
                    [
                        abs(case["soc_final_error_percentage_points"])
                        for case in cases
                    ]
                )
            ),
        }

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "diagnostic_type": "MC Default candidate temperature operator joint screen",
        "evidence_role": "post_outcome_semantic_diagnostic_only",
        "post_outcome": True,
        "parameter_fitting": False,
        "runtime_parameters_changed": False,
        "operator_selection_performed": False,
        "promotion_to_validation_prohibited": True,
        "protocol": str(protocol_path),
        "boundary_report": str(boundary_report_path),
        "boundary_condition_alignment": "same frozen co-located Pinlet/Tinlet_G replay",
        "screening_limits": SCREENING_LIMITS,
        "candidate_observation_operators": TEMPERATURE_OBSERVATIONS,
        "aggregate": aggregate,
        "cases": cases,
        "interpretation": (
            "Pressure and final-SOC errors are inherited from the frozen Pinlet boundary replay; "
            "only the temperature observation operator varies. A zero joint count for every "
            "operator means temperature-label ambiguity alone cannot explain the MC boundary failure. "
            "No candidate is selected from these post-outcome results."
        ),
        "claim_boundary": (
            "This is a post-outcome semantic decomposition of one public vehicle-tank replay. "
            "It is not a full-loop, station-control, consequence, safety, or prospective validation result."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=Path("data/public_validation/processed"))
    parser.add_argument("--protocol", type=Path, default=Path("research/mc_default_external_holdout_protocol.json"))
    parser.add_argument(
        "--boundary-report",
        type=Path,
        default=Path("research/mc_tank_boundary_diagnostic_2026_10_05.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/mc_temperature_joint_screen_diagnostic_2026_10_11.json"),
    )
    args = parser.parse_args()
    report = build_report(args.processed, args.protocol, args.boundary_report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["aggregate"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
