"""Run a post-access H2SAFE spatial-response diagnostic.

This deliberately uses a time-alignment-free response amplitude because the
public package does not cross-walk release wall-clock intervals to CSV-relative
time.  It is a development diagnostic after raw outcomes were opened, not a
prospective validation result.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
SOURCE_COORDINATES = {
    "Lab1_Small": (-5.186701676, 1.580460097, -4.322127),
    "Lab2_Large": (-11.63093726, 1.566073152, 15.86309373),
}


def _finite(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _read_coordinates(path: Path) -> dict[str, tuple[float, float, float]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return {
            str(row["id"]).strip().lower(): tuple(
                float(row[key]) for key in ("X", "Y", "Z")
            )
            for row in csv.DictReader(stream)
        }


def _score(
    source: tuple[float, float, float],
    sensor: tuple[float, float, float],
    *,
    vertical_axis: int,
) -> float:
    vertical = sensor[vertical_axis] - source[vertical_axis]
    horizontal = math.sqrt(sum(
        (sensor[index] - source[index]) ** 2
        for index in range(3)
        if index != vertical_axis
    ))
    return math.exp(
        0.7 * max(vertical, 0.0) - 1.2 * max(-vertical, 0.0)
    ) / (0.25 + horizontal * horizontal + 0.35 * abs(vertical))


def _response(values: list[float]) -> float:
    samples = np.asarray(values, dtype=float)
    return float(np.quantile(samples, 0.99) - np.quantile(samples, 0.10))


def _evaluate_case(
    path: Path,
    coordinates: dict[str, tuple[float, float, float]],
    source: tuple[float, float, float],
    *,
    vertical_axis: int,
) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    channels = [name for name in (rows[0].keys() if rows else ()) if name != "time"]
    evaluated: list[dict[str, Any]] = []
    for channel in channels:
        values = [
            value
            for row in rows
            if (value := _finite(row.get(channel))) is not None
        ]
        coordinate = coordinates.get(channel.lower())
        if coordinate is None or len(values) < 10:
            continue
        evaluated.append({
            "sensor": channel,
            "score": _score(source, coordinate, vertical_axis=vertical_axis),
            "response": _response(values),
        })
    scores = np.asarray([item["score"] for item in evaluated], dtype=float)
    responses = np.asarray([item["response"] for item in evaluated], dtype=float)
    sensor_count = len(evaluated)
    predictor_order = np.argsort(scores)[::-1]
    response_order = np.argsort(responses)[::-1]
    response_quartile = set(response_order[: max(1, math.ceil(sensor_count * 0.25))])
    predictor_top_five = set(predictor_order[:5])
    nearest_index = int(predictor_order[0])
    nearest_response_rank = int(np.where(response_order == nearest_index)[0][0]) + 1
    return {
        "case_id": f"{path.parent.name}:{path.name}",
        "valid_sensor_count": sensor_count,
        "spearman_score_vs_robust_response": float(spearmanr(scores, responses).statistic),
        "top5_predictor_recall_of_response_quartile": (
            len(predictor_top_five & response_quartile) / len(predictor_top_five)
        ),
        "nearest_sensor": evaluated[nearest_index]["sensor"],
        "nearest_sensor_response_rank": nearest_response_rank,
        "nearest_sensor_in_response_quartile": nearest_index in response_quartile,
        "maximum_response_sensor": evaluated[int(response_order[0])]["sensor"],
    }


def _aggregate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    median_rho = float(np.median([
        case["spearman_score_vs_robust_response"] for case in cases
    ]))
    rho_fraction = sum(
        case["spearman_score_vs_robust_response"] >= 0.4 for case in cases
    ) / len(cases)
    mean_recall = float(np.mean([
        case["top5_predictor_recall_of_response_quartile"] for case in cases
    ]))
    nearest_fraction = sum(
        case["nearest_sensor_in_response_quartile"] for case in cases
    ) / len(cases)
    screens = {
        "median_spearman_at_least_0_5": median_rho >= 0.5,
        "spearman_at_least_0_4_fraction_at_least_0_6": rho_fraction >= 0.6,
        "mean_top5_recall_at_least_0_6": mean_recall >= 0.6,
        "nearest_in_response_quartile_fraction_at_least_0_7": nearest_fraction >= 0.7,
    }
    return {
        "experiment_count": len(cases),
        "median_spearman": median_rho,
        "spearman_at_least_0_4_fraction": rho_fraction,
        "mean_top5_recall": mean_recall,
        "nearest_in_response_quartile_fraction": nearest_fraction,
        "screens": screens,
        "joint_pass": all(screens.values()),
    }


def run(raw_dir: Path) -> dict[str, Any]:
    axis_results: dict[str, Any] = {}
    for axis_name, axis_index in (("Y_as_elevation", 1), ("Z_as_elevation_sensitivity", 2)):
        cases: list[dict[str, Any]] = []
        for lab, source in SOURCE_COORDINATES.items():
            lab_dir = raw_dir / lab
            coordinates = _read_coordinates(lab_dir / "sensors.csv")
            cases.extend(
                _evaluate_case(
                    path,
                    coordinates,
                    source,
                    vertical_axis=axis_index,
                )
                for path in sorted(lab_dir.glob("test*.csv"))
            )
        axis_results[axis_name] = {"cases": cases, "aggregate": _aggregate(cases)}

    primary = axis_results["Y_as_elevation"]
    return {
        "schema_version": 1,
        "artifact_type": "post_access_h2safe_spatial_response_diagnostic",
        "recorded_at": "2026-10-08",
        "source": {
            "doi": "10.7799/17118570",
            "test_gas": "helium surrogate",
            "archive_sha256": "f1b8bf747b7787f00152ec416940c80a143ea044fc18ee8a69ac9da204d9158e",
        },
        "method": {
            "status": "POST_ACCESS_DEVELOPMENT_DIAGNOSTIC_NOT_VALIDATION",
            "response": "per-sensor q99 minus q10 over the complete trace",
            "reason_for_time_independent_response": (
                "The public package does not cross-walk wall-clock release intervals "
                "to CSV-relative time; release onset was not inferred from outcomes."
            ),
            "rank_predictor": (
                "exp(0.7*max(dy,0)-1.2*max(-dy,0)) / "
                "(0.25 + horizontal_distance_m^2 + 0.35*abs(dy))"
            ),
            "coordinate_decision": (
                "Y is treated as elevation because the published sensor coordinates form "
                "repeated physical height bands (including 0.6096 m and 10.2235 m); Z-axis "
                "results are retained as an explicit sensitivity check."
            ),
        },
        "results": axis_results,
        "decision": {
            "joint_spatial_screen_pass": primary["aggregate"]["joint_pass"],
            "runtime_use": (
                "Do not apply the failed geometry-only ranking to runtime detector routing. "
                "Retain the existing zone mapping, 1.0 and 0.45 concentration multipliers, "
                "and all alarm/trip thresholds until a new independent spatial holdout passes."
            ),
            "rejected_uses": [
                "helium-to-hydrogen concentration conversion",
                "amplitude fitting",
                "alarm or trip setpoint calibration",
                "detector placement validation",
                "CFD, ESD, safety-distance or full-station validation",
            ],
        },
        "claim_boundary": (
            "This post-access diagnostic supports only a development choice to replace "
            "arbitrary near/far detector assignment with a transparent coordinate ranking. "
            "It failed the joint spatial screen and is not independent validation."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data/public_validation/raw/h2safe_2026/extracted",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research/h2safe_spatial_response_diagnostic_2026_10_08.json",
    )
    args = parser.parse_args()
    result = run(args.raw_dir.resolve())
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    aggregate = result["results"]["Y_as_elevation"]["aggregate"]
    print(json.dumps({
        "output": str(args.output),
        "joint_pass": aggregate["joint_pass"],
        "median_spearman": aggregate["median_spearman"],
    }))


if __name__ == "__main__":
    main()
