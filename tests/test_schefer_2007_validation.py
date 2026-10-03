from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("CoolProp")

from h2station.schefer_2007_validation import (
    Schefer2007HoldoutResult,
    Schefer2007PressureTrace,
    evaluate_schefer_2007_holdout,
    load_schefer_2007_pressure_csv,
    simulate_adiabatic_blowdown_pressure,
)


def test_synthetic_trace_from_locked_model_passes_primary_screens():
    time_s = np.linspace(0.0, 900.0, 31)
    predicted = simulate_adiabatic_blowdown_pressure(time_s)
    result = evaluate_schefer_2007_holdout(
        Schefer2007PressureTrace(time_s=time_s, measured_pressure_psi=predicted)
    )
    assert isinstance(result, Schefer2007HoldoutResult)
    assert result.joint_primary_screen_pass is True
    assert result.pressure_nrmse_percent_initial_measured == pytest.approx(0.0)


def test_loader_rejects_too_few_points(tmp_path):
    path = tmp_path / "short.csv"
    path.write_text(
        "comment,,,\ncomment,,,\nx1,y1,x2,y2\n"
        + "\n".join(f"{i},{6000-i},," for i in range(10)),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="at least 15"):
        load_schefer_2007_pressure_csv(path)
