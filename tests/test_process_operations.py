"""Operator-controlled flow paths, finite supply, and sampled safety relief."""

from copy import deepcopy
from dataclasses import replace
from time import monotonic, sleep

import numpy as np
import pytest
from fastapi.testclient import TestClient

from h2station.api import ProcessSettings, _analyze_frame, app
from h2station.operations import ProcessRuntime
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario
from h2station.safety_runtime import FaultEvent, FaultKind


def _station(settings: dict):
    config = ReferenceScenario(duration_s=0.4, control_period_s=0.2)
    built = build_reference_scenario(config, UnavailableHyRAMBackend())
    process = ProcessRuntime(settings)
    built.simulator.process_runtime = process
    built.station.compressor_suction = lambda _time: process.trailer_state()
    return built, process


def test_idle_is_physically_frozen_and_vehicle_paths_are_independent():
    settings = ProcessSettings().model_dump()
    built, process = _station(settings)
    idle = built.simulator.simulate(built.initial_state, .4, .2)
    np.testing.assert_array_equal(idle.states[0], idle.states[-1])
    assert np.all(idle.nozzle_1_mass_flow_kg_s == 0)
    assert np.all(idle.nozzle_2_mass_flow_kg_s == 0)

    settings["vehicle_1"] = True
    process.configure(settings)
    filling = built.simulator.simulate(idle.final_state, .4, .2,
                                       start_time_s=.4, reset_runtime=False)
    assert filling.vehicle_pressure_pa[-1] > filling.vehicle_pressure_pa[0]
    assert filling.vehicle_2_pressure_pa[-1] == pytest.approx(filling.vehicle_2_pressure_pa[0])
    assert np.all(filling.nozzle_2_mass_flow_kg_s == 0)

    settings["vehicle_1"] = False
    process.configure(settings)
    stopped = built.simulator.simulate(filling.final_state, .4, .2,
                                       start_time_s=.8, reset_runtime=False)
    np.testing.assert_array_equal(stopped.states[0], stopped.states[-1])
    assert np.all(stopped.nozzle_1_mass_flow_kg_s == 0)


def test_recharge_needs_both_commands_and_depletes_trailer():
    settings = ProcessSettings().model_dump()
    settings["trailer_supply"] = True
    built, process = _station(settings)
    supply_only = built.simulator.simulate(built.initial_state, .4, .2)
    assert process.trailer_mass_kg == pytest.approx(settings["trailer_capacity_kg"])
    assert all(bank is None for bank in supply_only.recharge_bank)

    settings["pressure_recharge"] = True
    process.configure(settings)
    charging = built.simulator.simulate(supply_only.final_state, .4, .2,
                                        start_time_s=.4, reset_runtime=False)
    assert any(bank is not None for bank in charging.recharge_bank)
    assert process.trailer_mass_kg < settings["trailer_capacity_kg"]
    assert process.snapshot()["trailer_pressure_mpa"] < settings["trailer_pressure_mpa"]
    bank_gain = charging.final_state.banks[2].hydrogen_mass_kg - supply_only.final_state.banks[2].hydrogen_mass_kg
    assert bank_gain > 0
    assert bank_gain == pytest.approx(settings["trailer_capacity_kg"] - process.trailer_mass_kg, rel=1e-5)


def test_pressure_target_auto_stop_and_relief_hysteresis_with_mass_sink():
    settings = ProcessSettings().model_dump()
    settings.update(trailer_supply=True, pressure_recharge=True,
                    recharge_target_low_mpa=44.0, recharge_target_medium_mpa=64.0,
                    recharge_target_high_mpa=89.0)
    settings["relief_valves"]["high"].update(open_mpa=89.0, close_mpa=88.5, orifice_mm=.1)
    built, process = _station(settings)
    samples = []
    trajectory = built.simulator.simulate(built.initial_state, .4, .2, sample_callback=samples.append)
    assert process.snapshot()["relief_open"]["high"]
    assert np.max(trajectory.leak_mass_flow_by_release["relief-high"]) > 0
    assert any("relief-open:cascade.high" in sample.active_faults for sample in samples)
    assert any(snapshot.release_id == "relief-high" for sample in trajectory.risk_snapshots for snapshot in sample)
    assert process.snapshot()["settings"]["trailer_supply"] is False
    assert process.snapshot()["settings"]["pressure_recharge"] is False

    # Isolate relief to check that its released amount leaves the high bank.
    relief_only = deepcopy(settings)
    relief_only.update(trailer_supply=False, pressure_recharge=False)
    other, other_process = _station(relief_only)
    release = other.simulator.simulate(other.initial_state, .4, .2)
    assert release.final_state.banks[2].hydrogen_mass_kg < other.initial_state.banks[2].hydrogen_mass_kg
    assert other_process.relief_events({key: (88.4e6 if key == "high" else 0)
                                        for key in other_process.relief_open}, .6) == ()
    assert not other_process.snapshot()["relief_open"]["high"]
    reopened = other_process.relief_events({key: (89.1e6 if key == "high" else 0)
                                            for key in other_process.relief_open}, .8)
    assert len(reopened) == 1 and reopened[0].event_id == "relief-high"
    relief_only["relief_valves"]["high"]["enabled"] = False
    other_process.configure(relief_only)
    assert other_process.relief_events({key: (90e6 if key == "high" else 0)
                                        for key in other_process.relief_open}, 1.0) == ()


