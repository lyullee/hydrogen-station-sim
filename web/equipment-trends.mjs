/* Shared-time comparison of the process nodes represented on the flow diagram. */
const EQUIPMENT = [
  {id:'N01',name:'튜브트레일러',group:'supply'},
  {id:'N06',name:'압축기 최종 토출',group:'supply'},
  {id:'N07',name:'저압 저장',group:'storage'},
  {id:'N08',name:'중압 저장',group:'storage'},
  {id:'N09',name:'고압 저장',group:'storage'},
  {id:'N11',name:'충전기 1 · PCV',group:'fueling'},
  {id:'N12',name:'충전기 1 · 예냉',group:'fueling'},
  {id:'N14',name:'차량 1 탱크',group:'fueling'},
  {id:'N15',name:'충전기 2 · PCV',group:'fueling'},
  {id:'N16',name:'충전기 2 · 예냉',group:'fueling'},
  {id:'N18',name:'차량 2 탱크',group:'fueling'},
];
const COLORS=['#146aa3','#bb691d','#14856c','#a24878','#7468ad','#ae563f','#487ba9','#859126','#975d98','#499077','#425b7f'];
const METRICS=[{key:'P',name:'압력',unit:'MPa',decimals:1},{key:'T',name:'온도',unit:'°C',decimals:1},{key:'F',name:'유량',unit:'g/s',decimals:2}];
const GROUPS={supply:['N01','N06'],storage:['N07','N08','N09'],fueling:['N11','N12','N14','N15','N16','N18']};
const FLOW_INLET_TAG={N14:'FT-1301',N18:'FT-1701'};
const FAULT_NODES={
  'cascade.low':['N07'],'cascade.medium':['N08'],'cascade.high':['N09'],
  cascade:['N07','N08','N09'],header:['N07','N08','N09','N11','N15'],
  'dispenser.hose':['N11','N12','N14'],'dispenser_2.hose':['N15','N16','N18'],
  'dispenser.pcv':['N11'],'dispenser_2.pcv':['N15'],pcv:['N11','N15'],
  'vehicle.tank':['N14'],'vehicle_2.tank':['N18'],
  compressor:['N06'],supply:['N01'],precooler:['N12','N16'],cooler:['N12','N16'],vent:['N07','N08','N09'],
  station:EQUIPMENT.map(item=>item.id)
};
const KIND_LABEL={'hydrogen-leak':'누출','external-fire':'외부 화재','relief-open':'안전밸브 방출','pressure-disturbance':'압력 교란','temperature-disturbance':'온도 교란','sensor-bias':'센서 편향','sensor-freeze':'센서 고정'};
const KIND_COLOR={'hydrogen-leak':'#d54352','external-fire':'#ed793f','relief-open':'#d89b39'};
const TARGET_LABEL=Object.fromEntries(EQUIPMENT.map(item=>[item.id,item.name]));

export function faultNodes(fault){
  const target=String(fault||'').split(':').slice(1).join(':');
  if(FAULT_NODES[target])return FAULT_NODES[target];
  const sensor=/^(?:PT|TT|FT|GD|FD)-(\d{2})\d{2}$/.exec(target);
  const node=sensor&&`N${sensor[1]}`;
  if(node&&EQUIPMENT.some(item=>item.id===node))return [node];
  if(node==='N13')return ['N11'];
  if(node==='N17')return ['N15'];
  if(node==='N19')return ['N12','N16'];
  if(node==='N22')return ['N07','N08','N09'];
  if(node==='N23')return ['N11','N15'];
  return [];
}

export function incidentSegments(times,faultFrames,selected){
  const selectedSet=new Set(selected),open=new Map(),segments=[];
  for(let i=0;i<times.length;i++){
    const active=new Set((faultFrames?.[i]||[]).filter(fault=>faultNodes(fault).some(node=>selectedSet.has(node))));
    for(const [fault,start] of open)if(!active.has(fault)){
      segments.push({fault,start,end:times[i],nodes:faultNodes(fault)});open.delete(fault);
    }
    for(const fault of active)if(!open.has(fault))open.set(fault,times[i]);
  }
  const end=times.at(-1);
  for(const [fault,start] of open)segments.push({fault,start,end,nodes:faultNodes(fault)});
  return segments;
}

