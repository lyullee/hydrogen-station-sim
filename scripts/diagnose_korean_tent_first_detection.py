"""Summarize the published first-detection table from a Korean H2 tent study.

The source exposes sensor/nozzle coordinates and the first sensor to reach
10,000 ppm, but not the complete synchronized concentration traces.  This
diagnostic therefore evaluates a transparent nearest-source baseline only.
It is deliberately post-access evidence: it never changes runtime detector
routing, thresholds, risk distances, or a validation gate.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "research/korean_tent_first_detection_diagnostic_2026_10_14.json"

SENSOR_COORDINATES_M: dict[str, tuple[float, float, float]] = {
    "S1": (0.0, 4.0, 3.0),
    "S2": (4.0, 4.0, 3.0),
    "S3": (4.0, 2.0, 3.0),
    "S4": (4.0, 0.0, 3.0),
    "S5": (8.0, 0.0, 3.0),
}

NOZZLE_COORDINATES_M: dict[str, tuple[float, float, float]] = {
    "G1": (4.0, 2.0, 0.3),
    "G2": (8.0, 2.0, 0.3),
    "G3": (8.0, 4.0, 0.3),
    "G4": (6.0, 4.0, 0.3),
}

# Values transcribed from the published first-detection table/figures.
CASES: tuple[dict[str, Any], ...] = (
    {"case": 1, "nozzle": "G1", "direction": "vertical_up", "flow_l_min": 250, "first_sensor": "S3", "first_time_s": 15},
    {"case": 2, "nozzle": "G2", "direction": "vertical_up", "flow_l_min": 250, "first_sensor": "S5", "first_time_s": 17},
    {"case": 3, "nozzle": "G3", "direction": "vertical_up", "flow_l_min": 250, "first_sensor": "S5", "first_time_s": 24},
    {"case": 4, "nozzle": "G4", "direction": "vertical_up", "flow_l_min": 250, "first_sensor": "S2", "first_time_s": 18},
    {"case": 5, "nozzle": "G1", "direction": "horizontal_backward", "flow_l_min": 250, "first_sensor": "S3", "first_time_s": 15},
    {"case": 6, "nozzle": "G1", "direction": "horizontal_left", "flow_l_min": 250, "first_sensor": "S3", "first_time_s": 19},
    {"case": 7, "nozzle": "G1", "direction": "horizontal_forward", "flow_l_min": 250, "first_sensor": "S4", "first_time_s": 12},
    {"case": 8, "nozzle": "G1", "direction": "vertical_down", "flow_l_min": 250, "first_sensor": "S3", "first_time_s": 12},
    {"case": 9, "nozzle": "G1", "direction": "vertical_up", "flow_l_min": 150, "first_sensor": "S3", "first_time_s": 15},
    {"case": 10, "nozzle": "G1", "direction": "vertical_up", "flow_l_min": 400, "first_sensor": "S4", "first_time_s": 15},
)


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(a, b)))


def rank_nearest(nozzle: str) -> list[str]:
    """Rank upper sensors by 3-D distance to the release nozzle."""

    source = NOZZLE_COORDINATES_M[nozzle]
    return sorted(SENSOR_COORDINATES_M, key=lambda sensor: (_distance(source, SENSOR_COORDINATES_M[sensor]), sensor))


def evaluate() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    correct = 0
    top2 = 0
    observed_ranks: list[int] = []
    for case in CASES:
        ranking = rank_nearest(str(case["nozzle"]))
        observed = str(case["first_sensor"])
        rank = ranking.index(observed) + 1
        correct += int(ranking[0] == observed)
        top2 += int(observed in ranking[:2])
        observed_ranks.append(rank)
        rows.append({
            **case,
            "nearest_sensor_rank": ranking,
            "observed_sensor_rank": rank,
            "nearest_sensor_correct": ranking[0] == observed,
            "nearest_sensor_top2": observed in ranking[:2],
        })
    count = len(rows)
    return {
        "schema_version": 1,
        "artifact_type": "post_access_published_first_detection_diagnostic",
        "recorded_at": "2026-10-14",
        "status": "POST_ACCESS_DEVELOPMENT_DIAGNOSTIC",
        "source": {
            "title": "Concentration Responses of Upper Hydrogen Sensor Under Different Release Conditions in Semi-closed Vinyl Tent",
            "doi": "10.7316/JHNE.2026.37.4.295",
            "record_url": "https://journal.hydrogen.or.kr/_PR/view/?aidx=50481&bidx=4524",
            "license": "publisher page; aggregate values transcribed for research audit",
        },
        "apparatus": {
            "volume_m3": 96.0,
            "dimensions_m": [8.0, 4.0, 3.0],
            "sensor_coordinates_m": SENSOR_COORDINATES_M,
            "nozzle_coordinates_m": NOZZLE_COORDINATES_M,
            "threshold_ppm": 10000,
        },
        "cases": rows,
        "metrics": {
            "case_count": count,
            "nearest_source_top1_accuracy": correct / count,
            "nearest_source_top2_recall": top2 / count,
            "observed_rank_median": sorted(observed_ranks)[count // 2 - (1 if count % 2 == 0 else 0)],
            "observed_rank_values": observed_ranks,
            "first_sensor_counts": {
                sensor: sum(row["first_sensor"] == sensor for row in rows)
                for sensor in SENSOR_COORDINATES_M
            },
        },
        "eligibility_decision": {
            "independent_holdout": False,
            "runtime_parameter_updated": False,
            "validation_gate_changed": False,
            "promotion_prohibited": True,
            "reason": (
                "The published aggregate first-detection table was opened after the frozen spatial protocol; "
                "complete concentration traces, uncertainty records, and a station-matched geometry are not public."
            ),
        },
        "claim_boundary": (
            "This diagnostic shows that source distance alone cannot reproduce first detection in this one 96 m3 "
            "semi-closed tent (release direction, flow, ceiling, and edge effects matter). It is not a detector "
            "setpoint, safety distance, evacuation radius, station validation, CFD validation, or runtime calibration."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(args.output), **result["metrics"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