def test_relief_open_is_an_explicit_operator_warning_even_without_sensor_rule():
    frame = {"vehicle_pressure_mpa": 5, "vehicle_2_pressure_mpa": 8,
             "vehicle_temperature_c": 25, "vehicle_2_temperature_c": 25,
             "total_leak_flow_g_s": .02, "hazop": {"active": [], "releases": [
                 {"release_id": "relief-medium", "mass_flow_g_s": .02}]},
             "process_operations": {"relief_open": {"medium": True}},
             "active_faults": ["relief-open:cascade.medium"]}
    assessment = _analyze_frame(frame)
    assert assessment["status"] == "WARNING"
    assert any("중압 저장뱅크" in finding and "안전밸브 개방" in finding
               for finding in assessment["findings"])
    frame["active_faults"].append("external-fire:cascade.medium")
    assert _analyze_frame(frame)["status"] == "CRITICAL"


def test_recharge_auto_stop_switch_bypasses_bank_targets():
    settings = ProcessSettings().model_dump()
    settings.update(trailer_supply=True, pressure_recharge=True,
                    recharge_target_low_mpa=44.0, recharge_target_medium_mpa=64.0,
                    recharge_target_high_mpa=90.5)
    process = ProcessRuntime(settings)
    process.stop_recharge_at_targets((43.9e6, 63.9e6, 90.4e6))
    assert process.requested("pressure_recharge")
    process.stop_recharge_at_targets((45e6, 65e6, 95e6))
    assert not process.requested("trailer_supply")
    assert not process.requested("pressure_recharge")
    assert process.snapshot()["stop_reason"]["pressure_recharge"] == "bank-target"

    settings.update(recharge_auto_stop=False)
    process.configure(settings)
    process.stop_recharge_at_targets((45e6, 65e6, 95e6))
    assert process.requested("trailer_supply")
    assert process.requested("pressure_recharge")


def test_operator_bank_target_does_not_stop_one_mpa_early():
    built, _ = _station(ProcessSettings().model_dump())
    gases = tuple(bank.gas_state(state) for bank, state in
                  zip(built.station.banks, built.initial_state.banks))
    near_target = (gases[0], replace(gases[1], pressure_pa=67.5e6), gases[2])
    selected = built.station.supervisor.select_recharge_bank(
        built.station.banks, near_target, None,
        target_pressures_pa=(44e6, 68e6, 89e6))
    assert selected == 1


def test_opt_in_measured_boundary_profile_can_set_dispatch_margin():
    """The measured station-boundary profile must affect bank selection only when opted in."""
    default = build_reference_scenario(
        ReferenceScenario(), UnavailableHyRAMBackend()
    )
    calibrated = build_reference_scenario(
        ReferenceScenario(station_dispatch_pressure_margin_pa=540_000.0),
        UnavailableHyRAMBackend(),
    )

    assert default.station.supervisor.parameters.minimum_dispatch_pressure_margin_pa == pytest.approx(1.0e6)
    assert calibrated.station.supervisor.parameters.minimum_dispatch_pressure_margin_pa == pytest.approx(540_000.0)


def test_recharge_bank_waits_for_configured_restart_margin_after_target():
    built, _ = _station(ProcessSettings().model_dump())
    gases = tuple(bank.gas_state(state) for bank, state in
                  zip(built.station.banks, built.initial_state.banks))
    targets = (44e6, 68e6, 89e6)
    margins = (2e6, 3e6, 4e6)

    # The high bank is filled first and remains selected up to its target.
    selected = built.station.supervisor.select_recharge_bank(
        built.station.banks,
        tuple(replace(gas, pressure_pa=pressure)
              for gas, pressure in zip(gases, (44e6, 68e6, 88e6))),
        None, target_pressures_pa=targets, restart_margins_pa=margins,
    )
    assert selected == 2

    # Reaching the upper target disarms the bank. A small pressure drop must
    # not make the compressor chatter between recharge and standby.
    for high_pressure in (89e6, 88e6, 85.1e6):
        selected = built.station.supervisor.select_recharge_bank(
            built.station.banks,
            tuple(replace(gas, pressure_pa=pressure)
                  for gas, pressure in zip(gases, (44e6, 68e6, high_pressure))),
            None, target_pressures_pa=targets, restart_margins_pa=margins,
        )
        assert selected is None

    # It is re-armed only after the lower restart threshold is reached.
    selected = built.station.supervisor.select_recharge_bank(
        built.station.banks,
        tuple(replace(gas, pressure_pa=pressure)
              for gas, pressure in zip(gases, (44e6, 68e6, 85e6))),
        None, target_pressures_pa=targets, restart_margins_pa=margins,
    )
    assert selected == 2


