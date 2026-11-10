import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {currentFireResponse,safetyVisualState} from '../web/safety-visual-state.mjs';
test('repeated fire uses current active response instead of extinguished history',()=>{
 const s={fire_response:{old:{target:'cascade.low',status:'extinguished',intensity:0},new:{target:'cascade.low',status:'suppressing',intensity:.63}}};
 assert.equal(currentFireResponse(s,'cascade.low').intensity,.63);
 assert.ok(safetyVisualState(s).badges[0].includes('63%'));
 assert.ok(!safetyVisualState(s).badges.some(x=>x.includes('소멸')));
});
test('ESD does not keep stabilization pending; incomplete recovery guides rather than submits approval',async()=>{
 const host={innerHTML:'',querySelector:selector=>selector==="#replaySlider"?null:({value:"",addEventListener:()=>{}}),contains:()=>false,addEventListener:()=>{}};
 const s={current_metrics:{time_s:200},active_incidents:[],actions:[{kind:'personnel.evacuate',target:'storage',status:'confirmed',completed_s:100}],personnel:{storage:0},evacuated:{storage:2},access_restricted:{},power_isolated:{},recovery:{},valves:{},esd_requested:true};
 let tick;
 const context={document:{getElementById:()=>host,querySelector:()=>({getAttribute:()=> 'true'})},window:{getRemoteJobId:()=> 'test',latestProcessFrame:{active_faults:['emergency-stop:station']},addEventListener:()=>{}},setInterval:fn=>tick=fn,setTimeout:()=>{},fetch:async()=>({ok:true,json:async()=>s})};
 vm.runInNewContext(readFileSync(new URL('../web/safety-console.js',import.meta.url),'utf8'),context);
 tick();await new Promise(resolve=>setImmediate(resolve));
 assert.ok(host.innerHTML.includes('대피 및 누출·가스 안정화 확인'));
 assert.ok(host.innerHTML.includes('복구 점검 진행'));
 assert.ok(host.innerHTML.includes('다음 순서: 원인 제거'));
 assert.ok(!host.innerHTML.includes('data-action="restart.approve"'));
});
