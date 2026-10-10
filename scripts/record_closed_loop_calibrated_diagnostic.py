"""Record an explicitly post-outcome J2601 calibrated diagnostic.

The runner can evaluate already-consumed confirmation cases with development
calibrations.  This recorder keeps that result useful for repair work while
making it impossible to mistake the result for a new external holdout or a
production-parameter update.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    values = [float(row[key]) for row in rows]
    return sum(values) / len(values)


def build_record(
    validation_path: Path,
    baseline_path: Path,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    cases = list(validation.get("cases") or [])
    baseline_cases = {
        str(row["case_id"]): row for row in (baseline.get("cases") or [])
    }
    case_ids = [str(row["case_id"]) for row in cases]
    missing = sorted(set(case_ids) - set(baseline_cases))
    if missing:
        raise ValueError(f"baseline does not contain diagnostic cases: {missing}")
    aggregate = validation.get("aggregate") or {}
    baseline_aggregate = baseline.get("aggregate") or {}
    rows = [
        {
            "case_id": case_id,
            "screening_pass": bool(row.get("screening_pass")),
            "pressure_rmse_mpa": float(row["pressure_rmse_mpa"]),
            "temperature_rmse_c": float(row["temperature_rmse_c"]),
            "soc_rmse_percentage_points": float(row["soc_rmse_percentage_points"]),
            "final_stop_reason": row.get("final_stop_reason"),
            "baseline_pressure_rmse_mpa": float(baseline_cases[case_id]["pressure_rmse_mpa"]),
            "baseline_temperature_rmse_c": float(baseline_cases[case_id]["temperature_rmse_c"]),
            "baseline_soc_rmse_percentage_points": float(
                baseline_cases[case_id]["soc_rmse_percentage_points"]
            ),
        }
        for case_id, row in ((str(row["case_id"]), row) for row in cases)
    ]
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_type": "post_outcome_closed_loop_calibrated_confirmatory_diagnostic",
        "evidence_role": "model-development diagnostic only",
        "post_outcome": True,
        "parameter_fitting": False,
        "production_default_changed": False,
        "validation_gate_effect": "none",
        "source_commit": _git_commit(),
        "source_worktree_dirty_during_execution": bool(
            subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True).stdout.strip()
        ),
        "runner": {
            "artifact": str(validation_path.relative_to(root)).replace("\\", "/"),
            "sha256": _sha256(validation_path),
        },
        "baseline": {
            "artifact": str(baseline_path.relative_to(root)).replace("\\", "/"),
            "sha256": _sha256(baseline_path),
            "case_count": int(baseline_aggregate.get("case_count", 0)),
            "screening_pass_count": int(baseline_aggregate.get("screening_pass_count", 0)),
            "metrics_mean": {
                "pressure_rmse_mpa": _mean(list(baseline_cases.values()), "pressure_rmse_mpa"),
                "temperature_rmse_c": _mean(list(baseline_cases.values()), "temperature_rmse_c"),
                "soc_rmse_percentage_points": _mean(
                    list(baseline_cases.values()), "soc_rmse_percentage_points"
                ),
            },
        },
        "configuration": {
            "case_ids": case_ids,
            "case_count": len(case_ids),
            "tank_fit": validation.get("tank_fit"),
            "geometry_basis": validation.get("geometry_basis"),
            "vehicle_tank_thermal_model": validation.get("vehicle_tank_thermal_model"),
            "equivalent_capsule_aspect_ratio": validation.get(
                "vehicle_equivalent_capsule_aspect_ratio"
            ),
            "inlet_nozzle_diameter_m": validation.get("vehicle_inlet_nozzle_diameter_m"),
            "dispenser_flow_area_multiplier": validation.get(
                "dispenser_flow_area_multiplier"
            ),
            "precooler_duty_multiplier": validation.get("precooler_duty_multiplier"),
        },
        "diagnostic_aggregate": {
            "case_count": int(aggregate.get("case_count", len(cases))),
            "screening_pass_count": int(aggregate.get("screening_pass_count", 0)),
            "screening_pass_fraction": float(aggregate.get("screening_pass_fraction", 0.0)),
            "metrics_mean": {
                "pressure_rmse_mpa": _mean(rows, "pressure_rmse_mpa"),
                "temperature_rmse_c": _mean(rows, "temperature_rmse_c"),
                "soc_rmse_percentage_points": _mean(rows, "soc_rmse_percentage_points"),
            },
            "final_stop_reason_counts": aggregate.get("final_stop_reason_counts") or {},
        },
        "case_summary": rows,
        "claim_boundary": (
            "These cases were already consumed during development and are not a new "
            "independent holdout. The result cannot revise the frozen external gate, "
            "establish SAE conformance, validate field safety, or justify a production "
            "parameter change."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validation",
        type=Path,
        default=Path(
            "research/closed_loop_calibrated_confirmatory_diagnostic_2026_10_10/validation.json"
        ),
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("research/closed_loop_internal_comparison_v2.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/closed_loop_calibrated_confirmatory_diagnostic_2026_10_10.json"),
    )
    args = parser.parse_args()
    record = build_record(args.validation.resolve(), args.baseline.resolve())
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
