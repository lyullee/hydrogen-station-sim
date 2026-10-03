"""Select one global precooler-duty multiplier on declared development fills."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import numpy as np

from run_h2protocol_validation import _read_csv, _run_case_file


FROZEN_MODEL_FILES = (
    "src/h2station/dispenser.py",
    "src/h2station/full_station.py",
    "src/h2station/protocol.py",
    "src/h2station/scenario.py",
    "src/h2station/vehicle.py",
    "scripts/run_h2protocol_validation.py",
    "scripts/calibrate_closed_loop_thermal.py",
)


def _assert_frozen_model(commit: str) -> None:
    result = subprocess.run(
        ["git", "diff", "--quiet", commit, "--", *FROZEN_MODEL_FILES],
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            "Model files differ from the frozen thermal-calibration commit"
        )


def _score(rows: list[dict]) -> float:
    return float(np.mean([
        (float(row["pressure_rmse_mpa"]) / 5.0) ** 2
        + (float(row["temperature_rmse_c"]) / 10.0) ** 2
        + (float(row["soc_rmse_percentage_points"]) / 5.0) ** 2
        for row in rows
    ]))


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protocol", type=Path,
        default=Path("research/closed_loop_thermal_calibration_protocol.json"),
    )
    parser.add_argument(
        "--processed", type=Path,
        default=Path("data/public_validation/processed"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/public_validation/results/closed_loop_thermal_calibration"),
    )
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()

    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    frozen_commit = protocol.get("frozen_model_commit")
    if not frozen_commit:
        raise SystemExit("Freeze frozen_model_commit before evaluating candidates")
    _assert_frozen_model(str(frozen_commit))

    development = {int(value) for value in protocol["development_lab_test_numbers"]}
    summaries = [
        row for row in _read_csv(args.processed / "h2protocol_cases.csv")
        if int(float(row["lab_test_number"])) in development
    ]
    found = {int(float(row["lab_test_number"])) for row in summaries}
    if found != development:
        raise SystemExit(
            f"Development case mismatch: expected {sorted(development)}, got {sorted(found)}"
        )

    fixed = protocol["fixed_parameters"]
    tank_fit = {
        "effective_volume_multiplier": float(fixed["effective_volume_multiplier"]),
        "gas_liner_ua_multiplier": float(fixed["gas_liner_ua_multiplier"]),
    }
    flow_multiplier = float(fixed["dispenser_flow_area_multiplier"])
    candidates = tuple(float(value) for value in protocol["candidate_precooler_duty_multipliers"])

    rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(
                _run_case_file,
                summary,
                args.processed / "h2protocol_traces" / f"{summary['case_id']}.csv",
                tank_fit,
                flow_multiplier,
                multiplier,
            ): (multiplier, summary["case_id"])
            for multiplier in candidates
            for summary in summaries
        }
        for future in as_completed(futures):
            rows.append(future.result())

    rows.sort(key=lambda row: (
        float(row["precooler_duty_multiplier"]), int(row["lab_test_number"])
    ))
    candidate_results = []
    for multiplier in candidates:
        selected = [
            row for row in rows
            if float(row["precooler_duty_multiplier"]) == multiplier
        ]
        candidate_results.append({
            "multiplier": multiplier,
            "score": _score(selected),
            "screening_pass_count": sum(bool(row["screening_pass"]) for row in selected),
            "pressure_rmse_mean_mpa": float(np.mean([
                float(row["pressure_rmse_mpa"]) for row in selected
            ])),
            "temperature_rmse_mean_c": float(np.mean([
                float(row["temperature_rmse_c"]) for row in selected
            ])),
            "soc_rmse_mean_percentage_points": float(np.mean([
                float(row["soc_rmse_percentage_points"]) for row in selected
            ])),
        })
    winner = min(candidate_results, key=lambda row: (row["score"], row["multiplier"]))
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frozen_model_commit": frozen_commit,
        "protocol": str(args.protocol),
        "development_lab_test_numbers": sorted(development),
        "prohibited_evaluation_inputs": protocol["prohibited_evaluation_inputs"],
        "objective": protocol["selection_objective"],
        "candidate_results": candidate_results,
        "selected_precooler_duty_multiplier": winner["multiplier"],
        "selection_is_validation": False,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "calibration.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_csv(args.output / "case_metrics.csv", rows)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
