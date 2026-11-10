import pytest
from h2station.virtual_safety import VirtualSafetyRuntime
from h2station.safety_runtime import FaultEvent, FaultKind


@pytest.mark.parametrize("bank", ["low", "medium", "high"])
def test_delayed_spray_does_not_leave_a_hot_wall_reheating_the_bank_for_minutes(bank):
    from h2station.scenario import ReferenceScenario, build_reference_scenario
    from h2station.operations import ProcessRuntime
    from h2station.api import ProcessSettings
    from h2station.risk.runtime_backend import UnavailableHyRAMBackend

    fire = FaultEvent("long-fire", FaultKind.EXTERNAL_FIRE, f"cascade.{bank}", 46,
                      external_temperature_k=1073.15, heat_transfer_ua_w_k=1000)
    built = build_reference_scenario(
        ReferenceScenario(fault_events=(fire,)), UnavailableHyRAMBackend()
    )
    process = ProcessRuntime(ProcessSettings().model_dump())
    built.simulator.process_runtime = process
    def operate(time_s):
        device = process.safety.cooling[bank]
        if time_s >= 69 and not device["commanded"] and not device.get("auto_stopped"):
            process.safety.issue("cooling.on", bank, time_s)
    frames = []
    result = built.simulator.simulate(
        built.initial_state, 450, 1, sample_callback=frames.append,
        runtime_command_callback=operate, pace_idle=False
    )
    after_cooling = next(frame for frame in frames if frame.time_s >= 110)
    assert frames[-1].bank_temperature_k[bank] < after_cooling.bank_temperature_k[bank]
    assert frames[-1].bank_pressure_pa[bank] < after_cooling.bank_pressure_pa[bank]
    index = ("low", "medium", "high").index(bank)
    assert result.final_state.banks[index].wall_temperature_k < 298.35
    assert process.safety.cooling[bank]["auto_stopped"]

def test_fire_heat_and_response_decay_together_and_fault_interrupts():
    runtime=VirtualSafetyRuntime()
    fire=FaultEvent('fire',FaultKind.EXTERNAL_FIRE,'cascade.low',0,
                    external_temperature_k=1073.15,heat_transfer_ua_w_k=600)
    assert runtime.response_events((fire,),0)==(fire,)
    runtime.issue('cooling.on','low',0)
    effective=runtime.response_events((fire,),15)
    assert effective[0].heat_transfer_ua_w_k==pytest.approx(300)
    assert runtime.snapshot()['fire_response']['fire']['intensity']==pytest.approx(.5)
    # Repeated sampling cannot advance response without elapsed model time.
    assert runtime.response_events((fire,),15)[0].heat_transfer_ua_w_k==pytest.approx(300)
    runtime.set_fault('cooling.low','failure',15)
    assert runtime.response_events((fire,),21)[0].heat_transfer_ua_w_k==pytest.approx(360)
    runtime.set_fault('cooling.low','none',21)
    runtime.issue('cooling.on','low',21)
    assert runtime.response_events((fire,),40)==()
    assert runtime.snapshot()['fire_response']['fire']['status']=='extinguished'
    runtime.issue('cooling.off','low',40)
    assert runtime.response_events((fire,),50)==()

def test_spray_on_different_bank_does_not_extinguish_fire():
    runtime=VirtualSafetyRuntime()
    fire=FaultEvent('fire',FaultKind.EXTERNAL_FIRE,'cascade.low',0,
                    external_temperature_k=1073.15,heat_transfer_ua_w_k=600)
    runtime.response_events((fire,),0)
    runtime.issue('cooling.on','high',0)
    assert runtime.response_events((fire,),60)==(fire,)

def test_full_heat_integration_matches_fire_state_and_cools_after_extinction():
    from h2station.scenario import ReferenceScenario, build_reference_scenario
    from h2station.operations import ProcessRuntime
    from h2station.api import ProcessSettings
    from h2station.risk.runtime_backend import UnavailableHyRAMBackend
    fire=FaultEvent('fire',FaultKind.EXTERNAL_FIRE,'cascade.low',0,
                    external_temperature_k=1073.15,heat_transfer_ua_w_k=600)
    def run(cooling):
        built=build_reference_scenario(ReferenceScenario(duration_s=45,control_period_s=.5,fault_events=(fire,)),UnavailableHyRAMBackend())
        runtime=ProcessRuntime(ProcessSettings().model_dump())
        built.simulator.process_runtime=runtime
        if cooling:runtime.safety.issue('cooling.on','low',0)
        frames=[]
        built.simulator.simulate(built.initial_state,45,.5,sample_callback=frames.append)
        return frames,runtime
    cooled,runtime=run(True)
    hot,_=run(False)
    assert runtime.safety.snapshot()['fire_response']['fire']['status']=='extinguished'
    assert all('external-fire:cascade.low' not in f.active_faults for f in cooled if f.time_s>=31)
    assert 'external-fire:cascade.low' in hot[-1].active_faults
    assert cooled[-1].bank_temperature_k['low'] < hot[-1].bank_temperature_k['low']
    # Stored wall heat can still warm the gas after source extinction; do not
    # falsify the thermal inertia by forcing an immediate temperature drop.

