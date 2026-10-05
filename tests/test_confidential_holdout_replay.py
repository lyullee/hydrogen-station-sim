from __future__ import annotations

from h2station.controlled_station_replay import StationBoundaryProfile, fit_station_boundary_profile
from scripts.replay_confidential_station_holdout import _split_profile


def test_holdout_split_keeps_calibration_and_holdout_time_axes_separate():
    profile = StationBoundaryProfile(
        (0.0, 1.0, 2.0, 3.0, 4.0, 5.0),
        (40e6, 41e6, 42e6, 43e6, 44e6, 45e6),
    )
    calibration, holdout = _split_profile(profile, 0.5)
    assert calibration.time_s == (0.0, 1.0, 2.0)
    assert holdout.time_s == (0.0, 1.0, 2.0)
    assert calibration.pressure_pa[-1] < holdout.pressure_pa[0]
    summary = fit_station_boundary_profile(calibration)
    assert summary.sampled_rows == 3
