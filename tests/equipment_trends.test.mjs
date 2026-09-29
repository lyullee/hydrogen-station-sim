import assert from 'node:assert/strict';
import {test} from 'node:test';
import {faultNodes,incidentSegments} from '../web/equipment-trends.mjs';

test('faults affect only their mapped flow-diagram equipment',()=>{
  assert.deepEqual(faultNodes('hydrogen-leak:cascade.medium'),['N08']);
  assert.deepEqual(faultNodes('external-fire:vehicle_2.tank'),['N18']);
  assert.deepEqual(faultNodes('sensor-bias:PT-0901'),['N09']);
});

test('incident bands track overlapping faults and selected equipment',()=>{
  const times=[0,1,2,3,4];
  const faults=[[],['hydrogen-leak:cascade.medium'],['hydrogen-leak:cascade.medium','external-fire:cascade.low'],['external-fire:cascade.low'],[]];
  assert.deepEqual(incidentSegments(times,faults,['N08']),[
    {fault:'hydrogen-leak:cascade.medium',start:1,end:3,nodes:['N08']}
  ]);
  assert.deepEqual(incidentSegments(times,faults,['N07','N08']).map(({fault,start,end})=>[fault,start,end]),[
    ['hydrogen-leak:cascade.medium',1,3],['external-fire:cascade.low',2,4]
  ]);
});
