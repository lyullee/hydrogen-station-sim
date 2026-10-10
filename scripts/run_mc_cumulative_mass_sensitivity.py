"""Post-outcome MC tank mass-boundary sensitivity diagnostic.

The frozen MC boundary replay remains in
``run_mc_tank_boundary_diagnostic.py``.  This runner only asks whether the
remaining error changes when hydrogen mass is prescribed by the trapezoidal
integral of the published mass-flow channel.  The source has no independent
mass measurement, so this result is not a validation result and never changes
the runtime model or a readiness gate.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from run_mc_tank_boundary_diagnostic import (
    _f,
    _git_commit,
    _read_csv,
    run_case_cumulative_mass_boundary,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=Path("data/public_validation/processed"))
    parser.add_argument("--protocol", type=Path, default=Path("research/mc_default_external_holdout_protocol.json"))
    parser.add_argument("--output", type=Path, default=Path("research/mc_cumulative_mass_sensitivity_2026_10_10.json"))
    args = parser.parse_args()

    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    fit = {
        "effective_volume_multiplier": float(protocol["frozen_model"]["effective_volume_multiplier"]),
        "gas_liner_ua_multiplier": float(protocol["frozen_model"]["gas_liner_ua_multiplier"]),
    }
    summaries = {row["case_id"]: row for row in _read_csv(args.processed / "mc_default_cases.csv")}
    cases = []
    for member in protocol["selected_workbooks"]:
        summary = next(row for row in summaries.values() if row["source_member"] == member)
        trace = _read_csv(args.processed / "mc_default_traces" / f"{summary['case_id']}.csv")
        cases.append(run_case_cumulative_mass_boundary(
            summary, trace, fit, source_pressure_column="pressure_mpa",
        ))

    aggregate = {
        "case_count": len(cases),
        "joint_screening_pass_count": sum(case["screening_pass"] for case in cases),
        "joint_screening_pass_fraction": float(np.mean([case["screening_pass"] for case in cases])),
        "pressure_rmse_mpa_mean": float(np.mean([case["pressure_rmse_mpa"] for case in cases])),
        "temperature_rmse_c_mean": float(np.mean([case["temperature_rmse_c"] for case in cases])),
        "soc_rmse_percentage_points_mean": float(np.mean([case["soc_rmse_percentage_points"] for case in cases])),
        "soc_final_error_percentage_points_mean": float(np.mean([case["soc_final_error_percentage_points"] for case in cases])),
    }
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "artifact_type": "mc_cumulative_mass_boundary_sensitivity",
        "evidence_role": "development_diagnostic_only",
        "post_outcome": True,
        "parameter_fitting": False,
        "runtime_parameter_updated": False,
        "mass_boundary": "initial EOS mass plus trapezoidal integral of the published mass_flow_g_s channel",
        "source_limitation": "The MC trace has no independent mass channel; the prescribed path is derived from flow and is not an external validation boundary.",
        "protocol": str(args.protocol),
        "claim_boundary": "This separates ODE mass-state integration error from thermal/geometry error for the vehicle-tank submodel. It does not revise the frozen MC result, validate a station controller or protocol, select runtime parameters, or close a validation gate.",
        "screening_limits": {
            "pressure_rmse_mpa": 5.0,
            "temperature_rmse_c": 10.0,
            "soc_final_abs_error_percentage_points": 5.0,
        },
        "aggregate": aggregate,
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(aggregate, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
