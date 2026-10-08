from __future__ import annotations

import json
from pathlib import Path

import h5py
import numpy as np
import pytest
from scipy.io import savemat

from h2station.hytunnel_carpark_validation import (
    evaluate_dispersion_case,
    evaluate_mass_flow_case,
    load_hytunnel_mat,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/hytunnel_carpark_holdout_protocol_2026_10_08.json"


def _synthetic_mat(path: Path, experiment: int = 19) -> None:
    time = np.linspace(0.0, 120.0, 361)
    flow = np.where(time <= 90.0, 1.2 * np.exp(-time / 80.0), 0.0)
    vent = np.full_like(time, 365.0)
    concentration = np.zeros((len(time), 4))
    for index in range(1, len(time)):
        concentration[index] = concentration[index - 1] + 0.01 * flow[index - 1]
        concentration[index] *= np.exp(-vent[index - 1] / 3600.0 / 60.8 * (time[index] - time[index - 1]))
    pressure = 200.0 * np.exp(-time / 100.0)
    temperature = np.full_like(time, 20.0)
    savemat(
        path,
        {
            "S": {"time": time, "conc": concentration, "ID": np.arange(4), "pos": np.zeros((4, 3)), "iteration": np.arange(len(time)), "S0": np.zeros(4)},
            "MFM": {"time": time, "mfr": flow, "t0": 0.0, "p": pressure, "p_init": 200.0, "density": np.ones_like(time)},
            "Vent": {"time": time, "vfr": vent},
            "Tank": {"time": time, "p": pressure, "T": temperature},
        },
    )


def _synthetic_hdf5_mat(path: Path) -> None:
    time = np.linspace(0.0, 120.0, 361)
    with h5py.File(path, "w") as file:
        references = file.create_group("#refs#")
        sensor = file.create_group("S")
        time_cells = sensor.create_dataset("time", (4, 1), dtype=h5py.ref_dtype)
        concentration_cells = sensor.create_dataset("conc", (4, 1), dtype=h5py.ref_dtype)
        for index in range(4):
            sensor_time = references.create_dataset(f"time_{index}", data=time.reshape(1, -1))
            concentration = references.create_dataset(
                f"conc_{index}", data=(0.05 * (index + 1) * time).reshape(1, -1)
            )
            time_cells[index, 0] = sensor_time.ref
            concentration_cells[index, 0] = concentration.ref
        mfm = file.create_group("MFM")
        mfm.create_dataset("time", data=time.reshape(-1, 1))
        mfm.create_dataset("mfr", data=np.ones((1, len(time))))
        mfm.create_dataset("t0", data=[[0.0]])
        vent = file.create_group("Vent")
        vent.create_dataset("time", data=time.reshape(-1, 1))
        vent.create_dataset("vfr", data=np.full((1, len(time)), 365.0))
        tank = file.create_group("Tank")
        tank.create_dataset("time", data=time.reshape(-1, 1))
        tank.create_dataset("p", data=np.full((1, len(time)), 200.0))
        tank.create_dataset("T", data=np.full((1, len(time)), 20.0))


def test_mat_loader_preserves_documented_time_series(tmp_path: Path):
    path = tmp_path / "Exp19.mat"
    _synthetic_mat(path)
    trace = load_hytunnel_mat(path)
    assert trace.experiment == 19
    assert trace.concentration_volpct.shape == (361, 4)
    assert trace.mass_flow_g_s.shape == trace.mass_flow_time_s.shape
    assert trace.tank_pressure_bar is not None


def test_matlab_v73_hdf5_loader_dereferences_sensor_cells(tmp_path: Path):
    path = tmp_path / "Exp19.mat"
    _synthetic_hdf5_mat(path)
    trace = load_hytunnel_mat(path)
    assert trace.experiment == 19
    assert trace.concentration_volpct.shape == (361, 4)
    assert np.allclose(trace.concentration_volpct[:, 2], 0.15 * trace.sensor_time_s)
    assert trace.mass_flow_time_s.shape == (361,)


def test_hdf5_loader_treats_constant_flow_tank_group_as_optional(tmp_path: Path):
    path = tmp_path / "Exp04.mat"
    _synthetic_hdf5_mat(path)
    with h5py.File(path, "a") as file:
        del file["Tank/p"]
        del file["Tank/T"]
    trace = load_hytunnel_mat(path)
    assert trace.experiment == 4
    assert trace.tank_pressure_bar is None
    assert trace.tank_temperature_c is None


def test_evaluators_return_finite_metrics_without_time_shift_or_fit(tmp_path: Path):
    path = tmp_path / "Exp19.mat"
    _synthetic_mat(path)
    trace = load_hytunnel_mat(path)
    dispersion = evaluate_dispersion_case(trace)
    mass_flow = evaluate_mass_flow_case(trace)
    assert dispersion.points == 361
    assert dispersion.sensor_count == 4
    assert np.isfinite(dispersion.nrmse_percent_peak_measured)
    assert 30 <= mass_flow.points <= 121
    assert np.isfinite(mass_flow.spearman_rho)


def test_protocol_freezes_raw_timeseries_rules_before_mat_download():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == "FROZEN_BEFORE_RAW_MAT_TIMESERIES_DOWNLOAD"
    assert protocol["prior_access"]["raw_mat_files_downloaded"] is False
    assert protocol["prior_access"]["published_aggregate_outcomes_accessed"] is True
    assert protocol["parameter_policy"]["case_specific_fitting"] == "prohibited"
    assert protocol["aggregate_decision"]["retain_all_failures"] is True
