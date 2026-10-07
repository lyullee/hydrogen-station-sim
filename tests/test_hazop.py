from __future__ import annotations

import copy
import math
import time
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from h2station.api import ProcessSettings, app
from h2station.hazop.database import EventStore, load_catalog
from h2station.hazop.engine import RuleEngine
from h2station.hazop.expressions import Evaluator, Unknown, evaluate_gate, parse
from h2station.hazop.mapping import coverage
from h2station.dispenser import IsentropicRealGasRestriction, RestrictionParameters
from h2station.protocol import FuelingCommand, FuelingPhase
from h2station.hazop.runtime import HazopMonitor
from h2station.operations import ProcessRuntime
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario
from h2station.safety_runtime import FaultEvent, FaultKind
from h2station.tabulated import PropsSI


def isolated(expression="PT-1401", op=">=", threshold=87.5, latch=True, hold=.5):
    data = copy.deepcopy(load_catalog())
    r = next(r for r in data["rules"] if r["sensor_id"]=="PT-1401" and r["임계값"]==87.5)
    r.update({"신호식":expression,"연산자":op,"임계값":threshold,"지속_s":hold,
              "래치":latch,"gate_id":"G_ANY","복귀연산자":"<" if op==">=" else ">",
              "복귀값":threshold-1 if op==">=" else threshold+1,"복귀지속_s":.4})
    data["rules"] = [r]
    return data, r["rule_id"]


def frame(t, value=87.5, quality="GOOD", age=0, unit="MPa_abs", monitoring=True):
    return {"time_s":t,"signals":{"PT-1401":{"value":value,"quality":quality,"unit":unit,"time_s":t-age}},
            "modes":{"station.monitoring":monitoring}}


def test_packaged_catalog_keys_and_numeric_values():
    c = load_catalog()
    assert len(c["rules"]) == 214 and len(c["sensors"]) == 91
    assert all(isinstance(r["임계값"], float) for r in c["rules"])
    assert all(r["현장활성화"] is False for r in c["rules"])
    m = coverage(c)
    assert m["mapped_sensors"]==91
    assert not any(s["mapping_status"]=="UNAVAILABLE" for s in m["sensors"])
    assert m["physical_sensor_connections"]==0
    assert 0 < m["simulation_ready_rules"] < 214


def test_bank_header_and_dispenser_reverse_flow_rules_are_ready_but_other_paths_are_not():
    mapped = {row["rule_id"]: row for row in coverage(load_catalog())["rules"]}
    assert mapped["HZ-050"]["simulation_ready"] is True
    assert mapped["HZ-059"]["simulation_ready"] is True
    assert mapped["HZ-068"]["simulation_ready"] is True
    assert mapped["HZ-073"]["simulation_ready"] is True
    assert mapped["HZ-074"]["simulation_ready"] is True
    assert mapped["HZ-091"]["simulation_ready"] is True
    assert mapped["HZ-119"]["simulation_ready"] is True
    assert mapped["HZ-073"]["model_limits"] == []
    assert mapped["HZ-074"]["missing_signals"] == []
    assert mapped["HZ-091"]["model_limits"] == []
    assert mapped["HZ-119"]["model_limits"] == []
    assert mapped["HZ-009"]["simulation_ready"] is False
    assert "one-way restriction model cannot generate reverse flow" in mapped["HZ-009"]["model_limits"]


def test_pcv_isolation_failure_rules_have_command_and_stability_modes():
    mapped = {row["rule_id"]: row for row in coverage(load_catalog())["rules"]}
    for rule_id in ("HZ-078", "HZ-106"):
        assert mapped[rule_id]["simulation_ready"] is True
        assert mapped[rule_id]["missing_modes"] == []


def test_unloading_disconnect_residual_pressure_rule_is_simulation_ready():
    mapped = {row["rule_id"]: row for row in coverage(load_catalog())["rules"]}
    assert mapped["HZ-011"]["simulation_ready"] is True
    assert mapped["HZ-011"]["missing_modes"] == []


