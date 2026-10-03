import assert from 'node:assert/strict';
import test from 'node:test';
import { reconcileRiskRanges } from '../web/risk-range-state.mjs';
import { consequenceDisplayGeometry } from '../web/consequence-geometry.mjs';

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

test('the overlay includes a longer four-percent flammable plume',()=>{
  const row=release(2);
  row.consequence.flammable_plume_streamline_distance_m=6.5;
  const state=reconcileRiskRanges(new Map(),[row],0);
  assert.equal(state.get('leak-1').radius,6.5);
  assert.equal(state.get('leak-1').geometry.thermalBlastRadiusM,2);
  assert.equal(state.get('leak-1').geometry.flammablePlumeLengthM,6.5);
});

test('radial screening and directional plume geometry remain distinct',()=>{
  const geometry=consequenceDisplayGeometry({
    sampled_effect_radius_m:3,
    flammable_plume_streamline_distance_m:9,
    flammable_plume_x_extent_m:[0,9],
    flammable_plume_y_extent_m:[-1.2,1.2],
    release_angle_rad:Math.PI/2,
  });
  assert.equal(geometry.thermalBlastRadiusM,3);
  assert.equal(geometry.flammablePlumeLengthM,9);
  assert.equal(geometry.flammablePlumeHalfWidthM,1.2);
  assert.equal(geometry.releaseAngleRad,Math.PI/2);
  assert.equal(geometry.maxDisplayDistanceM,9);
});

test('active releases retain separate peak radial and plume distances',()=>{
  const first=release(7);
  first.consequence.flammable_plume_streamline_distance_m=4;
  const second=release(3);
  second.consequence.flammable_plume_streamline_distance_m=11;
  let state=reconcileRiskRanges(new Map(),[first],0);
  state=reconcileRiskRanges(state,[second],100);
  assert.equal(state.get('leak-1').geometry.thermalBlastRadiusM,7);
  assert.equal(state.get('leak-1').geometry.flammablePlumeLengthM,11);
  assert.equal(state.get('leak-1').displayState,'PEAK_HELD');
});
