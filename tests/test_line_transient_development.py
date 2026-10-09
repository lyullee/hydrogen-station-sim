from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("CoolProp")

from h2station.line_transient_development import (
    LineTransientParameters,
    simulate_line_transient,
)


def test_two_volume_release_keeps_source_and_line_states_finite():
    parameters = LineTransientParameters(
        source_volume_m3=0.098,
        source_pressure_pa_abs=15.513e6,
        source_temperature_k=315.15,
        line_length_m=7.6,
        line_inner_diameter_m=0.00794,
        outlet_inner_diameter_m=0.003175,
    )
    time = np.linspace(0.0, 1.0, 21)
    result = simulate_line_transient(time, parameters=parameters)

    assert result.time_s.shape == time.shape
    assert np.isfinite(result.source_pressure_pa).all()
    assert np.isfinite(result.line_pressure_pa).all()
    assert np.isfinite(result.source_flow_kg_s).all()
    assert np.isfinite(result.outlet_flow_kg_s).all()
    assert np.all(result.source_mass_kg > 0.0)
    assert np.all(result.line_mass_kg > 0.0)
    assert result.source_pressure_pa[-1] < result.source_pressure_pa[0]
    assert result.line_pressure_pa[-1] > result.line_pressure_pa[0]
    assert np.max(result.outlet_flow_kg_s) > 0.0


def test_invalid_time_grid_is_rejected():
    parameters = LineTransientParameters(
        source_volume_m3=0.1,
        source_pressure_pa_abs=10.0e6,
        source_temperature_k=293.15,
        line_length_m=1.0,
        line_inner_diameter_m=0.003,
        outlet_inner_diameter_m=0.001,
    )
    with pytest.raises(ValueError, match="strictly increasing"):
        simulate_line_transient(np.asarray([0.0, 0.1, 0.1]), parameters=parameters)


def test_finite_valve_response_uses_a_stable_real_gas_integration():
    parameters = LineTransientParameters(
        source_volume_m3=0.098,
        source_pressure_pa_abs=15.513e6,
        source_temperature_k=315.15,
        line_length_m=7.6,
        line_inner_diameter_m=0.00794,
        outlet_inner_diameter_m=0.003175,
        source_valve_time_constant_s=0.5,
    )
    result = simulate_line_transient(
        np.linspace(0.0, 2.0, 9), parameters=parameters
    )

    assert np.isfinite(result.source_pressure_pa).all()
    assert np.isfinite(result.outlet_flow_kg_s).all()
    assert result.source_flow_kg_s[0] == pytest.approx(0.0)
    assert np.max(result.source_flow_kg_s) > 0.0