def test_disconnected_trailer_with_trapped_unloading_pressure_triggers_hz011():
    built = build_reference_scenario(
        ReferenceScenario(duration_s=13.0, control_period_s=.2),
        UnavailableHyRAMBackend(),
    )
    process = ProcessRuntime(ProcessSettings().model_dump())
    built.simulator.process_runtime = process
    built.station.compressor_suction = lambda _time: process.trailer_state()
    safety = process.safety
    safety.line_pressure_mpa["trailer.station"] = 20.0
    safety.issue("valve.close", "trailer.source", 0.0, process=process)
    safety.issue("valve.close", "trailer.station", 0.0, process=process)
    safety.tick(.4)
    safety.tick(.8)
    safety.observe(
        .8, recharge_bank=None, dispatch_banks=(None, None),
        compressor_flow_g_s=0.0, dispenser_flows_g_s=(0.0, 0.0),
    )
    safety.issue("vehicle.evacuate", "trailer", .8, process=process)
    monitor = HazopMonitor()
    built.simulator.hazop_monitor = monitor

    built.simulator.simulate(
        built.initial_state, 13.0, .2, start_time_s=.8, pace_idle=False,
    )

    assert monitor.latest["modes"]["unloading.disconnect_requested"] is True
    assert monitor.latest["modes"]["unloading.depressurize_elapsed_s"] >= 10.0
    assert monitor.latest["signals"]["PT-0201"]["value"] == pytest.approx(20.0)
    assert any(item["rule_id"] == "HZ-011" for item in monitor.latest["active"])


@pytest.mark.parametrize(
    "target,flow_field,rule_id,other_rule_id",
    [
        ("dispenser.pcv", "pcv_1_mass_flow_kg_s", "HZ-078", "HZ-106"),
        ("dispenser_2.pcv", "pcv_2_mass_flow_kg_s", "HZ-106", "HZ-078"),
    ],
)
def test_pcv_seat_leak_is_target_specific_and_triggers_isolation_failure(
    target, flow_field, rule_id, other_rule_id,
):
    fault = FaultEvent(
        "seat-leak", FaultKind.PCV_SEAT_LEAK, target, 0.0, end_time_s=8.0,
    )
    built = build_reference_scenario(
        ReferenceScenario(duration_s=6.0, control_period_s=.2, fault_events=(fault,)),
        UnavailableHyRAMBackend(),
    )
    built.simulator.process_runtime = ProcessRuntime(ProcessSettings().model_dump())
    monitor = HazopMonitor()
    built.simulator.hazop_monitor = monitor

    trajectory = built.simulator.simulate(
        built.initial_state, 6.0, .2, pace_idle=False,
    )

    assert max(getattr(trajectory, flow_field)) > 0.0005
    assert any(item["rule_id"] == rule_id for item in monitor.latest["active"])
    assert not any(
        item["rule_id"] == other_rule_id for item in monitor.latest["active"]
    )


def test_check_valve_failure_reverse_flow_uses_vehicle_state_and_conserves_transfer():
    built = build_reference_scenario(
        ReferenceScenario(duration_s=.2, control_period_s=.2),
        UnavailableHyRAMBackend(),
    )
    partial = built.station.partial_station
    vehicle = partial.vehicle_tank.initial_state(70.0e6, 330.0)
    state = partial.initial_state(
        vehicle=vehicle,
        hose_pressure_pa=5.0e6,
        hose_temperature_k=298.15,
        coolant_temperature_k=298.15,
    )
    command = FuelingCommand(
        FuelingPhase.FILLING, 0.0, 70.0e6, 298.15, 0.0,
    )
    values = partial._flow_and_thermal_states(
        0.0, state, command, allow_reverse_flow=True,
    )
    derivative = partial.derivative(
        0.0, state, command, allow_reverse_flow=True,
    )
    assert values["nozzle_mass_flow"] < 0.0
    assert derivative.hose_hydrogen_mass_kg > 0.0
    assert derivative.vehicle.hydrogen_mass_kg < 0.0
    assert derivative.hose_hydrogen_mass_kg + derivative.vehicle.hydrogen_mass_kg == pytest.approx(0.0)
    assert (derivative.hose_hydrogen_internal_energy_j
            + derivative.vehicle.hydrogen_internal_energy_j) == pytest.approx(0.0, abs=1e-7)


def test_reverse_restriction_uses_downstream_temperature_as_new_upstream_state():
    restriction = IsentropicRealGasRestriction(
        RestrictionParameters(flow_area_m2=1.0e-6, discharge_coefficient=.8)
    )
    reverse = restriction.mass_flow_kg_s(
        5.0e6, 250.0, 70.0e6,
        allow_reverse_flow=True,
        downstream_temperature_k=330.0,
    )
    forward = restriction.mass_flow_kg_s(70.0e6, 330.0, 5.0e6)
    assert reverse == pytest.approx(-forward)


