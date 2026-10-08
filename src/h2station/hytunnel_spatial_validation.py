"""Frozen spatial-rank validation on HyTunnel-CS actual-hydrogen traces.

The orientation-class detector ranker was fixed during earlier H2SAFE
development.  This module evaluates that exact candidate against HyTunnel
sensor coordinates and per-sensor responses without fitting positions,
amplitudes, alarm thresholds or model coefficients.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from scipy.stats import spearmanr

from .hytunnel_carpark_validation import DISPERSION_CASES
from .spatial_detector import Point3D, orientation_aware_geometry_score


SOURCE_POSITION_M = Point3D(-5.0, 0.25, 0.0)
RELEASE_ORIENTATION = "vertical"
MINIMUM_SENSOR_SAMPLES = 30


@dataclass(frozen=True, slots=True)
class HyTunnelSpatialSensor:
    sensor_id: str
    position_m: Point3D
    time_s: np.ndarray
    concentration_volpct: np.ndarray


@dataclass(frozen=True, slots=True)
class HyTunnelSpatialCase:
    experiment: int
    release_start_s: float
    sensors: tuple[HyTunnelSpatialSensor, ...]


@dataclass(frozen=True, slots=True)
class SpatialCaseResult:
    experiment: int
    valid_sensor_count: int
    spearman_score_vs_robust_response: float
    top5_predictor_recall_of_response_quartile: float
    nearest_sensor: str
    nearest_sensor_in_response_quartile: bool
    maximum_response_sensor: str


def _cell_values(file: h5py.File, dataset: h5py.Dataset) -> list[np.ndarray]:
    values: list[np.ndarray] = []
    for reference in np.asarray(dataset[()]).reshape(-1):
        if not reference:
            values.append(np.asarray([]))
        else:
            values.append(np.asarray(file[reference][()]).squeeze())
    return values


def _matlab_text(value: np.ndarray, fallback: str) -> str:
    array = np.asarray(value).reshape(-1)
    if array.dtype.kind in {"u", "i"}:
        text = "".join(chr(int(item)) for item in array if int(item) != 0)
    else:
        text = "".join(str(item) for item in array)
    return text.strip() or fallback


def load_hytunnel_spatial_case(path: str | Path) -> HyTunnelSpatialCase:
    path = Path(path)
    digits = "".join(character for character in path.stem if character.isdigit())
    if not digits:
        raise ValueError("experiment number is missing from the MAT filename")
    experiment = int(digits)
    if experiment not in DISPERSION_CASES:
        raise ValueError("experiment is outside the frozen HyTunnel spatial case list")
    if not h5py.is_hdf5(path):
        raise ValueError("the frozen spatial loader requires MATLAB v7.3/HDF5")

    with h5py.File(path, "r") as file:
        sensor_group = file["S"]
        ids = _cell_values(file, sensor_group["ID"])
        positions = _cell_values(file, sensor_group["pos"])
        times = _cell_values(file, sensor_group["time"])
        concentrations = _cell_values(file, sensor_group["conc"])
        counts = {len(ids), len(positions), len(times), len(concentrations)}
        if len(counts) != 1:
            raise ValueError("S.ID, S.pos, S.time and S.conc cell counts differ")
        release_start_s = float(np.asarray(file["MFM/t0"][()]).squeeze())
        sensors: list[HyTunnelSpatialSensor] = []
        for index, (raw_id, raw_position, raw_time, raw_concentration) in enumerate(
            zip(ids, positions, times, concentrations, strict=True)
        ):
            position = np.asarray(raw_position, dtype=float).reshape(-1)
            time = np.asarray(raw_time, dtype=float).reshape(-1)
            concentration = np.asarray(raw_concentration, dtype=float).reshape(-1)
            if position.size != 3:
                # Several experiments retain extra concentration channels whose
                # coordinate cell is empty.  The frozen protocol excludes only
                # documented missing-position channels and keeps the case when
                # enough mapped sensors remain.
                continue
            if time.size != concentration.size:
                raise ValueError(f"S.time[{index}] and S.conc[{index}] lengths differ")
            sensors.append(HyTunnelSpatialSensor(
                sensor_id=_matlab_text(raw_id, f"sensor-{index + 1:02d}"),
                position_m=Point3D(*(float(value) / 1000.0 for value in position)),
                time_s=time,
                concentration_volpct=concentration,
            ))
    return HyTunnelSpatialCase(
        experiment=experiment,
        release_start_s=release_start_s,
        sensors=tuple(sensors),
    )


def _robust_response(sensor: HyTunnelSpatialSensor, release_start_s: float) -> float | None:
    valid = (
        np.isfinite(sensor.time_s)
        & np.isfinite(sensor.concentration_volpct)
        & (sensor.time_s >= release_start_s)
    )
    values = sensor.concentration_volpct[valid]
    if values.size < MINIMUM_SENSOR_SAMPLES:
        return None
    return float(np.quantile(values, 0.99) - np.quantile(values, 0.10))


def evaluate_spatial_case(case: HyTunnelSpatialCase) -> SpatialCaseResult:
    evaluated: list[dict[str, Any]] = []
    for sensor in case.sensors:
        response = _robust_response(sensor, case.release_start_s)
        if response is None or not math.isfinite(response):
            continue
        evaluated.append({
            "sensor": sensor.sensor_id,
            "score": orientation_aware_geometry_score(
                SOURCE_POSITION_M,
                sensor.position_m,
                RELEASE_ORIENTATION,
            ),
            "response": response,
        })
    if len(evaluated) < 8:
        raise ValueError("fewer than eight sensors have eligible spatial responses")
    evaluated.sort(key=lambda item: str(item["sensor"]))
    scores = np.asarray([item["score"] for item in evaluated], dtype=float)
    responses = np.asarray([item["response"] for item in evaluated], dtype=float)
    predictor_order = sorted(
        range(len(evaluated)),
        key=lambda index: (-scores[index], str(evaluated[index]["sensor"])),
    )
    response_order = sorted(
        range(len(evaluated)),
        key=lambda index: (-responses[index], str(evaluated[index]["sensor"])),
    )
    quartile_size = max(1, math.ceil(len(evaluated) * 0.25))
    response_quartile = set(response_order[:quartile_size])
    predictor_top_five = set(predictor_order[:5])
    nearest_index = predictor_order[0]
    return SpatialCaseResult(
        experiment=case.experiment,
        valid_sensor_count=len(evaluated),
        spearman_score_vs_robust_response=float(
            spearmanr(scores, responses).statistic
        ),
        top5_predictor_recall_of_response_quartile=(
            len(predictor_top_five & response_quartile) / len(predictor_top_five)
        ),
        nearest_sensor=str(evaluated[nearest_index]["sensor"]),
        nearest_sensor_in_response_quartile=nearest_index in response_quartile,
        maximum_response_sensor=str(evaluated[response_order[0]]["sensor"]),
    )


def aggregate_spatial_cases(cases: list[SpatialCaseResult]) -> dict[str, Any]:
    if not cases:
        raise ValueError("no eligible spatial cases")
    median_rho = float(np.median([
        case.spearman_score_vs_robust_response for case in cases
    ]))
    rho_fraction = sum(
        case.spearman_score_vs_robust_response >= 0.4 for case in cases
    ) / len(DISPERSION_CASES)
    mean_recall = float(np.sum([
        case.top5_predictor_recall_of_response_quartile for case in cases
    ]) / len(DISPERSION_CASES))
    nearest_fraction = sum(
        case.nearest_sensor_in_response_quartile for case in cases
    ) / len(DISPERSION_CASES)
    screens = {
        "all_18_declared_cases_eligible": len(cases) == len(DISPERSION_CASES),
        "median_spearman_at_least_0_5": median_rho >= 0.5,
        "spearman_at_least_0_4_fraction_at_least_0_6": rho_fraction >= 0.6,
        "mean_top5_recall_at_least_0_6": mean_recall >= 0.6,
        "nearest_in_response_quartile_fraction_at_least_0_7": (
            nearest_fraction >= 0.7
        ),
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


def evaluate_spatial_directory(directory: Path) -> dict[str, Any]:
    files = {
        int("".join(character for character in path.stem if character.isdigit())): path
        for path in directory.glob("Exp*.mat")
    }
    cases: list[SpatialCaseResult] = []
    failures: list[dict[str, Any]] = []
    for experiment in DISPERSION_CASES:
        path = files.get(experiment)
        if path is None:
            failures.append({"experiment": experiment, "reason": "missing file"})
            continue
        try:
            cases.append(evaluate_spatial_case(load_hytunnel_spatial_case(path)))
        except Exception as exc:
            failures.append({
                "experiment": experiment,
                "reason": f"{type(exc).__name__}: {exc}",
            })
    aggregate = aggregate_spatial_cases(cases) if cases else None
    return {
        "cases": [asdict(case) for case in cases],
        "aggregate": aggregate,
        "failures": failures,
    }


__all__ = [
    "HyTunnelSpatialCase",
    "HyTunnelSpatialSensor",
    "SOURCE_POSITION_M",
    "aggregate_spatial_cases",
    "evaluate_spatial_case",
    "evaluate_spatial_directory",
    "load_hytunnel_spatial_case",
]
