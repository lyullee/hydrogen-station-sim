/* The draft stays editable while the currently connected simulation is running. */
const $=id=>document.getElementById(id);
const controls={duration_s:'duration',control_period_s:'period',ambient_temperature_c:'ambient',initial_vehicle_pressure_mpa:'initial1',initial_vehicle_2_pressure_mpa:'initial2',initial_vehicle_temperature_c:'initialTemp1',initial_vehicle_2_temperature_c:'initialTemp2',target_vehicle_pressure_mpa:'target1',target_vehicle_2_pressure_mpa:'target2',pressure_ramp_rate_mpa_min:'ramp',delivery_temperature_c:'delivery',maximum_mass_flow_g_s:'maxFlow'};
let activeJobId=new URLSearchParams(location.search).get('job'),job=null,pollTimer,mutating=false,catalog=null,faultSerial=0;
let channel=null;try{channel=new BroadcastChannel('hrs-monitor');}catch{}
const faultCards=()=>[...$('faults').querySelectorAll('.fault-card')];
function errorMessage(message=''){$('errorStatus').textContent=message;$('errorStatus').hidden=!message;}
async function api(path,options={}){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
  try{
    const response=await fetch(path,{...options,signal:controller.signal});
    const body=await response.json().catch(()=>({}));
    if(!response.ok){const error=new Error(Array.isArray(body.detail)?body.detail.map(e=>`${e.loc?.slice(1).join('.')||''}: ${e.msg}`).join(' / '):body.detail||`서버 응답 ${response.status}`);error.status=response.status;throw error;}
    return body;
  }catch(error){if(error.name==='AbortError')throw new Error('서버 응답이 지연됩니다. 연결을 확인하고 다시 시도하세요.');throw error;}
  finally{clearTimeout(timer);}
}
function renderControls(){
  const running=['queued','running'].includes(job?.status);
  $('scenarioFields').disabled=mutating;$('run').disabled=mutating;
  $('run').textContent=mutating?'요청 처리 중…':running?'선택 사고 투입':'공정 실행';
  $('newRun').hidden=!running;$('newRun').disabled=mutating;
  $('stop').hidden=!running;$('stop').disabled=mutating||Boolean(job?.stop_requested);
  $('runHelp').textContent=running?'선택 사고를 현재 공정에 투입합니다. 시작·종료 시각은 지금부터의 지연·지속 시간(초)으로 적용됩니다. 초기 운전조건 변경은 새 공정 시작을 이용하세요.':'선택한 운전 조건과 사고로 새 시뮬레이션을 시작합니다.';
}
function updateJob(next){
  job=next;renderControls();
  const labels={queued:'실행 대기',running:'운전 중',complete:'실행 종료',failed:'계산 실패'};
  const stamp=`${labels[job.status]||job.status} · 모의 ${Number(job.simulated_time_s||0).toFixed(1)} s`;
  $('jobStatus').textContent=stamp+(job.continuous?' · 연속 모니터링':'');
  if(!mutating)$('status').textContent=job.stop_requested&&job.status==='running'?'정지 요청 반영 중…':stamp;
  if(job.status==='failed')errorMessage('계산 실패: '+(job.error||'서버 로그를 확인하세요.'));
}
function scheduleTrack(delay=1000){clearTimeout(pollTimer);pollTimer=setTimeout(track,delay);}
async function track(){
  const id=activeJobId;if(!id||mutating)return;
  try{const next=await api('/api/simulations/'+id);if(id!==activeJobId||mutating)return;updateJob(next);if(['queued','running'].includes(next.status)){await refreshLiveFaults();scheduleTrack();}}
  catch(error){if(id!==activeJobId||mutating)return;if(error.status===404){job=null;activeJobId=null;renderControls();$('jobStatus').textContent='이전 실행이 없습니다. 새 공정을 실행할 수 있습니다.';}else{$('jobStatus').textContent='실행 상태 연결 재시도 중';errorMessage(error.message);scheduleTrack(2500);}}
}
function publishJob(id){
  $('monitorLink').href='/?job='+encodeURIComponent(id);
  channel?.postMessage({type:'job-created',id});
  try{localStorage.setItem('hrs-active-job',id);}catch{}
  try{window.opener?.postMessage({type:'hrs-job-created',id},location.origin);}catch{}
}
async function stopAndWait(id){
  let current;
  try{current=await api('/api/simulations/'+id);}catch(e){if(e.status===404)return;throw e;}
  if(!['queued','running'].includes(current.status))return;
  $('status').textContent='현재 공정 정지 중…';
  await api('/api/simulations/'+id+'/stop',{method:'POST'});
  const deadline=Date.now()+45000;
  do{
    await new Promise(resolve=>setTimeout(resolve,600));
    current=await api('/api/simulations/'+id);
    updateJob(current);
    if(['complete','failed'].includes(current.status))return;
  }while(Date.now()<deadline);
  throw new Error('기존 공정이 아직 정지 중입니다. 중복 실행하지 않았습니다. 정지 완료 후 다시 실행하세요.');
}
function validateForm(){
  const invalid=[...$('scenarioForm').elements].find(e=>e.willValidate&&!e.validity.valid);
  if(!invalid)return true;
  for(let parent=invalid.parentElement;parent;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;
  errorMessage(`${invalid.closest('label')?.textContent.trim()||'입력값'}: ${invalid.validationMessage}`);invalid.focus();invalid.reportValidity();return false;
}
function readFault(card,index){
  const kind=card.querySelector('.kind').value,spec=catalog.kinds.find(k=>k.id===kind);
  const value=key=>card.querySelector(`[data-field="${key}"]`).value;
  const event={event_id:`remote-${Date.now()}-${index}`,kind,target:card.querySelector('.target').value,start_time_s:Number(value('start_time_s')),end_time_s:value('end_time_s')===''?null:Number(value('end_time_s'))};
  if(event.end_time_s!==null&&event.end_time_s<=event.start_time_s)throw new Error(`사고 ${index+1}: 종료 시각은 시작 시각보다 커야 합니다.`);
  if(!['queued','running'].includes(job?.status)&&!$('continuous').checked&&event.start_time_s>=Number($('duration').value))throw new Error(`사고 ${index+1}: 시작 시각이 계산 구간 밖입니다. 계산 구간을 늘리거나 시작을 앞당기세요.`);
  for(const key of spec.fields)event[key]=Number(value(key));
  return event;
}
function readPayload(){
  const payload=Object.fromEntries(Object.entries(controls).map(([key,id])=>[key,Number($(id).value)]));
  return {...payload,continuous:$('continuous').checked,faults:faultCards().map(readFault)};
}
async function run(event){
  event.preventDefault();if(mutating)return;errorMessage();if(!validateForm())return;
  const running=['queued','running'].includes(job?.status);
  let payload;try{payload=readPayload();}catch(error){errorMessage(error.message);return;}
  mutating=true;clearTimeout(pollTimer);renderControls();
  try{
    if(running){
      if(!payload.faults.length)throw new Error('현재 공정에 투입할 사고를 선택하세요.');
      const base=Number(job.simulated_time_s||0)+Math.max(.2,Number(payload.control_period_s||.2));
      for(const fault of payload.faults){
        const delay=fault.start_time_s,end=fault.end_time_s;
        fault.start_time_s=base+delay;fault.end_time_s=end===null?null:base+end;
        await api('/api/simulations/'+activeJobId+'/faults',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(fault)});
      }
      $('faults').replaceChildren();updateFaultCount();await refreshLiveFaults();
      $('status').textContent=`${payload.faults.length}개 사고를 운전 중 투입했습니다.`;return;
    }
    $('status').textContent='새 공정 등록 중…';
    const created=await api('/api/simulations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    activeJobId=created.id;job={...created,simulated_time_s:0,continuous:payload.continuous};
    history.replaceState(null,'','?job='+encodeURIComponent(activeJobId));publishJob(activeJobId);
    $('jobStatus').textContent='새 공정 연결 중';$('status').textContent='등록 완료 · 모니터 데이터 수신 대기';
  }catch(error){errorMessage('실행하지 못했습니다: '+error.message);$('status').textContent='실행 요청 오류';}
  finally{mutating=false;renderControls();if(activeJobId)track();}
}
async function refreshLiveFaults(){
  if(!activeJobId)return;
  const body=$('liveFaults');
  try{
    const data=await api('/api/simulations/'+activeJobId+'/faults');body.replaceChildren();
    if(!data.faults.length){body.textContent='운전 중 사고가 없습니다.';return;}
    for(const fault of data.faults){const row=document.createElement('div');row.className='live-fault';const label=document.createElement('span');label.textContent=`${fault.active?'진행 중':'대기'} · ${fault.kind} · ${fault.target} · ${Number(fault.start_time_s).toFixed(1)} s`;const button=document.createElement('button');button.type='button';button.textContent='이 사고 종료';button.addEventListener('click',async()=>{button.disabled=true;try{await api('/api/simulations/'+activeJobId+'/faults/'+encodeURIComponent(fault.event_id),{method:'DELETE'});$('status').textContent='사고 종료 명령을 현재 공정에 반영 중입니다.';await refreshLiveFaults();}catch(error){errorMessage(error.message);button.disabled=false;}});row.append(label,button);body.append(row);}
  }catch(error){body.textContent='현재 사고 목록을 읽지 못했습니다: '+error.message;}
}
async function startNewRun(){if(mutating)return;try{if(activeJobId)await stopAndWait(activeJobId);job=null;await run(new Event('submit',{cancelable:true}));}catch(error){errorMessage(error.message);}}
async function stop(){
  if(!activeJobId||mutating)return;mutating=true;clearTimeout(pollTimer);errorMessage();renderControls();
  try{await stopAndWait(activeJobId);$('status').textContent='정지 완료 · 새 시나리오를 실행할 수 있습니다.';}
  catch(error){errorMessage(error.message);}
  finally{mutating=false;renderControls();if(activeJobId)track();}
}
function updateFaultCount(){const count=faultCards().length;$('faultCount').textContent=count+'개';$('faultEmpty').hidden=count>0;}
function configureCard(card,reset=false){
  const spec=catalog.kinds.find(k=>k.id===card.querySelector('.kind').value),select=card.querySelector('.target'),old=select.value;
  select.replaceChildren(...spec.targets.map(t=>new Option(t.label,t.value)));if(spec.targets.some(t=>t.value===old))select.value=old;
  for(const label of card.querySelectorAll('[data-param]')){const visible=spec.fields.includes(label.dataset.param);label.hidden=!visible;label.querySelector('input').disabled=!visible;}
  const input=card.querySelector('[data-field="magnitude"]'),ratio=['pipe-restriction','precooler-loss'].includes(spec.id);
  input.min=ratio?'0':spec.id==='pressure-disturbance'?'-80':'-1000';input.max=ratio?'1':spec.id==='pressure-disturbance'?'100':'1000';
  if(reset)input.value=ratio?'.25':spec.id==='sensor-bias'?'20':'10';
  card.querySelector('.magnitude-label').textContent=ratio?(spec.id==='pipe-restriction'?'유효 개방률 (0~1)':'잔존 냉각 용량 (0~1)'):spec.id==='sensor-bias'?'센서 편향 · 표시 단위':'압력 변화량 (MPa)';
  card.querySelector('[data-field="external_temperature_c"]').min=spec.id==='external-fire'?'0.1':'-50';
  const showNote=()=>{const target=spec.targets.find(t=>t.value===select.value);card.querySelector('.fault-note').textContent=spec.note+(target?.unit?` 선택 센서: ${target.unit} · ${target.location}`:'');};
  select.onchange=showNote;showNote();
}
function addFault(event={},title='직접 구성'){
  if(!catalog){errorMessage('시나리오 목록을 먼저 불러와야 합니다.');return;}
  const card=$('faultTemplate').content.firstElementChild.cloneNode(true);card.dataset.number=++faultSerial;card.querySelector('.fault-title').textContent=`${faultSerial}. ${title}`;
  const select=card.querySelector('.kind');select.replaceChildren(...catalog.kinds.map(k=>new Option(k.label,k.id)));select.value=event.kind||'pressure-disturbance';
  configureCard(card,true);if(event.target)card.querySelector('.target').value=event.target;
  for(const [key,value] of Object.entries(event)){const input=card.querySelector(`[data-field="${key}"]`);if(input)input.value=value??'';}
  card.querySelector('.target').dispatchEvent(new Event('change'));
  select.addEventListener('change',()=>{configureCard(card,true);card.querySelector('.fault-title').textContent=`${card.dataset.number}. 직접 구성`;});
  card.querySelector('.remove').addEventListener('click',()=>{card.remove();updateFaultCount();});
  $('faults').append(card);updateFaultCount();
}
function renderLibrary(){
  const search=$('scenarioSearch').value.trim().toLowerCase(),category=$('categoryFilter').value;
  const filtered=catalog.scenarios.filter(s=>(category==='all'||s.category===category)&&`${s.title} ${s.description} ${s.faults.map(f=>f.target).join(' ')}`.toLowerCase().includes(search));
  $('catalogCount').textContent=`${filtered.length} / ${catalog.scenarios.length}개 · ${catalog.kinds.length}종`;
  $('scenarioLibrary').replaceChildren();
  for(const scenario of filtered){
    const card=document.createElement('article');card.className='scenario-option';
    const title=document.createElement('strong');title.textContent=scenario.title;
    const note=document.createElement('p');note.textContent=scenario.description;
    const button=document.createElement('button');button.type='button';button.textContent=`+ 추가${scenario.faults.length>1?' · '+scenario.faults.length+'개 사고':''}`;button.setAttribute('aria-label',scenario.title+' 추가');
    button.addEventListener('click',()=>{scenario.faults.forEach(f=>addFault(f,scenario.title));errorMessage();$('status').textContent=`${scenario.title} 추가 · 실행할 사고 ${faultCards().length}개`;});card.append(title,note,button);$('scenarioLibrary').append(card);
  }
  if(!filtered.length){const empty=document.createElement('p');empty.className='hint';empty.textContent='검색 결과가 없습니다. 분류나 검색어를 바꿔보세요.';$('scenarioLibrary').append(empty);}
}
async function initCatalog(){
  try{catalog=await api('/scenarios.json?v=20260928-sensors82');for(const c of catalog.categories)$('categoryFilter').add(new Option(c.label,c.id));renderLibrary();$('addFault').disabled=false;}
  catch(error){errorMessage('사고 목록을 불러오지 못했습니다: '+error.message);$('catalogCount').textContent='불러오기 실패';$('scenarioLibrary').textContent='새로고침 후 다시 시도하세요. 정상 운전은 실행할 수 있습니다.';}
}
async function health(){try{await api('/api/health');$('serverStatus').textContent='서버 연결됨';$('serverStatus').dataset.state='ready';}catch{$('serverStatus').textContent='서버 연결 실패';$('serverStatus').dataset.state='error';}}
$('scenarioForm').addEventListener('submit',run);$('stop').addEventListener('click',stop);
$('newRun').addEventListener('click',startNewRun);
$('addFault').addEventListener('click',()=>addFault());$('clearFaults').addEventListener('click',()=>{$('faults').replaceChildren();updateFaultCount();errorMessage();$('status').textContent='사고 목록을 비웠습니다. 정상 운전 조건으로 실행합니다.';});
$('scenarioSearch').addEventListener('input',()=>{if(catalog)renderLibrary();});$('categoryFilter').addEventListener('change',()=>{if(catalog)renderLibrary();});
if(activeJobId){$('monitorLink').href='/?job='+encodeURIComponent(activeJobId);track();}
renderControls();initCatalog();health();setInterval(health,30000);
