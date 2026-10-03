from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("CoolProp")

from h2station.ekoto_2012_validation import (
    EkotoFlowTrace,
    EkotoHoldoutResult,
    evaluate_ekoto_holdout,
    load_ekoto_flow_csv,
    predict_ekoto_mass_flow,
)


def test_synthetic_locked_model_trace_passes():
    time_s = np.linspace(0.0, 2.0, 25)
    predicted = predict_ekoto_mass_flow(time_s)
    result = evaluate_ekoto_holdout(
        EkotoFlowTrace(time_s=time_s, measured_mass_flow_kg_s=predicted)
    )
    assert isinstance(result, EkotoHoldoutResult)
    assert result.joint_primary_screen_pass is True
    assert result.mass_flow_nrmse_percent_peak_measured == pytest.approx(0.0)


def test_loader_rejects_too_few_points(tmp_path):
    path = tmp_path / "short.csv"
    path.write_text(
        "comment,,,,,,\ncomment,,,,,,\nx1,y1,x2,y2,x3,y3\n"
        + "\n".join(f",,,,{i},{10-i}" for i in range(10)),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="at least 15"):
        load_ekoto_flow_csv(path)
