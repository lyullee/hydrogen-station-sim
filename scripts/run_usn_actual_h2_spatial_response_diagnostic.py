"""Run a post-access spatial-response diagnostic on the public USN H2 archive.

The archive contains actual-hydrogen open-channel experiments with 29 sensor
coordinates per case.  Raw CSV rows are read transiently from ZIP members and
are never copied into the repository.  The result is a development diagnostic
only: the archive was opened before a new spatial holdout protocol was frozen.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import zipfile
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
COORDINATE_ARTIFACT = ROOT / "research/usn_open_channel_sensor_coordinates_2026_10_10.json"
SENSOR_RE = re.compile(r"sensor\s+(\d+)\s+h2 concentration", re.IGNORECASE)


def _finite(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _load_coordinates(path: Path) -> dict[str, tuple[float, float, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        key.lower(): tuple(float(item[axis]) for axis in ("x", "y", "z"))
        for key, item in payload["sensors_m"].items()
    }


def _response(values: list[float]) -> float:
    samples = np.asarray(values, dtype=float)
    return float(np.quantile(samples, 0.99) - np.quantile(samples, 0.10))


def _score(
    source: tuple[float, float, float],
    sensor: tuple[float, float, float],
    *,
    model: str,
) -> float:
    dx = sensor[0] - source[0]
    dy = sensor[1] - source[1]
    dz = sensor[2] - source[2]
    distance = math.sqrt(dx * dx + dy * dy + dz * dz)
    if model == "inverse_distance":
        return 1.0 / (0.05 + distance)
    # A transparent, non-fitted sensitivity for the reported downward release:
    # lower sensors are favoured, while distance still controls dilution.
    downward = max(-dz, 0.0)
    upward_penalty = max(dz, 0.0)
    return math.exp(0.9 * downward - 0.6 * upward_penalty) / (0.12 + distance * distance)


def _evaluate_member(
    archive: Path,
    coordinates: dict[str, tuple[float, float, float]],
    source: tuple[float, float, float],
    *,
    model: str,
    score_function: Callable[
        [tuple[float, float, float], tuple[float, float, float]], float
    ] | None = None,
) -> dict[str, Any]:
    with zipfile.ZipFile(archive) as package:
        csv_members = [name for name in package.namelist() if name.lower().endswith(".csv")]
        if len(csv_members) != 1:
            raise ValueError(f"expected one CSV member in {archive.name}, found {csv_members}")
        with package.open(csv_members[0]) as raw:
            rows = list(csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")))

    if not rows:
        raise ValueError(f"empty CSV member in {archive.name}")
    first_row = rows[0]
    channels: list[tuple[str, str]] = []
    for column in first_row:
        match = SENSOR_RE.search(column or "")
        if match:
            channels.append((column, f"sensor_{int(match.group(1)):02d}"))
    evaluated: list[dict[str, Any]] = []
    for column, sensor_id in channels:
        coordinate = coordinates.get(sensor_id)
        values = [
            number
            for row in rows
            if (number := _finite(row.get(column))) is not None
        ]
        if coordinate is None or len(values) < 10:
            continue
        evaluated.append({
            "sensor": sensor_id,
            "score": (
                score_function(source, coordinate)
                if score_function is not None
                else _score(source, coordinate, model=model)
            ),
            "response": _response(values),
        })
    scores = np.asarray([item["score"] for item in evaluated], dtype=float)
    responses = np.asarray([item["response"] for item in evaluated], dtype=float)
    response_order = np.argsort(responses)[::-1]
    predictor_order = np.argsort(scores)[::-1]
    sensor_count = len(evaluated)
    if sensor_count < 5:
        raise ValueError(f"too few mapped sensor channels in {archive.name}: {sensor_count}")
    response_quartile = set(response_order[: max(1, math.ceil(sensor_count * 0.25))])
    top_five = set(predictor_order[:5])
    nearest = int(predictor_order[0])
    nearest_rank = int(np.where(response_order == nearest)[0][0]) + 1
    flow_values = [_finite(row.get("mass flow meter 1 [g/s]")) for row in rows]
    pressure_values = [_finite(row.get("filling pressure [bar]")) for row in rows]
    flow_values = [value for value in flow_values if value is not None]
    pressure_values = [value for value in pressure_values if value is not None]
    return {
        "case_id": archive.stem,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "row_count": len(rows),
        "valid_sensor_count": sensor_count,
        "mean_mass_flow_g_s": float(np.mean(flow_values)) if flow_values else None,
        "peak_mass_flow_g_s": float(np.max(flow_values)) if flow_values else None,
        "max_filling_pressure_bar": float(np.max(pressure_values)) if pressure_values else None,
        "spearman_score_vs_robust_response": float(spearmanr(scores, responses).statistic),
        "top5_predictor_recall_of_response_quartile": len(top_five & response_quartile) / len(top_five),
        "nearest_sensor": evaluated[nearest]["sensor"],
        "nearest_sensor_response_rank": nearest_rank,
        "nearest_sensor_in_response_quartile": nearest in response_quartile,
        "maximum_response_sensor": evaluated[int(response_order[0])]["sensor"],
    }


def _aggregate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    rhos = [case["spearman_score_vs_robust_response"] for case in cases]
    recalls = [case["top5_predictor_recall_of_response_quartile"] for case in cases]
    nearest = [case["nearest_sensor_in_response_quartile"] for case in cases]
    screens = {
        "median_spearman_at_least_0_5": float(np.median(rhos)) >= 0.5,
        "spearman_at_least_0_4_fraction_at_least_0_6": sum(value >= 0.4 for value in rhos) / len(cases) >= 0.6,
        "mean_top5_recall_at_least_0_6": float(np.mean(recalls)) >= 0.6,
        "nearest_in_response_quartile_fraction_at_least_0_7": sum(nearest) / len(cases) >= 0.7,
    }
    return {
        "experiment_count": len(cases),
        "median_spearman": float(np.median(rhos)),
        "spearman_at_least_0_4_fraction": sum(value >= 0.4 for value in rhos) / len(cases),
        "mean_top5_recall": float(np.mean(recalls)),
        "nearest_in_response_quartile_fraction": sum(nearest) / len(cases),
        "screens": screens,
        "joint_pass": all(screens.values()),
    }


def run(raw_dir: Path, coordinates_path: Path) -> dict[str, Any]:
    coordinates = _load_coordinates(coordinates_path)
    source = (0.45, 0.5, 0.8)
    model_results: dict[str, Any] = {}
    for model in ("inverse_distance", "downward_release_sensitivity"):
        cases = [
            _evaluate_member(archive, coordinates, source, model=model)
            for archive in sorted(raw_dir.glob("*.zip"))
        ]
        model_results[model] = {"cases": cases, "aggregate": _aggregate(cases)}
    return {
        "schema_version": 1,
        "artifact_type": "post_access_usn_actual_h2_spatial_response_diagnostic",
        "recorded_at": "2026-10-11",
        "source": {
            "dataset_doi": "10.23642/USN.26117989",
            "article_doi": "10.1016/j.jlp.2025.105669",
            "test_gas": "actual hydrogen",
            "archive_count": len(list(raw_dir.glob("*.zip"))),
            "coordinates_artifact": str(coordinates_path.relative_to(ROOT)).replace("\\", "/"),
        },
        "method": {
            "status": "POST_ACCESS_DEVELOPMENT_DIAGNOSTIC_NOT_VALIDATION",
            "response": "per-sensor q99 minus q10 over the complete trace",
            "source_origin_m": source,
            "coordinate_frame": "x width, y streamwise distance from closed end, z height",
            "models": {
                "inverse_distance": "1/(0.05 + Euclidean distance)",
                "downward_release_sensitivity": "exp(0.9*max(-dz,0)-0.6*max(dz,0))/(0.12+distance^2)",
            },
            "outcome_independence": False,
        },
        "results": model_results,
        "decision": {
            "runtime_use": False,
            "holdout_gate_effect": False,
            "next_use": "Use only to pre-specify a new untouched spatial holdout protocol and candidate feature set.",
            "rejected_uses": [
                "hydrogen concentration or alarm-setpoint calibration",
                "detector placement or safety-distance validation",
                "CFD, ESD or full-station validation",
                "runtime parameter replacement",
            ],
        },
        "claim_boundary": (
            "Actual-hydrogen public traces strengthen component-level development evidence, "
            "but this post-access diagnostic is not independent validation and cannot change the frozen runtime model."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--coordinates", type=Path, default=COORDINATE_ARTIFACT)
    parser.add_argument("--output", type=Path, default=ROOT / "research/usn_actual_h2_spatial_response_diagnostic_2026_10_11.json")
    args = parser.parse_args()
    result = run(args.raw_dir.resolve(), args.coordinates.resolve())
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "output": str(args.output),
        "archive_count": result["source"]["archive_count"],
        "inverse_distance": result["results"]["inverse_distance"]["aggregate"],
        "downward_release_sensitivity": result["results"]["downward_release_sensitivity"]["aggregate"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
