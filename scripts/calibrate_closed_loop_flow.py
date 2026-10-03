"""Select one global dispenser-flow multiplier on frozen development fills.

This script is deliberately a small discrete selection, not a continuous fit.
H2P-L06 is excluded because it was used during exploratory diagnosis. The
confirmatory cases are never evaluated here.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from run_h2protocol_validation import _read_csv, _run_case_file


DEVELOPMENT_LAB_TESTS = frozenset((1, 4, 11, 13, 19, 22, 29, 31))
# The original 1.0--1.75 grid improved monotonically and selected its upper
# bound after the active-fill parser correction. The extended values are an
# explicitly adaptive development search; they are not confirmatory evidence.
CANDIDATES = (1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5)


def _score(rows: list[dict]) -> float:
    values = [
        (float(row["pressure_rmse_mpa"]) / 5.0) ** 2
        + (float(row["temperature_rmse_c"]) / 10.0) ** 2
        + (float(row["soc_rmse_percentage_points"]) / 5.0) ** 2
        for row in rows
    ]
    return float(np.mean(values))


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=Path("data/public_validation/processed"))
    parser.add_argument(
        "--tank-validation-json", type=Path,
        default=Path("data/public_validation/results/tank_model/validation.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/public_validation/results/closed_loop_flow_calibration"),
    )
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()

    tank_report = json.loads(args.tank_validation_json.read_text(encoding="utf-8"))
    tank_fit = {
        "effective_volume_multiplier": float(
            tank_report["fit"]["effective_volume_multiplier"]
        ),
        "gas_liner_ua_multiplier": float(
            tank_report["fit"]["gas_liner_ua_multiplier"]
        ),
    }
    summaries = [
        row for row in _read_csv(args.processed / "h2protocol_cases.csv")
        if int(float(row["lab_test_number"])) in DEVELOPMENT_LAB_TESTS
    ]
    found = {int(float(row["lab_test_number"])) for row in summaries}
    if found != DEVELOPMENT_LAB_TESTS:
        raise SystemExit(f"Development case mismatch: expected {sorted(DEVELOPMENT_LAB_TESTS)}, got {sorted(found)}")

    rows = []
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {}
        for multiplier in CANDIDATES:
            for summary in summaries:
                future = pool.submit(
                    _run_case_file,
                    summary,
                    args.processed / "h2protocol_traces" / f"{summary['case_id']}.csv",
                    tank_fit,
                    multiplier,
                )
                futures[future] = (multiplier, summary["case_id"])
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(
                f"evaluated {row['case_id']} at {row['dispenser_flow_area_multiplier']:.2f}",
                flush=True,
            )
    rows.sort(key=lambda row: (
        float(row["dispenser_flow_area_multiplier"]), int(row["lab_test_number"])
    ))
    candidates = []
    for multiplier in CANDIDATES:
        selected = [
            row for row in rows
            if float(row["dispenser_flow_area_multiplier"]) == multiplier
        ]
        candidates.append({
            "multiplier": multiplier,
            "score": _score(selected),
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
    winner = min(candidates, key=lambda row: row["score"])
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "development_lab_test_numbers": sorted(DEVELOPMENT_LAB_TESTS),
        "exploratory_case_excluded": "H2P-L06",
        "selection_timing": (
            "adaptive development search after the original grid selected its "
            "upper bound; not external validation"
        ),
        "confirmatory_lab_test_numbers": [3, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36],
        "tank_fit_source": str(args.tank_validation_json),
        "tank_fit": tank_fit,
        "objective": "mean((P_RMSE/5 MPa)^2 + (T_RMSE/10 degC)^2 + (SOC_RMSE/5 percentage points)^2)",
        "candidates": candidates,
        "selected_dispenser_flow_area_multiplier": winner["multiplier"],
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
