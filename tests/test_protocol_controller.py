from __future__ import annotations

import pytest

from h2station.protocol import (
    FuelingObservation,
    FuelingSchedule,
    SampledFuelingController,
)
from h2station.tabulated import PropsSI


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
