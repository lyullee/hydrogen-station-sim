"""Evaluate a declared-capacity/EOS tank volume without changing production defaults.

The public H2Protocol summaries expose nominal capacity and working pressure but
not a machine-readable vessel volume.  This diagnostic replaces the historical
linear 0.122 m3/4.7 kg assumption with ``capacity / rho(P_nominal, 15 C)`` for
each case, while retaining the already-frozen global tank, flow and thermal
parameters.  It is a sensitivity report, not a new calibration or a validation
claim.  Outcomes must not be used to close the IJHE gates without a new frozen
protocol and prospective review.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from h2station.tabulated import PropsSI  # noqa: E402
import run_h2protocol_validation as runner  # noqa: E402


DEFAULT_OUTPUT = ROOT / "research/h2protocol_capacity_geometry_diagnostic_2026_10_05.json"
REFERENCE_TEMPERATURE_K = 288.15


def capacity_eos_volume_m3(capacity_kg: float, nominal_pressure_mpa: float) -> float:
    density = float(
        PropsSI(
            "Dmass",
            "P",
            float(nominal_pressure_mpa) * 1.0e6,
            "T",
            REFERENCE_TEMPERATURE_K,
            "Hydrogen",
        )
    )
    if density <= 0.0:
        raise ValueError("Hydrogen EOS density must be positive")
    return float(capacity_kg / density)


def _run_case_worker(args: tuple[dict[str, str], Path, dict[str, float], float, float]) -> dict:
    summary, trace_path, tank_fit, flow_multiplier, thermal_multiplier = args
    nominal_pressure_mpa = float(summary["nominal_pressure_mpa"])
    runner._tank_volume_from_nominal_capacity = (
        lambda capacity_kg, pressure=nominal_pressure_mpa: capacity_eos_volume_m3(
            float(capacity_kg), pressure
        )
    )
    trace = runner._read_csv(trace_path)
    result = runner.run_case(
        summary,
        trace,
        tank_fit,
        flow_multiplier,
        thermal_multiplier,
    )
    result["volume_assumption"] = (
        "capacity divided by tabulated Hydrogen density at nominal working "
        "pressure and 15 C; no volume parameter fitted"
    )
    result["capacity_eos_volume_m3"] = capacity_eos_volume_m3(
        float(summary["tank_capacity_kg"]), nominal_pressure_mpa
    )
    return result


def run(
    processed: Path = ROOT / "data/public_validation/processed",
    output: Path = DEFAULT_OUTPUT,
    tank_validation: Path = ROOT / "research/tank_model_validation_v2.json",
    flow_calibration: Path = ROOT / "research/closed_loop_flow_calibration_v2.json",
    thermal_calibration: Path = ROOT / "research/closed_loop_thermal_calibration_v2.json",
    jobs: int = 4,
) -> dict:
    tank_report = json.loads(tank_validation.read_text(encoding="utf-8"))
    tank_fit = {
        "effective_volume_multiplier": float(tank_report["fit"]["effective_volume_multiplier"]),
        "gas_liner_ua_multiplier": float(tank_report["fit"]["gas_liner_ua_multiplier"]),
    }
    flow_report = json.loads(flow_calibration.read_text(encoding="utf-8"))
    thermal_report = json.loads(thermal_calibration.read_text(encoding="utf-8"))
    flow_multiplier = float(flow_report["selected_dispenser_flow_area_multiplier"])
    thermal_multiplier = float(thermal_report["selected_precooler_duty_multiplier"])

    summaries = sorted(
        runner._read_csv(processed / "h2protocol_cases.csv"),
        key=lambda row: int(float(row["lab_test_number"])),
    )
    tasks = [
        (
            summary,
            processed / "h2protocol_traces" / f"{summary['case_id']}.csv",
            tank_fit,
            flow_multiplier,
            thermal_multiplier,
        )
        for summary in summaries
    ]
    cases_by_id: dict[str, dict] = {}
    with ProcessPoolExecutor(max_workers=max(1, int(jobs))) as pool:
        futures = {pool.submit(_run_case_worker, task): task[0]["case_id"] for task in tasks}
        for future in as_completed(futures):
            result = future.result()
            cases_by_id[result["case_id"]] = result
    cases = [cases_by_id[summary["case_id"]] for summary in summaries]

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "diagnostic_capacity_geometry_sensitivity_only",
        "claim_limit": (
            "This report retains the frozen global fit and changes only the declared "
            "capacity-to-volume basis. It is not a confirmatory validation, does not "
            "change production defaults, and cannot close any IJHE gate. A new frozen "
            "protocol is required before treating this geometry rule as a model update."
        ),
        "geometry_rule": {
            "temperature_k": REFERENCE_TEMPERATURE_K,
            "pressure_basis": "each case nominal_working_pressure_mpa",
            "density_source": "h2station.tabulated.PropsSI Hydrogen EOS table",
            "formula": "V = declared_capacity_kg / rho(P_nominal, 288.15 K)",
        },
        "fit_sources": {
            "tank": str(tank_validation),
            "flow": str(flow_calibration),
            "thermal": str(thermal_calibration),
            "effective_volume_multiplier": tank_fit["effective_volume_multiplier"],
            "gas_liner_ua_multiplier": tank_fit["gas_liner_ua_multiplier"],
            "dispenser_flow_area_multiplier": flow_multiplier,
            "precooler_duty_multiplier": thermal_multiplier,
        },
        "aggregate": runner._aggregate(cases),
        "cases": cases,
        "source_commit": runner._git_commit(),
        "source_worktree_dirty": runner._git_worktree_dirty(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=ROOT / "data/public_validation/processed")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    report = run(args.processed, args.output, jobs=args.jobs)
    print(json.dumps(report["aggregate"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