function bisect(times,value){let lo=0,hi=times.length;while(lo<hi){const mid=(lo+hi)>>1;if(times[mid]<value)lo=mid+1;else hi=mid;}return lo;}
function nearest(times,value){const i=bisect(times,value);return Math.max(0,Math.min(times.length-1,i>0&&Math.abs(times[i-1]-value)<Math.abs((times[i]??Infinity)-value)?i-1:i));}
function numericSignal(frame,tag){const signal=frame?.signals?.[tag];return signal?.quality==='GOOD'&&Number.isFinite(signal.value)?signal.value:null;}
function display(value,metric){return Number.isFinite(value)?`${value.toFixed(metric.decimals)} ${metric.unit}`:'—';}
function faultDescription(fault){const [kind,target]=String(fault).split(':');const nodes=faultNodes(fault);return `${KIND_LABEL[kind]||'설비 이상'} · ${nodes.map(id=>TARGET_LABEL[id]).join('·')||target||'구역'}`;}

let catalogPromise;
function getCatalog(){return catalogPromise ||= fetch('/api/hazop/catalog').then(response=>{if(!response.ok)throw new Error('센서 목록 조회 실패');return response.json();}).catch(error=>{catalogPromise=null;throw error;});}

export function mountEquipmentTrends(body){
  const dialog=document.getElementById('workspaceDialog');dialog.classList.add('equipment-trend-dialog');body.classList.add('equipment-trend-workspace');
  body.innerHTML=`<div class="et-intro"><div><b>주요 공정 설비 비교</b><span>설비별 가상 센서값을 같은 모의 시간축에 겹쳐 봅니다.</span></div><span id="etClock">데이터 대기</span></div>
    <div class="et-toolbar"><div class="et-presets" role="group" aria-label="설비 빠른 선택"><button type="button" data-preset="storage">저장뱅크</button><button type="button" data-preset="supply">공급·압축</button><button type="button" data-preset="fueling">충전라인</button><button type="button" data-preset="all">전체 주요 설비</button></div><label>기간 <select id="etWindow"><option value="120">최근 120초</option><option value="600">최근 10분</option><option value="all">전체 이력</option></select></label><label>압력 그래프 <select id="etPressureMode"><option value="change">기간 시작 대비 변화</option><option value="absolute">절대압력 비교</option></select></label><label class="et-overlay"><input type="checkbox" id="etIncidents" checked> 사고 영향 구간</label><button type="button" id="etExport">CSV 저장</button></div>
    <div class="et-content"><aside class="et-equipment"><header><b>설비 선택</b><small id="etSelectionCount">0개 선택</small></header><div id="etEquipmentRows" class="et-equipment-rows"></div></aside><section class="et-graphs"><div id="etIncidentStrip" class="et-incident-strip"></div><div id="etCharts" class="et-charts"></div><p class="et-note">동일 시간축 · 배경색은 사고 입력 활성 시간 · 압력 변화는 기간 시작값 기준 · 저장뱅크 FT는 공정 토출 유량이며 누출 유량은 별도 표시 · GOOD 품질 센서만 표시</p></section></div>`;
  const $=id=>body.querySelector('#'+id),selected=new Set(GROUPS.storage),rows=new Map(),canvases=new Map();
  let catalog=null,alive=true,hoverIndex=null,lastPaint=0,scheduled=false;
  const equipmentRows=$('etEquipmentRows'),chartWrap=$('etCharts');
  for(const [index,item] of EQUIPMENT.entries()){
    const row=document.createElement('label');row.className='et-equipment-row';row.dataset.node=item.id;
    const check=document.createElement('input');check.type='checkbox';check.checked=selected.has(item.id);check.value=item.id;check.setAttribute('aria-label',`${item.name} 추세 표시`);
    const swatch=document.createElement('i');swatch.style.background=COLORS[index];
    const name=document.createElement('span');name.className='et-equipment-name';name.textContent=item.name;
    const tag=document.createElement('small');tag.textContent=item.id;
    const readings=document.createElement('span');readings.className='et-equipment-readings';readings.textContent='센서 연결 대기';
    row.append(check,swatch,name,tag,readings);equipmentRows.append(row);rows.set(item.id,{row,check,readings});
    check.addEventListener('change',()=>{if(check.checked)selected.add(item.id);else selected.delete(item.id);refresh();});
  }
  for(const metric of METRICS){
    const article=document.createElement('article');article.className='et-chart';
    const heading=document.createElement('header'),title=document.createElement('strong'),range=document.createElement('small');title.textContent=`${metric.name} · ${metric.unit}`;range.textContent='—';heading.append(title,range);
    const canvas=document.createElement('canvas');canvas.setAttribute('role','img');canvas.setAttribute('aria-label',`${metric.name} 설비별 공통 시간축 추세`);
    article.append(heading,canvas);chartWrap.append(article);canvases.set(metric.key,{canvas,range,title});
    canvas.addEventListener('pointermove',event=>{const times=window.getStation3DState?.()?.result?.series?.time_s||[];if(!times.length)return;const rect=canvas.getBoundingClientRect(),t0=Number(canvas.dataset.t0),t1=Number(canvas.dataset.t1),left=49,right=14;hoverIndex=nearest(times,t0+Math.max(0,Math.min(1,(event.clientX-rect.left-left)/(rect.width-left-right)))*(t1-t0));schedule(true);});
    canvas.addEventListener('pointerleave',()=>{hoverIndex=null;schedule(true);});
  }
  function chosenTags(frames,current){
    const sensors=catalog?.sensors||[],tags=new Map();
    for(const item of EQUIPMENT){const byMetric={};for(const metric of METRICS){
      const candidates=sensors.filter(sensor=>sensor.node_id===item.id&&sensor.sensor_id?.startsWith(metric.key+'T-')).map(sensor=>sensor.sensor_id);
      byMetric[metric.key]=candidates.find(tag=>numericSignal(frames[current],tag)!==null)||candidates[0]||
        (metric.key==='F'?FLOW_INLET_TAG[item.id]:null)||null;
    }tags.set(item.id,byMetric);}return tags;
  }
  function firstValue(frames,tag,first,last){for(let i=first;i<=last;i++){const value=numericSignal(frames[i],tag);if(value!==null)return value;}return null;}
  function draw(metric,times,frames,tags,segments,first,last,t0,t1,cursor){
    const {canvas,range,title}=canvases.get(metric.key),rect=canvas.getBoundingClientRect(),w=rect.width,h=rect.height;if(w<40||h<40)return;
    const ratio=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);canvas.dataset.t0=t0;canvas.dataset.t1=t1;
    const ctx=canvas.getContext('2d');ctx.scale(ratio,ratio);const p={l:49,r:14,t:10,b:22},plotW=w-p.l-p.r,plotH=h-p.t-p.b,span=Math.max(.001,t1-t0);
    const selectedItems=EQUIPMENT.filter(item=>selected.has(item.id));
    const change=metric.key==='P'&&$('etPressureMode').value==='change';
    title.textContent=change?'압력 변화 · MPa':`${metric.name} · ${metric.unit}`;
    const precision=change?2:metric.decimals;
    const baselines=new Map(selectedItems.map(item=>{const tag=tags.get(item.id)?.[metric.key];return [item.id,tag?firstValue(frames,tag,first,last):null];}));
    const valueAt=(item,i)=>{const value=numericSignal(frames[i],tags.get(item.id)?.[metric.key]);return value===null?null:change?value-(baselines.get(item.id)??value):value;};
    let lo=Infinity,hi=-Infinity;const step=Math.max(1,Math.floor((last-first)/Math.max(450,plotW*1.5)));
    for(const item of selectedItems){const tag=tags.get(item.id)?.[metric.key];if(!tag)continue;for(let i=first;i<=last;i+=step){const v=valueAt(item,i);if(v!==null){lo=Math.min(lo,v);hi=Math.max(hi,v);}}const final=valueAt(item,last);if(final!==null){lo=Math.min(lo,final);hi=Math.max(hi,final);}}
    if(!Number.isFinite(lo)){lo=0;hi=1;}const pad=Math.max(change?.02:metric.key==='F'?.05:metric.key==='P'?.2:.5,(hi-lo)*.12);lo-=pad;hi+=pad;range.textContent=`${lo.toFixed(precision)}–${hi.toFixed(precision)} ${metric.unit}`;
    ctx.fillStyle='#fff';ctx.fillRect(0,0,w,h);ctx.font='10px Consolas,monospace';ctx.textBaseline='middle';
    for(let n=0;n<4;n++){const y=p.t+n*plotH/3;ctx.strokeStyle='#e2ebf2';ctx.beginPath();ctx.moveTo(p.l,y);ctx.lineTo(w-p.r,y);ctx.stroke();ctx.fillStyle='#6b8195';ctx.fillText((hi-(hi-lo)*n/3).toFixed(precision),4,y);}
    for(const segment of segments){if(segment.end<t0||segment.start>t1)continue;const x=p.l+Math.max(0,segment.start-t0)/span*plotW,end=p.l+Math.min(span,segment.end-t0)/span*plotW;const kind=segment.fault.split(':')[0];ctx.fillStyle=kind==='external-fire'?'rgba(237,121,63,.15)':kind==='hydrogen-leak'?'rgba(213,67,82,.15)':kind==='relief-open'?'rgba(216,155,57,.12)':'rgba(110,113,159,.10)';ctx.fillRect(x,p.t,Math.max(2,end-x),plotH);}
    for(const item of selectedItems){const tag=tags.get(item.id)?.[metric.key];if(!tag)continue;ctx.strokeStyle=COLORS[EQUIPMENT.indexOf(item)];ctx.lineWidth=selectedItems.length>8?1.5:2;ctx.beginPath();let started=false;
      const point=i=>{const value=valueAt(item,i);if(value===null){started=false;return;}const x=p.l+(times[i]-t0)/span*plotW,y=p.t+plotH-(value-lo)/(hi-lo)*plotH;if(started)ctx.lineTo(x,y);else{ctx.moveTo(x,y);started=true;}};
      for(let i=first;i<=last;i+=step)point(i);if((last-first)%step)point(last);ctx.stroke();
    }
    const cursorTime=times[cursor],cursorX=p.l+(cursorTime-t0)/span*plotW;if(cursorTime>=t0&&cursorTime<=t1){ctx.strokeStyle='#294f6a';ctx.setLineDash([4,3]);ctx.beginPath();ctx.moveTo(cursorX,p.t);ctx.lineTo(cursorX,p.t+plotH);ctx.stroke();ctx.setLineDash([]);}
    ctx.fillStyle='#6b8195';ctx.textBaseline='alphabetic';ctx.fillText(`${t0.toFixed(0)} s`,p.l,h-4);ctx.textAlign='right';ctx.fillText(`${t1.toFixed(0)} s`,w-p.r,h-4);ctx.textAlign='left';
    if(!selectedItems.length||![...selectedItems].some(item=>tags.get(item.id)?.[metric.key])){ctx.fillStyle='#8b9dad';ctx.textAlign='center';ctx.fillText(selectedItems.length?'연결된 센서 없음':'비교할 설비를 선택하세요',p.l+plotW/2,p.t+plotH/2);ctx.textAlign='left';}
  }
  function refresh(){
    if(!alive)return;const runtime=window.getStation3DState?.(),series=runtime?.result?.series,times=series?.time_s||[],frames=runtime?.result?.hazop?.frames||[],last=Math.min(times.length,frames.length)-1;
    $('etSelectionCount').textContent=`${selected.size}개 선택`;
    for(const button of body.querySelectorAll('[data-preset]')){const ids=button.dataset.preset==='all'?EQUIPMENT.map(item=>item.id):GROUPS[button.dataset.preset];button.setAttribute('aria-pressed',String(ids.every(id=>selected.has(id))&&selected.size===ids.length));}
    const tags=chosenTags(frames,Math.max(0,last)),cursor=hoverIndex===null?Math.min(Math.max(0,runtime?.index??last),Math.max(0,last)):Math.min(hoverIndex,Math.max(0,last));
    $('etClock').textContent=last<0?'시뮬레이션 수신 대기':`모의 ${times[cursor].toFixed(1)} s · ${hoverIndex===null?'현재 선택 시점':'커서 시점'}`;
    const end=last<0?0:times[last],windowValue=$('etWindow').value,t0=last<0?0:windowValue==='all'?times[0]:Math.max(times[0],end-Number(windowValue)),first=last<0?0:Math.min(last,bisect(times,t0));
    for(const item of EQUIPMENT){const row=rows.get(item.id),values=METRICS.map(metric=>display(numericSignal(frames[cursor],tags.get(item.id)?.[metric.key]),metric));
      const pressureTag=tags.get(item.id)?.P,baseline=last<0?null:firstValue(frames,pressureTag,first,last),current=numericSignal(frames[cursor],pressureTag);
      const delta=baseline!==null&&current!==null?`  ·  ΔP ${(current-baseline)>=0?'+':''}${(current-baseline).toFixed(2)} MPa`:'';
      const leaks=(frames[cursor]?.releases||[]).filter(release=>faultNodes(`hydrogen-leak:${release.component_id}`).includes(item.id));
      const leakFlow=leaks.reduce((sum,release)=>sum+(Number(release.mass_flow_g_s)||0),0);
      row.readings.textContent=last<0?'데이터 대기':values.join('  ·  ')+delta+(leakFlow>0?`  ·  누출 ${leakFlow.toFixed(2)} g/s`:'');
      row.row.classList.toggle('selected',selected.has(item.id));row.row.classList.toggle('leaking',leakFlow>0);row.check.checked=selected.has(item.id);}
    const strip=$('etIncidentStrip');strip.replaceChildren();const overlay=$('etIncidents').checked;
    if(last<0){strip.textContent='공정이 시작되면 설비별 추세와 사고 영향 구간이 표시됩니다.';for(const {canvas} of canvases.values()){const ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);}return;}
    const segments=overlay?incidentSegments(times.slice(first,last+1),series.active_faults?.slice(first,last+1),selected):[];
    if(!overlay)strip.textContent='사고 영향 표시 꺼짐';else if(!segments.length)strip.textContent='선택 설비에 기록된 사고 영향 구간 없음';else{
      const lead=document.createElement('b');lead.textContent=`영향 구간 ${segments.length}건`;strip.append(lead);
      for(const segment of segments.slice(-6)){const chip=document.createElement('span');const kind=segment.fault.split(':')[0];chip.className='et-incident-chip';chip.style.setProperty('--incident-color',KIND_COLOR[kind]||'#777ba1');chip.textContent=`${faultDescription(segment.fault)}  ${segment.start.toFixed(0)}–${segment.end.toFixed(0)} s`;chip.title=segment.fault;strip.append(chip);}
    }
    for(const metric of METRICS)draw(metric,times,frames,tags,segments,first,last,t0,end,cursor);
  }
  function schedule(immediate=false){if(!alive)return;const now=performance.now();if(immediate||now-lastPaint>220){lastPaint=now;refresh();return;}if(!scheduled){scheduled=true;requestAnimationFrame(()=>{scheduled=false;if(performance.now()-lastPaint>160){lastPaint=performance.now();refresh();}});}}
  for(const button of body.querySelectorAll('[data-preset]'))button.addEventListener('click',()=>{selected.clear();for(const id of button.dataset.preset==='all'?EQUIPMENT.map(item=>item.id):GROUPS[button.dataset.preset])selected.add(id);schedule(true);});
  $('etWindow').addEventListener('change',()=>schedule(true));$('etPressureMode').addEventListener('change',()=>schedule(true));$('etIncidents').addEventListener('change',()=>schedule(true));
  $('etExport').addEventListener('click',()=>{
    const runtime=window.getStation3DState?.(),times=runtime?.result?.series?.time_s||[],frames=runtime?.result?.hazop?.frames||[];
    if(!times.length||!catalog||!selected.size){window.notifyOperator?.('내보낼 설비 추세가 없습니다.');return;}
    const tags=chosenTags(frames,times.length-1),items=EQUIPMENT.filter(item=>selected.has(item.id));
    const columns=items.flatMap(item=>METRICS.map(metric=>({item,metric,tag:tags.get(item.id)?.[metric.key]})));
    const quote=value=>`"${String(value??'').replaceAll('"','""')}"`;
    const lines=[['time_s',...columns.map(({item,metric,tag})=>`${item.id}_${tag||metric.key}`),'active_faults'].map(quote).join(',')];
    for(let i=0;i<Math.min(times.length,frames.length);i++)lines.push([times[i],...columns.map(({tag})=>numericSignal(frames[i],tag)??''),(runtime.result.series.active_faults?.[i]||[]).join('; ')].map(quote).join(','));
    const url=URL.createObjectURL(new Blob(['\uFEFF'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download='hrs-equipment-trends.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  const onFrame=()=>schedule(),onResize=()=>schedule(true);window.addEventListener('station-frame',onFrame);window.addEventListener('resize',onResize);
  getCatalog().then(data=>{if(!alive)return;catalog=data;schedule(true);}).catch(()=>{if(!alive)return;stripError();});
  function stripError(){$('etIncidentStrip').textContent='센서 목록에 연결할 수 없습니다. 서버 상태를 확인하세요.';}
  schedule(true);
  return ()=>{alive=false;window.removeEventListener('station-frame',onFrame);window.removeEventListener('resize',onResize);dialog.classList.remove('equipment-trend-dialog');};
}
if(typeof window!=='undefined')window.mountEquipmentTrends=mountEquipmentTrends;
