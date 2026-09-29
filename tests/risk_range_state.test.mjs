import assert from 'node:assert/strict';
import test from 'node:test';
import { reconcileRiskRanges } from '../web/risk-range-state.mjs';

const release=(radius)=>({id:'leak-1',component:'dispenser.hose',actual:true,
  consequence:{sampled_effect_radius_m:radius}});
const hypothesis=(radius)=>({id:'scenario-N13',component:'dispenser.hose',actual:false,
  consequence:{sampled_effect_radius_m:radius}});

test('an active release keeps its peak radius through a below-threshold recalculation',()=>{
  let state=reconcileRiskRanges(new Map(),[release(5)],0);
  state=reconcileRiskRanges(state,[release(0)],500);
  assert.equal(state.get('leak-1').radius,5);
  assert.equal(state.get('leak-1').displayState,'PEAK_HELD');
  state=reconcileRiskRanges(state,[release(3)],1000);
  assert.equal(state.get('leak-1').radius,5);
  state=reconcileRiskRanges(state,[release(8)],1500);
  assert.equal(state.get('leak-1').radius,8);
});

test('a finished release is labelled as recent, then removed after the grace period',()=>{
  let state=reconcileRiskRanges(new Map(),[release(5)],0);
  state=reconcileRiskRanges(state,[],1000);
  assert.equal(state.get('leak-1').displayState,'RECENTLY_ENDED');
  state=reconcileRiskRanges(state,[],3101);
  assert.equal(state.has('leak-1'),false);
});

test('hypothetical cases follow the current assessment, not a past peak',()=>{
  let state=reconcileRiskRanges(new Map(),[hypothesis(5)],0);
  state=reconcileRiskRanges(state,[hypothesis(3)],100);
  assert.equal(state.get('scenario-N13').radius,3);
  state=reconcileRiskRanges(state,[],200);
  assert.equal(state.has('scenario-N13'),false);
});
