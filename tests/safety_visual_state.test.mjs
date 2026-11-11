import assert from 'node:assert/strict';
import test from 'node:test';
import { safetyVisualState } from '../web/safety-visual-state.mjs';
test('spray follows running feedback, not commands; fire stays until input ends',()=>{
 const s={cooling:{low:{commanded:true,running:false,fault:true}}};
 assert.deepEqual(safetyVisualState(s).spraying,[]);
 s.cooling.low={commanded:true,running:true,fault:false};
 const active=safetyVisualState(s,['external-fire:cascade.low']);
 assert.deepEqual(active.spraying,['low']);
 assert.ok(active.badges.some(x=>x.includes('화재 입력 유지')));
 assert.ok(!safetyVisualState(s,[]).badges.some(x=>x.includes('화재 입력 유지')));
 s.cooling.low.running=false;
 assert.deepEqual(safetyVisualState(s).spraying,[]);
 assert.deepEqual(safetyVisualState(null).spraying,[]);
});
test('auxiliary, power, access and recovery changes invalidate the visual state',()=>{
 const state={time_s:1,cooling:{},ventilation:{storage:{running:true}},power_isolated:{storage:false},access_restricted:{storage:false}};
 const first=safetyVisualState(state);
 state.time_s=2;assert.equal(first.signature,safetyVisualState(state).signature);
 state.power_isolated.storage=true;assert.notEqual(first.signature,safetyVisualState(state).signature);
 state.access_restricted.storage=true;state.responders_notified=true;state.recovery_approved=true;
 const result=safetyVisualState(state);
 assert.ok(result.badges.some(x=>x.includes('전원 차단')));
 assert.ok(result.badges.some(x=>x.includes('출입 통제')));
 assert.ok(result.badges.some(x=>x.includes('통보 완료')));
 assert.ok(result.badges.some(x=>x.includes('재가동 승인')));
});


test('ventilation stop stays visible rather than silently dropping the running badge',()=>{
 const state={ventilation:{compressor:{running:true,fault:false}}};
 const on=safetyVisualState(state);
 state.ventilation.compressor.running=false;
 const off=safetyVisualState(state);
 assert.deepEqual(off.ventilating,[]);
 assert.ok(off.badges.includes('압축기 환기 정지'));
 assert.notEqual(on.signature,off.signature);
});


test('dispenser spray feedback and extinguished flame have matching readable badges',()=>{
 const state={cooling:{dispenser_2:{running:true,commanded:true}},
  fire_response:{f:{target:'dispenser_2.hose',status:'suppressing',intensity:.5}}};
 const active=safetyVisualState(state,['external-fire:dispenser_2.hose']);
 assert.deepEqual(active.spraying,['dispenser_2']);
 assert.ok(active.badges.includes('2번 충전호스 훈련 화재 50% · 살수로 감소 중'));
 state.cooling.dispenser_2={running:false,commanded:false,auto_stopped:true};
 state.fire_response.f={...state.fire_response.f,status:'extinguished',intensity:0};
 const ended=safetyVisualState(state);
 assert.deepEqual(ended.spraying,[]);
 assert.ok(ended.badges.includes('2번 충전호스·차량 잔열 냉각 완료 · 자동 종료'));
 assert.ok(ended.badges.includes('2번 충전호스 훈련 화재 소멸 · 복구 점검 대기'));
});
