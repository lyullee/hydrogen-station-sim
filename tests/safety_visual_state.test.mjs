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