def test_recharge_without_auto_stop_adds_mass_above_selected_target():
    settings = ProcessSettings().model_dump()
    settings.update(trailer_supply=True, pressure_recharge=True,
                    recharge_auto_stop=False,
                    recharge_target_low_mpa=40.0, recharge_target_medium_mpa=60.0,
                    recharge_target_high_mpa=85.0)
    built, process = _station(settings)
    charging = built.simulator.simulate(built.initial_state, .4, .2)
    assert "low" in charging.recharge_bank
    assert charging.final_state.banks[0].hydrogen_mass_kg > built.initial_state.banks[0].hydrogen_mass_kg
    assert process.requested("pressure_recharge")


def test_recharge_without_auto_stop_crosses_a_target_set_above_initial_pressure():
    settings = ProcessSettings(trailer_supply=True, pressure_recharge=True,
                               recharge_auto_stop=False,
                               recharge_target_low_mpa=45.001).model_dump()
    built, process = _station(settings)
    charging = built.simulator.simulate(built.initial_state, .4, .2)
    initial = built.station.banks[0].gas_state(built.initial_state.banks[0]).pressure_pa
    final = built.station.banks[0].gas_state(charging.final_state.banks[0]).pressure_pa
    assert initial < 45.001e6 < final
    assert process.requested("trailer_supply")
    assert process.requested("pressure_recharge")


def test_recharge_auto_stop_off_does_not_use_a_second_trailer_residual_cutoff():
    settings = ProcessSettings(trailer_supply=True, pressure_recharge=True,
                               recharge_auto_stop=False).model_dump()
    process = ProcessRuntime(settings)
    process.account_compressor(40.0, 1.0)
    assert 2.0 < process.snapshot()["trailer_pressure_mpa"] < 5.0
    process.stop_recharge_at_targets((50e6, 70e6, 100e6))
    assert process.requested("trailer_supply")
    assert process.requested("pressure_recharge")


@pytest.mark.parametrize("vehicle,pressure_field,flow_field", [
    ("vehicle_1", "vehicle_pressure_pa", "nozzle_1_mass_flow_kg_s"),
    ("vehicle_2", "vehicle_2_pressure_pa", "nozzle_2_mass_flow_kg_s"),
])
def test_vehicle_auto_stop_off_keeps_simulated_fill_above_operator_target(
        vehicle, pressure_field, flow_field):
    settings = ProcessSettings().model_dump()
    settings.update({vehicle: True, f"{vehicle}_auto_stop": False,
                     f"{vehicle}_target_pressure_mpa": 4.0})
    built, process = _station(settings)
    result = built.simulator.simulate(built.initial_state, .4, .2)
    pressure = getattr(result, pressure_field)
    assert pressure[0] > 4e6
    assert pressure[-1] > pressure[0]
    assert np.any(getattr(result, flow_field) > 0)
    assert process.requested(vehicle)


def test_vehicle_auto_stop_off_keeps_controller_filling_past_target():
    from h2station.protocol import FuelingObservation, FuelingSchedule, FuelingPhase, SampledFuelingController

    schedule = FuelingSchedule(target_pressure_pa=70e6,
        average_pressure_ramp_rate_pa_s=1e6, delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=.06)
    controller = SampledFuelingController(schedule)
    controller.start(0, 69e6)
    observation = FuelingObservation(time_s=2, pressure_pa=70e6,
        temperature_k=298.15, density_kg_m3=30, measured_mass_flow_kg_s=0)
    command = controller.update(observation, .2, auto_stop=False)
    assert command.phase is FuelingPhase.FILLING
    assert command.valve_opening > 0
    assert command.reference_pressure_pa > schedule.target_pressure_pa

    controller.reset()
    controller.start(0, 69e6)
    stopped = controller.update(observation, .2, auto_stop=True)
    assert stopped.phase is FuelingPhase.COMPLETE


def test_vehicle_2_without_auto_stop_crosses_a_target_above_initial_pressure():
    settings = ProcessSettings(vehicle_2=True, vehicle_2_auto_stop=False,
                               vehicle_2_target_pressure_mpa=5.001).model_dump()
    built, process = _station(settings)
    result = built.simulator.simulate(built.initial_state, .4, .2)
    assert result.vehicle_2_pressure_pa[0] < 5.001e6 < result.vehicle_2_pressure_pa[-1]
    assert np.max(result.nozzle_2_mass_flow_kg_s) > 0
    assert np.max(result.nozzle_1_mass_flow_kg_s) == 0
    assert process.requested("vehicle_2")