@pytest.mark.parametrize(
    "target,state_field,flow_field,signal,rule_id",
    [
        ("dispenser.hose", "partial_station", "nozzle_1_mass_flow_kg_s", "FT-1301", "HZ-091"),
        ("dispenser_2.hose", "secondary_partial_station", "nozzle_2_mass_flow_kg_s", "FT-1701", "HZ-119"),
    ],
)
def test_check_valve_failure_reaches_live_hazop_reverse_alarm(
    target, state_field, flow_field, signal, rule_id,
):
    fault = FaultEvent("reverse", FaultKind.CHECK_VALVE_FAILURE, target, 0.0, end_time_s=2.0)
    built = build_reference_scenario(
        ReferenceScenario(
            duration_s=1.0,
            control_period_s=.2,
            initial_vehicle_pressure_pa=70.0e6,
            initial_vehicle_2_pressure_pa=70.0e6,
            fault_events=(fault,),
        ),
        UnavailableHyRAMBackend(),
    )
    partial = (built.station.partial_station if state_field == "partial_station"
               else built.station.secondary_partial_station)
    vehicle = partial.vehicle_tank.initial_state(70.0e6, 298.15)
    low_pressure_hose = partial.initial_state(
        vehicle, 5.0e6, 298.15, 233.15,
    )
    initial = replace(built.initial_state, **{state_field: low_pressure_hose})
    monitor = HazopMonitor()
    built.simulator.hazop_monitor = monitor

    trajectory = built.simulator.simulate(initial, 1.0, .2)

    assert min(getattr(trajectory, flow_field)) < 0.0
    assert monitor.latest["signals"][signal]["value"] <= -1.0
    alarm = next(item for item in monitor.latest["active"] if item["rule_id"] == rule_id)
    assert alarm["state"] == "TRIGGER"


def test_inclusive_threshold_elapsed_time_and_manual_reset():
    c, rid = isolated()
    engine = RuleEngine(c)
    assert engine.evaluate(frame(0))["rules"][0]["state"] == "PENDING"
    assert engine.evaluate(frame(.4))["rules"][0]["state"] == "PENDING"
    assert engine.evaluate(frame(.5))["rules"][0]["state"] == "TRIGGER"
    assert engine.evaluate(frame(.6,85))["rules"][0]["state"] == "LATCHED"
    assert engine.evaluate(frame(1.1,85))["rules"][0]["state"] == "LATCHED"
    assert engine.evaluate(frame(1.2,85),{rid})["rules"][0]["state"] == "NORMAL"


@pytest.mark.parametrize("bad", [frame(.3,None),frame(.3,float('nan')),frame(.3,90,'BAD'),frame(.3,90,age=1),frame(.3,90,unit='Pa'),frame(.3,90,monitoring=None)])
def test_bad_missing_stale_wrong_unit_reset_persistence(bad):
    c,_=isolated()
    e=RuleEngine(c)
    e.evaluate(frame(0,90))
    assert e.evaluate(bad)["rules"][0]["state"]=="UNKNOWN"
    assert e.evaluate(frame(.6,90))["rules"][0]["state"]=="PENDING"
    assert e.evaluate(frame(1.1,90))["rules"][0]["state"]=="TRIGGER"


def test_low_threshold_and_zero_not_missing():
    c,_=isolated(op='<=',threshold=2,latch=False,hold=0)
    e=RuleEngine(c)
    assert e.evaluate(frame(0,0))["rules"][0]["state"]=='TRIGGER'


def test_unknown_while_latched_preserves_alarm_and_quality():
    c,_=isolated(hold=0)
    e=RuleEngine(c); e.evaluate(frame(0,90))
    item=e.evaluate(frame(.2,None))["rules"][0]
    assert item['state']=='LATCHED' and item['quality']=='UNKNOWN'


def test_untrusted_dsl_rejected_and_three_valued_mode_logic():
    with pytest.raises(ValueError):parse("__import__('os').system('x')")
    assert evaluate_gate('a.x == true AND a.y == false',{'a.x':True}) is None
    assert evaluate_gate('a.x == true AND a.y == false',{'a.x':False}) is False


