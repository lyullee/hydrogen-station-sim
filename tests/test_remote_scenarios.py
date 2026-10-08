"""The remote library only exposes working fault/target combinations."""
import json
from pathlib import Path
import numpy as np
import pytest
from pydantic import ValidationError
from h2station.api import SimulationInput
from h2station.hazop.mapping import MODEL_BINDINGS
from h2station.hazop.runtime import HazopMonitor
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.protocol import CommunicationLossPolicy
from h2station.scenario import ReferenceScenario, build_reference_scenario
from h2station.safety_runtime import FaultKind

CATALOG=json.loads((Path(__file__).resolve().parents[1]/'web/scenarios.json').read_text(encoding='utf-8'))
ROOT = Path(__file__).resolve().parents[1]


def test_remote_exposes_optional_hgv43_training_controls():
    html = (ROOT / 'web/remote.html').read_text(encoding='utf-8')
    script = (ROOT / 'web/remote.js').read_text(encoding='utf-8')
    for control_id in (
        'minimumStartupTime', 'maximumStartupMass', 'startupMassWindow',
        'pressureCorridorLower', 'pressureCorridorUpper',
        'fuelingTemperatureCategory', 'communicationLossPolicy',
    ):
        assert f'id="{control_id}"' in html
        assert control_id in script
    assert 'SAE J2601 또는 HGV 4.3 인증 시험이 아닙니다' in html
    assert not script.rstrip().endswith(r'\n')


def test_hgv43_training_inputs_require_a_complete_startup_mass_window():
    with pytest.raises(ValidationError, match="must be configured together"):
        SimulationInput(maximum_startup_mass_kg=0.05)

    request = SimulationInput(
        maximum_startup_mass_kg=0.05,
        startup_mass_window_s=3.0,
        minimum_startup_time_s=1.0,
        pressure_corridor_lower_tolerance_mpa=2.0,
        pressure_corridor_upper_tolerance_mpa=3.0,
        fueling_temperature_category="T30",
        communication_loss_policy="hold-and-resume",
    )
    assert request.maximum_startup_mass_kg == pytest.approx(0.05)
    assert request.startup_mass_window_s == pytest.approx(3.0)
    assert request.fueling_temperature_category == "T30"
    assert request.communication_loss_policy == "hold-and-resume"


def test_remote_catalog_covers_all_implemented_faults_and_mapped_sensors():
    assert {k['id'] for k in CATALOG['kinds']}=={k.value for k in FaultKind}
    assert {f['kind'] for s in CATALOG['scenarios'] for f in s['faults']}=={k.value for k in FaultKind}
    assert len(CATALOG['scenarios'])==74
    assert len({s['id'] for s in CATALOG['scenarios']})==74
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


def test_dispenser_communication_fault_reaches_selected_controller_feedback():
    event = SimulationInput(duration_s=.2, control_period_s=.2, faults=[{
        'event_id': 'crc-1',
        'kind': 'communication-invalid-crc',
        'target': 'dispenser',
        'start_time_s': 0,
    }]).faults[0].to_event()
    built = build_reference_scenario(
        ReferenceScenario(fault_events=(event,)), UnavailableHyRAMBackend()
    )
    samples = []

    built.simulator.simulate(
        built.initial_state, .2, .2, sample_callback=samples.append
    )

    assert samples[-1].fueling_communication_state == 'invalid-crc'
    assert samples[-1].fueling_stop_reason == 'communication-invalid-crc'
    assert samples[-1].fueling_2_communication_state == 'valid'


def test_finite_data_loss_holds_then_resumes_selected_dispenser():
    event = SimulationInput(duration_s=.6, control_period_s=.2, faults=[{
        'event_id': 'loss-1',
        'kind': 'communication-data-loss',
        'target': 'dispenser',
        'start_time_s': 0,
        'end_time_s': .2,
    }]).faults[0].to_event()
    built = build_reference_scenario(
        ReferenceScenario(
            duration_s=.6,
            control_period_s=.2,
            fault_events=(event,),
            communication_loss_policy=CommunicationLossPolicy.HOLD_AND_RESUME,
        ),
        UnavailableHyRAMBackend(),
    )
    samples = []

    built.simulator.simulate(
        built.initial_state, .6, .2, sample_callback=samples.append
    )

    assert samples[0].fueling_communication_state == 'data-loss'
    assert samples[0].fueling_stop_reason == 'communication-data-loss-hold'
    assert samples[-1].fueling_communication_state == 'valid'
    assert samples[-1].fueling_stop_reason is None
    assert samples[-1].fueling_2_communication_state == 'valid'


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
