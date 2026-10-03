from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("CoolProp")

from h2station.preslhy_nonadiabatic import (
    DischaVesselParameters,
    evaluate_nonadiabatic_trace,
    simulate_nonadiabatic_blowdown,
)
from h2station.preslhy_validation import PreslhyTrace


def _trace() -> PreslhyTrace:
    return PreslhyTrace(
        case_id="synthetic-development-check",
        source_package="none",
        source_member="none",
        nozzle_diameter_mm=2.0,
        time_s=np.linspace(-0.5, 4.0, 46),
        pressure_bar_abs=np.linspace(200.0, 1.1, 46),
        initial_temperature_k=300.0,
        ambient_pressure_pa=101_325.0,
        pressure_unit_interpretation="synthetic_absolute",
        temperature_substituted=False,
        ambient_pressure_substituted=False,
    )


def test_discha_geometry_and_wall_capacity_are_report_derived():
    parameters = DischaVesselParameters()
    assert parameters.internal_area_m2 == pytest.approx(0.1106, rel=0.01)
    assert parameters.wall_heat_capacity_j_k == 14_000.0


def test_nonadiabatic_blowdown_conserves_direction_and_heats_gas_from_wall():
    times = np.linspace(0.1, 2.0, 20)
    result = simulate_nonadiabatic_blowdown(_trace(), times)
    assert np.all(np.diff(result.mass_kg) < 0.0)
    assert np.all(np.diff(result.pressure_pa) < 0.0)
    assert result.gas_temperature_k[-1] < result.wall_temperature_k[-1]
    assert np.all(result.mass_flow_kg_s >= 0.0)


def test_nonadiabatic_model_does_not_require_runtime_table_throat_domain():
    trace = _trace()
    result = simulate_nonadiabatic_blowdown(trace, np.linspace(0.1, 8.0, 40))
    assert result.pressure_pa[-1] < result.pressure_pa[0]


def test_development_evaluator_returns_original_screen_schema(monkeypatch):
    trace = _trace()
    monkeypatch.setattr(
        "h2station.preslhy_nonadiabatic.eligible_pressure_window",
        lambda _trace: (
            np.linspace(0.1, 2.0, 20),
            np.linspace(190.0, 20.0, 20),
        ),
    )
    result = evaluate_nonadiabatic_trace(trace)
    assert result.case_id == trace.case_id
    assert isinstance(result.joint_primary_screen_pass, bool)
    assert result.peak_mass_flow_kg_s > 0.0