def test_rate_and_linepack_balance_not_raw_flow_difference():
    history=[]
    for t in [0,.5,1,1.5,2]:
        f=frame(t,10+t)
        for tag,value,unit in [('FT-1101',10,'g/s'),('FT-1301',4,'g/s'),('MASS_HOSE_1',1+.006*t,'kg')]:
            f['signals'][tag]={'value':value,'quality':'GOOD','time_s':t,'unit':unit}
        history.append(f)
    specs={s['sensor_id']:s for s in load_catalog()['sensors']}
    ev=Evaluator(history,specs)
    assert ev.evaluate('RATE(PT-1401,2)',history[-1])==pytest.approx(1)
    assert ev.evaluate('BALANCE(FT-1101,FT-1301,MASS_HOSE_1,2)',history[-1])==pytest.approx(0,abs=1e-10)
    history[2]['signals']['FT-1101']['quality']='BAD'
    with pytest.raises(Unknown):ev.evaluate('BALANCE(FT-1101,FT-1301,MASS_HOSE_1,2)',history[-1])


def test_age_does_not_need_good_measurement_quality():
    f=frame(2,90,'BAD',age=2)
    assert Evaluator([f],{}).evaluate('AGE(PT-1401)',f)==2


def test_isothermal_pressure_removes_temperature_only_pressure_change():
    specs = {s['sensor_id']: s for s in load_catalog()['sensors']}
    density = PropsSI('Dmass', 'P', 65e6, 'T', 288.15, 'Hydrogen')
    frames = []
    for time_s in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0):
        temperature_k = 288.15 + (330.0 - 288.15) * time_s / 5.0
        pressure_mpa = PropsSI(
            'P', 'Dmass', density, 'T', temperature_k, 'Hydrogen'
        ) / 1e6
        frames.append({
            'time_s': time_s,
            'signals': {
                'PT-0801': {'value': pressure_mpa, 'quality': 'GOOD', 'unit': 'MPa_abs', 'time_s': time_s},
                'TT-0801': {'value': temperature_k - 273.15, 'quality': 'GOOD', 'unit': 'degC', 'time_s': time_s},
            },
            'modes': {},
        })
    value = Evaluator(frames, specs).evaluate(
        'RATE(P_ISOTHERM(PT-0801,TT-0801),5)', frames[-1]
    )
    assert value == pytest.approx(0.0, abs=1e-8)


def test_isothermal_bank_loss_rules_are_simulation_ready():
    rows = {row['rule_id']: row for row in coverage(load_catalog())['rules']}
    for rule_id in ('HZ-048', 'HZ-057', 'HZ-066'):
        assert rows[rule_id]['simulation_ready'] is True
        assert rows[rule_id]['missing_modes'] == []
        assert rows[rule_id]['model_limits'] == []


def test_existing_process_states_unlock_compressor_cooling_and_vent_rules():
    rows = {row['rule_id']: row for row in coverage(load_catalog())['rules']}
    for rule_id in ('HZ-012', 'HZ-017', 'HZ-041', 'HZ-131', 'HZ-136', 'HZ-137'):
        assert rows[rule_id]['simulation_ready'] is True
        assert rows[rule_id]['missing_modes'] == []


def test_isothermal_bank_loss_rule_triggers_despite_heating():
    catalog = copy.deepcopy(load_catalog())
    rule = next(row for row in catalog['rules'] if row['rule_id'] == 'HZ-057')
    catalog['rules'] = [rule]
    catalog['gates'] = [
        row for row in catalog['gates'] if row['gate_id'] == rule['gate_id']
    ]
    engine = RuleEngine(catalog)
    result = None
    for step in range(21):
        time_s = 0.5 * step
        reference_pressure_pa = (65.0 - 0.10 * time_s) * 1e6
        temperature_k = 288.15 + (330.0 - 288.15) * time_s / 10.0
        density = PropsSI(
            'Dmass', 'P', reference_pressure_pa, 'T', 288.15, 'Hydrogen'
        )
        measured_pressure_mpa = PropsSI(
            'P', 'Dmass', density, 'T', temperature_k, 'Hydrogen'
        ) / 1e6
        result = engine.evaluate({
            'time_s': time_s,
            'signals': {
                'PT-0801': {'value': measured_pressure_mpa, 'quality': 'GOOD', 'unit': 'MPa_abs', 'time_s': time_s},
                'TT-0801': {'value': temperature_k - 273.15, 'quality': 'GOOD', 'unit': 'degC', 'time_s': time_s},
            },
            'modes': {
                'bank.08.inlet_closed': True,
                'bank.08.outlet_closed': True,
                'bank.08.relief_active': False,
                'bank.08.stable_s': 10.0 + time_s,
            },
        })
    assert result is not None
    item = result['rules'][0]
    assert item['state'] == 'TRIGGER'
    assert item['value'] == pytest.approx(-0.10, abs=1e-6)


