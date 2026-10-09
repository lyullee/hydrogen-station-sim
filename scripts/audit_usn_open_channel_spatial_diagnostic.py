"""Reproduce a bounded spatial-response diagnostic for the public USN data.

The raw CC BY archives are intentionally supplied by path rather than bundled
in the repository.  This script joins their measured concentration channels to
the sensor coordinates transcribed from Table 1 of the companion article.  It
is a post-access development diagnostic: it does not fit a dispersion model,
calibrate alarm thresholds, or change runtime detector routing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from h2station.public_validation import iter_dispersion_experiments


ROOT = Path(__file__).resolve().parents[1]
COORDINATE_ARTIFACT = ROOT / "research/usn_open_channel_sensor_coordinates_2026_10_10.json"
DEFAULT_OUTPUT = ROOT / "research/usn_open_channel_spatial_diagnostic_2026_10_10.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rank(values: Sequence[float]) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    order = np.argsort(array, kind="mergesort")
    ranks = np.empty(len(array), dtype=float)
    ranks[order] = np.arange(len(array), dtype=float)
    # Average ties so the metric remains a proper Spearman rank correlation.
    sorted_values = array[order]
    start = 0
    while start < len(array):
        end = start + 1
        while end < len(array) and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = (start + end - 1) / 2.0
        start = end
    return ranks


def _spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_rank = _rank(left)
    right_rank = _rank(right)
    left_centered = left_rank - np.mean(left_rank)
    right_centered = right_rank - np.mean(right_rank)
    denominator = float(np.linalg.norm(left_centered) * np.linalg.norm(right_centered))
    return float(np.dot(left_centered, right_centered) / denominator) if denominator else 0.0


def _response_quartile_recall(response: Sequence[float], predicted: Sequence[float], top_fraction: float = 0.25) -> float:
    count = len(response)
    if count == 0:
        return 0.0
    top_count = max(1, int(math.ceil(count * top_fraction)))
    response_top = set(np.argsort(np.asarray(response), kind="mergesort")[-top_count:])
    predicted_top = set(np.argsort(np.asarray(predicted), kind="mergesort")[-top_count:])
    return float(len(response_top & predicted_top) / len(response_top))


def _geometry_score(source: Mapping[str, float], sensor: Mapping[str, float]) -> float:
    dx = float(sensor["x"]) - float(source["x"])
    dy = float(sensor["y"]) - float(source["y"])
    dz = float(sensor["z"]) - float(source["z"])
    distance = math.sqrt(dx * dx + dy * dy + dz * dz)
    if distance <= 1e-12:
        return float("inf")
    # A downward release gives a transparent directional prior: closer sensors
    # below the inlet receive a modest weight.  Coefficients are declared priors.
    downward_alignment = max(0.0, -dz) / distance
    return (1.0 + 0.5 * downward_alignment) / (0.25 + distance * distance)


def _case_result(experiment: Any, coordinates: Mapping[str, Mapping[str, float]], source: Mapping[str, float]) -> dict[str, Any]:
    available = [
        (index, sensor_id, coordinates[f"sensor_{int(sensor_id):02d}"])
        for index, sensor_id in enumerate(experiment.sensor_ids)
        if f"sensor_{int(sensor_id):02d}" in coordinates
    ]
    if len(available) < 5:
        raise ValueError(f"{experiment.case_id} has too few coordinate-matched sensors")
    start = experiment.baseline_duration_s + 2.0 * experiment.filling_duration_s / 3.0
    steady = experiment.concentrations_percent[
        (experiment.sensor_time_s >= start)
        & (experiment.sensor_time_s <= experiment.baseline_duration_s + experiment.filling_duration_s)
    ]
    response: list[float] = []
    predicted: list[float] = []
    sensor_ids: list[str] = []
    for index, sensor_id, coordinate in available:
        values = np.maximum(steady[:, index], 0.0)
        response.append(float(np.quantile(values, 0.90) - np.quantile(values, 0.10)))
        predicted.append(_geometry_score(source, coordinate))
        sensor_ids.append(str(sensor_id))
    return {
        "case_id": experiment.case_id,
        "article_test_id": experiment.article_test_id,
        "mean_mass_flow_g_s": experiment.mean_mass_flow_g_s,
        "matched_sensor_count": len(sensor_ids),
        "sensor_ids": sensor_ids,
        "spearman_geometry_vs_q90_minus_q10": _spearman(predicted, response),
        "top_quartile_recall": _response_quartile_recall(response, predicted),
        "response_metric": "steady q90 minus q10 concentration vol%",
    }


def build_diagnostic(raw_directory: Path, coordinate_path: Path = COORDINATE_ARTIFACT) -> dict[str, Any]:
    coordinates_record = json.loads(coordinate_path.read_text(encoding="utf-8"))
    coordinates = coordinates_record["sensors_m"]
    source = coordinates_record["coordinate_frame"]["release_origin_m"]
    experiments = list(iter_dispersion_experiments(raw_directory))
    cases = [_case_result(experiment, coordinates, source) for experiment in experiments]
    correlations = [item["spearman_geometry_vs_q90_minus_q10"] for item in cases]
    recalls = [item["top_quartile_recall"] for item in cases]
    aggregate = {
        "experiment_count": len(cases),
        "sensor_coordinate_count": len(coordinates),
        "median_spearman": float(np.median(correlations)),
        "spearman_at_least_0_4_fraction": float(np.mean(np.asarray(correlations) >= 0.4)),
        "mean_top_quartile_recall": float(np.mean(recalls)),
        "screens": {
            "median_spearman_at_least_0_5": float(np.median(correlations)) >= 0.5,
            "spearman_at_least_0_4_fraction_at_least_0_6": float(np.mean(np.asarray(correlations) >= 0.4)) >= 0.6,
            "mean_top_quartile_recall_at_least_0_6": float(np.mean(recalls)) >= 0.6,
        },
    }
    archive_paths = sorted(raw_directory.glob("23_FFI_P101_T*.zip"))
    nested_archive_paths = sorted((raw_directory / "raw").glob("23_FFI_P101_T*.zip"))
    if nested_archive_paths and not archive_paths:
        archive_paths = nested_archive_paths
    archive_hashes = {path.name: _sha256(path) for path in archive_paths}
    return {
        "schema_version": 1,
        "artifact_type": "post_access_usn_open_channel_spatial_response_diagnostic",
        "recorded_at": "2026-10-10",
        "source": {
            "dataset_doi": "10.23642/USN.26117989",
            "article_doi": "10.1016/j.jlp.2025.105669",
            "license": "CC BY 4.0",
            "raw_archive_count": len(archive_hashes),
            "raw_archive_sha256": archive_hashes,
            "coordinate_artifact": str(coordinate_path.relative_to(ROOT)).replace("\\", "/"),
            "coordinate_artifact_sha256": _sha256(coordinate_path),
        },
        "method": {
            "status": "POST_ACCESS_DEVELOPMENT_DIAGNOSTIC_NOT_VALIDATION",
            "response": "steady q90 minus q10 concentration by sensor",
            "geometry": "distance to article Table 1 release origin with a fixed downward-release prior",
            "release_origin_m": source,
            "runtime_parameter_application": False,
        },
        "results": {"cases": cases, "aggregate": aggregate},
        "decision": {
            "spatial_holdout_ready": False,
            "runtime_detector_routing_changed": False,
            "claim_supported": False,
            "reason": "raw archives were accessed before a new holdout protocol was frozen; results remain a reproducible actual-hydrogen diagnostic",
        },
        "claim_boundary": "This diagnostic uses public actual-hydrogen concentration traces and article sensor coordinates to screen a fixed geometry prior. It is not CFD, detector-placement, alarm-threshold, ESD, safety-distance or station-runtime validation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--coordinates", type=Path, default=COORDINATE_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_diagnostic(args.raw.resolve(), args.coordinates.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(json.dumps(result["results"]["aggregate"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
