/* The draft stays editable while the currently connected simulation is running. */
const $=id=>document.getElementById(id);
const controls={duration_s:'duration',control_period_s:'period',ambient_temperature_c:'ambient',initial_vehicle_pressure_mpa:'initial1',initial_vehicle_2_pressure_mpa:'initial2',initial_vehicle_temperature_c:'initialTemp1',initial_vehicle_2_temperature_c:'initialTemp2',initial_bank_low_fill_percent:'bankFillLow',initial_bank_medium_fill_percent:'bankFillMedium',initial_bank_high_fill_percent:'bankFillHigh',pressure_ramp_rate_mpa_min:'ramp',delivery_temperature_c:'delivery',maximum_mass_flow_g_s:'maxFlow'};
let activeJobId=new URLSearchParams(location.search).get('job'),job=null,pollTimer,mutating=false,catalog=null,faultSerial=0,esdRequested=false;
let lastProcessFrame=-1,lastHydratedJobId=null;
let activeRemoteTab='operations';
let speedSaving=false;
const reliefDefinitions=[['low','저압 저장뱅크',50,49],['medium','중압 저장뱅크',70,69],['high','고압 저장뱅크',100,99],['hose_1','1번 충전호스',90,88],['hose_2','2번 충전호스',90,88],['vehicle_1','차량 1 탱크',87.5,85],['vehicle_2','차량 2 탱크',87.5,85]];
const bankFillSettings=[['bankFillLow','bankPressureLow',50],['bankFillMedium','bankPressureMedium',70],['bankFillHigh','bankPressureHigh',100]];
function updateBankPressurePreview(){
  for(const [inputId,outputId,maximumMpa] of bankFillSettings){
    const percent=Number($(inputId).value);
    $(outputId).textContent=Number.isFinite(percent)&&percent>=1&&percent<=100
      ?`시작 압력 ${(maximumMpa*percent/100).toFixed(2)} MPa`
      :'1–100% 범위로 입력하세요';
  }
}
const operationNames={trailer_supply:'공급',pressure_recharge:'보완',vehicle_1:'차량 1 충전',vehicle_2:'차량 2 충전'};
const activityReasons={'recharge-off':'압력 보완 명령 대기','supply-off':'트레일러 공급 명령 대기','bank-target':'설정한 저장뱅크 목표압력 도달','vehicle-target':'설정한 차량 목표압력·충전량 도달','compressor-starting':'압축기 기동 대기','bank-unavailable':'공급 가능한 저장뱅크 없음','valve-starting':'밸브 개방·압력 형성 중',esd:'ESD 차단','source-depleted':'트레일러 공급압·재고 소진','safety-temperature':'차량 가스 온도 보호 차단',operator:'운전자 정지'};
let channel=null;try{channel=new BroadcastChannel('hrs-monitor');}catch{}
const faultCards=()=>[...$('faults').querySelectorAll('.fault-card')];
function errorMessage(message=''){$('errorStatus').textContent=message;$('errorStatus').hidden=!message;}
function setRemoteTab(tab){
  if(!['operations','incidents','settings'].includes(tab))return;
  activeRemoteTab=tab;
  document.querySelectorAll('[data-remote-tab]').forEach(button=>button.setAttribute('aria-selected',String(button.dataset.remoteTab===tab)));
  document.querySelectorAll('[data-remote-pane]').forEach(pane=>pane.hidden=pane.dataset.remotePane!==tab);
  renderControls();
}
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
  $('run').textContent=mutating?'요청 처리 중…':running?'선택 사고 투입':'모니터링 시작';
  $('run').hidden=running&&activeRemoteTab!=='incidents';
  $('newRun').hidden=!running||activeRemoteTab!=='settings';$('newRun').disabled=mutating;
  $('stop').hidden=!running;$('stop').disabled=mutating||Boolean(job?.stop_requested);
  $('resetProcess').disabled=mutating;
  const esdLatched=Boolean(window.latestProcessFrame?.esd);
  $('esdStop').disabled=mutating||!running||esdRequested||esdLatched;
  $('esdStop').textContent=esdLatched?'ESD 차단 중':esdRequested?'ESD 반영 중…':'ESD 차단';
  $('runHelp').textContent=running?activeRemoteTab==='incidents'?'선택한 사고를 현재 공정에 투입합니다.':'운전 중 · 공정 버튼으로 개별 시작/정지할 수 있습니다.':activeRemoteTab==='incidents'?'선택한 사고와 함께 모니터링을 시작합니다.':'공정 시작 버튼을 누르면 연속 모니터링이 자동으로 시작됩니다.';
  renderProcess();
}
function initReliefRows(){
  const body=$('reliefRows');
  for(const [key,label,open,close] of reliefDefinitions){
    const row=document.createElement('div');row.className='relief-row';row.dataset.relief=key;
    row.innerHTML=`<strong>${label}</strong><label class="switch-label"><input class="relief-enabled" type="checkbox" checked> 자동</label><label>열림 MPa<input class="relief-open" type="number" min="0.2" max="120" step="any" value="${open}"></label><label>닫힘 MPa<input class="relief-close" type="number" min="0.2" max="120" step="any" value="${close}"></label><label>구경 mm<input class="relief-orifice" type="number" min="0.01" max="20" step="any" value="1"></label><span class="relief-state">닫힘</span>`;
    body.append(row);
  }
}
function readProcessSettings(){
  const value=id=>{const input=$(id);if(!input.value||!input.checkValidity())throw new Error(`${input.closest('label')?.textContent.trim()||id}: 유효한 값을 입력하세요.`);return Number(input.value);},relief_valves={};
  for(const row of $('reliefRows').children){
    const inputs=[...row.querySelectorAll('input[type="number"]')];if(inputs.some(input=>!input.value||!input.checkValidity()))throw new Error(`${row.querySelector('strong').textContent}: 안전밸브 입력값을 확인하세요.`);
    const opening=Number(row.querySelector('.relief-open').value),closing=Number(row.querySelector('.relief-close').value);
    if(closing>=opening)throw new Error(`${row.querySelector('strong').textContent}: 닫힘 압력은 열림 압력보다 낮아야 합니다.`);
    relief_valves[row.dataset.relief]={enabled:row.querySelector('.relief-enabled').checked,open_mpa:opening,close_mpa:closing,orifice_mm:Number(row.querySelector('.relief-orifice').value)};
  }
  return {trailer_supply:false,pressure_recharge:false,vehicle_1:false,vehicle_2:false,
    trailer_pressure_mpa:value('trailerPressure'),trailer_temperature_c:value('trailerTemperature'),trailer_capacity_kg:value('trailerCapacity'),
    recharge_auto_stop:$('rechargeAutoStop').checked,recharge_target_low_mpa:value('rechargeTargetLow'),
    recharge_target_medium_mpa:value('rechargeTargetMedium'),recharge_target_high_mpa:value('rechargeTargetHigh'),
    vehicle_1_auto_stop:$('vehicle1AutoStop').checked,vehicle_1_target_pressure_mpa:value('vehicle1TargetPressure'),
    vehicle_2_auto_stop:$('vehicle2AutoStop').checked,vehicle_2_target_pressure_mpa:value('vehicle2TargetPressure'),relief_valves};
}
function hydrateProcessSettings(settings){
  if(!settings)return;
  const fields={trailerPressure:'trailer_pressure_mpa',trailerCapacity:'trailer_capacity_kg',
    trailerTemperature:'trailer_temperature_c',rechargeTargetLow:'recharge_target_low_mpa',
    rechargeTargetMedium:'recharge_target_medium_mpa',rechargeTargetHigh:'recharge_target_high_mpa',
    vehicle1TargetPressure:'vehicle_1_target_pressure_mpa',vehicle2TargetPressure:'vehicle_2_target_pressure_mpa'};
  for(const [id,key] of Object.entries(fields))if(settings[key]!==undefined)$(id).value=settings[key];
  for(const [id,key] of [['rechargeAutoStop','recharge_auto_stop'],['vehicle1AutoStop','vehicle_1_auto_stop'],['vehicle2AutoStop','vehicle_2_auto_stop']])
    if(settings[key]!==undefined)$(id).checked=Boolean(settings[key]);
  if(settings.recharge_auto_stop!==undefined)$('trailerAutoStop').checked=Boolean(settings.recharge_auto_stop);
  for(const row of $('reliefRows').children){const valve=settings.relief_valves?.[row.dataset.relief];if(!valve)continue;
    row.querySelector('.relief-enabled').checked=Boolean(valve.enabled);
    row.querySelector('.relief-open').value=valve.open_mpa;
    row.querySelector('.relief-close').value=valve.close_mpa;
    row.querySelector('.relief-orifice').value=valve.orifice_mm;}
}
function renderProcess(){
  const running=['queued','running'].includes(job?.status),snapshot=job?.operations,settings=snapshot?.settings||{};
  const frame=window.latestProcessFrame,frameRevision=frame?.process_operations?.revision;
  const confirmed=Boolean(running&&snapshot&&frame&&frameRevision===snapshot.revision);
  const bankNames={low:'저압',medium:'중압',high:'고압'};
  const bankTargets=Object.entries(bankNames).map(([bank,label])=>({label,
    pressure:Number(frame?.bank_pressure_mpa?.[bank]),
    target:Number(settings[`recharge_target_${bank}_mpa`]??$(`rechargeTarget${bank[0].toUpperCase()+bank.slice(1)}`).value)}));
  const bankOver=bankTargets.filter(({pressure,target})=>Number.isFinite(pressure)&&pressure>target+0.05);
  const rechargeAutoStop=settings.recharge_auto_stop??$('rechargeAutoStop').checked;
  const flowing=[];let requestedCount=0;
  for(const [key,name] of Object.entries(operationNames)){
    const card=document.querySelector(`[data-process="${key}"]`),on=Boolean(running&&settings[key]),button=card.querySelector('.process-toggle');
    const activity=confirmed?frame.process_activity?.[key]:null;
    let status=job?.status==='complete'?'실행 종료':'정지',detail=job?.status==='complete'?'새 공정을 시작할 수 있습니다.':'요청 없음';
    if(on){requestedCount++;status='명령 접수';detail='다음 계산 반영 대기';}
    if(activity){
      if(activity.state==='flowing'){status='실제 작동';detail=`유량 ${Number(activity.flow_g_s).toFixed(2)} g/s`;flowing.push(name);}
      else if(activity.state==='waiting'){status='흐름 대기';detail=activityReasons[activity.reason]||'설비 조건 확인 중';}
      else if(activity.state==='blocked'){status=activity.reason==='source-depleted'?'공급 한계':'안전 차단';detail=activityReasons[activity.reason]||'안전 계층 차단';}
      else if(activity.state==='auto-stopped'){status='자동 종료';detail=activityReasons[activity.reason]||'설정 조건 도달';}
      else if(!on&&snapshot?.stop_reason?.[key]==='operator'){detail='운전자 정지';}
    }
    card.dataset.active=String(on);card.dataset.flowing=String(activity?.state==='flowing');card.querySelector('.process-state').textContent=status;card.querySelector('.process-activity').textContent=detail;
    let targetLine=card.querySelector('.process-target-state');
    if(!targetLine){targetLine=document.createElement('div');targetLine.className='process-target-state';button.before(targetLine);}
    if(key==='trailer_supply'||key==='pressure_recharge'){
      card.dataset.overfill=String(!rechargeAutoStop);
      card.dataset.overTarget=String(bankOver.length>0);
      targetLine.textContent=rechargeAutoStop
        ?`자동 종료 ON · 뱅크 목표 ${bankTargets.map(({label,target})=>`${label} ${target.toFixed(1)}`).join(' / ')} MPa`
        :bankOver.length?`설정 목표 초과 · ${bankOver.map(({label,pressure,target})=>`${label} +${(pressure-target).toFixed(2)} MPa`).join(' · ')}`
          :'목표 초과 주입 ON · 설정 목표에서도 자동 종료하지 않음';
    }else{
      const lane=key==='vehicle_1'?1:2;
      const autoStop=settings[`${key}_auto_stop`]??$(`vehicle${lane}AutoStop`).checked;
      card.dataset.overfill=String(!autoStop);
      const target=Number(settings[`${key}_target_pressure_mpa`]??$(`vehicle${lane}TargetPressure`).value);
      const pressure=Number(lane===1?frame?.vehicle_pressure_mpa:frame?.vehicle_2_pressure_mpa);
      const exceeded=Number.isFinite(pressure)&&pressure>target+0.05;
      card.dataset.overTarget=String(exceeded);
      targetLine.textContent=autoStop?`자동 종료 ON · 목표 ${target.toFixed(1)} MPa`
        :exceeded?`설정 목표 초과 · ${pressure.toFixed(2)} / ${target.toFixed(1)} MPa (+${(pressure-target).toFixed(2)})`
          :`목표 초과 충전 ON · ${Number.isFinite(pressure)?pressure.toFixed(2)+' / ':''}${target.toFixed(1)} MPa · 목표에서 멈추지 않음`;
    }
    const indicator=document.querySelector(`[data-status-process="${key}"]`);
    indicator.dataset.state=activity?.state||(!running?'off':on?'pending':'off');
    indicator.querySelector('b').textContent=status;
    indicator.title=`${name}: ${detail}`;
    button.textContent=on?`${name} 정지`:`${name} 시작`;button.disabled=mutating||Boolean(activeJobId&&!job);
  }
  $('processSummary').textContent=!running?'모니터링 대기 · 공정 명령 없음':flowing.length?`실제 작동 ${flowing.length}개 · ${flowing.join(' · ')}`:requestedCount?`공정 요청 ${requestedCount}개 · 실제 흐름 대기`:'공정 대기 · 요청된 명령 없음';
  const lag=job?.realtime_lag_s==null?null:Number(job.realtime_lag_s);
  const rate=job?.simulation_rate_x==null?null:Number(job.simulation_rate_x);
  const target=Number(running?job.speed_multiplier||1:$('simulationSpeed').value);
  $('calculationPace').textContent=!running?`선택 ${target}× · 시작 대기`:`목표 ${target}× · 실제 ${rate==null?'측정 중':rate.toFixed(1)+'×'}${lag!=null&&lag>.5?` · ${lag.toFixed(1)}초 지연`:''}`;
  $('calculationPace').dataset.lag=String(running&&lag!=null&&lag>.5);
  $('simulationSpeed').disabled=speedSaving||running&&!job.continuous||!running&&!$('continuous').checked;
  $('applyProcess').disabled=!running||mutating;
  for(const id of ['trailerPressure','trailerCapacity','trailerTemperature'])$(id).disabled=running||mutating;
  if(snapshot){$('trailerReading').textContent=`재고 ${Number(snapshot.trailer_inventory_kg).toFixed(3)} kg · 압력 ${Number(snapshot.trailer_pressure_mpa).toFixed(3)} MPa · 이송 ${Number(snapshot.trailer_transferred_kg).toFixed(3)} kg`;
    $('rechargeReading').textContent=`누적 보충 ${Number(snapshot.recharge_transferred_kg).toFixed(3)} kg${frame?.recharge_bank?' · '+frame.recharge_bank.toUpperCase()+' 뱅크':''}`;
    for(const row of $('reliefRows').children)row.querySelector('.relief-state').textContent=snapshot.relief_open?.[row.dataset.relief]?'열림':'닫힘';}
  if(frame){$('vehicle1Reading').textContent=`탱크 ${Number(frame.vehicle_mass_kg||0).toFixed(3)} kg · ${Number(frame.vehicle_pressure_mpa||0).toFixed(3)} MPa`;$('vehicle2Reading').textContent=`탱크 ${Number(frame.vehicle_2_mass_kg||0).toFixed(3)} kg · ${Number(frame.vehicle_2_pressure_mpa||0).toFixed(3)} MPa`;}
}
async function applyProcessSettings(operation=null){
  if(operation&&!['queued','running'].includes(job?.status)){await startProcessFromIdle(operation);return;}
  if(!activeJobId||!['queued','running'].includes(job?.status)){errorMessage('먼저 모니터링을 시작하세요.');return;}
  if(mutating)return;
  let settings;try{settings={...readProcessSettings()};for(const key of Object.keys(operationNames))settings[key]=Boolean(job.operations?.settings?.[key]);if(operation){const next=!settings[operation];if(operation==='trailer_supply'||operation==='pressure_recharge'){settings.trailer_supply=next;settings.pressure_recharge=next;}else settings[operation]=next;}}catch(error){errorMessage(error.message);return;}
  mutating=true;errorMessage();renderControls();
  try{const snapshot=await api('/api/simulations/'+activeJobId+'/operations',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(settings)});job.operations=snapshot;renderProcess();$('status').textContent=operation?`${operation==='trailer_supply'||operation==='pressure_recharge'?'트레일러 공급·압력 보완':operationNames[operation]} ${snapshot.settings[operation]?'시작':'정지'} 요청 반영 중`:'목표압력·안전밸브 설정 적용 완료';}
  catch(error){errorMessage(error.message);}finally{mutating=false;renderControls();if(activeJobId)scheduleTrack(500);}
}
async function applySimulationSpeed(){
  const speed=Number($('simulationSpeed').value);
  if(!activeJobId||!['queued','running'].includes(job?.status)){renderProcess();return;}
  if(speedSaving||!job.continuous)return;
  speedSaving=true;errorMessage();renderProcess();
  try{
    const updated=await api('/api/simulations/'+activeJobId+'/speed',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({speed_multiplier:speed})});
    job.speed_multiplier=updated.speed_multiplier;job.simulation_rate_x=null;job.realtime_lag_s=null;
    $('status').textContent=`계산 목표 속도를 ${speed}×로 변경했습니다.`;
  }catch(error){$('simulationSpeed').value=String(job.speed_multiplier||1);errorMessage('계산 속도를 변경하지 못했습니다: '+error.message);}
  finally{speedSaving=false;renderProcess();if(activeJobId)scheduleTrack(250);}
}
function updateJob(next){
  job=next;
  if(!speedSaving&&job.speed_multiplier)$('simulationSpeed').value=String(job.speed_multiplier);
  if(job.id!==lastHydratedJobId&&job.operations?.settings){hydrateProcessSettings(job.operations.settings);lastHydratedJobId=job.id;}
  renderControls();
  const labels={queued:'실행 대기',running:'운전 중',complete:'실행 종료',failed:'계산 실패'};
  const stamp=`${labels[job.status]||job.status} · 모의 ${Number(job.simulated_time_s||0).toFixed(1)} s`;
  $('jobStatus').textContent=stamp+(job.continuous?' · 연속 모니터링':'');
  if(!mutating)$('status').textContent=job.stop_requested&&job.status==='running'?'정지 요청 반영 중…':stamp;
  if(job.status==='failed')errorMessage('계산 실패: '+(job.error||'서버 로그를 확인하세요.'));
}
function scheduleTrack(delay=1000){clearTimeout(pollTimer);pollTimer=setTimeout(track,delay);}
async function track(){
  const id=activeJobId;if(!id)return;if(mutating){scheduleTrack(500);return;}
  try{const next=await api('/api/simulations/'+id);if(id!==activeJobId||mutating)return;updateJob(next);await refreshProcessFrame();if(['queued','running'].includes(next.status)){await refreshLiveFaults();scheduleTrack();}}
  catch(error){if(id!==activeJobId||mutating)return;if(error.status===404){job=null;activeJobId=null;renderControls();$('jobStatus').textContent='이전 실행이 없습니다. 새 공정을 실행할 수 있습니다.';}else{$('jobStatus').textContent='실행 상태 연결 재시도 중';errorMessage(error.message);scheduleTrack(2500);}}
}
async function refreshProcessFrame(){
  if(!activeJobId)return;
  try{const data=await api(`/api/simulations/${activeJobId}/frames?after=${lastProcessFrame}`);const frames=data.frames||[];if(frames.length){window.latestProcessFrame=frames.at(-1);lastProcessFrame=window.latestProcessFrame.sequence;renderControls();}}catch{}
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
function validateForm(includeFaults=true){
  const invalid=[...$('scenarioForm').elements].find(e=>e.willValidate&&(includeFaults||!e.closest('.fault-card'))&&!e.validity.valid);
  if(!invalid)return true;
  const pane=invalid.closest('[data-remote-pane]');if(pane)setRemoteTab(pane.dataset.remotePane);
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
function readPayload(includeFaults=true){
  const payload=Object.fromEntries(Object.entries(controls).map(([key,id])=>[key,Number($(id).value)]));
  const process_settings=readProcessSettings();
  // The scheduled target is capped at the independent PLC threshold. In
  // over-target mode the live controller intentionally ramps beyond it.
  payload.target_vehicle_pressure_mpa=Math.min(87.5,process_settings.vehicle_1_target_pressure_mpa);
  payload.target_vehicle_2_pressure_mpa=Math.min(87.5,process_settings.vehicle_2_target_pressure_mpa);
  return {...payload,continuous:$('continuous').checked,speed_multiplier:$('continuous').checked?Number($('simulationSpeed').value):1,process_settings,faults:includeFaults?faultCards().map(readFault):[]};
}
async function createSimulationJob(payload,description){
  const created=await api('/api/simulations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  activeJobId=created.id;lastProcessFrame=-1;window.latestProcessFrame=null;esdRequested=false;
  lastHydratedJobId=created.id;
  job={...created,simulated_time_s:0,continuous:payload.continuous,speed_multiplier:payload.speed_multiplier,operations:{settings:payload.process_settings}};
  history.replaceState(null,'','?job='+encodeURIComponent(activeJobId));publishJob(activeJobId);
  $('jobStatus').textContent='새 공정 연결 중';$('status').textContent=description;
}
async function startProcessFromIdle(operation){
  if(mutating||Boolean(activeJobId&&!job))return;
  errorMessage();if(!validateForm(false))return;
  let payload;try{payload=readPayload(false);}catch(error){errorMessage(error.message);return;}
  payload.continuous=true;$('continuous').checked=true;
  payload.process_settings[operation]=true;
  if(operation==='trailer_supply'||operation==='pressure_recharge'){
    payload.process_settings.trailer_supply=true;
    payload.process_settings.pressure_recharge=true;
  }
  mutating=true;clearTimeout(pollTimer);renderControls();
  try{await createSimulationJob(payload,`${operation==='trailer_supply'||operation==='pressure_recharge'?'트레일러 공급·압력 보완':operationNames[operation]} 시작 요청 · 데이터 수신 대기`);}
  catch(error){errorMessage('공정을 시작하지 못했습니다: '+error.message);$('status').textContent='공정 시작 오류';}
  finally{mutating=false;renderControls();if(activeJobId)track();}
}
async function run(event){
  event.preventDefault();if(mutating)return;errorMessage();if(!validateForm())return;
  const running=['queued','running'].includes(job?.status);
  let payload;try{payload=readPayload();}catch(error){errorMessage(error.message);return;}
  mutating=true;clearTimeout(pollTimer);renderControls();
  try{
    if(running){
      if(!payload.faults.length)throw new Error('현재 공정에 투입할 사고를 선택하세요.');
      for(const fault of payload.faults){
        await api('/api/simulations/'+activeJobId+'/faults?relative=true',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(fault)});
      }
      $('faults').replaceChildren();updateFaultCount();await refreshLiveFaults();
      $('status').textContent=`${payload.faults.length}개 사고를 운전 중 투입했습니다.`;return;
    }
    $('status').textContent='새 공정 등록 중…';
    await createSimulationJob(payload,'등록 완료 · 모니터 데이터 수신 대기');
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
async function resetProcess(){
  if(mutating)return;
  errorMessage();if(!validateForm(false))return;
  let payload;try{payload=readPayload(false);}catch(error){errorMessage(error.message);return;}
  payload.continuous=true;payload.faults=[];
  for(const operation of Object.keys(operationNames))payload.process_settings[operation]=false;
  mutating=true;clearTimeout(pollTimer);renderControls();
  try{
    if(activeJobId)await stopAndWait(activeJobId);
    await createSimulationJob(payload,'초기 조건으로 공정을 재설정했습니다. 모든 공정 요청·사고·ESD가 해제됐습니다.');
    $('faults').replaceChildren();updateFaultCount();await refreshLiveFaults();
  }catch(error){errorMessage('공정 초기화 실패: '+error.message);}
  finally{mutating=false;renderControls();if(activeJobId)track();}
}
async function requestEsd(){
  if(mutating||esdRequested||!activeJobId||!['queued','running'].includes(job?.status))return;
  mutating=true;clearTimeout(pollTimer);renderControls();errorMessage();
  try{
    await api('/api/simulations/'+activeJobId+'/faults?relative=true',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event_id:`remote-esd-${Date.now()}`,kind:'emergency-stop',target:'station',start_time_s:0,end_time_s:null})});
    esdRequested=true;$('status').textContent='ESD 차단 명령 전송 · 안전 PLC 반영 대기';await refreshLiveFaults();
  }catch(error){errorMessage('ESD 차단 명령 실패: '+error.message);}
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
  try{catalog=await api('/scenarios.json?v=20260929-flame91');for(const c of catalog.categories)$('categoryFilter').add(new Option(c.label,c.id));renderLibrary();$('addFault').disabled=false;}
  catch(error){errorMessage('사고 목록을 불러오지 못했습니다: '+error.message);$('catalogCount').textContent='불러오기 실패';$('scenarioLibrary').textContent='새로고침 후 다시 시도하세요. 정상 운전은 실행할 수 있습니다.';}
}
async function health(){try{await api('/api/health');$('serverStatus').textContent='서버 연결됨';$('serverStatus').dataset.state='ready';}catch{$('serverStatus').textContent='서버 연결 실패';$('serverStatus').dataset.state='error';}}
$('scenarioForm').addEventListener('submit',run);$('stop').addEventListener('click',stop);
$('simulationSpeed').addEventListener('change',applySimulationSpeed);
$('continuous').addEventListener('change',()=>{if(!$('continuous').checked)$('simulationSpeed').value='1';renderProcess();});
document.querySelectorAll('[data-remote-tab]').forEach(button=>button.addEventListener('click',()=>setRemoteTab(button.dataset.remoteTab)));
const trailerFields=document.querySelector('[data-process="trailer_supply"] .process-fields');
const trailerDetails=document.createElement('details');const trailerSummary=document.createElement('summary');trailerSummary.textContent='트레일러 초기 조건';trailerDetails.append(trailerSummary);trailerFields.before(trailerDetails);trailerDetails.append(trailerFields);
$('applyProcess').addEventListener('click',()=>applyProcessSettings());
for(const id of ['vehicle1AutoStop','vehicle2AutoStop','rechargeTargetLow','rechargeTargetMedium','rechargeTargetHigh','vehicle1TargetPressure','vehicle2TargetPressure'])
  $(id).addEventListener('change',()=>{if(['queued','running'].includes(job?.status))applyProcessSettings();else renderProcess();});
for(const [source,other] of [['trailerAutoStop','rechargeAutoStop'],['rechargeAutoStop','trailerAutoStop']])
  $(source).addEventListener('change',()=>{$(other).checked=$(source).checked;if(['queued','running'].includes(job?.status))applyProcessSettings();else renderProcess();});
document.querySelectorAll('.process-toggle').forEach(button=>button.addEventListener('click',()=>applyProcessSettings(button.dataset.operation)));
$('newRun').addEventListener('click',startNewRun);
$('resetProcess').addEventListener('click',resetProcess);
$('esdStop').addEventListener('click',requestEsd);
$('addFault').addEventListener('click',()=>addFault());$('clearFaults').addEventListener('click',()=>{$('faults').replaceChildren();updateFaultCount();errorMessage();$('status').textContent='사고 목록을 비웠습니다. 정상 운전 조건으로 실행합니다.';});
$('scenarioSearch').addEventListener('input',()=>{if(catalog)renderLibrary();});$('categoryFilter').addEventListener('change',()=>{if(catalog)renderLibrary();});
initReliefRows();
for(const [inputId] of bankFillSettings)$(inputId).addEventListener('input',updateBankPressurePreview);
updateBankPressurePreview();
if(activeJobId){$('monitorLink').href='/?job='+encodeURIComponent(activeJobId);track();}
renderControls();initCatalog();health();setInterval(health,30000);