def test_model_tag_fault_activates_candidate_without_inventing_leak(tmp_path):
    fault=FaultEvent('sensor-test',FaultKind.SENSOR_BIAS,'PT-1401',0,magnitude=90)
    built=build_reference_scenario(ReferenceScenario(duration_s=1,control_period_s=.2,fault_events=(fault,)),UnavailableHyRAMBackend())
    monitor=HazopMonitor(run_id='test',store=EventStore(tmp_path/'events.sqlite3'))
    built.simulator.hazop_monitor=monitor
    samples=[]
    trajectory=built.simulator.simulate(built.initial_state,1,.2,sample_callback=samples.append)
    assert monitor.latest['active']
    group=next(g for g in monitor.latest['groups'] if g['node_id']=='N14')
    assert group['hyram_status']=='NEEDS_RELEASE_INPUTS'
    assert monitor.latest['releases']==[]
    assert trajectory.esd_time_s is None  # Advisory tag fault does not modify physical PLC.
    assert samples[-1].hose_2_pressure_pa > 0
    assert len(EventStore(tmp_path/'events.sqlite3').events('test'))>0
    assert not any(k.startswith('GD-') for k in monitor.latest['signals'])


class FixedConsequenceBackend:
    available=True
    name='test'
    def evaluate_release(self,request):
        return {'status':'calculated','maximum_heat_flux_w_m2':1.0,'maximum_concentration':.02}


@pytest.mark.parametrize('indoor_missing', [False, True])
def test_actual_release_links_without_fabricating_location_gd(indoor_missing):
    faults=(FaultEvent('leak',FaultKind.HYDROGEN_LEAK,'vehicle.tank',0,leak_diameter_m=.0001),
            FaultEvent('sensor',FaultKind.SENSOR_BIAS,'PT-1401',0,magnitude=90))
    class Backend(FixedConsequenceBackend):
        def evaluate_release(self, request):
            result = super().evaluate_release(request)
            if indoor_missing: result['indoor_status'] = 'enclosure-not-configured'
            return result
    built=build_reference_scenario(ReferenceScenario(fault_events=faults),Backend())
    monitor=HazopMonitor();built.simulator.hazop_monitor=monitor
    built.simulator.simulate(built.initial_state,.8,.2)
    g=next(g for g in monitor.latest['groups'] if g['node_id']=='N14')
    assert g['hyram_status']==('PARTIAL_RESULT' if indoor_missing else 'RESULT_LINKED') and g['release_ids']==['leak']
    assert not any(k.startswith('GD-') for k in monitor.latest['signals'])


def test_api_catalog_live_detail_and_persisted_events(tmp_path,monkeypatch):
    monkeypatch.setenv('H2STATION_HAZOP_EVENTS_DB',str(tmp_path/'events.sqlite3'))
    with TestClient(app) as client:
        assert client.get('/api/hazop/mapping').json()['mapped_sensors']==91
        assert len(client.get('/api/hazop/catalog').json()['rules'])==214
        created=client.post('/api/simulations',json={'duration_s':.8,'faults':[{'event_id':'bias','kind':'sensor-bias','target':'PT-1401','start_time_s':0,'magnitude':90}]}).json()
        for _ in range(200):
            job=client.get('/api/simulations/'+created['id']).json()
            if job['status'] in ('complete','failed'):break
            time.sleep(.03)
        assert job['status']=='complete',job
        result=client.get('/api/simulations/'+created['id']+'/result').json()
        assert len(result['hazop']['frames'])==len(result['series']['time_s'])
        assert client.get('/api/simulations/'+created['id']+'/hazop').json()['groups']
        assert client.get('/api/hazop/runs/'+created['id']+'/events').json()['events']
        with client.websocket_connect('/api/simulations/'+created['id']+'/stream') as socket:
            frame_count=0
            while True:
                msg=socket.receive_json()
                if msg['type']=='complete':break
                if msg['type']=='frame':
                    frame_count+=1
                    assert msg['frame']['hose_2_pressure_mpa']>0
                    assert 'hazop' in msg['frame']
            assert frame_count==len(result['series']['time_s'])


