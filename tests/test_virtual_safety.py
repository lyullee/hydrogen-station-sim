"""Virtual response commands must change the station, not merely its labels."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from time import monotonic, sleep
import warnings

from h2station.api import ProcessSettings, app
from h2station.api import (_queue_incident_resolution, _virtual_fault_signature,
                           _virtual_safety_metrics, _virtual_training_evaluation)
from h2station.operations import ProcessRuntime
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario
from h2station.safety_runtime import FaultEvent, FaultKind
from h2station.virtual_safety import VirtualSafetyRuntime, suggested_actions
from h2station.hazop.response import load_playbooks, structured_guidance


def station(settings: dict):
    built = build_reference_scenario(ReferenceScenario(duration_s=1.0, control_period_s=.2),
                                     UnavailableHyRAMBackend())
    process = ProcessRuntime(settings)
    built.simulator.process_runtime = process
    built.station.compressor_suction = lambda _: process.trailer_state()
    return built, process


def test_dispenser_isolation_only_stops_its_own_vehicle_and_confirms_flow():
    settings = ProcessSettings(vehicle_1=True, vehicle_2=True).model_dump()
    built, process = station(settings)
    before = built.simulator.simulate(built.initial_state, .8, .2)
    assert before.nozzle_1_mass_flow_kg_s[-1] > 0
    assert before.nozzle_2_mass_flow_kg_s[-1] > 0
    command = process.safety.issue("valve.close", "dispenser.1", .8, process=process)
    assert command["status"] == "commanded"
    assert process.safety.snapshot()["valves"]["dispenser.1"]["actual_open"]
    samples = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        after = built.simulator.simulate(before.final_state, 1.4, .2,
                                         start_time_s=.8, reset_runtime=False,
                                         sample_callback=samples.append)
    assert after.time_s[-1] == pytest.approx(2.2)
    assert not any("lsoda: Illegal input" in str(item.message) for item in caught)
    assert after.nozzle_1_mass_flow_kg_s[-1] == 0
    assert after.nozzle_2_mass_flow_kg_s[-1] > 0
    isolated_pressures = [sample.virtual_safety["line_pressure_mpa"]["dispenser.1"]
                          for sample in samples if not sample.virtual_safety["valves"]["dispenser.1"]["actual_open"]]
    assert len(isolated_pressures) >= 2
    assert isolated_pressures == pytest.approx([isolated_pressures[0]] * len(isolated_pressures))
    assert samples[-1].bank_temperature_k["high"] > 0
    assert samples[-1].bank_mass_kg["high"] > 0
    assert samples[-1].virtual_safety["actions"] == []
    assert process.safety.snapshot()["actions"][-1]["status"] == "confirmed"


def test_trailer_and_bank_inlet_valves_stop_recharge_and_vent_depletes_bank():
    settings = ProcessSettings(trailer_supply=True, pressure_recharge=True,
                               recharge_auto_stop=False).model_dump()
    built, process = station(settings)
    before = built.simulator.simulate(built.initial_state, .6, .2)
    assert process.trailer_mass_kg < settings["trailer_capacity_kg"]
    process.safety.issue("valve.close", "trailer.station", .6, process=process)
    closed = built.simulator.simulate(before.final_state, 1.0, .2,
                                      start_time_s=.6, reset_runtime=False)
    assert process.trailer_mass_kg == pytest.approx(
        settings["trailer_capacity_kg"] - process.snapshot()["trailer_transferred_kg"])
    assert all(bank is None for bank in closed.recharge_bank[-3:])
    mass_before = closed.final_state.banks[2].hydrogen_mass_kg
    process.safety.issue("vent.open", "vent.high", 1.6, process=process)
    vented = built.simulator.simulate(closed.final_state, 1.0, .2,
                                      start_time_s=1.6, reset_runtime=False)
    assert vented.final_state.banks[2].hydrogen_mass_kg < mass_before
    assert vented.leak_mass_flow_by_release["vent-high"].max() > 0


def test_actuator_failure_and_recovery_gate():
    safety = VirtualSafetyRuntime()
    safety.set_fault("compressor.discharge", "stuck_open", 0)
    safety.issue("valve.close", "compressor.discharge", 0)
    safety.tick(.6)
    assert safety.snapshot()["actions"][-1]["status"] == "failed"
    assert safety.opening("compressor.discharge") == 1
    safety.set_fault("compressor.discharge", "none", .6)
    safety.issue("valve.close", "compressor.discharge", .6)
    safety.tick(1.1)
    safety.observe(1.2, recharge_bank=None, dispatch_banks=(None, None),
                   compressor_flow_g_s=0, dispenser_flows_g_s=(0, 0))
    assert safety.snapshot()["actions"][-1]["status"] == "commanded"
    safety.observe(1.6, recharge_bank=None, dispatch_banks=(None, None),
                   compressor_flow_g_s=0, dispenser_flows_g_s=(0, 0))
    assert safety.snapshot()["actions"][-1]["status"] == "confirmed"
    with pytest.raises(ValueError, match="Recovery checks incomplete"):
        safety.issue("restart.approve", "station", 1.6)
    with pytest.raises(ValueError, match="purge procedure"):
        safety.issue("recovery.record", "purge_complete", 1.6)
    safety.issue("valve.close", "bank.medium.inlet", 1.6)
    safety.issue("valve.close", "bank.medium.outlet", 1.6)
    safety.tick(2.1)
    safety.issue("purge.run", "medium", 2.1)
    assert safety.snapshot()["purge_bank"] == "medium"
    safety.tick(7.1)
    assert safety.snapshot()["recovery"]["purge_complete"]
    assert safety.snapshot()["purge_h2_fraction"]["medium"] < .01


def test_vehicle_departure_requires_stopped_transfer_and_confirmed_isolation():
    process = ProcessRuntime(ProcessSettings(vehicle_1=True).model_dump())
    safety = process.safety
    with pytest.raises(ValueError, match="Stop the connected transfer"):
        safety.issue("vehicle.evacuate", "vehicle_1", 0, process=process)
    process.stop("vehicle_1", "safety-action")
    with pytest.raises(ValueError, match="isolation"):
        safety.issue("vehicle.evacuate", "vehicle_1", 0, process=process)
    safety.issue("valve.close", "dispenser.1", 0)
    safety.tick(.5)
    safety.observe(1.0, recharge_bank=None, dispatch_banks=(None, None),
                   compressor_flow_g_s=0, dispenser_flows_g_s=(0, 0))
    safety.issue("vehicle.evacuate", "vehicle_1", 1.0, process=process)
    assert safety.snapshot()["vehicles"]["vehicle_1"] == 0
    assert safety.snapshot()["vehicles_evacuated"]["vehicle_1"] == 1
    assert safety.snapshot()["vehicles"]["vehicle_2"] == 1
    with pytest.raises(ValueError, match="has departed"):
        process.configure({**process.settings, "vehicle_1": True})


def test_storage_personnel_evacuation_updates_remaining_count_and_access_state():
    safety = VirtualSafetyRuntime()
    assert safety.snapshot()["personnel"]["storage"] == 2
    action = safety.issue("personnel.evacuate", "storage", 0)
    state = safety.snapshot()
    assert action["status"] == "confirmed"
    assert action["after"] == {"remaining": 0, "evacuated": 2}
    assert state["personnel"]["storage"] == 0
    assert state["evacuated"]["storage"] == 2
    assert state["access_restricted"]["storage"] is True


def test_plan_mapping_exposes_equipment_specific_actions():
    actions = suggested_actions("external_fire", "N08")
    assert {item["target"] for item in actions} >= {
        "bank.medium.inlet", "bank.medium.outlet", "medium"}
    plan = next(item for item in load_playbooks()["plans"] if item["id"] == "external_fire")
    guidance = structured_guidance([{"plan": {**plan, "sensor_id": "TT-0801"},
                                      "evidence": ["TT-0801"]}], actual_alert=True)
    assert any(item["target"] == "bank.medium.inlet"
               for item in guidance["plans"][0]["executable_actions"])


def test_recovery_tests_require_isolation_and_complete_in_sequence():
    safety = VirtualSafetyRuntime()
    safety.issue("recovery.record", "source_removed", 0)
    safety.issue("recovery.record", "leak_repaired", 0)
    with pytest.raises(ValueError, match="Isolate"):
        safety.issue("tightness.test", "high", 0)
    for side in ("inlet", "outlet"):
        safety.issue("valve.close", f"bank.high.{side}", 0)
    safety.tick(.5)
    baseline = {"bank_pressure_mpa": {"high": 90},
                "total_leak_flow_g_s": 0, "detectors_good": True}
    safety.issue("tightness.test", "high", .5, baseline_metrics=baseline)
    assert not safety.snapshot()["recovery"]["tightness_test"]
    safety.tick(3.6)
    assert safety.snapshot()["recovery"]["tightness_test"]
    safety.issue("detector.test", "all", 3.6,
                 baseline_metrics={**baseline, "detectors_good": False})
    safety.tick(4.7)
    assert not safety.snapshot()["recovery"]["detector_test"]
    safety.issue("detector.test", "all", 4.7, baseline_metrics=baseline)
    safety.tick(5.8)
    assert safety.snapshot()["recovery"]["detector_test"]
    safety.issue("valve.test", "all", 5.8, baseline_metrics=baseline)
    safety.tick(6.9)
    assert safety.snapshot()["recovery"]["valve_test"]
    safety.issue("purge.run", "high", 6.9)
    safety.tick(12.0)
    safety.issue("pressure.test", "high", 12.0, baseline_metrics=baseline)
    safety.tick(15.1)
    assert safety.snapshot()["recovery"]["pressure_test"]
    assert safety.snapshot()["line_pressure_mpa"]["bank.high.outlet"] == pytest.approx(90)
    safety.issue("recovery.record", "supervisor_approval", 15.1)
    safety.issue("restart.approve", "station", 15.1)
    assert safety.snapshot()["recovery_approved"]


def test_ventilation_and_cooling_change_virtual_hazard_physics():
    safety = VirtualSafetyRuntime()
    normal = safety.detector_multiplier("cascade.medium")
    safety.issue("ventilation.off", "storage", 0)
    assert safety.detector_multiplier("cascade.medium") > normal
    safety.wind_speed_m_s = 12
    assert safety.detector_multiplier("cascade.medium") < 1.3

    fire = FaultEvent("external-fire", FaultKind.EXTERNAL_FIRE, "cascade.medium", 0,
                      external_temperature_k=1100, heat_transfer_ua_w_k=5000)
    def run(cooling: bool):
        built = build_reference_scenario(ReferenceScenario(duration_s=2, control_period_s=.2,
                                          fault_events=(fire,)), UnavailableHyRAMBackend())
        process = ProcessRuntime(ProcessSettings().model_dump())
        built.simulator.process_runtime = process
        if cooling:
            process.safety.issue("cooling.on", "medium", 0)
        trajectory = built.simulator.simulate(built.initial_state, 2, .2)
        return trajectory.final_state.banks[1].wall_temperature_k
    assert run(True) < run(False)


def test_action_comparison_has_bank_inventory_temperature_and_flow():
    frame = {"time_s": 5.0, "bank_pressure_mpa": {"high": 82.0},
             "bank_temperature_c": {"high": 31.0}, "bank_mass_kg": {"high": 24.0},
             "nozzle_1_flow_g_s": 3.2, "nozzle_2_flow_g_s": 0.0,
             "process_activity": {"pressure_recharge": {"flow_g_s": 6.0}}}
    metrics = _virtual_safety_metrics(frame)
    assert metrics["bank_temperature_c"]["high"] == 31.0
    assert metrics["bank_mass_kg"]["high"] == 24.0
    assert metrics["compressor_flow_g_s"] == 6.0
    assert metrics["nozzle_1_flow_g_s"] == 3.2


def test_training_marks_unanswered_incident_below_prompt_response():
    job = {"frames": [{"time_s": 10.0, "active_faults": ["external-fire:cascade.high"],
                       "total_leak_flow_g_s": 0.0, "hazop": {"releases": []}}]}
    safety = VirtualSafetyRuntime()
    ignored = _virtual_training_evaluation(job, safety)
    safety.issue("operation.stop", "all", 10.0,
                 process=ProcessRuntime(ProcessSettings().model_dump()))
    answered = _virtual_training_evaluation(job, safety)
    assert ignored["first_protective_action_s"] is None
    assert ignored["training_score"] < answered["training_score"]


def test_replay_comparison_matches_same_leak_despite_new_event_id():
    def frame(event_id: str, diameter_m: float):
        return {"active_faults": ["hydrogen-leak:cascade.high"],
                "hazop": {"releases": [{"release_id": event_id,
                                        "component_id": "cascade.high",
                                        "orifice_diameter_m": diameter_m}]}}
    assert _virtual_fault_signature([frame("remote-1", .0002)]) == \
           _virtual_fault_signature([frame("remote-2", .0002)])
    assert _virtual_fault_signature([frame("remote-1", .0002)]) != \
           _virtual_fault_signature([frame("remote-3", .0005)])


def test_esd_and_confirmed_immediate_stop_queue_active_incident_end():
    process = ProcessRuntime(ProcessSettings(vehicle_1=True).model_dump())
    leak = FaultEvent("training-leak", FaultKind.HYDROGEN_LEAK,
                      "cascade.high", 0, leak_diameter_m=.001)
    job = {"fault_registry": {leak.event_id: leak},
           "pending_fault_commands": [], "auto_resolved_fault_ids": []}
    process.safety.issue("esd.trip", "station", 2, process=process)
    assert _queue_incident_resolution(job, process, 2) == []
    process.safety.issue("operation.stop", "all", 2, process=process)
    assert _queue_incident_resolution(job, process, 2) == ["training-leak"]
    assert job["pending_fault_commands"] == [("remove", "training-leak")]
    assert process.safety.snapshot()["actions"][-1]["kind"] == "incident.auto-resolve"
    # Repeated samples cannot queue duplicate removals or duplicate response records.
    assert _queue_incident_resolution(job, process, 2.2) == []
    assert job["pending_fault_commands"] == [("remove", "training-leak")]


def test_live_safety_api_separates_command_feedback_and_replays():
    with TestClient(app) as client:
        page = client.get('/remote.html')
        assert page.status_code == 200 and 'safetyConsole' in page.text
        assert '계산 정지 · 완전 초기화' in page.text
        assert client.get('/safety-console.js').status_code == 200
        created = client.post("/api/simulations", json={
            "continuous": True, "control_period_s": .2,
            "process_settings": ProcessSettings().model_dump(),
        })
        assert created.status_code == 202, created.text
        job_id = created.json()["id"]
        root = f"/api/simulations/{job_id}/safety"
        try:
            command = client.post(root + "/actions", json={"kind": "valve.close",
                                                         "target": "trailer.station"})
            assert command.status_code == 200, command.text
            assert command.json()["action"]["status"] == "commanded"
            deadline = monotonic() + 8
            while monotonic() < deadline:
                state = client.get(root).json()
                if state["valves"]["trailer.station"]["status"] == "confirmed":
                    break
                sleep(.05)
            else:
                pytest.fail("Valve closure confirmation did not arrive")
            assert state["valves"]["trailer.station"]["actual_open"] is False
            assert state["actions"][-1]["status"] == "confirmed"
            assert client.post(root + "/actions", json={"kind": "restart.approve",
                                                          "target": "station"}).status_code == 422
            replay = client.get(root + "/replay")
            assert replay.status_code == 200
            assert replay.json()["actions"][-1]["kind"] == "valve.close"
            assert replay.json()["evaluation"]["training_score"] <= 100
        finally:
            client.post(f"/api/simulations/{job_id}/stop")
