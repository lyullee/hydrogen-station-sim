"""Post-outcome sensitivity search for a future spatial-rank holdout.

The frozen H2SAFE/HyTunnel spatial ranker is never modified by this script.
All candidate selection happens after the existing outcomes were observed, so
the artifact is development evidence only and cannot promote runtime routing.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr

from h2station.hytunnel_carpark_validation import DISPERSION_CASES
from h2station.hytunnel_spatial_validation import (
    SOURCE_POSITION_M,
    _robust_response,
    load_hytunnel_spatial_case,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _case_rows(raw_dir: Path) -> list[list[tuple[float, float, float, float]]]:
    rows: list[list[tuple[float, float, float, float]]] = []
    for experiment in DISPERSION_CASES:
        case = load_hytunnel_spatial_case(raw_dir / f"Exp{experiment:02d}.mat")
        case_rows: list[tuple[float, float, float, float]] = []
        for sensor in case.sensors:
            response = _robust_response(sensor, case.release_start_s)
            if response is None or not math.isfinite(response):
                continue
            horizontal = math.hypot(
                sensor.position_m.x - SOURCE_POSITION_M.x,
                sensor.position_m.z - SOURCE_POSITION_M.z,
            )
            vertical = sensor.position_m.y - SOURCE_POSITION_M.y
            case_rows.append((horizontal, vertical, float(response), 1.0))
        rows.append(case_rows)
    return rows


def _score(row: tuple[float, float, float, float], parameters: tuple[float, ...]) -> float:
    horizontal, vertical, _response, _marker = row
    up, down, vertical_weight, denominator_power, horizontal_power = parameters
    return math.exp(
        up * max(vertical, 0.0) - down * max(-vertical, 0.0)
    ) / (
        0.25 + horizontal**horizontal_power + vertical_weight * abs(vertical)
    ) ** denominator_power


def _evaluate(rows: list[list[tuple[float, float, float, float]]], parameters: tuple[float, ...]) -> dict[str, Any]:
    case_metrics: list[dict[str, float | bool]] = []
    for case_rows in rows:
        scores = np.asarray([_score(row, parameters) for row in case_rows], dtype=float)
        responses = np.asarray([row[2] for row in case_rows], dtype=float)
        predictor_order = np.argsort(scores)[::-1]
        response_order = np.argsort(responses)[::-1]
        quartile = set(response_order[: max(1, math.ceil(len(case_rows) * 0.25))])
        top_five = set(predictor_order[:5])
        case_metrics.append({
            "spearman": float(spearmanr(scores, responses).statistic),
            "top5_recall": len(top_five & quartile) / len(top_five),
            "nearest_success": bool(predictor_order[0] in quartile),
        })
    median_spearman = float(np.median([item["spearman"] for item in case_metrics]))
    rho_fraction = float(np.mean([item["spearman"] >= 0.4 for item in case_metrics]))
    mean_recall = float(np.mean([item["top5_recall"] for item in case_metrics]))
    nearest_fraction = float(np.mean([item["nearest_success"] for item in case_metrics]))
    screens = {
        "median_spearman_at_least_0_5": median_spearman >= 0.5,
        "spearman_at_least_0_4_fraction_at_least_0_6": rho_fraction >= 0.6,
        "mean_top5_recall_at_least_0_6": mean_recall >= 0.6,
        "nearest_in_response_quartile_fraction_at_least_0_7": nearest_fraction >= 0.7,
    }
    return {
        "median_spearman": median_spearman,
        "spearman_at_least_0_4_fraction": rho_fraction,
        "mean_top5_recall": mean_recall,
        "nearest_in_response_quartile_fraction": nearest_fraction,
        "screens": screens,
        "joint_screen_pass": all(screens.values()),
        "cases": case_metrics,
    }


def run(raw_dir: Path) -> dict[str, Any]:
    rows = _case_rows(raw_dir)
    baseline_parameters = (0.7, 1.2, 0.35, 1.0, 2.0)
    # This is a declared sensitivity grid, not a model-fitting procedure for
    # runtime.  The resulting winner is explicitly post-outcome and must be
    # frozen and tested on a new cohort before any application.
    candidates: list[tuple[tuple[float, ...], dict[str, Any]]] = []
    for up in (0.2, 0.4, 0.6, 0.7, 0.8, 1.0):
        for down in (0.2, 0.5, 0.8, 1.0, 1.2, 1.5):
            for vertical_weight in (0.1, 0.2, 0.35, 0.5, 1.0):
                for denominator_power in (0.5, 0.75, 1.0, 1.25, 1.5):
                    for horizontal_power in (1.0, 1.5, 2.0, 2.5):
                        parameters = (up, down, vertical_weight, denominator_power, horizontal_power)
                        candidates.append((parameters, _evaluate(rows, parameters)))
    ranked = sorted(
        candidates,
        key=lambda item: (
            bool(item[1]["joint_screen_pass"]),
            item[1]["mean_top5_recall"],
            item[1]["median_spearman"],
            item[1]["nearest_in_response_quartile_fraction"],
        ),
        reverse=True,
    )
    best_parameters, best_metrics = ranked[0]
    return {
        "schema_version": 1,
        "artifact_type": "post_outcome_hytunnel_spatial_rank_candidate_sensitivity",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "post_outcome_development_only": True,
        "source": {
            "dataset_doi": "10.23642/USN.14405903",
            "article_doi": "10.3390/en14113008",
            "license": "CC BY 4.0",
            "raw_files_committed": False,
        },
        "selection": {
            "declared_case_count": len(DISPERSION_CASES),
            "candidate_count": len(ranked),
            "parameter_order": ["upward_vertical_weight", "downward_vertical_penalty", "vertical_denominator_weight", "denominator_power", "horizontal_distance_power"],
            "baseline_parameters": list(baseline_parameters),
            "candidate_parameters": list(best_parameters),
            "outcomes_seen_before_selection": True,
            "new_independent_holdout": False,
            "parameter_fitting_for_runtime": False,
        },
        "baseline": _evaluate(rows, baseline_parameters),
        "candidate": best_metrics,
        "top_candidates": [
            {"parameters": list(parameters), "metrics": metrics}
            for parameters, metrics in ranked[:10]
        ],
        "decision": {
            "candidate_can_replace_frozen_model": False,
            "runtime_application": False,
            "readiness_gate_effect": "none",
            "next_step": "Freeze the declared candidate before collecting a new independent spatial cohort with source orientation, HVAC vector and per-sensor coordinates in one frame.",
        },
        "claim_boundary": (
            "The candidate is selected after outcome access on the existing public actual-hydrogen cases. "
            "It is not independent validation, detector-placement validation, CFD, alarm-setpoint calibration, "
            "ESD validation, outdoor HRS dispersion or a site safety-distance result."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("tmp/hytunnel_carpark_raw"))
    parser.add_argument("--output", type=Path, default=Path("research/hytunnel_spatial_candidate_sensitivity_2026_10_11.json"))
    args = parser.parse_args()
    result = run(args.raw_dir.resolve())
    result["source"]["raw_directory_sha256"] = _sha256(args.raw_dir / "Exp04.mat")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "output": str(args.output),
        "baseline": result["baseline"]["joint_screen_pass"],
        "candidate": result["candidate"]["joint_screen_pass"],
        "mean_top5_recall": result["candidate"]["mean_top5_recall"],
        "runtime_application": result["decision"]["runtime_application"],
    }))


if __name__ == "__main__":
    main()