def test_physical_pressure_disturbance_changes_process_state():
    fault = FaultEvent('pressure', FaultKind.PRESSURE_DISTURBANCE, 'vehicle.tank', 0, magnitude=20, rate_s=2)
    base = build_reference_scenario(ReferenceScenario(duration_s=1, control_period_s=.2), UnavailableHyRAMBackend())
    disturbed = build_reference_scenario(ReferenceScenario(duration_s=1, control_period_s=.2, fault_events=(fault,)), UnavailableHyRAMBackend())
    normal = base.simulator.simulate(base.initial_state, 1, .2)
    changed = disturbed.simulator.simulate(disturbed.initial_state, 1, .2)
    assert changed.vehicle_pressure_pa[-1] > normal.vehicle_pressure_pa[-1] * 1.05


def test_external_fire_uses_heat_transfer_and_changes_temperature():
    fault = FaultEvent('fire', FaultKind.EXTERNAL_FIRE, 'vehicle.tank', 0, external_temperature_k=1000, heat_transfer_ua_w_k=5000)
    base = build_reference_scenario(ReferenceScenario(duration_s=5, control_period_s=.5), UnavailableHyRAMBackend())
    heated = build_reference_scenario(ReferenceScenario(duration_s=5, control_period_s=.5, fault_events=(fault,)), UnavailableHyRAMBackend())
    normal = base.simulator.simulate(base.initial_state, 5, .5)
    changed = heated.simulator.simulate(heated.initial_state, 5, .5)
    assert changed.vehicle_temperature_k[-1] > normal.vehicle_temperature_k[-1] + .001


def test_leak_mass_is_removed_from_physical_inventory():
    fault = FaultEvent('leak', FaultKind.HYDROGEN_LEAK, 'vehicle.tank', 0, leak_diameter_m=.0002)
    base = build_reference_scenario(ReferenceScenario(duration_s=3, control_period_s=.5), UnavailableHyRAMBackend())
    leaking = build_reference_scenario(ReferenceScenario(duration_s=3, control_period_s=.5, fault_events=(fault,)), UnavailableHyRAMBackend())
    normal = base.simulator.simulate(base.initial_state, 3, .5)
    changed = leaking.simulator.simulate(leaking.initial_state, 3, .5)
    assert changed.vehicle_pressure_pa[-1] < normal.vehicle_pressure_pa[-1]
    assert changed.leak_mass_flow_by_release['leak'].max() > 0

@pytest.mark.parametrize('target,tag', [('dispenser_2.hose','GD-1701'),('vehicle_2.tank','GD-1701'),('cascade.low','GD-0701'),('cascade.high','GD-0901')])
def test_virtual_detector_follows_actual_release_zone(target, tag):
    fault=FaultEvent('zone-leak',FaultKind.HYDROGEN_LEAK,target,0,leak_diameter_m=.0001)
    built=build_reference_scenario(ReferenceScenario(fault_events=(fault,)),UnavailableHyRAMBackend())
    monitor=HazopMonitor(virtual_detectors=True);built.simulator.hazop_monitor=monitor
    built.simulator.simulate(built.initial_state,.2,.2)
    signals=monitor.latest['signals']
    assert signals[tag]['value'] > 0
    assert signals[tag]['origin']=='VIRTUAL_DETECTOR_PROXY'
    assert signals['GD-2001']['value']==0  # No unrelated header alarm.
    assert len([k for k in signals if k.startswith('GD-')])==15
    assert len([k for k in signals if k in monitor.mapper.specs])==91


def test_every_catalog_sensor_has_finite_sample_and_detector_fault_uses_db_tag():
    fault=FaultEvent('detector-test',FaultKind.SENSOR_BIAS,'GD-0101',0,magnitude=1.5)
    built=build_reference_scenario(ReferenceScenario(fault_events=(fault,)),UnavailableHyRAMBackend())
    monitor=HazopMonitor(virtual_detectors=True);built.simulator.hazop_monitor=monitor
    built.simulator.simulate(built.initial_state,.2,.2)
    signals=monitor.latest['signals']
    assert all(tag in signals and signals[tag]['quality']=='GOOD' and math.isfinite(signals[tag]['value'])
               for tag in monitor.mapper.specs)
    assert signals['PT-0301']['value'] < signals['PT-0401']['value'] < signals['PT-0501']['value'] < signals['PT-0601']['value']
    assert signals['FT-1901']['origin']=='DERIVED_THERMAL_PROXY'
    assert signals['GD-0101']['origin']=='SIMULATED_SENSOR_BIAS'
    assert signals['GD-0101']['value']>=1.5


