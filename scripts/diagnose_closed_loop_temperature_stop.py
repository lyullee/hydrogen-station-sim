"""Post-outcome sensitivity diagnostic for the MC Default closed-loop failure.

This script deliberately does *not* modify the frozen validation result or the
production model.  It reruns the same eight public traces while changing only
the diagnostic vehicle-gas temperature trip (and the mirrored controller
schedule limit).  The result answers a narrow question: are the negative
full-loop metrics dominated by the 85 degC protection stop, or do large errors
remain after that stop is moved?  Because the diagnostic is post-outcome, it
cannot be used as an external validation pass or as parameter fitting.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path

from scripts import run_h2protocol_validation as validation


def _summaries(protocol: dict, processed: Path) -> list[dict[str, str]]:
    rows = validation._read_csv(processed / "mc_default_cases.csv")
    by_member = {row["source_member"]: row for row in rows}
    summaries = []
    for index, member in enumerate(protocol["selected_workbooks"], start=1):
        row = dict(by_member[member])
        row["lab_test_number"] = str(index)
        row["scheduled_aprr_mpa_min"] = row["protocol_effective_aprr_mpa_min"]
        row["target_vehicle_pressure_mpa"] = row["protocol_target_pressure_mpa"]
        summaries.append(row)
    return summaries


def _run_at_limit(
    summaries: list[dict[str, str]],
    processed: Path,
    limit_c: float,
    tank_fit: dict[str, float],
    flow_multiplier: float,
) -> list[dict]:
    original_builder = validation.build_reference_scenario

    def diagnostic_builder(config, backend):
        # Keep every frozen input and model parameter; only lift the trip limit
        # for this sensitivity run.  The safety PLC uses a separate copy of the
        # same limit, so both layers must be changed consistently.
        lifted = replace(
            config,
            maximum_gas_temperature_k=limit_c + 273.15,
        )
        built = original_builder(lifted, backend)
        built.simulator.safety_plc.limits = replace(
            built.simulator.safety_plc.limits,
            maximum_vehicle_temperature_k=limit_c + 273.15,
        )
        return built

    validation.build_reference_scenario = diagnostic_builder
    try:
        return [
            validation._run_case_file(
                summary,
                processed / "mc_default_traces" / f"{summary['case_id']}.csv",
                tank_fit,
                flow_multiplier,
            )
            for summary in summaries
        ]
    finally:
        validation.build_reference_scenario = original_builder


def _run_one_case(
    summary: dict[str, str],
    processed: Path,
    limit_c: float,
    tank_fit: dict[str, float],
    flow_multiplier: float,
) -> dict:
    """Worker entry point; each case gets a clean interpreter/model state."""
    return _run_at_limit(
        [summary], processed, limit_c, tank_fit, flow_multiplier,
    )[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protocol", type=Path,
        default=Path("research/mc_default_external_holdout_protocol.json"),
    )
    parser.add_argument(
        "--processed", type=Path,
        default=Path("data/public_validation/processed"),
    )
    parser.add_argument(
        "--baseline", type=Path,
        default=Path("data/public_validation/results/closed_loop_external_holdout/validation.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("research/closed_loop_temperature_stop_diagnostic_2026_10_04.json"),
    )
    parser.add_argument(
        "--limits-c", type=float, nargs="+", default=[85.0, 95.0, 105.0, 120.0],
    )
    args = parser.parse_args()

    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    summaries = _summaries(protocol, args.processed)
    tank_fit = {
        "effective_volume_multiplier": float(protocol["frozen_model"]["effective_volume_multiplier"]),
        "gas_liner_ua_multiplier": float(protocol["frozen_model"]["gas_liner_ua_multiplier"]),
    }
    flow_multiplier = float(protocol["frozen_model"]["dispenser_flow_area_multiplier"])

    runs: list[dict] = []
    for limit_c in args.limits_c:
        with ProcessPoolExecutor(max_workers=min(8, len(summaries))) as pool:
            futures = [
                pool.submit(
                    _run_one_case,
                    summary,
                    args.processed,
                    limit_c,
                    tank_fit,
                    flow_multiplier,
                )
                for summary in summaries
            ]
            rows = [future.result() for future in futures]
        aggregate = validation._aggregate(rows)
        runs.append({
            "temperature_limit_c": limit_c,
            "aggregate": aggregate,
            "cases": rows,
        })

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "diagnostic_type": "post-outcome temperature-stop sensitivity",
        "baseline_validation": str(args.baseline),
        "baseline_source_commit": baseline.get("source_commit"),
        "baseline_screening_pass_fraction": baseline.get("aggregate", {}).get("screening_pass_fraction"),
        "post_outcome": True,
        "validation_gate_effect": "none; this artifact cannot change the frozen external holdout decision",
        "parameter_fitting": False,
        "scope": [
            "Same eight selected MC Default traces, parsing rules and frozen fit values as the baseline.",
            "Only the controller and safety-PLC vehicle-gas temperature stop was lifted for sensitivity.",
            "The lifted limit is a diagnostic counterfactual, not an allowable operating limit.",
            "A passing sensitivity run would still require a new predeclared prospective protocol and independent holdout.",
        ],
        "runs": runs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    for run in runs:
        agg = run["aggregate"]
        print(
            f"{run['temperature_limit_c']:.1f} C: "
            f"{agg['screening_pass_count']}/{agg['case_count']} pass, "
            f"P RMSE {agg['metrics']['pressure_rmse_mpa']['mean']:.2f} MPa, "
            f"T RMSE {agg['metrics']['temperature_rmse_c']['mean']:.2f} C, "
            f"SOC RMSE {agg['metrics']['soc_rmse_percentage_points']['mean']:.2f} pp, "
            f"stops {agg['final_stop_reason_counts']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
