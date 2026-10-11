from __future__ import annotations

import numpy as np
import pytest

from h2station.usn_ignited_jet import (
    calibrated_pressure_bar_g,
    load_ignited_jet_csv,
    summarize_raw_trace,
)


def test_loader_preserves_decimal_comma_raw_channels(tmp_path):
    path = tmp_path / "Ign_pipe_geom_EXP_001.csv"
    path.write_text(
        "Tid;Kanal Trigger;Kanal trykk pos. 0;Kanal Trykk pos.1;Kanal Trykk pos. 2;Kanal Trykk pos.3;Kanal Nozzle pressure\n"
        "(ms);(V);(V);(V);(V);(V);(V)\n"
        "-0,5;0,0;-0,1;0,2;0,0;0,1;1,0\n"
        "0,0;0,1;-0,2;0,3;0,0;0,2;1,5\n",
        encoding="utf-8",
    )
    trace = load_ignited_jet_csv(path)
    assert trace.row_count == 2
    assert trace.time_s[0] == pytest.approx(-0.0005)
    assert trace.pressure_channel_v.shape == (2, 4)
    assert trace.pressure_channel_v[1, 0] == pytest.approx(-0.2)
    summary = summarize_raw_trace(trace)
    assert summary["calibration_applied"] is False
    assert summary["time_strictly_increasing"] is True


def test_loader_can_bound_inspection_without_reordering(tmp_path):
    path = tmp_path / "trace.csv"
    path.write_text(
        "labels\nunits\n0,0;0,0;0,0;0,0;0,0;0,0;1,0\n"
        "-1,0;0,0;0,0;0,0;0,0;0,0;1,0\n",
        encoding="utf-8",
    )
    trace = load_ignited_jet_csv(path, max_rows=1)
    assert trace.row_count == 1
    assert trace.time_ms[0] == pytest.approx(0.0)


def test_calibration_requires_explicit_parameters():
    result = calibrated_pressure_bar_g(
        np.asarray([0.0, 1.0]), bar_per_volt=2.0, zero_voltage_v=0.5, sign=-1.0
    )
    assert np.allclose(result, [1.0, -1.0])
    with pytest.raises(ValueError):
        calibrated_pressure_bar_g([0.0], bar_per_volt=0.0)
