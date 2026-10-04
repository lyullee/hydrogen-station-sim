from __future__ import annotations

import pytest

from h2station.protocol import (
    FuelingControllerParameters,
    FuelingObservation,
    FuelingPhase,
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


def test_reference_scenario_wires_gas_temperature_stop_into_both_schedules():
    built = build_reference_scenario(
        ReferenceScenario(maximum_gas_temperature_k=401.15),
        UnavailableHyRAMBackend(),
    )

    assert built.station.partial_station.controller.schedule.maximum_gas_temperature_k == pytest.approx(401.15)
    assert built.station.secondary_partial_station.controller.schedule.maximum_gas_temperature_k == pytest.approx(401.15)


def test_delivery_temperature_profile_is_interpolated_in_controller_commands():
    schedule = FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=1.0e5,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.060,
        delivery_temperature_profile_k=((0.0, 240.0), (10.0, 260.0)),
    )
    controller = SampledFuelingController(schedule)
    at_start = controller.update(_observation(0.0), 1.0)
    at_mid = controller.update(_observation(5.0), 1.0)
    after_profile = controller.update(_observation(15.0), 1.0)

    assert at_start.delivery_temperature_target_k == pytest.approx(240.0)
    assert at_mid.delivery_temperature_target_k == pytest.approx(250.0)
    assert after_profile.delivery_temperature_target_k == pytest.approx(260.0)


def test_delivery_temperature_profile_rejects_nonmonotonic_time():
    with pytest.raises(ValueError, match="strictly increasing"):
        FuelingSchedule(
            target_pressure_pa=70.0e6,
            average_pressure_ramp_rate_pa_s=1.0e5,
            delivery_temperature_k=233.15,
            maximum_mass_flow_kg_s=0.060,
            delivery_temperature_profile_k=((1.0, 240.0), (1.0, 260.0)),
        )


def test_pressure_reference_profile_replaces_constant_ramp():
    schedule = FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=1.0e5,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.060,
        pressure_reference_profile_pa=((0.0, 5.0e6), (10.0, 25.0e6)),
    )
    controller = SampledFuelingController(schedule)
    at_start = controller.update(_observation(0.0), 1.0)
    at_mid = controller.update(_observation(5.0), 1.0)
    after_profile = controller.update(_observation(15.0), 1.0)

    assert at_start.reference_pressure_pa == pytest.approx(5.0e6)
    assert at_mid.reference_pressure_pa == pytest.approx(15.0e6)
    assert after_profile.reference_pressure_pa == pytest.approx(25.0e6)


def test_optional_pressure_hold_leak_check_pauses_and_resumes_without_decay():
    schedule = FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=5.0e6,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.060,
        leak_check_pressure_interval_pa=2.0e6,
        leak_check_pause_s=5.0,
    )
    controller = SampledFuelingController(schedule)

    filling = controller.update(_observation(0.0, 5.0e6), 1.0)
    paused = controller.update(_observation(1.0, 7.1e6), 1.0)
    waiting = controller.update(_observation(3.0, 7.1e6), 1.0)
    resumed = controller.update(_observation(6.0, 7.1e6), 1.0)

    assert filling.phase is FuelingPhase.FILLING
    assert paused.phase is FuelingPhase.LEAK_CHECK
    assert paused.valve_opening == 0.0
    assert paused.stop_reason == "leak-check-pause"
    assert waiting.phase is FuelingPhase.LEAK_CHECK
    assert resumed.phase is FuelingPhase.FILLING
    assert resumed.valve_opening > 0.0


def test_pressure_hold_leak_check_aborts_when_pressure_decays():
    schedule = FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=5.0e6,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.060,
        leak_check_pressure_interval_pa=2.0e6,
        leak_check_pause_s=5.0,
        leak_check_pressure_drop_tolerance_pa=10_000.0,
    )
    controller = SampledFuelingController(schedule)

    controller.update(_observation(0.0, 5.0e6), 1.0)
    controller.update(_observation(1.0, 7.1e6), 1.0)
    failed = controller.update(_observation(6.0, 7.0e6), 1.0)

    assert failed.phase is FuelingPhase.ABORTED
    assert failed.valve_opening == 0.0
    assert failed.stop_reason == "leak-test-pressure-drop"


def test_pressure_hold_leak_check_parameters_are_validated():
    with pytest.raises(ValueError, match="interval"):
        FuelingSchedule(
            target_pressure_pa=70.0e6,
            average_pressure_ramp_rate_pa_s=1.0e5,
            delivery_temperature_k=233.15,
            maximum_mass_flow_kg_s=0.060,
            leak_check_pressure_interval_pa=0.0,
        )
    with pytest.raises(ValueError, match="pause"):
        FuelingSchedule(
            target_pressure_pa=70.0e6,
            average_pressure_ramp_rate_pa_s=1.0e5,
            delivery_temperature_k=233.15,
            maximum_mass_flow_kg_s=0.060,
            leak_check_pause_s=0.0,
        )
