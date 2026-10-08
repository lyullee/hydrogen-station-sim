from __future__ import annotations

import json
from pathlib import Path

import h5py
import numpy as np

from h2station.hytunnel_spatial_validation import (
    SOURCE_POSITION_M,
    aggregate_spatial_cases,
    evaluate_spatial_case,
    load_hytunnel_spatial_case,
)
from h2station.spatial_detector import Point3D, orientation_aware_geometry_score


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/hytunnel_spatial_holdout_protocol_2026_10_08.json"


def _char_codes(text: str) -> np.ndarray:
    return np.asarray([[ord(character)] for character in text], dtype=np.uint16)


def _synthetic_spatial_mat(path: Path) -> None:
    positions_m = [
        Point3D(-5.0 + 0.25 * index, 0.30 + 0.08 * index, 0.05 * index)
        for index in range(24)
    ]
    time = np.linspace(0.0, 120.0, 361)
    with h5py.File(path, "w") as file:
        refs = file.create_group("#refs#")
        sensor = file.create_group("S")
        cells = {
            name: sensor.create_dataset(name, (len(positions_m), 1), dtype=h5py.ref_dtype)
            for name in ("ID", "pos", "time", "conc")
        }
        for index, position in enumerate(positions_m):
            score = orientation_aware_geometry_score(
                SOURCE_POSITION_M, position, "vertical"
            )
            payloads = {
                "ID": _char_codes(f"S{index + 1:02d}"),
                "pos": np.asarray([
                    position.x * 1000.0,
                    position.y * 1000.0,
                    position.z * 1000.0,
                ]),
                "time": time.reshape(1, -1),
                "conc": (score * np.linspace(0.0, 1.0, len(time))).reshape(1, -1),
            }
            for name, payload in payloads.items():
                dataset = refs.create_dataset(f"{name}_{index}", data=payload)
                cells[name][index, 0] = dataset.ref
        mfm = file.create_group("MFM")
        mfm.create_dataset("t0", data=[[0.0]])


def test_hytunnel_spatial_loader_maps_ids_positions_and_series(tmp_path: Path):
    path = tmp_path / "Exp04.mat"
    _synthetic_spatial_mat(path)
    case = load_hytunnel_spatial_case(path)
    assert case.experiment == 4
    assert len(case.sensors) == 24
    assert case.sensors[0].sensor_id == "S01"
    assert case.sensors[0].position_m == Point3D(-5.0, 0.30, 0.0)
    assert case.sensors[0].time_s.shape == (361,)


def test_exact_frozen_candidate_passes_ordered_synthetic_cases(tmp_path: Path):
    path = tmp_path / "Exp04.mat"
    _synthetic_spatial_mat(path)
    result = evaluate_spatial_case(load_hytunnel_spatial_case(path))
    assert result.valid_sensor_count == 24
    assert result.spearman_score_vs_robust_response > 0.99
    assert result.nearest_sensor_in_response_quartile is True
    aggregate = aggregate_spatial_cases([result] * 18)
    assert aggregate["joint_screen_pass"] is True


def test_loader_skips_only_channels_with_missing_position_cells(tmp_path: Path):
    path = tmp_path / "Exp04.mat"
    _synthetic_spatial_mat(path)
    with h5py.File(path, "a") as file:
        empty = file["#refs#"].create_dataset("empty_position", data=np.asarray([]))
        file["S/pos"][0, 0] = empty.ref
    case = load_hytunnel_spatial_case(path)
    assert len(case.sensors) == 23
    assert all(sensor.sensor_id != "S01" for sensor in case.sensors)


def test_protocol_freezes_spatial_endpoint_before_spatial_outcome_access():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == "FROZEN_BEFORE_HYTUNNEL_SPATIAL_OUTCOME_ACCESS"
    assert protocol["prior_access"]["per_sensor_spatial_responses_computed"] is False
    assert protocol["model_lock"]["parameter_fitting"] == "prohibited"
    assert protocol["aggregate_decision"]["all_declared_cases_must_be_eligible"] is True
