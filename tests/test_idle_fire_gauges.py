import pytest
from h2station.api import ProcessSettings
from h2station.operations import ProcessRuntime
from h2station.scenario import ReferenceScenario,build_reference_scenario
from h2station.safety_runtime import FaultEvent,FaultKind
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
@pytest.mark.parametrize('target',['cascade.low','cascade.medium','cascade.high','dispenser.hose','dispenser_2.hose'])
def test_idle_fire_heats_without_negative_pressure_or_zero_flow_throttling_failure(target):
 fire=FaultEvent('idle-heat',FaultKind.EXTERNAL_FIRE,target,0,end_time_s=15,external_temperature_k=1073.15,heat_transfer_ua_w_k=1000)
 b=build_reference_scenario(ReferenceScenario(fault_events=(fire,)),UnavailableHyRAMBackend());b.simulator.process_runtime=ProcessRuntime(ProcessSettings().model_dump());frames=[]
 b.simulator.simulate(b.initial_state,20,.5,sample_callback=frames.append)
 def readings(f):
  if target.startswith('cascade.'):return f.bank_pressure_pa[target.split('.')[1]],f.bank_temperature_k[target.split('.')[1]]
  prefix='hose_2' if target.startswith('dispenser_2') else 'hose';return getattr(f,prefix+'_pressure_pa'),getattr(f,prefix+'_temperature_k')
 p0,t0=readings(frames[0]);p1,t1=readings(frames[28]);assert p1>=p0-1;assert t1>t0
 assert all(p>0 and t>0 for p,t in map(readings,frames))
 assert frames[-1].nozzle_mass_flow_kg_s==0

@pytest.mark.parametrize('target', ['dispenser.hose', 'dispenser_2.hose'])
def test_idle_hose_residual_heat_dissipates_after_fire(target):
 fire=FaultEvent('residual-heat',FaultKind.EXTERNAL_FIRE,target,0,end_time_s=15,external_temperature_k=473.15,heat_transfer_ua_w_k=200)
 b=build_reference_scenario(ReferenceScenario(fault_events=(fire,)),UnavailableHyRAMBackend())
 b.simulator.process_runtime=ProcessRuntime(ProcessSettings().model_dump());frames=[]
 b.simulator.simulate(b.initial_state,60,.5,sample_callback=frames.append)
 prefix='hose_2' if target.startswith('dispenser_2') else 'hose'
 hot=next(f for f in frames if f.time_s>=20)
 assert getattr(frames[-1],prefix+'_temperature_k') < getattr(hot,prefix+'_temperature_k')
 assert 0 < getattr(frames[-1],prefix+'_pressure_pa') < getattr(hot,prefix+'_pressure_pa')
 assert frames[-1].nozzle_mass_flow_kg_s == 0


@pytest.mark.parametrize('target',['cascade.low','cascade.medium','cascade.high','dispenser.hose','dispenser_2.hose','vehicle.tank','vehicle_2.tank'])
def test_sustained_depressurization_does_not_create_a_vacuum(target):
 event=FaultEvent('depressurize',FaultKind.PRESSURE_DISTURBANCE,target,0,magnitude=-100,rate_s=1)
 b=build_reference_scenario(ReferenceScenario(fault_events=(event,)),UnavailableHyRAMBackend())
 b.simulator.process_runtime=ProcessRuntime(ProcessSettings().model_dump());frames=[]
 b.simulator.simulate(b.initial_state,60,1,sample_callback=frames.append)
 def reading(f,kind):
  if target.startswith('cascade.'):return getattr(f,'bank_'+kind)[target.split('.')[1]]
  prefix={'dispenser.hose':'hose','dispenser_2.hose':'hose_2','vehicle.tank':'vehicle','vehicle_2.tank':'vehicle_2'}[target]
  return getattr(f,prefix+'_'+kind)
 pressures=[reading(f,'pressure_pa') for f in frames]
 assert min(pressures)>=101325*.99
 assert pressures[-1]<pressures[0]
 assert all(reading(f,'pressure_pa')>0 for f in frames)
