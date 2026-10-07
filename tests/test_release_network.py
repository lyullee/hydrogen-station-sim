from __future__ import annotations

import numpy as np
import pytest

from h2station.release_network import ReleaseNetworkInputs, simulate_release_network


def _inputs(**overrides):
    values = dict(
        source_volume_m3=0.098,
        source_pressure_pa_abs=15.513e6,
        source_temperature_k=315.15,
        line_volume_m3=3.8e-4,
        line_initial_pressure_pa_abs=101_325.0,
        line_initial_temperature_k=293.15,
        upstream_diameter_m=0.003175,
        terminal_diameter_m=0.00794,
        valve_opening_time_s=0.05,
    )
    values.update(overrides)
    return ReleaseNetworkInputs(**values)


def test_release_network_has_finite_opening_and_distinct_line_state():
    time = np.linspace(0.0, 0.25, 51)
    result = simulate_release_network(time, inputs=_inputs())

    assert np.all(np.isfinite(result.line_pressure_pa_abs))
    assert result.line_pressure_pa_abs[1] > result.line_pressure_pa_abs[0]
    assert result.terminal_mass_flow_kg_s[0] == pytest.approx(0.0, abs=1.0e-9)
    assert result.terminal_mass_flow_kg_s[-1] > 0.0
    assert result.upstream_mass_flow_kg_s[1] < result.upstream_mass_flow_kg_s[-1]
    assert result.valve_opening_fraction[0] == 0.0
    assert result.valve_opening_fraction[-1] == 1.0
    assert result.line_pressure_profile_pa_abs.shape == (len(time), 1)


def test_declared_line_volumes_create_a_resolved_pressure_gradient():
    time = np.linspace(0.0, 0.08, 17)
    result = simulate_release_network(
        time,
        inputs=_inputs(
            line_segments=3,
            intersegment_diameter_m=0.0025,
            intersegment_discharge_coefficient=0.8,
            valve_opening_shape_exponent=2.0,
        ),
    )

    assert result.line_pressure_profile_pa_abs.shape == (len(time), 3)
    assert result.line_temperature_profile_k.shape == (len(time), 3)
    assert result.line_mass_profile_kg.shape == (len(time), 3)
    assert result.intersegment_mass_flow_kg_s.shape == (len(time), 2)
    assert result.valve_opening_fraction[4] == pytest.approx(0.16, abs=2.0e-6)
    assert result.line_pressure_profile_pa_abs[-1, 0] > result.line_pressure_profile_pa_abs[-1, -1]
    assert np.max(np.abs(result.mass_balance_residual_kg)) < 1.0e-8


def test_release_network_mass_closure_is_explicit():
    time = np.linspace(0.0, 0.5, 101)
    result = simulate_release_network(time, inputs=_inputs())
    source_loss = result.source_mass_kg[0] - result.source_mass_kg[-1]
    line_accumulation = result.line_mass_kg[-1] - result.line_mass_kg[0]
    terminal_release = np.trapezoid(result.terminal_mass_flow_kg_s, result.time_s)

    assert source_loss == pytest.approx(line_accumulation + terminal_release, rel=2.0e-4)
    assert result.cumulative_terminal_release_kg[-1] == pytest.approx(
        source_loss - line_accumulation, rel=1.0e-6,
    )
    assert np.max(np.abs(result.mass_balance_residual_kg)) < 1.0e-8


def test_release_network_energy_closure_is_explicit_for_wall_and_boundary_heat():
    time = np.linspace(0.0, 0.5, 101)
    result = simulate_release_network(
        time,
        inputs=_inputs(
            source_wall_mass_kg=2.0,
            line_wall_mass_kg=1.0,
            source_internal_area_m2=0.8,
            line_internal_area_m2=0.2,
            source_external_area_m2=1.0,
            line_external_area_m2=0.4,
            source_wall_temperature_k=305.15,
            line_wall_temperature_k=295.15,
            internal_heat_transfer_w_m2_k=100.0,
            external_heat_transfer_w_m2_k=15.0,
            ambient_temperature_k=293.15,
        ),
    )

    assert result.cumulative_terminal_enthalpy_j[-1] > 0.0
    assert np.max(np.abs(result.energy_balance_residual_j)) < 1.0


def test_release_network_rejects_nonphysical_inputs():
    with pytest.raises(ValueError, match="line_volume_m3"):
        _inputs(line_volume_m3=0.0)
    with pytest.raises(ValueError, match="discharge coefficients"):
        _inputs(upstream_discharge_coefficient=1.1)
    with pytest.raises(ValueError, match="intersegment_diameter_m"):
        _inputs(line_segments=2)


def test_zero_thermal_capacity_keeps_wall_temperature_fixed():
    time = np.linspace(0.0, 0.1, 11)
    result = simulate_release_network(
        time,
        inputs=_inputs(
            source_wall_mass_kg=0.0,
            line_wall_mass_kg=0.0,
            source_internal_area_m2=1.0,
            line_internal_area_m2=1.0,
            source_external_area_m2=1.0,
            line_external_area_m2=1.0,
            internal_heat_transfer_w_m2_k=100.0,
            external_heat_transfer_w_m2_k=100.0,
        ),
    )
    assert np.all(result.source_wall_temperature_k == pytest.approx(315.15))
    assert np.all(result.line_wall_temperature_k == pytest.approx(293.15))


def test_external_heat_transfer_uses_external_area():
    time = np.linspace(0.0, 0.2, 21)
    common = dict(
        source_wall_mass_kg=2.0,
        line_wall_mass_kg=1.0,
        source_internal_area_m2=0.0,
        line_internal_area_m2=0.0,
        external_heat_transfer_w_m2_k=250.0,
        ambient_temperature_k=293.15,
        source_wall_temperature_k=380.0,
        line_wall_temperature_k=380.0,
    )
    without_external_area = simulate_release_network(
        time, inputs=_inputs(**common, source_external_area_m2=0.0, line_external_area_m2=0.0)
    )
    with_external_area = simulate_release_network(
        time, inputs=_inputs(**common, source_external_area_m2=4.0, line_external_area_m2=2.0)
    )

    assert (
        with_external_area.source_wall_temperature_k[-1]
        < without_external_area.source_wall_temperature_k[-1]
    )
    assert (
        with_external_area.line_wall_temperature_k[-1]
        < without_external_area.line_wall_temperature_k[-1]
    )
