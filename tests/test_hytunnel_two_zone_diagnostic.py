from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import savemat

from h2station.hytunnel_carpark_validation import load_hytunnel_mat
from h2station.hytunnel_two_zone_diagnostic import (
    TwoZoneInputs,
    evaluate_two_zone_case,
    simulate_two_zone_concentration,
)


def _synthetic_mat(path: Path) -> None:
    time = np.linspace(0.0, 120.0, 361)
    flow = np.where(time <= 90.0, 1.2 * np.exp(-time / 80.0), 0.0)
    vent = np.full_like(time, 365.0)
    concentration = np.zeros((len(time), 4))
    for index in range(1, len(time)):
        concentration[index] = concentration[index - 1] + 0.01 * flow[index - 1]
        concentration[index] *= np.exp(-vent[index - 1] / 3600.0 / 60.8 * (time[index] - time[index - 1]))
    savemat(
        path,
        {
            "S": {"time": time, "conc": concentration},
            "MFM": {"time": time, "mfr": flow, "t0": 0.0},
            "Vent": {"time": time, "vfr": vent},
        },
    )


def test_two_zone_geometry_is_derived_from_published_enclosure_dimensions():
    inputs = TwoZoneInputs()
    assert 0.40 < inputs.source_zone_fraction < 0.42
    assert np.isclose(inputs.source_zone_volume_m3 + inputs.bulk_zone_volume_m3, 60.8)


def test_two_zone_model_preserves_nonnegative_finite_mean(tmp_path: Path):
    path = tmp_path / "Exp04.mat"
    _synthetic_mat(path)
    trace = load_hytunnel_mat(path)
    time, measured, predicted, source, bulk = simulate_two_zone_concentration(trace)
    assert len(time) == len(measured) == len(predicted) == len(source) == len(bulk)
    assert np.all(np.isfinite(predicted))
    assert np.all(predicted >= 0.0)
    assert np.all(source >= 0.0)
    assert np.all(bulk >= 0.0)


def test_two_zone_evaluator_has_same_frozen_screen_shape(tmp_path: Path):
    path = tmp_path / "Exp04.mat"
    _synthetic_mat(path)
    result = evaluate_two_zone_case(load_hytunnel_mat(path))
    assert result.points > 30
    assert np.isfinite(result.nrmse_percent_peak_measured)
