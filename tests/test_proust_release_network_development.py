from __future__ import annotations

import json
from math import pi
from pathlib import Path

import numpy as np
import pytest

from h2station.proust_release_network_development import (
    ProustApparatusGeometry,
    proust_terminal_diameter_m,
)
from h2station.release_network import simulate_release_network


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "proust_release_network_development_protocol_2026_10_11.json"


def test_nominal_line_volume_is_derived_from_published_dimensions():
    geometry = ProustApparatusGeometry()
    assert geometry.supply_line_volume_m3 == pytest.approx(pi * 0.01**2 / 4.0 * 10.0)


def test_factory_preserves_source_line_terminal_and_valve_contract():
    geometry = ProustApparatusGeometry()
    inputs = geometry.to_network_inputs(
        source_pressure_pa_abs=90.0e6,
        source_temperature_k=293.15,
        terminal_diameter_m=proust_terminal_diameter_m(2.0),
    )
    assert inputs.source_volume_m3 == pytest.approx(0.025)
    assert inputs.line_volume_m3 == pytest.approx(geometry.supply_line_volume_m3)
    assert inputs.upstream_diameter_m == pytest.approx(0.010)
    assert inputs.terminal_diameter_m == pytest.approx(0.002)
    assert inputs.valve_opening_time_s == pytest.approx(0.1)


def test_factory_input_runs_through_development_network_with_mass_closure():
    geometry = ProustApparatusGeometry()
    result = simulate_release_network(
        np.asarray([0.0, 0.1, 0.2]),
        inputs=geometry.to_network_inputs(
            source_pressure_pa_abs=90.0e6,
            source_temperature_k=293.15,
            terminal_diameter_m=proust_terminal_diameter_m(1.0),
        ),
    )
    assert np.all(np.isfinite(result.terminal_mass_flow_kg_s))
    assert result.terminal_mass_flow_kg_s[-1] > 0.0
    assert result.mass_balance_residual_kg[-1] == pytest.approx(0.0, abs=1.0e-10)


def test_terminal_case_is_restricted_to_published_sizes():
    with pytest.raises(ValueError):
        proust_terminal_diameter_m(4.0)


def test_geometry_rejects_nonphysical_dimensions():
    with pytest.raises(ValueError):
        ProustApparatusGeometry(supply_line_length_m=0.0)


def test_protocol_explicitly_blocks_validation_and_runtime_promotion():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == "DEVELOPMENT_ONLY_NO_VALIDATION"
    assert protocol["implementation"]["runtime_application"] is False
    assert protocol["implementation"]["parameter_fitting"] is False
    assert "prospective" in protocol["promotion_rule"]
