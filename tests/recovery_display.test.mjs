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


for(const transition of ['new-job','new-hazard'])test(`${transition} clears the previous action result`,async()=>{
 let tick,click,currentJob='old';
 const host={innerHTML:'',querySelector:selector=>selector==='#replaySlider'?null:({value:'',addEventListener:()=>{}}),querySelectorAll:()=>[],contains:()=>false,addEventListener:(type,fn)=>{if(type==='click')click=fn;}};
 const s={current_metrics:{time_s:1},recovery_approved:true,active_incidents:[],actions:[],personnel:{},evacuated:{},access_restricted:{},power_isolated:{},recovery:{},valves:{}};
 const context={document:{getElementById:()=>host,querySelector:()=>({getAttribute:()=> 'true'})},window:{getRemoteJobId:()=>currentJob,addEventListener:()=>{},executeVirtualSafetyAction:async()=>({status:'confirmed',kind:'esd.trip'})},setInterval:fn=>tick=fn,setTimeout:()=>{},fetch:async()=>({ok:true,json:async()=>({...s})})};
 vm.runInNewContext(readFileSync(new URL('../web/safety-console.js',import.meta.url),'utf8'),context);
 tick();await new Promise(resolve=>setImmediate(resolve));
 const button={dataset:{action:'esd.trip',target:'station'},textContent:'이전 훈련 차단',hasAttribute:()=>false};
 await click({target:{closest:selector=>selector==='button'?button:null}});
 assert.ok(host.innerHTML.includes('이전 훈련 차단 · 완료'));
 if(transition==='new-job')currentJob='new';else s.recovery_approved=false;tick();await new Promise(resolve=>setImmediate(resolve));
 assert.ok(!host.innerHTML.includes('이전 훈련 차단'));

});


test('hose incident requires dispenser evacuation and keeps the same zone after repair',async()=>{
 let tick;
 const host={innerHTML:'',querySelector:selector=>selector==='#replaySlider'?null:({value:'',addEventListener:()=>{}}),contains:()=>false,addEventListener:()=>{}};
 const s={current_metrics:{time_s:20},active_incidents:[{kind:'hydrogen-leak',target:'dispenser.hose'}],actions:[{kind:'personnel.evacuate',target:'storage',status:'confirmed',completed_s:1},{kind:'restart.approve',status:'confirmed',completed_s:2}],personnel:{storage:2,dispenser:2},evacuated:{storage:0,dispenser:0},access_restricted:{},power_isolated:{},recovery:{},valves:{}};
 const context={document:{getElementById:()=>host,querySelector:()=>({getAttribute:()=> 'true'})},window:{getRemoteJobId:()=> 'hose',addEventListener:()=>{}},setInterval:fn=>tick=fn,setTimeout:()=>{},fetch:async()=>({ok:true,json:async()=>({...s})})};
 vm.runInNewContext(readFileSync(new URL('../web/safety-console.js',import.meta.url),'utf8'),context);
 tick();await new Promise(resolve=>setImmediate(resolve));
 assert.ok(host.innerHTML.includes('충전구역 잔류 2명 대피 필요'));
 assert.ok(!host.innerHTML.includes('저장구역 잔류 2명 대피 필요'));
 s.current_metrics.time_s=30;s.active_incidents=[];s.personnel.dispenser=0;s.evacuated.dispenser=2;
 s.actions.push({kind:'personnel.evacuate',target:'dispenser',status:'confirmed',completed_s:25});
 tick();await new Promise(resolve=>setImmediate(resolve));
 assert.ok(host.innerHTML.includes('충전구역 2명 대피 및 누출·가스 안정화 확인'));
 const stage=host.innerHTML.match(/<article[^>]*><span>03<\/span>[\s\S]*?<\/article>/)?.[0];
 assert.ok(stage?.includes('30.0 s'));
 assert.ok(!stage?.includes('25.0 s'));
 assert.ok(!host.innerHTML.includes('저장구역 잔류 2명 대피 필요'));
});