def test_solver_stop_is_checked_inside_window_and_esd_survives_restart():
    fault=FaultEvent('esd',FaultKind.EMERGENCY_STOP,'station',0)
    built=build_reference_scenario(ReferenceScenario(fault_events=(fault,)),UnavailableHyRAMBackend())
    samples=[]
    first=built.simulator.simulate(built.initial_state,60,.2,sample_callback=samples.append,stop_callback=lambda:len(samples)>=3)
    assert first.time_s[-1] == pytest.approx(.4)
    assert first.esd_time_s == 0
    second=built.simulator.simulate(first.final_state,.2,.2,start_time_s=.400001,reset_runtime=False)
    assert second.esd_time_s == 0


def test_api_rejects_invalid_fault_before_queueing():
    with TestClient(app) as client:
        response=client.post('/api/simulations',json={'faults':[{'event_id':'invalid','kind':'external-fire','target':'vehicle.tank','start_time_s':10,'end_time_s':5,'external_temperature_c':800,'heat_transfer_ua_w_k':1000}]})
        assert response.status_code==422


def test_frame_cursor_and_continuous_stop_result_alignment(tmp_path, monkeypatch):
    import h2station.api as api
    monkeypatch.setenv('H2STATION_HAZOP_EVENTS_DB',str(tmp_path/'events.sqlite3'))
    monkeypatch.setattr(api,'load_hyram_backend',lambda:UnavailableHyRAMBackend())
    with TestClient(app) as client:
        job=client.post('/api/simulations',json={'duration_s':.4,'continuous':True,'control_period_s':.2}).json()
        path='/api/simulations/'+job['id']
        for _ in range(300):
            snapshot=client.get(path+'/frames').json()
            if len(snapshot['frames'])>=5:break
            time.sleep(.02)
        assert len(snapshot['frames'])>=5
        cursor=snapshot['frames'][2]['sequence']
        resumed=client.get(path+'/frames',params={'after':cursor}).json()
        assert all(f['sequence']>cursor for f in resumed['frames'])
        assert client.post(path+'/stop').status_code==200
        for _ in range(300):
            status=client.get(path).json()
            if status['status'] in ('complete','failed'):break
            time.sleep(.02)
        assert status['status']=='complete',status
        result=client.get(path+'/result').json();length=len(result['series']['time_s'])
        assert length>=5
        assert len(result['hazop']['frames'])==length
        assert len(result['series']['analysis'])==length
        assert len(result['series']['gas_detectors'])==length
        assert all(len(values)==length for values in result['series']['bank_pressure_mpa'].values())
        assert len(result['series']['header_pressure_mpa'])==length
        assert len(result['series']['header_temperature_c'])==length
        assert len(result['series']['header_mass_kg'])==length
        assert len(result['series']['header_inflow_g_s'])==length
        assert client.get('/api/simulations/missing/frames').status_code==404

def test_storage_release_chokes_before_table_cold_limit():
    from h2station.dispenser import IsentropicRealGasRestriction, RestrictionParameters
    restriction=IsentropicRealGasRestriction(RestrictionParameters(flow_area_m2=1e-8,discharge_coefficient=.8))
    atmospheric=restriction.mass_flow_kg_s(90e6,298.15,101325)
    higher_backpressure=restriction.mass_flow_kg_s(90e6,298.15,5e6)
    assert atmospheric > 0
    assert atmospheric == pytest.approx(higher_backpressure,rel=2e-5)
    assert restriction.mass_flow_kg_s(90e6,298.15,89e6) < atmospheric

def test_analysis_includes_hazop_candidates_without_claiming_plc_trip():
    from h2station.api import _analyze_frame
    frame={'hazop':{'active':[{'severity':'ALARM'}]}}
    assert _analyze_frame(frame)['status']=='WARNING'
    frame['hazop']['active'][0]['severity']='TRIP'
    assert _analyze_frame(frame)['status']=='CRITICAL'
    assert not any('ESD 래치' in s for s in _analyze_frame(frame)['findings'])
    assert _analyze_frame({})['status']=='NORMAL'
