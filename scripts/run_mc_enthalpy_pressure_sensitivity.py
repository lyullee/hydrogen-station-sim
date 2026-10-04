"""Sensitivity of MC vehicle-tank replay to the inlet enthalpy pressure basis.

The MC workbooks expose storage-source pressure and vehicle pressure, but not
the pressure immediately upstream of the vehicle nozzle.  This diagnostic
keeps measured mass flow and inlet temperature fixed and changes only the
pressure used to evaluate inlet enthalpy.  It is post-outcome, unfitted and
cannot be treated as validation or as a production-model change.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from run_mc_tank_boundary_diagnostic import _read_csv, run_case


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    processed = ROOT / "data/public_validation/processed"
    protocol = json.loads((ROOT / "research/mc_default_external_holdout_protocol.json").read_text(encoding="utf-8"))
    summaries = {row["case_id"]: row for row in _read_csv(processed / "mc_default_cases.csv")}
    fit = {
        "effective_volume_multiplier": float(protocol["frozen_model"]["effective_volume_multiplier"]),
        "gas_liner_ua_multiplier": float(protocol["frozen_model"]["gas_liner_ua_multiplier"]),
    }
    runs = []
    for mode in ("source_pressure_1_mpa", "source_pressure_3_mpa", "vehicle_pressure_mpa"):
        rows = []
        for member in protocol["selected_workbooks"]:
            summary = next(row for row in summaries.values() if row["source_member"] == member)
            trace = _read_csv(processed / "mc_default_traces" / f"{summary['case_id']}.csv")
            if mode == "vehicle_pressure_mpa":
                for item in trace:
                    item[mode] = item["pressure_mpa"]
            rows.append(run_case(summary, trace, fit, source_pressure_column=mode))
        runs.append({
            "inlet_enthalpy_pressure_basis": mode,
            "case_count": len(rows),
            "aggregate": {
                "pressure_rmse_mpa_mean": float(np.mean([row["pressure_rmse_mpa"] for row in rows])),
                "temperature_rmse_c_mean": float(np.mean([row["temperature_rmse_c"] for row in rows])),
                "soc_rmse_percentage_points_mean": float(np.mean([row["soc_rmse_percentage_points"] for row in rows])),
            },
            "cases": rows,
        })
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": "post-outcome diagnostic run",
        "diagnostic_type": "MC inlet enthalpy pressure-basis sensitivity",
        "evidence_role": "development_diagnostic_only",
        "post_outcome": True,
        "parameter_fitting": False,
        "fixed_boundaries": ["measured mass_flow_g_s", "measured inlet_gas_temperature_c"],
        "variable_only": "pressure used for inlet hydrogen enthalpy evaluation",
        "claim_boundary": "The workbook does not expose nozzle-upstream pressure. This sensitivity cannot select a production boundary, establish causal correctness, validate the full station, or close an IJHE/full-objective gate.",
        "fit_source": "frozen MC Default model values; no case-specific fitting",
        "runs": runs,
    }
    output = ROOT / "research/mc_enthalpy_pressure_sensitivity_2026_10_05.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for run in runs:
        print(run["inlet_enthalpy_pressure_basis"], json.dumps(run["aggregate"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
