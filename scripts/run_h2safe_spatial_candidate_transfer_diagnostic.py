"""Apply the frozen HyTunnel spatial candidate to the independent H2SAFE files.

This is a post-access transfer diagnostic, not a validation result.  The
candidate parameters were selected after the HyTunnel outcomes were visible;
H2SAFE is a helium surrogate and has no unambiguous release-to-CSV time
crosswalk.  The script therefore compares rank-only sensor-response metrics
and explicitly keeps the runtime model unchanged.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
BASELINE_PARAMETERS = (0.7, 1.2, 0.35, 1.0, 2.0)
CANDIDATE_PARAMETERS = (0.2, 1.0, 1.0, 1.25, 1.0)


def _finite(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _read_coordinates(path: Path) -> dict[str, tuple[float, float, float]]:
    import csv

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
    parameters: tuple[float, ...],
) -> float:
    horizontal = math.hypot(sensor[0] - source[0], sensor[2] - source[2])
    vertical = sensor[1] - source[1]
    upward, downward, vertical_weight, denominator_power, horizontal_power = parameters
    return math.exp(
        upward * max(vertical, 0.0) - downward * max(-vertical, 0.0)
    ) / (
        0.25 + horizontal**horizontal_power + vertical_weight * abs(vertical)
    ) ** denominator_power


def _evaluate_case(
    path: Path,
    coordinates: dict[str, tuple[float, float, float]],
    source: tuple[float, float, float],
    parameters: tuple[float, ...],
) -> dict[str, Any]:
    import csv

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    evaluated: list[tuple[float, float, str]] = []
    for channel in (rows[0].keys() if rows else ()):
        if channel == "time" or channel.lower() not in coordinates:
            continue
        values = [
            value
            for row in rows
            if (value := _finite(row.get(channel))) is not None
        ]
        if len(values) < 10:
            continue
        evaluated.append((
            _score(source, coordinates[channel.lower()], parameters),
            float(np.quantile(values, 0.99) - np.quantile(values, 0.10)),
            channel,
        ))
    if len(evaluated) < 8:
        raise ValueError(f"fewer than eight usable sensors in {path}")
    scores = np.asarray([item[0] for item in evaluated], dtype=float)
    responses = np.asarray([item[1] for item in evaluated], dtype=float)
    predictor_order = np.argsort(scores)[::-1]
    response_order = np.argsort(responses)[::-1]
    response_quartile = set(response_order[: max(1, math.ceil(len(evaluated) * 0.25))])
    top_five = set(predictor_order[:5])
    nearest = int(predictor_order[0])
    return {
        "case_id": f"{path.parent.name}:{path.name}",
        "valid_sensor_count": len(evaluated),
        "spearman_score_vs_robust_response": float(
            spearmanr(scores, responses).statistic
        ),
        "top5_predictor_recall_of_response_quartile": len(top_five & response_quartile) / len(top_five),
        "nearest_sensor": evaluated[nearest][2],
        "nearest_sensor_response_rank": int(np.where(response_order == nearest)[0][0]) + 1,
        "nearest_sensor_in_response_quartile": nearest in response_quartile,
        "maximum_response_sensor": evaluated[int(response_order[0])][2],
    }


def _aggregate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    median_rho = float(np.median([
        case["spearman_score_vs_robust_response"] for case in cases
    ]))
    rho_fraction = float(np.mean([
        case["spearman_score_vs_robust_response"] >= 0.4 for case in cases
    ]))
    mean_recall = float(np.mean([
        case["top5_predictor_recall_of_response_quartile"] for case in cases
    ]))
    nearest_fraction = float(np.mean([
        case["nearest_sensor_in_response_quartile"] for case in cases
    ]))
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
        "joint_screen_pass": all(screens.values()),
    }


def _run_parameters(raw_dir: Path, parameters: tuple[float, ...]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for lab, source in SOURCE_COORDINATES.items():
        lab_dir = raw_dir / lab
        coordinates = _read_coordinates(lab_dir / "sensors.csv")
        for path in sorted(lab_dir.glob("test*.csv")):
            cases.append(_evaluate_case(path, coordinates, source, parameters))
    return {"cases": cases, "aggregate": _aggregate(cases)}


def run(raw_dir: Path) -> dict[str, Any]:
    baseline = _run_parameters(raw_dir, BASELINE_PARAMETERS)
    candidate = _run_parameters(raw_dir, CANDIDATE_PARAMETERS)
    return {
        "schema_version": 1,
        "artifact_type": "post_access_h2safe_spatial_candidate_transfer_diagnostic",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "POST_ACCESS_TRANSFER_DIAGNOSTIC_NOT_VALIDATION",
        "source": {
            "doi": "10.7799/17118570",
            "test_gas": "helium surrogate",
            "timing_crosswalk_available": False,
            "candidate_source_artifact": "research/hytunnel_spatial_candidate_sensitivity_2026_10_11.json",
        },
        "parameters": {
            "baseline": list(BASELINE_PARAMETERS),
            "candidate": list(CANDIDATE_PARAMETERS),
            "parameter_order": [
                "upward_vertical_weight", "downward_vertical_penalty",
                "vertical_denominator_weight", "denominator_power",
                "horizontal_distance_power",
            ],
            "candidate_selected_after_hytunnel_outcome_access": True,
        },
        "baseline": baseline,
        "candidate": candidate,
        "decision": {
            "runtime_application": False,
            "readiness_gate_effect": "none",
            "candidate_replaces_frozen_model": False,
            "reason": (
                "The candidate loses nearest-sensor transfer on the H2SAFE helium files "
                "and the public release-to-CSV timing crosswalk is absent."
            ),
        },
        "claim_boundary": (
            "This compares rank-only transfer on a helium surrogate after both source "
            "datasets were public. It is not hydrogen concentration validation, CFD, "
            "detector placement validation, alarm/ESD calibration or a safety-distance result."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir", type=Path,
        default=ROOT / "data/public_validation/raw/h2safe_2026/extracted",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "research/h2safe_spatial_candidate_transfer_diagnostic_2026_10_11.json",
    )
    args = parser.parse_args()
    result = run(args.raw_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "output": str(args.output),
        "baseline_nearest_fraction": result["baseline"]["aggregate"]["nearest_in_response_quartile_fraction"],
        "candidate_nearest_fraction": result["candidate"]["aggregate"]["nearest_in_response_quartile_fraction"],
        "runtime_application": result["decision"]["runtime_application"],
    }))


if __name__ == "__main__":
    main()
