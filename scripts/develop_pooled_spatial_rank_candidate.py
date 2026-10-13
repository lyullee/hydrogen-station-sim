"""Develop one future spatial-rank candidate on two consumed cohorts.

Both HyTunnel-CS and H2SAFE outcomes were available before this search.  The
result is therefore development evidence only.  The selected candidate is
copied into ``h2station.prospective_spatial_rank`` and must be tested without
further tuning on a new actual-hydrogen cohort before any runtime use.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.stats import spearmanr

from h2station.hytunnel_carpark_validation import DISPERSION_CASES
from h2station.hytunnel_spatial_validation import (
    SOURCE_POSITION_M,
    _robust_response,
    load_hytunnel_spatial_case,
)
from h2station.prospective_spatial_rank import FROZEN_PARAMETERS
from scripts.run_h2safe_spatial_candidate_transfer_diagnostic import (
    SOURCE_COORDINATES,
    _finite,
    _read_coordinates,
)


ROOT = Path(__file__).resolve().parents[1]
PARAMETER_ORDER = (
    "upward_vertical_weight",
    "downward_vertical_penalty",
    "vertical_denominator_weight",
    "denominator_power",
    "horizontal_distance_power",
)
THRESHOLDS = {
    "median_spearman": 0.5,
    "spearman_at_least_0_4_fraction": 0.6,
    "mean_top5_recall": 0.6,
    "nearest_in_response_quartile_fraction": 0.7,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _score(horizontal: float, vertical: float, parameters: tuple[float, ...]) -> float:
    upward, downward, vertical_weight, denominator_power, horizontal_power = parameters
    return math.exp(
        upward * max(vertical, 0.0) - downward * max(-vertical, 0.0)
    ) / (
        0.25 + horizontal**horizontal_power + vertical_weight * abs(vertical)
    ) ** denominator_power


def _aggregate(
    cases: Iterable[list[tuple[float, float, float]]],
    parameters: tuple[float, ...],
) -> dict[str, Any]:
    rows: list[dict[str, float | bool]] = []
    for case in cases:
        scores = np.asarray([_score(h, v, parameters) for h, v, _ in case])
        responses = np.asarray([response for _, _, response in case])
        predicted = np.argsort(scores)[::-1]
        observed = np.argsort(responses)[::-1]
        quartile = set(observed[: max(1, math.ceil(len(case) * 0.25))])
        top_five = set(predicted[:5])
        rows.append({
            "spearman": float(spearmanr(scores, responses).statistic),
            "top5_recall": len(top_five & quartile) / len(top_five),
            "nearest_success": bool(predicted[0] in quartile),
        })
    aggregate = {
        "experiment_count": len(rows),
        "median_spearman": float(np.median([row["spearman"] for row in rows])),
        "spearman_at_least_0_4_fraction": float(np.mean([
            row["spearman"] >= 0.4 for row in rows
        ])),
        "mean_top5_recall": float(np.mean([row["top5_recall"] for row in rows])),
        "nearest_in_response_quartile_fraction": float(np.mean([
            row["nearest_success"] for row in rows
        ])),
    }
    screens = {
        "median_spearman_at_least_0_5": aggregate["median_spearman"] >= 0.5,
        "spearman_at_least_0_4_fraction_at_least_0_6": (
            aggregate["spearman_at_least_0_4_fraction"] >= 0.6
        ),
        "mean_top5_recall_at_least_0_6": aggregate["mean_top5_recall"] >= 0.6,
        "nearest_in_response_quartile_fraction_at_least_0_7": (
            aggregate["nearest_in_response_quartile_fraction"] >= 0.7
        ),
    }
    aggregate["screens"] = screens
    aggregate["joint_pass"] = all(screens.values())
    return aggregate


def _hytunnel_cases(raw_dir: Path) -> list[list[tuple[float, float, float]]]:
    cases: list[list[tuple[float, float, float]]] = []
    for experiment in DISPERSION_CASES:
        case = load_hytunnel_spatial_case(raw_dir / f"Exp{experiment:02d}.mat")
        sensors: list[tuple[float, float, float]] = []
        for sensor in case.sensors:
            response = _robust_response(sensor, case.release_start_s)
            if response is None or not math.isfinite(response):
                continue
            horizontal = math.hypot(
                sensor.position_m.x - SOURCE_POSITION_M.x,
                sensor.position_m.z - SOURCE_POSITION_M.z,
            )
            vertical = sensor.position_m.y - SOURCE_POSITION_M.y
            sensors.append((horizontal, vertical, float(response)))
        cases.append(sensors)
    return cases


def _h2safe_cases(raw_dir: Path) -> list[list[tuple[float, float, float]]]:
    cases: list[list[tuple[float, float, float]]] = []
    for lab, source in SOURCE_COORDINATES.items():
        lab_dir = raw_dir / lab
        coordinates = _read_coordinates(lab_dir / "sensors.csv")
        for path in sorted(lab_dir.glob("test*.csv")):
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                trace = list(csv.DictReader(stream))
            sensors: list[tuple[float, float, float]] = []
            for channel in (trace[0].keys() if trace else ()):
                if channel == "time" or channel.lower() not in coordinates:
                    continue
                values = [
                    value for row in trace
                    if (value := _finite(row.get(channel))) is not None
                ]
                if len(values) < 10:
                    continue
                coordinate = coordinates[channel.lower()]
                horizontal = math.hypot(
                    coordinate[0] - source[0], coordinate[2] - source[2]
                )
                vertical = coordinate[1] - source[1]
                response = float(np.quantile(values, 0.99) - np.quantile(values, 0.10))
                sensors.append((horizontal, vertical, response))
            if len(sensors) < 8:
                raise ValueError(f"fewer than eight usable H2SAFE sensors in {path}")
            cases.append(sensors)
    return cases


def _parameter_grid() -> Iterable[tuple[float, ...]]:
    for upward in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0):
        for downward in (0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5):
            for vertical_weight in (0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5):
                for denominator_power in (0.5, 0.75, 1.0, 1.25, 1.5):
                    for horizontal_power in (0.75, 1.0, 1.25, 1.5, 2.0, 2.5):
                        yield (
                            upward, downward, vertical_weight,
                            denominator_power, horizontal_power,
                        )


def _selection_key(item: dict[str, Any]) -> tuple[float, float, float]:
    ratios: list[float] = []
    for cohort in (item["hytunnel_actual_hydrogen"], item["h2safe_helium"]):
        ratios.extend([
            cohort["median_spearman"] / THRESHOLDS["median_spearman"],
            cohort["spearman_at_least_0_4_fraction"]
            / THRESHOLDS["spearman_at_least_0_4_fraction"],
            cohort["mean_top5_recall"] / THRESHOLDS["mean_top5_recall"],
            cohort["nearest_in_response_quartile_fraction"]
            / THRESHOLDS["nearest_in_response_quartile_fraction"],
        ])
    item["minimum_normalized_screen_margin"] = min(ratios)
    return (
        min(ratios),
        np.mean([
            item["hytunnel_actual_hydrogen"]["mean_top5_recall"],
            item["h2safe_helium"]["mean_top5_recall"],
        ]),
        np.mean([
            item["hytunnel_actual_hydrogen"]["median_spearman"],
            item["h2safe_helium"]["median_spearman"],
        ]),
    )


def run(hytunnel_dir: Path, h2safe_dir: Path) -> dict[str, Any]:
    hytunnel = _hytunnel_cases(hytunnel_dir)
    h2safe = _h2safe_cases(h2safe_dir)
    candidates: list[dict[str, Any]] = []
    for parameters in _parameter_grid():
        candidate = {
            "parameters": list(parameters),
            "hytunnel_actual_hydrogen": _aggregate(hytunnel, parameters),
            "h2safe_helium": _aggregate(h2safe, parameters),
        }
        candidate["both_cohorts_joint_pass"] = bool(
            candidate["hytunnel_actual_hydrogen"]["joint_pass"]
            and candidate["h2safe_helium"]["joint_pass"]
        )
        _selection_key(candidate)
        candidates.append(candidate)
    candidates.sort(key=_selection_key, reverse=True)
    selected = candidates[0]
    frozen = [getattr(FROZEN_PARAMETERS, name) for name in PARAMETER_ORDER]
    if selected["parameters"] != frozen:
        raise RuntimeError("selected grid candidate does not match frozen implementation")
    source_module = ROOT / "src/h2station/prospective_spatial_rank.py"
    return {
        "schema_version": 1,
        "artifact_type": "post_outcome_pooled_spatial_rank_development",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "DEVELOPMENT_ONLY_NOT_VALIDATION",
        "selection": {
            "candidate_count": len(candidates),
            "parameter_order": list(PARAMETER_ORDER),
            "objective": (
                "maximize the minimum normalized margin over four frozen screens "
                "in each consumed cohort; break ties by pooled top-five recall and "
                "then pooled median Spearman"
            ),
            "outcomes_seen_before_search": True,
            "selected": selected,
        },
        "sources": {
            "hytunnel_actual_hydrogen": {
                "dataset_doi": "10.23642/USN.14405903",
                "experiment_count": len(hytunnel),
            },
            "h2safe_helium": {
                "dataset_doi": "10.7799/17118570",
                "experiment_count": len(h2safe),
                "test_gas": "helium surrogate",
                "release_time_crosswalk_available": False,
            },
        },
        "implementation": {
            "path": "src/h2station/prospective_spatial_rank.py",
            "sha256": _sha256(source_module),
            "runtime_imported": False,
        },
        "decision": {
            "new_independent_validation": False,
            "readiness_gate_effect": "none",
            "runtime_application": False,
            "future_candidate_frozen": True,
            "next_step": (
                "Evaluate without tuning on a newly acquired actual-hydrogen cohort "
                "with source and sensor coordinates in one frame."
            ),
        },
        "claim_boundary": (
            "This pooled search uses two already-consumed cohorts. It is model "
            "development, not independent validation, concentration prediction, "
            "detector-placement validation, alarm calibration, CFD, ESD, or a "
            "site safety-distance result."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--hytunnel-dir", type=Path, default=ROOT / "tmp/hytunnel_carpark_raw"
    )
    parser.add_argument(
        "--h2safe-dir", type=Path,
        default=ROOT / "data/public_validation/raw/h2safe_2026/extracted",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "research/pooled_spatial_rank_development_2026_10_13.json",
    )
    args = parser.parse_args()
    result = run(args.hytunnel_dir.resolve(), args.h2safe_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    selected = result["selection"]["selected"]
    print(json.dumps({
        "output": str(args.output),
        "parameters": selected["parameters"],
        "both_cohorts_joint_pass": selected["both_cohorts_joint_pass"],
        "minimum_normalized_screen_margin": selected["minimum_normalized_screen_margin"],
        "runtime_application": result["decision"]["runtime_application"],
    }))


if __name__ == "__main__":
    main()
