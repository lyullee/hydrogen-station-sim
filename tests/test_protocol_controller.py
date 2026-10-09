from __future__ import annotations

import pytest

from h2station.protocol import (
    CommunicationLossPolicy,
    FuelingControllerParameters,
    FuelingCommunicationState,
    FuelingObservation,
    FuelingPhase,
    FuelingSchedule,
    FuelingTemperatureCategory,
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


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        (FuelingCommunicationState.ABORT, "communication-abort"),
        (FuelingCommunicationState.HALT, "communication-halt"),
        (FuelingCommunicationState.DATA_LOSS, "communication-data-loss"),
        (FuelingCommunicationState.INVALID_CRC, "communication-invalid-crc"),
        (FuelingCommunicationState.INVALID_VALUE, "communication-invalid-value"),
    ],
)
def test_communication_faults_conservatively_terminate_fueling(state, reason):
    controller = SampledFuelingController(FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=1.0e5,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.060,
    ))
    baseline = _observation(0.0)
    controller.update(baseline, 0.2)
    faulted = FuelingObservation(
        time_s=1.0,
        pressure_pa=baseline.pressure_pa,
        temperature_k=baseline.temperature_k,
        density_kg_m3=baseline.density_kg_m3,
        measured_mass_flow_kg_s=0.01,
        communication_state=state,
    )

    command = controller.update(faulted, 0.2)

    assert command.phase is FuelingPhase.ABORTED
    assert command.valve_opening == 0.0
    assert command.stop_reason == reason
    assert command.communication_state is state


def test_data_loss_can_hold_and_resume_when_explicitly_configured():
    controller = SampledFuelingController(FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=1.0e5,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.060,
        communication_loss_policy=CommunicationLossPolicy.HOLD_AND_RESUME,
    ))
    controller.update(_observation(0.0), 0.2)
    lost = FuelingObservation(
        **{
            **_observation(1.0).__dict__,
            "communication_state": FuelingCommunicationState.DATA_LOSS,
        }
    )

    held = controller.update(lost, 0.2)
    resumed = controller.update(_observation(2.0), 0.2)

    assert held.phase is FuelingPhase.COMMUNICATION_HOLD
    assert held.valve_opening == 0.0
    assert held.stop_reason == "communication-data-loss-hold"
    assert resumed.phase is FuelingPhase.FILLING
    assert resumed.valve_opening > 0.0


def test_minimum_startup_time_holds_then_allows_flow():
    controller = SampledFuelingController(FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=1.0e5,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.060,
        minimum_startup_time_s=2.0,
    ))

    held = controller.update(_observation(0.0), 0.2)
    released = controller.update(_observation(2.0), 0.2)

    assert held.phase is FuelingPhase.FILLING
    assert held.stop_reason == "minimum-startup-time"
    assert held.valve_opening == 0.0
    assert released.phase is FuelingPhase.FILLING
    assert released.valve_opening > 0.0


def test_flow_before_minimum_startup_time_aborts():
    controller = SampledFuelingController(FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=1.0e5,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.060,
        minimum_startup_time_s=2.0,
    ))
    controller.update(_observation(0.0), 0.2)
    early_flow = FuelingObservation(
        **{**_observation(1.0).__dict__, "measured_mass_flow_kg_s": 0.01}
    )

    command = controller.update(early_flow, 0.2)

    assert command.phase is FuelingPhase.ABORTED
    assert command.stop_reason == "startup-flow-before-minimum-time"


def test_maximum_startup_mass_limit_aborts_inside_window():
    controller = SampledFuelingController(FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=1.0e5,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.060,
        maximum_startup_mass_kg=0.05,
        startup_mass_window_s=3.0,
    ))
    controller.update(_observation(0.0), 0.5)
    high_startup_mass = FuelingObservation(
        **{**_observation(1.0).__dict__, "measured_mass_flow_kg_s": 0.06}
    )

    command = controller.update(high_startup_mass, 1.0)

    assert command.phase is FuelingPhase.ABORTED
    assert command.stop_reason == "maximum-startup-mass"
    assert command.delivered_mass_kg == pytest.approx(0.06)


