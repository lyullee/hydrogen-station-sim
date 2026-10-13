"""Reproduce the frozen orientation-class transfer diagnostic on USN data.

The USN open-channel archives were opened after the repository already contained
post-access spatial diagnostics.  This runner therefore records a reproducibility
and transfer diagnostic only.  It cannot promote the detector, change the
readiness gate, or claim an independent holdout.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile
from typing import Any

import numpy as np
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COORDINATES = ROOT / "research/usn_open_channel_sensor_coordinates_2026_10_10.json"
DEFAULT_OUTPUT = ROOT / "research/usn_orientation_class_spatial_transfer_diagnostic_2026_10_14.json"
SOURCE = (0.45, 0.8, 0.5)  # candidate frame: x horizontal, y elevation, z streamwise
MODEL_COMMIT = "2056c04"
MODEL_PATH = "src/h2station/spatial_detector.py"
MODEL_SHA256 = "d01b4378a43b3dc233d7093733119963c11db208f604160eba0fa7f962d7580a"


def _finite(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _score(point: tuple[float, float, float]) -> float:
    vertical = point[1] - SOURCE[1]
    horizontal = math.hypot(point[0] - SOURCE[0], point[2] - SOURCE[2])
    return math.exp(0.7 * max(vertical, 0.0) - 1.2 * max(-vertical, 0.0)) / (
        0.25 + horizontal * horizontal + 0.35 * abs(vertical)
    )


def _coordinates(path: Path) -> dict[str, tuple[float, float, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        key.lower(): (float(value["x"]), float(value["z"]), float(value["y"]))
        for key, value in payload["sensors_m"].items()
    }


def _csv_member(archive: Path) -> tuple[str, bytes]:
    with zipfile.ZipFile(archive) as handle:
        names = [name for name in handle.namelist() if name.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"expected one CSV in {archive.name}, found {names}")
        name = names[0]
        return name, handle.read(name)


def _response(rows: list[dict[str, str]], channel: str) -> float | None:
    values = [
        number
        for row in rows
        if (number := _finite(row.get(channel))) is not None
    ]
    if len(values) < 30:
        return None
    return float(np.quantile(values, 0.99) - np.quantile(values, 0.10))


def _case(archive: Path, coordinates: dict[str, tuple[float, float, float]]) -> dict[str, Any]:
    member, raw = _csv_member(archive)
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="replace"))))
    channels = [
        key for key in (rows[0].keys() if rows else ())
        if key.lower().startswith("sensor ") and "h2 concentration" in key.lower()
    ]
    responses: list[tuple[str, float, float]] = []
    for channel in channels:
        sensor_number = channel.lower().split("sensor ", 1)[1].split(" ", 1)[0]
        point = coordinates.get(f"sensor_{int(sensor_number):02d}")
        response = _response(rows, channel)
        if point is not None and response is not None:
            responses.append((channel, _score(point), response))
    if len(responses) < 8:
        raise ValueError(f"fewer than eight valid sensors in {archive.name}")
    scores = np.asarray([item[1] for item in responses], dtype=float)
    observed = np.asarray([item[2] for item in responses], dtype=float)
    predicted_order = np.argsort(scores)[::-1]
    observed_order = np.argsort(observed)[::-1]
    top_quartile = set(observed_order[: max(1, math.ceil(len(responses) * 0.25))])
    top_five = set(predicted_order[:5])
    nearest = int(predicted_order[0])
    rho = spearmanr(scores, observed).statistic
    return {
        "case_id": archive.stem,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "csv_member": member,
        "row_count": len(rows),
        "valid_sensor_count": len(responses),
        "response_definition": "q99 minus q10 over the complete published trace",
        "spearman_score_vs_robust_response": float(rho),
        "top5_predictor_recall_of_response_quartile": len(top_five & top_quartile) / len(top_five),
        "nearest_sensor": responses[nearest][0],
        "nearest_sensor_response_rank": int(np.where(observed_order == nearest)[0][0]) + 1,
        "nearest_sensor_in_response_quartile": nearest in top_quartile,
        "maximum_response_sensor": responses[int(observed_order[0])][0],
    }


def _aggregate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    rho = [case["spearman_score_vs_robust_response"] for case in cases]
    recall = [case["top5_predictor_recall_of_response_quartile"] for case in cases]
    nearest = [case["nearest_sensor_in_response_quartile"] for case in cases]
    screens = {
        "median_spearman_at_least_0_5": float(np.median(rho)) >= 0.5,
        "spearman_at_least_0_4_fraction_at_least_0_6": float(np.mean(np.asarray(rho) >= 0.4)) >= 0.6,
        "mean_top5_recall_at_least_0_6": float(np.mean(recall)) >= 0.6,
        "nearest_in_response_quartile_fraction_at_least_0_7": float(np.mean(nearest)) >= 0.7,
    }
    return {
        "experiment_count": len(cases),
        "median_spearman": float(np.median(rho)),
        "spearman_at_least_0_4_fraction": float(np.mean(np.asarray(rho) >= 0.4)),
        "mean_top5_recall": float(np.mean(recall)),
        "nearest_in_response_quartile_fraction": float(np.mean(nearest)),
        "reference_screens": screens,
        "joint_screen_pass": all(screens.values()),
    }


def build(raw_dir: Path, coordinates_path: Path) -> dict[str, Any]:
    coordinates = _coordinates(coordinates_path)
    archives = sorted(raw_dir.glob("*.zip"))
    cases = [_case(archive, coordinates) for archive in archives]
    aggregate = _aggregate(cases)
    return {
        "schema_version": 1,
        "artifact_type": "post_access_usn_orientation_class_spatial_transfer_diagnostic",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "POST_ACCESS_REPRODUCIBILITY_DIAGNOSTIC_NOT_INDEPENDENT_VALIDATION",
        "source": {
            "dataset_doi": "10.23642/USN.26117989.v2",
            "article_doi": "10.1016/j.jlp.2025.105669",
            "test_gas": "actual hydrogen",
            "archive_count": len(archives),
            "coordinate_artifact": str(coordinates_path.relative_to(ROOT)),
            "license": "CC BY 4.0",
        },
        "model_lock": {
            "candidate": "orientation_class_rank_v2",
            "implementation": MODEL_PATH,
            "implementation_sha256": MODEL_SHA256,
            "pre_access_model_freeze_commit": MODEL_COMMIT,
            "coordinate_transform": "candidate(x,y,z) = dataset(x,z,y)",
            "source_origin_candidate_frame": list(SOURCE),
            "response_window": "complete published trace; q99 minus q10",
            "parameter_fitting_in_this_run": False,
        },
        "provenance_boundary": {
            "dataset_raw_accessed_before_this_artifact": True,
            "dataset_used_in_prior_post_access_spatial_diagnostic": True,
            "independent_holdout": False,
            "prospective_validation": False,
            "runtime_application": False,
            "readiness_gate_effect": False,
            "reason": (
                "This run reproduces a pre-locked formula on a public actual-hydrogen dataset, "
                "but the dataset was already opened and used in repository diagnostics before "
                "this artifact was written. It therefore cannot be reported as a new independent holdout."
            ),
        },
        "cases": cases,
        "aggregate": aggregate,
        "decision": {
            "reproducibility_result": "PASS" if aggregate["joint_screen_pass"] else "FAIL",
            "independent_validation_result": "NOT_ASSESSED",
            "runtime_detector_routing_changed": False,
            "gate_changed": False,
        },
        "claim_boundary": (
            "The frozen geometry rank is reproducible and transfers across the published "
            "open-channel actual-hydrogen cases under the stated rank screens. This does not "
            "validate outdoor HRS detector placement, concentration amplitude, alarm/trip setpoints, "
            "CFD, consequence distance, ESD effectiveness or a station-to-vehicle loop."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--coordinates", type=Path, default=DEFAULT_COORDINATES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build(args.raw_dir.resolve(), args.coordinates.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "archive_count": result["aggregate"]["experiment_count"],
        "median_spearman": result["aggregate"]["median_spearman"],
        "mean_top5_recall": result["aggregate"]["mean_top5_recall"],
        "nearest_fraction": result["aggregate"]["nearest_in_response_quartile_fraction"],
        "joint_screen_pass": result["aggregate"]["joint_screen_pass"],
        "independent_validation": result["decision"]["independent_validation_result"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
