from __future__ import annotations

from dataclasses import replace

import pytest

pytest.importorskip("CoolProp")

from h2station.proust_release_validation import (
    ProustReleasePoint,
    evaluate_series,
    predict_mass_flow_kg_s,
)


def _point(index: int, pressure_mpa: float = 20.0) -> ProustReleasePoint:
    base = ProustReleasePoint(
        case_id="synthetic-2mm",
        nozzle_diameter_mm=2.0,
        source_pressure_pa_abs=pressure_mpa * 1.0e6,
        source_temperature_k=285.0,
        measured_mass_flow_kg_s=0.01,
        digitization_uncertainty_kg_s=0.0001,
        source_figure="synthetic",
        point_index=index,
    )
    return replace(base, measured_mass_flow_kg_s=predict_mass_flow_kg_s(base))


def test_series_passes_when_measurements_equal_locked_model():
    points = [_point(index, 10.0 + 5.0 * index) for index in range(8)]
    result = evaluate_series(points)
    assert result.points == 8
    assert result.mass_flow_nrmse_percent_peak_measured == pytest.approx(0.0)
    assert result.joint_primary_screen_pass is True


def test_series_requires_eight_points_and_one_diameter():
    with pytest.raises(ValueError, match="at least eight"):
        evaluate_series([_point(index) for index in range(7)])
    mixed = [_point(index, 10.0 + index) for index in range(8)]
    mixed[-1] = replace(mixed[-1], nozzle_diameter_mm=3.0)
    with pytest.raises(ValueError, match="one case and diameter"):
        evaluate_series(mixed)

