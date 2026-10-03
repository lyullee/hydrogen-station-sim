from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from h2station.api import app
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario
from h2station.safety_runtime import FaultEvent, FaultKind
from h2station.thermo import HydrogenEOS
from h2station.tabulated import PropsSI
from h2station.validation import (
    DynamicModelValidator,
    OutputChannel,
    ValidationCriterion,
    ValidationTrace,
    mass_balance_residual_kg,
)


class DetectorBackend:
    available = True
    name = "test-detector"

    def evaluate_release(self, request):
        return {
            "status": "calculated",
            "detector_concentrations": {"D-01": 0.03},
            "mass_flow_override_kg_s": request.mass_flow_override_kg_s,
        }


@pytest.mark.parametrize("pressure,temperature", [(5.0e6, 233.15), (35.0e6, 298.15), (90.0e6, 360.0)])
def test_coolprop_rho_u_round_trip(pressure, temperature):
    eos = HydrogenEOS()
    reference = eos.state_pt(pressure, temperature)
    recovered = eos.state_rho_u(reference.density, reference.internal_energy)
    assert recovered.pressure == pytest.approx(reference.pressure, rel=1.0e-8)
    assert recovered.temperature == pytest.approx(reference.temperature, rel=1.0e-8)


def test_tabulated_rho_u_boundary_is_bounded_for_cold_blowdown():
    """Adjacent density rows do not reject an in-table 60 K boundary state."""
    pressure = PropsSI("P", "Dmass", 0.640865, "Umass", 625703.0)
    temperature = PropsSI("T", "Dmass", 0.640865, "Umass", 625703.0)
    assert np.isfinite(pressure)
    assert 60.0 <= temperature <= 60.1


def test_validation_and_mass_balance():
    time = np.array([0.0, 1.0, 2.0])
    reference = ValidationTrace(
        OutputChannel.VEHICLE_GAS_PRESSURE,
        time,
        np.array([1.0, 2.0, 3.0]),
        "Pa",
        "reference",
        "case-1",
    )
    simulation = ValidationTrace(
        OutputChannel.VEHICLE_GAS_PRESSURE,
        time,
        np.array([1.0, 2.0, 3.0]),
        "Pa",
        "simulation",
        "case-1",
    )
    result = DynamicModelValidator().compare(
        simulation,
        reference,
        ValidationCriterion(maximum_nrmse=1.0e-12),
    )
    assert result.passed
    residual = mass_balance_residual_kg(
        time,
        np.array([1.0, 1.0, 1.0]),
        np.zeros(3),
        2.0,
        4.0,
    )
    assert abs(residual) < 1.0e-12


def test_short_nominal_closed_loop():
    config = ReferenceScenario(duration_s=0.4, control_period_s=0.2)
    built = build_reference_scenario(config, UnavailableHyRAMBackend())
    samples = []
    result = built.simulator.simulate(
        built.initial_state,
        config.duration_s,
        config.control_period_s,
        sample_callback=samples.append,
    )
    assert len(result.time_s) == 3
    assert np.all(np.isfinite(result.states))
    assert result.vehicle_pressure_pa[-1] > 0.0
    assert len(samples) == len(result.time_s)
    assert all(np.isfinite(sample.precooler_outlet_temperature_k) for sample in samples)


def test_leak_concentration_trips_esd():
    leak = FaultEvent(
        event_id="test-leak",
        kind=FaultKind.HYDROGEN_LEAK,
        target="dispenser.hose",
        start_time_s=0.0,
        leak_diameter_m=1.0e-4,
        indoor=True,
    )
    config = ReferenceScenario(
        duration_s=1.0,
        control_period_s=0.2,
        fault_events=(leak,),
    )
    built = build_reference_scenario(config, DetectorBackend())
    result = built.simulator.simulate(
        built.initial_state,
        config.duration_s,
        config.control_period_s,
    )
    assert result.esd_time_s is not None
    assert any(command.esd_latched for command in result.safety_commands)
    assert np.max(result.leak_mass_flow_by_release["test-leak"]) > 0.0


def test_api_and_frontend_are_packaged():
    paths = {route.path for route in app.routes}
    assert "/api/health" in paths
    assert "/api/simulations" in paths
    root = Path(__file__).resolve().parents[1]
    assert (root / "web" / "index.html").is_file()
    assert (root / "web" / "app.js").is_file()
    assert (root / "web" / "styles.css").is_file()