def test_live_operator_leak_uses_stable_solver_and_depletes_inventory():
    leak = FaultEvent(event_id="operator-leak", kind=FaultKind.HYDROGEN_LEAK,
                      target="cascade.high", start_time_s=0, leak_diameter_m=.0002)
    built = build_reference_scenario(ReferenceScenario(duration_s=32, control_period_s=1,
                                      fault_events=(leak,)), UnavailableHyRAMBackend())
    process = ProcessRuntime(ProcessSettings().model_dump())
    built.simulator.process_runtime = process
    result = built.simulator.simulate(built.initial_state, 32, 1)
    assert np.max(result.leak_mass_flow_by_release["operator-leak"]) > 0
    assert result.final_state.banks[2].hydrogen_mass_kg < built.initial_state.banks[2].hydrogen_mass_kg - .03
    initial_pressure = built.station.banks[2].gas_state(built.initial_state.banks[2]).pressure_pa
    final_pressure = built.station.banks[2].gas_state(result.final_state.banks[2]).pressure_pa
    assert final_pressure < initial_pressure - .3e6


def test_live_api_operation_settings_can_be_changed_and_invalid_hysteresis_rejected():
    with TestClient(app) as client:
        start = client.post("/api/simulations", json={
            "continuous": True, "duration_s": 2, "control_period_s": .2,
            "process_settings": ProcessSettings().model_dump(),
        })
        assert start.status_code == 202, start.text
        job_id = start.json()["id"]
        try:
            path = f"/api/simulations/{job_id}/operations"
            deadline = monotonic() + 8
            while monotonic() < deadline:
                idle_job = client.get(f"/api/simulations/{job_id}").json()
                if idle_job["simulated_time_s"] >= .2:
                    break
                sleep(.05)
            else:
                pytest.fail("Idle monitor clock did not advance")
            assert idle_job["realtime_lag_s"] is not None
            speed_path = f"/api/simulations/{job_id}/speed"
            for speed in (0.5, 1, 2, 3, 5, 10, 30, 50, 100):
                changed_speed = client.put(speed_path, json={"speed_multiplier": speed})
                assert changed_speed.status_code == 200, changed_speed.text
                assert client.get(f"/api/simulations/{job_id}").json()["speed_multiplier"] == speed
            assert client.put(speed_path, json={"speed_multiplier": 7}).status_code == 422
            delayed = client.post(f"/api/simulations/{job_id}/faults?relative=true", json={
                "event_id": "speed-delay-test", "kind": "sensor-bias", "target": "PT-1101",
                "start_time_s": 5.0, "end_time_s": 10.0, "magnitude": 0.0,
            })
            assert delayed.status_code == 202, delayed.text
            listed = client.get(f"/api/simulations/{job_id}/faults").json()["faults"]
            assert any(row["event_id"] == "speed-delay-test" and
                       row["start_time_s"] >= delayed.json()["simulated_time_s"] + 4.0
                       for row in listed)
            assert client.delete(f"/api/simulations/{job_id}/faults/speed-delay-test").status_code == 202
            settings = client.get(path).json()["settings"]
            settings["vehicle_2"] = True
            settings["vehicle_2_target_pressure_mpa"] = 72.0
            changed = client.put(path, json=settings)
            assert changed.status_code == 200, changed.text
            assert changed.json()["settings"]["vehicle_2"] is True
            assert changed.json()["settings"]["vehicle_2_target_pressure_mpa"] == 72.0
            command_revision = changed.json()["revision"]
            deadline = monotonic() + 12
            while monotonic() < deadline:
                frames = client.get(f"/api/simulations/{job_id}/frames").json()["frames"]
                if any(frame["nozzle_2_flow_g_s"] > 0 and
                       frame["process_operations"]["revision"] >= command_revision and
                       frame["process_activity"]["vehicle_2"]["state"] == "flowing"
                       for frame in frames):
                    break
                sleep(.05)
            else:
                pytest.fail("Vehicle 2 command did not produce flow")
            assert all(frame["nozzle_1_flow_g_s"] == 0 for frame in frames)
            assert frames[-1]["realtime_lag_s"] is not None
            assert frames[-1]["simulation_rate_x"] is not None
            settings["vehicle_2"] = False
            assert client.put(path, json=settings).status_code == 200
            settings["relief_valves"]["high"]["close_mpa"] = 101
            assert client.put(path, json=settings).status_code == 422
        finally:
            client.post(f"/api/simulations/{job_id}/stop")