@pytest.mark.parametrize(
    ("pressure_pa", "expected_reason"),
    [
        (3.5e6, "lower-pressure-corridor"),
        (6.5e6, "upper-pressure-corridor"),
    ],
)
def test_configurable_pressure_corridor_aborts_outside_reference(
    pressure_pa, expected_reason
):
    controller = SampledFuelingController(FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=1.0e5,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.060,
        pressure_corridor_lower_tolerance_pa=1.0e6,
        pressure_corridor_upper_tolerance_pa=1.0e6,
    ))
    controller.update(_observation(0.0, 5.0e6), 0.2)

    command = controller.update(_observation(1.0, pressure_pa), 0.2)

    assert command.phase is FuelingPhase.ABORTED
    assert command.stop_reason == expected_reason


def test_selected_t30_category_rejects_out_of_range_delivery_temperature():
    controller = SampledFuelingController(FuelingSchedule(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=1.0e5,
        delivery_temperature_k=243.15,
        maximum_mass_flow_kg_s=0.060,
        fueling_temperature_category=FuelingTemperatureCategory.T30,
    ))
    baseline = _observation(0.0)
    too_cold = FuelingObservation(
        **{**baseline.__dict__, "delivery_temperature_k": 235.15}
    )

    command = controller.update(too_cold, 0.2)

    assert command.phase is FuelingPhase.ABORTED
    assert command.stop_reason == "fuel-delivery-temperature-category"
    assert command.fueling_temperature_category == "T30"


def test_public_temperature_category_boundaries_are_explicit():
    common = dict(
        target_pressure_pa=70.0e6,
        average_pressure_ramp_rate_pa_s=1.0e5,
        delivery_temperature_k=243.15,
        maximum_mass_flow_kg_s=0.060,
    )

    assert FuelingSchedule(
        **common, fueling_temperature_category=FuelingTemperatureCategory.T40
    ).temperature_category_bounds_k() == pytest.approx((233.15, 240.15))
    assert FuelingSchedule(
        **common, fueling_temperature_category=FuelingTemperatureCategory.T30
    ).temperature_category_bounds_k() == pytest.approx((240.15, 247.15))
    assert FuelingSchedule(
        **common, fueling_temperature_category=FuelingTemperatureCategory.T20
    ).temperature_category_bounds_k() == pytest.approx((247.15, 255.65))


def test_reference_scenario_wires_training_conformance_controls_to_both_dispensers():
    built = build_reference_scenario(
        ReferenceScenario(
            minimum_startup_time_s=1.5,
            maximum_startup_mass_kg=0.08,
            startup_mass_window_s=4.0,
            pressure_corridor_lower_tolerance_pa=2.0e6,
            pressure_corridor_upper_tolerance_pa=3.0e6,
            fueling_temperature_category=FuelingTemperatureCategory.T30,
            communication_loss_policy=CommunicationLossPolicy.HOLD_AND_RESUME,
        ),
        UnavailableHyRAMBackend(),
    )

    for controller in (
        built.station.partial_station.controller,
        built.station.secondary_partial_station.controller,
    ):
        schedule = controller.schedule
        assert schedule.minimum_startup_time_s == pytest.approx(1.5)
        assert schedule.maximum_startup_mass_kg == pytest.approx(0.08)
        assert schedule.startup_mass_window_s == pytest.approx(4.0)
        assert schedule.pressure_corridor_lower_tolerance_pa == pytest.approx(2.0e6)
        assert schedule.pressure_corridor_upper_tolerance_pa == pytest.approx(3.0e6)
        assert schedule.fueling_temperature_category is FuelingTemperatureCategory.T30
        assert schedule.communication_loss_policy is CommunicationLossPolicy.HOLD_AND_RESUME


def test_reference_scenario_wires_optional_leak_check_to_both_dispensers():
    built = build_reference_scenario(
        ReferenceScenario(
            leak_check_pressure_interval_pa=3.0e6,
            leak_check_pause_s=5.0,
            leak_check_pressure_drop_tolerance_pa=12_000.0,
        ),
        UnavailableHyRAMBackend(),
    )

    for controller in (
        built.station.partial_station.controller,
        built.station.secondary_partial_station.controller,
    ):
        schedule = controller.schedule
        assert schedule.leak_check_pressure_interval_pa == pytest.approx(3.0e6)
        assert schedule.leak_check_pause_s == pytest.approx(5.0)
        assert schedule.leak_check_pressure_drop_tolerance_pa == pytest.approx(12_000.0)
