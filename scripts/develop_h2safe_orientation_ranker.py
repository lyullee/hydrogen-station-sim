"""Evaluate an orientation-class H2SAFE detector-ranking candidate.

The H2SAFE outcomes were already opened before this candidate was selected.
Consequently this is development evidence, not independent validation.  The
script preserves the original failed baseline, evaluates one transparent
orientation-class refinement, and refuses to change runtime routing.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.stats import spearmanr

from h2station.spatial_detector import (
    Point3D,
    geometry_score,
    orientation_aware_geometry_score,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_COORDINATES = {
    "Lab1_Small": Point3D(-5.186701676, 1.580460097, -4.322127),
    "Lab2_Large": Point3D(-11.63093726, 1.566073152, 15.86309373),
}
ORIENTATIONS = {
    "Lab1_Small:test1.csv": "vertical",
    "Lab2_Large:test1.csv": "horizontal",
    "Lab2_Large:test2.csv": "vertical",
    "Lab2_Large:test3.csv": "vertical",
    "Lab2_Large:test4.csv": "vertical",
}


def _finite(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _read_coordinates(path: Path) -> dict[str, Point3D]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return {
            str(row["id"]).strip().lower(): Point3D(
                *(float(row[key]) for key in ("X", "Y", "Z"))
            )
            for row in csv.DictReader(stream)
        }


def _robust_response(values: list[float]) -> float:
    samples = np.asarray(values, dtype=float)
    return float(np.quantile(samples, 0.99) - np.quantile(samples, 0.10))


def _evaluate_case(
    path: Path,
    coordinates: dict[str, Point3D],
    source: Point3D,
    orientation: str,
    predictor: Callable[[Point3D], float],
) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    channels = [name for name in (rows[0].keys() if rows else ()) if name != "time"]
    evaluated: list[dict[str, Any]] = []
    for channel in channels:
        values = [
            value for row in rows
            if (value := _finite(row.get(channel))) is not None
        ]
        coordinate = coordinates.get(channel.lower())
        if coordinate is None or len(values) < 10:
            continue
        evaluated.append({
            "sensor": channel,
            "score": predictor(coordinate),
            "response": _robust_response(values),
        })
    scores = np.asarray([item["score"] for item in evaluated], dtype=float)
    responses = np.asarray([item["response"] for item in evaluated], dtype=float)
    predictor_order = np.argsort(scores)[::-1]
    response_order = np.argsort(responses)[::-1]
    quartile_size = max(1, math.ceil(len(evaluated) * 0.25))
    response_quartile = set(response_order[:quartile_size])
    predictor_top_five = set(predictor_order[:5])
    nearest_index = int(predictor_order[0])
    return {
        "case_id": f"{path.parent.name}:{path.name}",
        "orientation": orientation,
        "valid_sensor_count": len(evaluated),
        "spearman_score_vs_robust_response": float(
            spearmanr(scores, responses).statistic
        ),
        "top5_predictor_recall_of_response_quartile": (
            len(predictor_top_five & response_quartile) / len(predictor_top_five)
        ),
        "nearest_sensor": evaluated[nearest_index]["sensor"],
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
        "reference_screens": screens,
        "internal_reference_screen_pass": all(screens.values()),
    }


def build(raw_dir: Path) -> dict[str, Any]:
    baseline: list[dict[str, Any]] = []
    candidate: list[dict[str, Any]] = []
    for lab, source in SOURCE_COORDINATES.items():
        lab_dir = raw_dir / lab
        coordinates = _read_coordinates(lab_dir / "sensors.csv")
        for path in sorted(lab_dir.glob("test*.csv")):
            case_id = f"{lab}:{path.name}"
            orientation = ORIENTATIONS[case_id]
            baseline.append(_evaluate_case(
                path,
                coordinates,
                source,
                orientation,
                lambda point, source=source: geometry_score(source, point),
            ))
            candidate.append(_evaluate_case(
                path,
                coordinates,
                source,
                orientation,
                lambda point, source=source, orientation=orientation: (
                    orientation_aware_geometry_score(source, point, orientation)
                ),
            ))
    baseline_aggregate = _aggregate(baseline)
    candidate_aggregate = _aggregate(candidate)
    return {
        "schema_version": 1,
        "artifact_type": "post_access_h2safe_orientation_ranker_development",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "doi": "10.7799/17118570",
            "test_gas": "helium surrogate",
            "archive_sha256": "f1b8bf747b7787f00152ec416940c80a143ea044fc18ee8a69ac9da204d9158e",
        },
        "integrity": {
            "status": "POST_ACCESS_DEVELOPMENT_ONLY_NOT_VALIDATION",
            "outcomes_seen_before_candidate_selection": True,
            "parameter_fitting_performed": False,
            "independent_holdout_evaluated": False,
            "runtime_application": False,
            "selection_disclosure": (
                "The orientation-class form was selected after the failed H2SAFE "
                "geometry-only result was known. Passing the same internal reference "
                "screens is diagnostic and cannot revise the frozen validation failure."
            ),
        },
        "candidate": {
            "name": "orientation_class_rank_v2",
            "vertical_formula": (
                "exp(0.7*max(dy,0)-1.2*max(-dy,0)) / "
                "(0.25 + horizontal_distance_m^2 + 0.35*abs(dy))"
            ),
            "horizontal_unknown_azimuth_formula": (
                "exp(-0.5*abs(dy)) / "
                "(0.25 + horizontal_distance_m^2 + 0.35*abs(dy))"
            ),
            "reasoning": (
                "For a declared horizontal release without a published nozzle azimuth, "
                "marginalize direction and penalize vertical separation symmetrically "
                "instead of assuming the buoyant far field dominates the near field."
            ),
            "omitted_inputs": [
                "horizontal nozzle azimuth/vector",
                "vent coordinates and velocity vectors in the sensor coordinate frame",
                "obstacle porosity and flow resistance",
                "time-aligned release interval",
                "declared signal concentration unit",
            ],
        },
        "baseline": {"cases": baseline, "aggregate": baseline_aggregate},
        "orientation_candidate": {
            "cases": candidate,
            "aggregate": candidate_aggregate,
        },
        "delta": {
            "mean_top5_recall": (
                candidate_aggregate["mean_top5_recall"]
                - baseline_aggregate["mean_top5_recall"]
            ),
            "nearest_in_response_quartile_fraction": (
                candidate_aggregate["nearest_in_response_quartile_fraction"]
                - baseline_aggregate["nearest_in_response_quartile_fraction"]
            ),
        },
        "decision": {
            "development_candidate_retained": (
                candidate_aggregate["internal_reference_screen_pass"]
            ),
            "independent_validation_pass": False,
            "runtime_use": "PROHIBITED_UNTIL_NEW_PRE_ACCESS_HOLDOUT_PASSES",
            "next_validation": (
                "Freeze this exact candidate, then evaluate a new independent indoor "
                "release cohort with nozzle and HVAC vectors declared in the same frame."
            ),
        },
        "claim_boundary": (
            "The candidate explains the known horizontal-release failure and passes the "
            "internal H2SAFE reference screens, but it is post-access development evidence. "
            "It does not validate H2 concentration, detector placement, ESD, CFD, outdoor "
            "dispersion, consequence distance or station runtime routing."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data/public_validation/raw/h2safe_2026/extracted",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research/h2safe_orientation_development_2026_10_08.json",
    )
    args = parser.parse_args()
    result = build(args.raw_dir.resolve())
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "output": str(args.output),
        "baseline_pass": result["baseline"]["aggregate"]["internal_reference_screen_pass"],
        "candidate_pass": result["orientation_candidate"]["aggregate"]["internal_reference_screen_pass"],
        "independent_validation_pass": result["decision"]["independent_validation_pass"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