def test_isolated_hose_leak_depletes_but_vessel_leak_keeps_residual_inventory():
    from h2station.scenario import ReferenceScenario, build_reference_scenario
    from h2station.operations import ProcessRuntime
    from h2station.api import ProcessSettings
    from h2station.risk.runtime_backend import UnavailableHyRAMBackend
    for target in ('dispenser.hose','cascade.low'):
        leak=FaultEvent('leak',FaultKind.HYDROGEN_LEAK,target,0,leak_diameter_m=.001)
        built=build_reference_scenario(ReferenceScenario(duration_s=60,control_period_s=.5,fault_events=(leak,)),UnavailableHyRAMBackend())
        runtime=ProcessRuntime(ProcessSettings().model_dump());built.simulator.process_runtime=runtime
        for valve in ('dispenser.1','bank.low.inlet','bank.low.outlet'):
            runtime.safety.issue('valve.close',valve,0)
        frames=[]
        built.simulator.simulate(built.initial_state,180,.5,sample_callback=frames.append)
        first=frames[0].total_leak_mass_flow_kg_s;last=frames[-1].total_leak_mass_flow_kg_s
        if target=='dispenser.hose':assert last < first*.01
        else:assert 0 < last < first

def test_vent_release_is_not_reported_as_a_bank_body_leak():
    from h2station.scenario import ReferenceScenario, build_reference_scenario
    from h2station.operations import ProcessRuntime
    from h2station.api import ProcessSettings
    from h2station.risk.runtime_backend import UnavailableHyRAMBackend
    built=build_reference_scenario(ReferenceScenario(duration_s=2,control_period_s=.2),UnavailableHyRAMBackend())
    runtime=ProcessRuntime(ProcessSettings().model_dump());built.simulator.process_runtime=runtime
    runtime.safety.issue('vent.open','vent.low',0)
    from h2station.hazop.runtime import HazopMonitor
    built.simulator.hazop_monitor=HazopMonitor(virtual_detectors=True)
    frames=[];built.simulator.simulate(built.initial_state,2,.2,sample_callback=frames.append)
    assert 'vent-open:cascade.low' in frames[-1].active_faults
    assert 'hydrogen-leak:cascade.low' not in frames[-1].active_faults
    signals=frames[-1].hazop['signals']
    assert signals['GD-2001']['value']>0
    assert signals['GD-0701']['value']==0


def test_post_fire_cooling_stops_after_delay_even_when_fire_event_removed():
    runtime = VirtualSafetyRuntime()
    fire = FaultEvent('post', FaultKind.EXTERNAL_FIRE, 'cascade.low', 0,
                      external_temperature_k=1073.15, heat_transfer_ua_w_k=600)
    runtime.issue('cooling.on', 'low', 0)
    runtime.response_events((fire,), 0)
    runtime.response_events((fire,), 30)
    assert runtime.cooling['low']['post_cooling_remaining_s'] == 10
    runtime.response_events((), 35)
    assert runtime.cooling['low']['running']
    assert runtime.cooling['low']['post_cooling_remaining_s'] == 5
    runtime.response_events((), 40)
    assert not runtime.cooling['low']['running']
    assert runtime.cooling['low']['auto_stopped']
    assert runtime.cooling_events(40, 298.15) == ()
    assert all(row['running'] for row in runtime.ventilation.values())


def test_post_cooling_fault_pauses_and_new_fire_cancels_countdown():
    runtime = VirtualSafetyRuntime()
    fire = FaultEvent('first', FaultKind.EXTERNAL_FIRE, 'cascade.low', 0,
                      external_temperature_k=1073.15, heat_transfer_ua_w_k=600)
    runtime.issue('cooling.on', 'low', 0)
    runtime.response_events((fire,), 0)
    runtime.response_events((fire,), 30)
    runtime.set_fault('cooling.low', 'failure', 30)
    runtime.response_events((), 90)
    assert runtime.cooling['low']['post_cooling_remaining_s'] == 10
    runtime.set_fault('cooling.low', 'none', 90)
    runtime.issue('cooling.on', 'low', 90)
    new_fire = FaultEvent('second', FaultKind.EXTERNAL_FIRE, 'cascade.low', 90,
                          external_temperature_k=1073.15, heat_transfer_ua_w_k=600)
    runtime.response_events((new_fire,), 90)
    assert 'post_cooling_remaining_s' not in runtime.cooling['low']
    runtime.response_events((new_fire,), 100)
    assert runtime.cooling['low']['running']


def test_ended_first_fire_does_not_block_second_fire_cooling_shutdown():
    runtime = VirtualSafetyRuntime()
    first = FaultEvent('first-ended', FaultKind.EXTERNAL_FIRE, 'cascade.low', 0,
                      external_temperature_k=1073.15, heat_transfer_ua_w_k=600)
    second = FaultEvent('second-extinguished', FaultKind.EXTERNAL_FIRE, 'cascade.low', 30,
                       external_temperature_k=1073.15, heat_transfer_ua_w_k=600)
    runtime.response_events((first,), 0)
    runtime.response_events((), 20)
    assert runtime.fire_response[first.event_id]['status'] == 'ended'
    runtime.response_events((second,), 30)
    runtime.issue('cooling.on', 'low', 30)
    runtime.response_events((second,), 60)
    assert runtime.fire_response[second.event_id]['status'] == 'extinguished'
    runtime.response_events((), 75)
    assert runtime.cooling['low']['auto_stopped']
    assert not runtime.cooling['low']['running']
