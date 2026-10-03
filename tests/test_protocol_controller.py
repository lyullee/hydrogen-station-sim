from __future__ import annotations

import pytest

from h2station.protocol import (
    FuelingControllerParameters,
    FuelingObservation,
    FuelingSchedule,
    SampledFuelingController,
)
from h2station.tabulated import PropsSI
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario


def _observation(time_s: float, pressure_pa: float = 5.0e6) -> FuelingObservation:
    temperature_k = 298.15
    density = float(PropsSI(
        "Dmass", "P", pressure_pa, "T", temperature_k, "Hydrogen"
    ))
    return FuelingObservation(
        time_s=time_s,
        pressure_pa=pressure_pa,
        temperature_k=temperature_k,
        density_kg_m3=density,
        measured_mass_flow_kg_s=0.0,
    )


def test_slew_limit_does_not_drive_integrator_against_positive_ramp_error():
    controller = SampledFuelingController(FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=5.0e6,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.060,
    ))
    controller.update(_observation(0.0), 0.2)
    commands = [controller.update(_observation(index * 0.2), 0.2) for index in range(1, 5)]

    assert [command.valve_opening for command in commands] == pytest.approx(
        [0.006, 0.012, 0.018, 0.024]
    )
    assert controller._integral_error_pa_s >= 0.0


def test_flow_limiter_does_not_reverse_integrator_under_positive_pressure_error():
    """A transient high flow must not make the PI controller latch shut."""
    controller = SampledFuelingController(
        FuelingSchedule(
            target_pressure_pa=70.0e6,
            average_pressure_ramp_rate_pa_s=55_000.0,
            delivery_temperature_k=233.15,
            maximum_mass_flow_kg_s=0.060,
        ),
        FuelingControllerParameters(maximum_opening_slew_per_s=1.0),
    )
    controller.update(_observation(0.0, 2.6e6), 0.5)
    controller.update(_observation(1.0, 2.6e6), 0.5)
    limited = FuelingObservation(
        time_s=1.5,
        pressure_pa=2.6e6,
        temperature_k=298.15,
        density_kg_m3=_observation(1.5, 2.6e6).density_kg_m3,
        measured_mass_flow_kg_s=0.12,
    )
    controller.update(limited, 0.5)
    recovered = controller.update(_observation(2.0, 2.6e6), 0.5)

    assert recovered.valve_opening > 0.0
    assert controller._integral_error_pa_s >= 0.0


def test_precooler_trip_limit_follows_warm_delivery_temperature_class():
    built = build_reference_scenario(
        ReferenceScenario(delivery_temperature_k=265.0),
        UnavailableHyRAMBackend(),
    )

    assert built.simulator.safety_plc.limits.maximum_precooler_outlet_temperature_k == pytest.approx(280.0)
