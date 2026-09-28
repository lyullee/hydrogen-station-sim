"""The remote library only exposes working fault/target combinations."""
import json
from pathlib import Path
import numpy as np
import pytest
from h2station.api import SimulationInput
from h2station.hazop.mapping import MODEL_BINDINGS
from h2station.hazop.runtime import HazopMonitor
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario
from h2station.safety_runtime import FaultKind

CATALOG=json.loads((Path(__file__).resolve().parents[1]/'web/scenarios.json').read_text(encoding='utf-8'))


def test_remote_catalog_covers_all_implemented_faults_and_mapped_sensors():
    assert {k['id'] for k in CATALOG['kinds']}=={k.value for k in FaultKind}
    assert {f['kind'] for s in CATALOG['scenarios'] for f in s['faults']}=={k.value for k in FaultKind}
    assert len(CATALOG['scenarios'])==68
    assert len({s['id'] for s in CATALOG['scenarios']})==68
    for kind in ('sensor-bias','sensor-freeze'):
        assert {t['value'] for t in next(k for k in CATALOG['kinds'] if k['id']==kind)['targets']}==set(MODEL_BINDINGS)


@pytest.mark.parametrize('scenario',CATALOG['scenarios'],ids=lambda s:s['id'])
def test_preset_payload_and_model_execute(scenario):
    # Keep relative start times for compound events, moving the first event to 0.
    start=min(f['start_time_s'] for f in scenario['faults'])
    faults=[{**f,'start_time_s':f['start_time_s']-start,'end_time_s':None if f['end_time_s'] is None else f['end_time_s']-start} for f in scenario['faults']]
    request=SimulationInput(duration_s=.2,control_period_s=.2,faults=faults)
    for fault in request.faults:
        kind=next(k for k in CATALOG['kinds'] if k['id']==fault.kind.value)
        assert fault.target in {t['value'] for t in kind['targets']}
        assert fault.start_time_s<30
    built=build_reference_scenario(ReferenceScenario(fault_events=tuple(f.to_event() for f in request.faults)),UnavailableHyRAMBackend())
    built.simulator.hazop_monitor=HazopMonitor(virtual_detectors=True)
    trajectory=built.simulator.simulate(built.initial_state,.2,.2)
    assert len(trajectory.time_s)==2
    assert np.isfinite(trajectory.states).all()
    assert trajectory.final_state is not None


@pytest.mark.parametrize('target', ['cascade.low', 'cascade.medium', 'cascade.high', 'dispenser.hose', 'dispenser_2.hose'])
@pytest.mark.parametrize('source_c', [-40, 800])
def test_external_heat_reaches_wall_and_process_gas(target, source_c):
    """Heat must change inventory temperature, not just render a fire marker."""
    event = SimulationInput(faults=[{
        'event_id': 'thermal', 'kind': 'temperature-disturbance', 'target': target,
        'start_time_s': 0, 'external_temperature_c': source_c,
        'heat_transfer_ua_w_k': 1000,
    }]).faults[0].to_event()
    base = build_reference_scenario(ReferenceScenario(), UnavailableHyRAMBackend())
    heated = build_reference_scenario(ReferenceScenario(fault_events=(event,)), UnavailableHyRAMBackend())
    normal = base.simulator.simulate(base.initial_state, 2, .2).final_state
    changed = heated.simulator.simulate(heated.initial_state, 2, .2).final_state
    direction = 1 if source_c > 25 else -1
    if target.startswith('cascade.'):
        index = {'cascade.low': 0, 'cascade.medium': 1, 'cascade.high': 2}[target]
        normal_wall, changed_wall = normal.banks[index].wall_temperature_k, changed.banks[index].wall_temperature_k
    else:
        normal_line = normal.partial_station if target == 'dispenser.hose' else normal.secondary_partial_station
        changed_line = changed.partial_station if target == 'dispenser.hose' else changed.secondary_partial_station
        normal_wall, changed_wall = normal_line.hose_wall_temperature_k, changed_line.hose_wall_temperature_k
    assert direction * (changed_wall - normal_wall) > 0
    normal_gas = base.simulator._gas_for_target(target, normal)
    changed_gas = heated.simulator._gas_for_target(target, changed)
    assert direction * (changed_gas.temperature_k - normal_gas.temperature_k) > 0
