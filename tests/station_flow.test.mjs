import assert from 'node:assert/strict';
import test from 'node:test';
import { stationRouteActive } from '../web/station-flow.mjs';

test('vehicle 2 alone lights only its fueling route and selected bank', () => {
  const live = { esd:false, flow1:0, flow2:12, dispatch:null,
    dispatch2:'medium', recharge:null };
  assert.equal(stationRouteActive('fueling',live),false);
  assert.equal(stationRouteActive('fueling2',live),true);
  assert.equal(stationRouteActive('dispatch:low',live),false);
  assert.equal(stationRouteActive('dispatch:medium',live),true);
});

test('vehicle 1 and shutdown use their own signals', () => {
  const live = { esd:false, flow1:9, flow2:0, dispatch:'high',
    dispatch2:null, recharge:'low' };
  assert.equal(stationRouteActive('fueling',live),true);
  assert.equal(stationRouteActive('fueling2',live),false);
  assert.equal(stationRouteActive('dispatch:high',live),true);
  assert.equal(stationRouteActive('recharge:low',live),true);
  assert.equal(stationRouteActive('compressor',live),true);
  live.esd = true;
  assert.equal(stationRouteActive('fueling',live),false);
  assert.equal(stationRouteActive('compressor',live),false);
});
