const $ = (id) => document.getElementById(id);
window.publicImpactText = value => String(value ?? '').replace(/HyRAM\+?/gi, '피해영향예측');
const state = { result: null, index: 0, playing: false, timer: null, activeJobId: null, health:null, mapping:null, followLive:true, lastSequence:-1, connection:'idle', lastReceived:0, generation:0 };
let lastLivePaintAt=0;
const incidentSources = { hazop:false, impact:false, analysis:false };
const reliefNames={low:'저압 저장뱅크',medium:'중압 저장뱅크',high:'고압 저장뱅크',hose_1:'1번 충전호스',hose_2:'2번 충전호스',vehicle_1:'차량 1 탱크',vehicle_2:'차량 2 탱크'};
function updateIncidentPanels(source, active) {
  incidentSources[source] = Boolean(active);
  const incident = Object.values(incidentSources).some(Boolean);
  document.body.dataset.alertState = incident ? 'incident' : 'normal';
  const hazopPanel = $('hazopPanel');
  const impactPanel = $('impactPanel');
  if (hazopPanel) hazopPanel.hidden = !incident;
  if (impactPanel) impactPanel.hidden = !incident;
}
updateIncidentPanels('initial', false);
const scenarioDuration = () => Number($('duration')?.value || 300);

async function checkHealth() {
  try {
    const health = await fetch('/api/health').then(r => r.json());
    state.health=health;
    $('systemBadge').className = `system-badge ${health.hyram_available ? 'ready' : 'warn'}`;
    $('systemBadge').querySelector('span').textContent = health.hyram_available ? '전체 시스템 준비' : '시뮬레이터 준비 / 피해영향예측 미연결';
    $('footerHyram').textContent = health.hyram_available ? '피해영향예측 엔진 연결 · 누출 시 계산' : '피해영향예측 엔진 미연결';
    $('riskKpi').textContent = health.hyram_available ? '피해영향예측 대기' : '피해영향예측 미연결';
    $('hazopCatalogStatus').textContent = health.hazop?.status === 'ready' ? `${health.hazop.sensor_count}개 센서 연결` : '센서 분석 연결 실패';
    const mappingResponse = await fetch('/api/hazop/mapping');
    if (mappingResponse.ok) {
      const mapping = await mappingResponse.json();state.mapping=mapping;
      const labels = {PROCESS_STATE:'모델 상태', DERIVED_SHARED:'공유 계산값', BOUNDARY_SETTING:'공급 경계값', UNAVAILABLE:'입력 없음'};
      $('hazopMapping').innerHTML = mapping.sensors.map(s => `<tr><td>${escapeHtml(s.sensor_id)}</td><td>${escapeHtml(labels[s.mapping_status] || s.mapping_status)}</td><td>${escapeHtml(s.binding)}</td></tr>`).join('');
      if(!state.result?.series?.time_s?.length)$('hazopMetrics').textContent = `${mapping.mapped_sensors}/${mapping.sensor_total} 센서 신호 연결`;
    }
  } catch (_) {
    $('systemBadge').className = 'system-badge warn';
    $('systemBadge').querySelector('span').textContent = 'API 연결 실패';
  }
}

async function runSimulation() {
  stopPlayback();
  const button = $('runButton');
  if (!button) return;
  button.disabled = true;
  button.querySelector('span').textContent = '계산 준비 중';
  beginCalculationMonitor();
  const faults = $('leakFault').checked ? [{ event_id:'hose-leak-ui', kind:'hydrogen-leak', target:'dispenser.hose', start_time_s:45, leak_diameter_mm:0.5, indoor:false }] : [];
  if ($('hazopTest').value === 'pressure1') faults.push({event_id:'hazop-pt1',kind:'sensor-bias',target:'PT-1401',start_time_s:0,magnitude:90});
  if ($('hazopTest').value === 'temperature2') faults.push({event_id:'hazop-tt2',kind:'sensor-bias',target:'TT-1601',start_time_s:0,magnitude:40});
  const payload = {
    duration_s: Number($('duration').value),
    control_period_s: Number($('controlPeriod').value),
    ambient_temperature_c: Number($('ambientTemp').value),
    initial_vehicle_pressure_mpa: Number($('initialPressure').value),
    initial_vehicle_2_pressure_mpa: Number($('initialPressure2').value),
    faults
  };
  try {
    const created = await fetch('/api/simulations', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) }).then(async r => { if (!r.ok) throw new Error(await r.text()); return r.json(); });
    await streamJob(created.id);
  } catch (error) {
    failCalculationMonitor(error.message);
    button.disabled = false;
    button.querySelector('span').textContent = '다시 시작';
    addLocalEvent('ERROR', error.message, 'trip');
  }
}

async function streamJob(id) {
  state.socket?.close(); state.generation++; const generation=state.generation;
  state.activeJobId=id;state.followLive=true;state.lastSequence=-1;state.connection='connecting';
  lastLivePaintAt=0;
  state.lastReceived=0;stopPlayback();initializeLiveResult();beginCalculationMonitor();
  const url=new URL(location.href);url.searchParams.set('job',id);history.replaceState(null,'',url);
  $('remoteLink').href='/remote.html?job='+encodeURIComponent(id);
  Object.keys(incidentSources).forEach(key=>incidentSources[key]=false);updateIncidentPanels('initial',false);
  $('stopMonitor').hidden=false; $('stopMonitor').disabled=false;
  return new Promise((resolve,reject)=>{
    let finished=false;
    const fail=message=>{if(finished||generation!==state.generation)return;finished=true;state.connection='failed';state.socket?.close();failCalculationMonitor(message);addLocalEvent('ERROR',message,'trip');$('stopMonitor').hidden=true;reject(new Error(message));};
    const complete=async()=>{if(finished||generation!==state.generation)return;finished=true;state.connection='complete';$('stopMonitor').hidden=true;state.socket?.close();try{await loadFinalResult(id,false);resolve();}catch(e){failCalculationMonitor(e.message);reject(e);}};
    const acceptStatus=job=>{state.job=job;state.connection=job.status==='failed'?'failed':job.status==='complete'?'complete':'connected';state.lastReceived=Date.now();updateCalculationMonitor(job);if(job.status==='failed')fail(job.error||'계산 오류');};
    const poll=async()=>{
      if(finished||generation!==state.generation)return;
      try{
        const response=await fetch(`/api/simulations/${id}/frames?after=${state.lastSequence}`);
        if(!response.ok)throw new Error(response.status===404?'시뮬레이션을 찾을 수 없습니다. 리모콘에서 새로 실행하세요.':`통신 오류 ${response.status}`);
        const snapshot=await response.json();acceptStatus(snapshot.job);
        snapshot.frames.forEach(acceptFrame);
        if(snapshot.job.status==='complete')return complete();
        if(!finished)setTimeout(poll,1000);
      }catch(e){fail(e.message);}
    };
    const acceptFrame=frame=>{if(generation!==state.generation||finished||frame.sequence<=state.lastSequence)return;state.lastSequence=frame.sequence;state.lastReceived=Date.now();applyLiveFrame(frame);};
    const socket=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/api/simulations/${id}/stream`);state.socket=socket;
    socket.onmessage=async e=>{
      if(generation!==state.generation||finished)return;
      try{const msg=JSON.parse(e.data);if(msg.type==='status')acceptStatus(msg.job);else if(msg.type==='frame')acceptFrame(msg.frame);else if(msg.type==='error')fail(msg.message);else if(msg.type==='complete')complete();}catch(error){fail(error.message);}
    };
    socket.onclose=()=>{if(!finished&&generation===state.generation){state.connection='reconnecting';poll();}};
  });
}
window.connectStationJob=id=>streamJob(id).catch(e=>window.notifyOperator?.(e.message));
window.updateConnectionDisplay=()=>{
  const labels={idle:'시나리오 대기',connecting:'모델 연결 중',connected:'실시간 수신',reconnecting:'재연결 중',complete:'계산 완료 · 이력',failed:'계산 / 연결 오류'};
  const elapsed=state.lastReceived?(Date.now()-state.lastReceived)/1000:0;
  $('connectionShort').textContent=labels[state.connection]||'대기';
  $('connectionDot').style.background=state.connection==='connected'&&elapsed<10?'var(--cyan)':state.connection==='failed'?'var(--red)':'var(--muted)';
  const activity=state.lastFrame?.process_activity||{},names={trailer_supply:'트레일러',pressure_recharge:'압력 보완',vehicle_1:'차량 1',vehicle_2:'차량 2'};
  const flowing=Object.entries(activity).filter(([,value])=>value?.state==='flowing');
  const requested=Object.keys(names).filter(key=>state.lastFrame?.process_operations?.settings?.[key]).length;
  const processText=flowing.length?flowing.map(([key,value])=>`${names[key]} ${Number(value.flow_g_s||0).toFixed(1)} g/s`).join(' · '):requested?'공정 명령 반영 대기':'공정 대기';
  const lag=Number(state.lastFrame?.realtime_lag_s||0);
  const speed=Number(state.job?.speed_multiplier||1);
  $('connectionStatus').textContent=(labels[state.connection]||'대기')+(state.connection==='connected'?` · ${processText}`:state.job?` · 모의 ${Number(state.job.simulated_time_s||0).toFixed(1)} s`:'')+(state.connection==='connected'&&speed>1?` · 목표 ${speed}×`:'')+(lag>.5?` · 계산 ${lag.toFixed(1)}초 지연`:'')+(state.connection==='connected'&&elapsed>10?' · 데이터 갱신 지연':'');
};

function initializeLiveResult() {
  state.result = {
    summary: { duration_s:0, hyram_available:Boolean(state.health?.hyram_available) },
    series: {
      time_s:[], vehicle_pressure_mpa:[], vehicle_temperature_c:[], soc_percent:[],
      vehicle_2_pressure_mpa:[], vehicle_2_temperature_c:[], vehicle_2_soc_percent:[],
      pcv_flow_g_s:[], nozzle_flow_g_s:[], total_leak_flow_g_s:[],
      pcv_1_flow_g_s:[], pcv_2_flow_g_s:[], nozzle_1_flow_g_s:[], nozzle_2_flow_g_s:[], active_faults:[],
      hose_pressure_mpa:[], hose_temperature_c:[], bank_pressure_mpa:{ low:[], medium:[], high:[] },
      dispatch_bank:[], dispatch_bank_2:[], recharge_bank:[], process_activity:[], process_operations:[], esd:[], leaks:{}
    },
    events:[], risk_updates:[], hazop:{frames:[]}
  };
  state.index = 0;state.lastFrame=null;
  $('timeline').value = 0;
  $('timeline').max = 0;
}

function applyLiveFrame(frame) {
  const s = state.result.series;
  s.time_s.push(frame.time_s);
  s.vehicle_pressure_mpa.push(frame.vehicle_pressure_mpa);
  s.vehicle_temperature_c.push(frame.vehicle_temperature_c);
  s.soc_percent.push(frame.soc_percent);
  s.vehicle_2_pressure_mpa.push(frame.vehicle_2_pressure_mpa);
  s.vehicle_2_temperature_c.push(frame.vehicle_2_temperature_c);
  s.vehicle_2_soc_percent.push(frame.vehicle_2_soc_percent);
  s.pcv_flow_g_s.push(frame.pcv_flow_g_s);
  s.nozzle_flow_g_s.push(frame.nozzle_flow_g_s);
  s.pcv_1_flow_g_s.push(frame.pcv_1_flow_g_s);
  s.pcv_2_flow_g_s.push(frame.pcv_2_flow_g_s);
  s.nozzle_1_flow_g_s.push(frame.nozzle_1_flow_g_s);
  s.nozzle_2_flow_g_s.push(frame.nozzle_2_flow_g_s);
  s.total_leak_flow_g_s.push(frame.total_leak_flow_g_s);
  s.active_faults.push(frame.active_faults || []);
  (s.released_mass_kg ||= []).push(frame.released_mass_kg||0);
  (s.peak_vehicle_temperature_c ||= []).push(frame.peak_vehicle_temperature_c);
  (s.trip_causes ||= []).push(frame.trip_causes||[]);
  (s.analysis ||= []).push(frame.analysis || null);
  (s.gas_detectors ||= []).push(frame.gas_detectors || {});
  s.hose_pressure_mpa.push(frame.hose_pressure_mpa);
  s.hose_temperature_c.push(frame.hose_temperature_c);
  (s.hose_2_pressure_mpa ||= []).push(frame.hose_2_pressure_mpa);
  (s.hose_2_temperature_c ||= []).push(frame.hose_2_temperature_c);
  state.result.hazop.frames.push(frame.hazop);
  s.dispatch_bank.push(frame.dispatch_bank);
  s.dispatch_bank_2.push(frame.dispatch_bank_2);
  s.recharge_bank.push(frame.recharge_bank);
  s.process_activity.push(frame.process_activity || {});
  s.process_operations.push(frame.process_operations || null);
  s.esd.push(frame.esd);
  for (const [name, pressure] of Object.entries(frame.bank_pressure_mpa)) {
    if (!s.bank_pressure_mpa[name]) s.bank_pressure_mpa[name] = [];
    s.bank_pressure_mpa[name].push(pressure);
  }
  state.result.summary.duration_s = frame.time_s;
  // Bound browser memory for continuous monitoring; all arrays share one index.
  const excess=s.time_s.length-12000;
  if(excess>0){Object.values(s).forEach(v=>{if(Array.isArray(v))v.splice(0,excess);});Object.values(s.bank_pressure_mpa).forEach(v=>v.splice(0,excess));state.result.hazop.frames.splice(0,excess);state.index=Math.max(0,state.index-excess);}
  const previous=state.lastFrame;
  let eventAdded=false;
  const emit=(message,severity='info')=>{eventAdded=true;state.result.events.push({time_s:frame.time_s,message,severity});};
  if(!previous)emit('시뮬레이션 모니터 연결');
  if(previous&&previous.dispatch_bank!==frame.dispatch_bank)emit(`1번 토출 뱅크 → ${frame.dispatch_bank||'격리'}`);
  if(previous&&previous.dispatch_bank_2!==frame.dispatch_bank_2)emit(`2번 토출 뱅크 → ${frame.dispatch_bank_2||'격리'}`);
  if(frame.esd&&!previous?.esd)emit('ESD 작동 · '+(frame.trip_causes||[]).join(', '),'trip');
  for(const key of frame.relief_valves_open||[])if(!previous?.relief_valves_open?.includes(key))emit(`안전밸브 개방 · ${reliefNames[key]||key}`,'warning');
  for(const key of previous?.relief_valves_open||[])if(!frame.relief_valves_open?.includes(key))emit(`안전밸브 재폐쇄 · ${reliefNames[key]||key}`);
  for(const fault of frame.active_faults||[])if(!fault.startsWith('relief-open:')&&!previous?.active_faults?.includes(fault))emit('사고 활성 · '+fault,'warning');
  for(const fault of previous?.active_faults||[])if(!fault.startsWith('relief-open:')&&!frame.active_faults?.includes(fault))emit('사고 입력 종료 · '+fault);
  for(const alarm of frame.hazop?.events||[])emit(`${alarm.sensor_id} · ${alarm.name} · ${alarm.state}`,alarm.active?'warning':'info');
  if(state.result.events.length>500)state.result.events.splice(0,state.result.events.length-500);
  state.lastFrame=frame;
  const now=Date.now(),riskChanged=previous?.analysis?.status!==frame.analysis?.status;
  if(eventAdded||riskChanged||now-lastLivePaintAt>=100){
    lastLivePaintAt=now;
    window.updateConnectionDisplay?.();renderEvents(state.result.events);
    $('timeline').max=Math.max(0,s.time_s.length-1);
    if(state.followLive)updateFrame(s.time_s.length-1);else drawCursor();
  }

}

async function loadFinalResult(id,autoplay) {
  const response=await fetch(`/api/simulations/${id}/result`);if(!response.ok)throw new Error('결과 조회 실패');
  const result=await response.json();if(id!==state.activeJobId)return;
  if(!state.result?.series?.time_s?.length)state.result=result;
  else {state.result.summary=result.summary;state.result.risk_updates=result.risk_updates;}
  completeCalculationMonitor();$('timeline').max=Math.max(0,state.result.series.time_s.length-1);
  renderEvents(state.result.events||[]);updateFrame(state.result.series.time_s.length-1);
  if(autoplay)startPlayback();
}

function updateFrame(index) {
  if (!state.result?.series?.time_s?.length) return;
  const s = state.result.series;
  state.index = Math.max(0, Math.min(index, s.time_s.length - 1));
  $('timeline').value = state.index;
  renderHazop(state.result.hazop?.frames?.[state.index]);
  renderLiveAnalysis(s.analysis?.[state.index],s.gas_detectors?.[state.index]);
  renderLiveImpact({active_faults:s.active_faults?.[state.index],esd:s.esd?.[state.index],total_leak_flow_g_s:s.total_leak_flow_g_s?.[state.index],released_mass_kg:s.released_mass_kg?.[state.index],peak_vehicle_temperature_c:s.peak_vehicle_temperature_c?.[state.index],vehicle_temperature_c:s.vehicle_temperature_c?.[state.index]});
  const pressure = s.vehicle_pressure_mpa[state.index];
  const temp = s.vehicle_temperature_c[state.index];
  const soc = s.soc_percent[state.index];
  const flow = s.nozzle_flow_g_s[state.index];
  const pressure2 = s.vehicle_2_pressure_mpa[state.index];
  const temp2 = s.vehicle_2_temperature_c[state.index];
  const soc2 = s.vehicle_2_soc_percent[state.index];
  const flow1 = s.nozzle_1_flow_g_s[state.index];
  const flow2 = s.nozzle_2_flow_g_s[state.index];
  const leak = s.total_leak_flow_g_s[state.index];
  const esd = s.esd[state.index];
  $('pressureKpi').textContent = pressure.toFixed(1);
  $('temperatureKpi').textContent = temp.toFixed(1);
  $('socKpi').textContent = soc.toFixed(1);
  const assessment=s.analysis?.[state.index]?.status;
  $('safetyKpi').textContent = esd?'ESD':assessment==='CRITICAL'?'위험':assessment==='WARNING'?'경고':assessment==='ADVISORY'?'주의':(flow>.01?'충전 중':'정상');
  $('timeOutput').textContent = `${s.time_s[state.index].toFixed(1)} s`;
  $('flowLabel').textContent = `${flow.toFixed(1)} g/s`;
  $('vehicle2Pressure').textContent = `2번 ${pressure2.toFixed(1)} MPa`;
  $('vehicle2Temperature').textContent = `2번 ${temp2.toFixed(1)} °C`;
  $('vehicle2Soc').textContent = `2번 ${soc2.toFixed(1)}% SOC`;
  $('flowSplitLabel').textContent = `1번 ${flow1.toFixed(1)} / 2번 ${flow2.toFixed(1)} g/s`;
  $('pressureBar').style.width = `${Math.min(100, pressure / 70 * 100)}%`;
  $('temperatureBar').style.width = `${Math.min(100, Math.max(0, (temp + 40) / 125 * 100))}%`;
  $('socBar').style.width = `${Math.min(100, soc)}%`;
  $('safetyBar').style.width = esd ? '100%' : '12%';
  const operations=s.process_operations?.[state.index]?.settings||{},activity=s.process_activity?.[state.index]||{};
  const supplyFlow=Number(activity.trailer_supply?.flow_g_s||0),supplyRequested=Boolean(operations.trailer_supply&&operations.pressure_recharge);
  $('supplyFlowLabel').textContent=supplyFlow>.01?`${supplyFlow.toFixed(1)} g/s`:supplyRequested?'공급 요청 중':'공급 대기';
  $('supplyUnit').classList.toggle('active',supplyFlow>.01&&!esd);
  $('supplyUnit').classList.toggle('requested',supplyRequested&&supplyFlow<=.01);
  $('compressorUnit').classList.toggle('active',supplyFlow>.01&&!esd);
  $('compressorUnit').classList.toggle('requested',supplyRequested&&supplyFlow<=.01);
  $('pcvUnit').classList.toggle('active', flow > .01 && !esd);
  $('coolerUnit').classList.toggle('active', flow > .01 && !esd);
  $('vehicleUnit').classList.toggle('active', flow > .01);
  $('pcvUnit').classList.toggle('trip', esd);
  document.querySelectorAll('.flow-map .pipe').forEach(pipe => {const recharge=pipe.classList.contains('supply-line')||pipe.classList.contains('recharge-line');pipe.classList.toggle('flowing',recharge?supplyFlow>.01:flow1+flow2>.01);pipe.classList.toggle('requested',recharge&&supplyRequested&&supplyFlow<=.01);});
  document.querySelectorAll('.bank').forEach(bank => {const name=bank.dataset.bank,recharging=name===s.recharge_bank[state.index];bank.classList.toggle('active',name===s.dispatch_bank[state.index]||name===s.dispatch_bank_2?.[state.index]||recharging);bank.classList.toggle('recharging',recharging&&supplyFlow>.01);bank.classList.toggle('requested',supplyRequested&&recharging&&supplyFlow<=.01);});
  for (const name of ['low','medium','high']) {
    const value = s.bank_pressure_mpa[name][state.index];
    $(`bank${name[0].toUpperCase()+name.slice(1)}`).textContent = value.toFixed(1);
  }
  $('dispatchStatus').textContent = s.dispatch_bank[state.index] ? `${s.dispatch_bank[state.index].toUpperCase()} 뱅크 토출` : '토출 뱅크 없음';
  $('rechargeStatus').textContent = s.recharge_bank[state.index] ? `${s.recharge_bank[state.index].toUpperCase()} 뱅크 재충전` : '압축기 대기';
  $('leakStatus').textContent = leak > .001 ? `누출 ${leak.toFixed(2)} g/s` : '누출 없음';
  $('leakStatus').classList.toggle('danger', leak > .001);
  const faults=s.active_faults?.[state.index]||[];
  const reliefOpen=Object.keys(s.process_operations?.[state.index]?.relief_open||{}).filter(key=>s.process_operations[state.index].relief_open[key]);
  document.querySelectorAll('.flow-map .unit,.flow-map .bank').forEach(node=>{
    const id=node.dataset.bank||node.id,target=faults.find(f=>{
      const [,component]=f.split(':');return id==='compressorUnit'?component?.startsWith('compressor'):id==='pcvUnit'?component?.includes('pcv'):id==='coolerUnit'?component?.includes('cooler'):id==='vehicleUnit'?component?.includes('vehicle')||component?.includes('hose'):component===`cascade.${id}`;
    });
    node.classList.toggle('fault-active',Boolean(target)&&!target.startsWith('relief-open:'));node.dataset.fault=target?.startsWith('relief-open:')?'':target?.split(':')[0]||'';
    const bank=node.dataset.bank,relief=bank?reliefOpen.includes(bank):node.id==='vehicleUnit'?reliefOpen.some(key=>key.startsWith('vehicle_')):node.id==='pcvUnit'?reliefOpen.some(key=>key.startsWith('hose_')):false;
    node.classList.toggle('relief-open',relief);
  });
  let reliefStatus=$('reliefFlowStatus');if(!reliefStatus){reliefStatus=document.createElement('span');reliefStatus.id='reliefFlowStatus';document.querySelector('.flow-status').append(reliefStatus);}
  reliefStatus.textContent=reliefOpen.length?`안전밸브 개방 · ${reliefOpen.map(key=>reliefNames[key]||key).join(', ')}`:'';
  reliefStatus.hidden=!reliefOpen.length;
  const releases=state.result.hazop?.frames?.[state.index]?.releases||[],ranges=releases.filter(r=>r.consequence?.status==='calculated');
  if(!$('flowRisk')){const note=document.createElement('span');note.id='flowRisk';document.querySelector('.flow-status').append(note);}
  $('flowRisk').textContent=ranges.length?(Number(ranges[0].consequence.sampled_effect_radius_m)>0?`피해영향예측 표본 영향 ${Number(ranges[0].consequence.sampled_effect_radius_m).toFixed(1)} m${ranges[0].consequence.effect_range_status==='BEYOND_SAMPLED_POINTS'?' 이상':''} · 배치 미검증`:`피해영향예측 ${Number(ranges[0].consequence.sampled_max_distance_m).toFixed(1)} m 관측점까지 기준 미달 · 범위 미확정`):'';
  $('riskKpi').textContent = ranges.length ? '피해영향예측 계산 완료' : releases.length ? '피해영향예측 계산 대기' : (state.result.summary.hyram_available ? '피해영향예측 대기' : '피해영향예측 미연결');
  window.dispatchEvent(new Event('station-frame'));
  drawCursor();
}

function startPlayback() {
  if (!state.result || state.playing) return;
  if (state.index >= state.result.series.time_s.length - 1) state.index = 0;
  state.followLive=false;
  state.playing = true;
  $('playButton').textContent = '정지';
  state.timer = setInterval(() => {
    updateFrame(state.index + 1);
    if (state.index >= state.result.series.time_s.length - 1) stopPlayback();
  }, 35);
}
function stopPlayback() { state.playing = false; clearInterval(state.timer); $('playButton').textContent = '재생'; }

function drawChart(){
  const canvas=$('trendChart'),rect=canvas.getBoundingClientRect();if(rect.width<1||rect.height<1)return;
  const ratio=Math.min(devicePixelRatio||1,2);canvas.width=rect.width*ratio;canvas.height=rect.height*ratio;
  const ctx=canvas.getContext('2d');ctx.scale(ratio,ratio);
  const w=rect.width,h=rect.height,p={l:38,r:12,t:12,b:20};state.chart={ctx,w,h,p};
  ctx.strokeStyle='#25354a';ctx.fillStyle='#869aaf';ctx.font='9px Consolas';
  const s=state.result?.series;const metric=$('trendMetric')?.value||'pressure';
  const nodeData=window.nodeMonitor?.series({pressure:0,temperature:1,flow:2}[metric]);
  const values=nodeData?[nodeData.values]:[['vehicle_pressure_mpa','vehicle_2_pressure_mpa'],['vehicle_temperature_c','vehicle_2_temperature_c'],['nozzle_1_flow_g_s','nozzle_2_flow_g_s']][{pressure:0,temperature:1,flow:2}[metric]].map(k=>s?.[k]||[]);const count=s?.time_s?.length||0;
  const legend=document.querySelector('.chart-panel .legend');if(legend&&nodeData)legend.textContent=`${window.nodeMonitor.selectedNode} · ${nodeData.tag||'센서 없음'} · ${nodeData.unit}`;
  $('chartEmpty').hidden=count>0;
  let lo=metric==='temperature'?-40:0,hi=metric==='pressure'?100:metric==='temperature'?100:60;
  values.forEach(v=>v.forEach(n=>{if(Number.isFinite(n)){lo=Math.min(lo,n);hi=Math.max(hi,n);}}));
  for(let i=0;i<4;i++){const y=p.t+(h-p.t-p.b)*i/3;ctx.beginPath();ctx.moveTo(p.l,y);ctx.lineTo(w-p.r,y);ctx.stroke();ctx.fillText((hi-(hi-lo)*i/3).toFixed(0),3,y+3);}
  if(!count)return;
  const t0=s.time_s[0],t1=s.time_s[count-1],span=Math.max(.001,t1-t0);
  values.forEach((series,n)=>{ctx.strokeStyle=n?'#8daeff':'#4ed9c2';ctx.lineWidth=1.5;ctx.beginPath();let begun=false;const step=Math.max(1,Math.floor(count/(w*2)));for(let i=0;i<count;i+=step){const value=series[i];if(!Number.isFinite(value)){begun=false;continue;}const x=p.l+(w-p.l-p.r)*(s.time_s[i]-t0)/span,y=h-p.b-(h-p.t-p.b)*(value-lo)/(hi-lo);if(!begun){ctx.moveTo(x,y);begun=true;}else ctx.lineTo(x,y);}ctx.stroke();});
  ctx.fillStyle='#869aaf';ctx.fillText(t0.toFixed(1)+' s',p.l,h-3);ctx.fillText(t1.toFixed(1)+' s',w-60,h-3);
  const x=p.l+(w-p.l-p.r)*((s.time_s[state.index]??t1)-t0)/span;ctx.strokeStyle='#cedbea80';ctx.setLineDash([3,4]);ctx.beginPath();ctx.moveTo(x,p.t);ctx.lineTo(x,h-p.b);ctx.stroke();ctx.setLineDash([]);
}
function drawCursor(){drawChart();}
window.drawStationTrend=drawChart;

function renderEvents(events) { const list=$('eventList');$('eventCount').textContent=`${events.length} EVENTS`;if(!events.length){list.innerHTML='<p class="empty">이 시나리오에는 기록된 전환 또는 안전 이벤트가 없습니다.</p>';return;}list.innerHTML=events.slice(-100).reverse().map(e=>`<div class="event ${e.severity}"><time>${e.time_s.toFixed(1)} s</time><span>${escapeHtml(e.message)}</span></div>`).join(''); }
function addLocalEvent(time,message,severity){$('eventList').innerHTML=`<div class="event ${severity}"><time>${time}</time><span>${escapeHtml(message)}</span></div>`;}
function escapeHtml(value){const div=document.createElement('div');div.textContent=value;return div.innerHTML;}

function renderHazop(frame) {
  if (!frame) {updateIncidentPanels('hazop',false);return;}
  const counts=frame.counts || {};
  const unknown=counts.UNKNOWN || 0;
  $('hazopMetrics').textContent=`${frame.mapped_sensor_count}/${frame.sensor_total} 센서 연결 · 사고 후보 ${frame.groups?.length || 0}건 · 판정불가 ${unknown} · 조건 대기 ${counts.PENDING || 0}`;
  const status={RESULT_LINKED:'피해영향예측 결과 연결', PARTIAL_RESULT:'피해영향예측 부분 결과 연결', NEEDS_RELEASE_INPUTS:'실제 누출 미등록 · 센서 기준 가정 결과는 SAGA 확인', BACKEND_UNAVAILABLE:'피해영향예측 엔진 연결 불가', NOT_APPLICABLE:'직접 영향계산 대상 아님'};
  const groups=frame.groups || [];
  const active=frame.active || [];
  let html=groups.map(g=>{
    const names=active.filter(a=>g.rule_ids.includes(a.rule_id)).map(a=>`${a.name} (${a.value == null ? '판정불가' : Number(a.value).toFixed(3)} ${a.unit} / ${a.operator} ${a.threshold})`);
    return `<article class="hazop-candidate"><b>${escapeHtml(g.node_id)} · ${escapeHtml(g.severity)} 후보</b><p>${names.map(escapeHtml).join('<br>')}</p><small>${escapeHtml(status[g.hyram_status] || g.hyram_status)}${g.release_ids.length ? ' · '+g.release_ids.map(escapeHtml).join(', ') : ''}</small></article>`;
  }).join('');
  if (!html) html=`<p class="empty">현재 활성 사고 후보가 없습니다. 미수신 센서 ${unknown}개는 상태를 판단하지 않았습니다.</p>`;
  for (const release of frame.releases || []) {
    const extent=release.consequence?.sampled_effect_radius_m;
    html+=`<p class="hazop-release">누출 ${escapeHtml(release.release_id)} · ${escapeHtml(release.component_id)} · 피해영향예측 ${release.consequence?.status==='calculated'?'계산 완료':'계산 불가'}${Number(extent)>0?` · 5 kW/m²/5 kPa 표본 영향 ${Number(extent).toFixed(1)} m${release.consequence.effect_range_status==='BEYOND_SAMPLED_POINTS'?' 이상':''}`:release.consequence?.status==='calculated'?` · ${Number(release.consequence.sampled_max_distance_m||0).toFixed(1)} m 관측점까지 기준 미달(범위 미확정)`:''}${release.cached ? ' (이전 계산값)' : ''}</p>`;
  }
  if(frame.persistence_error)html+=`<p class="hazop-error">이벤트 저장 실패: ${escapeHtml(frame.persistence_error)}</p>`;
  $('hazopAlerts').innerHTML=html;
  updateIncidentPanels('hazop', groups.length > 0 || active.length > 0 || (frame.releases || []).length > 0 || Boolean(frame.persistence_error));
}

function renderLiveImpact(frame) {
  const faults=frame.active_faults||[]; $('impactStatus').textContent=faults.length?'사고 입력 활성':'정상 운전 기준';
  $('impactFaults').textContent=faults.length?`${faults.length}건`:'없음';
  $('impactLeak').innerHTML=`${Number(frame.total_leak_flow_g_s||0).toFixed(2)} <em>g/s</em>`;
  $('impactMass').innerHTML=`${Number(frame.released_mass_kg||0).toFixed(Number(frame.released_mass_kg||0)>0&&Number(frame.released_mass_kg||0)<.001?6:3)} <em>kg</em>`;
  $('impactTemp').innerHTML=`${Number(frame.peak_vehicle_temperature_c ?? frame.vehicle_temperature_c ?? 25).toFixed(1)} <em>°C</em>`;
  $('impactEsd').textContent=frame.esd?'작동':'없음';
  updateIncidentPanels('impact', faults.length > 0 || Boolean(frame.esd) || Number(frame.total_leak_flow_g_s || 0) > 0);
}
function renderLiveAnalysis(analysis, detectors={}) {
  if (!analysis) { $('analysisStatus').textContent='WAIT';$('analysisHeadline').textContent='운전 데이터 대기';$('analysisFindings').textContent='연결된 모델을 기다리고 있습니다.';updateIncidentPanels('analysis',false);return; }
  const status = String(analysis.status || 'NORMAL');
  const node = $('analysisStatus');
  node.textContent = status;
  node.className = `analysis-state ${status}`;node.parentElement.dataset.state=status;
  $('analysisHeadline').textContent = window.publicImpactText(analysis.headline || '실시간 분석 대기');
  $('analysisFindings').textContent = window.publicImpactText((analysis.findings || []).join(' · ') || '연결된 신호가 정상 범위입니다.');
  const entries = Object.entries(detectors || {});
  $('detectorStrip').innerHTML = entries.length ? entries.map(([tag, value]) => {
    if(!Number.isFinite(value?.value)||value?.quality!=='GOOD')return `<span>${escapeHtml(tag)} 미수신</span>`;
    const v = Number(value.value); const level = v >= 2 ? 'trip' : v >= 1 ? 'alarm' : '';
    return `<button type="button" class="${level}" data-detector="${escapeHtml(tag)}" title="${escapeHtml(value.zone || tag)} · ${escapeHtml(value.origin || '가상 검지')}">${escapeHtml(tag)} <b>${v.toFixed(2)}</b><small> %</small></button>`;
  }).join('') : '<span>가스검지기 미수신</span>';
  const detectorAlarm = entries.some(([, value]) => Number(value?.value || 0) >= 1);
  updateIncidentPanels('analysis', status !== 'NORMAL' || detectorAlarm);
}
function renderImpact(impact) {
  if (!impact) return;
  $('impactStatus').textContent=impact.fault_targets?.length?'사고 결과':'정상 운전 기준';
  $('impactFaults').textContent=impact.fault_targets?.length?`${impact.fault_targets.length}개 위치`:'없음';
  $('impactLeak').innerHTML=`${Number(impact.peak_leak_flow_g_s||0).toFixed(2)} <em>g/s</em>`;
  $('impactMass').innerHTML=`${Number(impact.released_mass_kg||0).toFixed(3)} <em>kg</em>`;
  $('impactTemp').innerHTML=`${Number(impact.peak_vehicle_temperature_c||25).toFixed(1)} <em>°C</em>`;
  $('impactEsd').textContent=impact.esd_time_s == null?'없음':`${Number(impact.esd_time_s).toFixed(1)} s`;
  updateIncidentPanels('impact', Boolean(impact.fault_targets?.length) || impact.esd_time_s != null || Number(impact.peak_leak_flow_g_s || 0) > 0);
}

const calculationMonitorState = { startedAt: null, job: null, lastLogKey: '' };

function beginCalculationMonitor() {
  calculationMonitorState.startedAt = Date.now();
  calculationMonitorState.job = null;
  calculationMonitorState.lastLogKey = '';
  $('monitorLog').innerHTML = '<p>계산 작업을 생성하고 있습니다.</p>';
  $('monitorButton').className = 'monitor-button is-running';
  renderCalculationMonitor();
}

function updateCalculationMonitor(job) {
  calculationMonitorState.job = job;
  calculationMonitorState.startedAt ||= Date.parse(job.started_at||job.created_at)||Date.now();
  const logKey = `${job.phase}:${Math.floor((job.progress || 0) / 10)}`;
  if (logKey !== calculationMonitorState.lastLogKey) {
    calculationMonitorState.lastLogKey = logKey;
    const stamp = new Date().toLocaleTimeString('ko-KR', { hour12:false });
    $('monitorLog').insertAdjacentHTML('afterbegin', `<p><time>${stamp}</time>${escapeHtml(job.activity || job.status)}</p>`);
  }
  renderCalculationMonitor();
}

function completeCalculationMonitor() {
  $('monitorButton').className = 'monitor-button is-complete';
  renderCalculationMonitor();
}

async function stopActiveMonitor() {
  if (!state.activeJobId) return;
  $('stopMonitor').disabled = true;
  try { await fetch(`/api/simulations/${state.activeJobId}/stop`, {method:'POST'}); }
  catch (error) { addLocalEvent('ERROR', error.message, 'trip'); }
}

function failCalculationMonitor(message) {
  calculationMonitorState.job = { ...(calculationMonitorState.job || {}), status:'failed', phase:'failed', activity:message };
  $('monitorButton').className = 'monitor-button is-failed';
  renderCalculationMonitor();
}

function renderCalculationMonitor() {
  const job = calculationMonitorState.job || {};
  const progress = Number(job.progress || 0);
  const simulated = Number(job.simulated_time_s || 0);
  const continuous = Boolean(job.continuous);
  const duration = Number(job.duration_s || scenarioDuration() || 0);
  const elapsed = calculationMonitorState.startedAt ? (Date.now() - calculationMonitorState.startedAt) / 1000 : 0;
  const ratio = duration > 0 ? simulated / duration : 0;
  const eta = ratio > 0 && ratio < 1 ? elapsed * (1 - ratio) / ratio : 0;
  const updatedAge = job.updated_at ? Math.max(0, (Date.now() - Date.parse(job.updated_at)) / 1000) : null;
  const phaseNames = { monitoring:'무제한 모니터링', queued:'작업 대기', initializing:'모델 초기화', integrating:'동적 방정식 해석', serializing:'결과 변환', complete:'완료', failed:'오류' };

  $('monitorPercent').textContent = continuous?'∞':`${progress}%`;
  $('monitorProgressBar').style.width = `${progress}%`;
  $('monitorActivity').textContent = job.activity || '시뮬레이션을 시작하면 계산 상태가 표시됩니다.';
  $('monitorPhase').textContent = (phaseNames[job.phase] || '대기')+(continuous&&job.speed_multiplier?` · 목표 ${job.speed_multiplier}×`:'');
  $('monitorSimTime').textContent = continuous ? `${simulated.toFixed(1)} s · ∞` : `${simulated.toFixed(1)} / ${duration.toFixed(1)} s`;
  $('monitorSteps').textContent = `${job.solver_step || 0} / ${job.total_steps || 0}`;
  $('monitorElapsed').textContent = formatMonitorTime(elapsed);
  $('monitorEta').textContent = continuous ? '제한 없음' : job.status === 'complete' ? '완료' : ratio > 0 ? `약 ${formatMonitorTime(eta)}` : '계산 중 산정';
  $('monitorBackend').textContent = job.hyram_backend ? (job.hyram_backend.includes('not configured') ? '피해영향예측 엔진 미연결' : '피해영향예측 엔진 연결') : '초기화 중';
  $('monitorHeartbeat').textContent = job.status === 'complete' ? '계산 완료' : job.status === 'failed' ? '계산 오류' : updatedAge === null ? '작업 준비 중' : updatedAge < 5 ? `계산 동작 중 · ${updatedAge.toFixed(1)}초 전 갱신${continuous&&job.simulation_rate_x!=null?` · 실제 ${Number(job.simulation_rate_x).toFixed(1)}×`:''}` : `긴 해석 구간 수행 중 · ${updatedAge.toFixed(0)}초 전 갱신`;
  $('monitorLiveDot').className = job.status === 'failed' ? 'failed' : job.status === 'complete' ? 'complete' : 'running';
}

function formatMonitorTime(seconds) {
  if (!Number.isFinite(seconds)) return '산정 불가';
  if (seconds < 60) return `${Math.max(0, Math.round(seconds))} s`;
  return `${Math.floor(seconds / 60)} min ${Math.round(seconds % 60)} s`;
}

if ($('runButton')) $('runButton').addEventListener('click',runSimulation);
$('monitorButton').addEventListener('click',()=>{renderCalculationMonitor();$('calculationMonitor').showModal();});
$('monitorClose').addEventListener('click',()=>$('calculationMonitor').close());
$('stopMonitor')?.addEventListener('click',stopActiveMonitor);
$('playButton').addEventListener('click',()=>state.playing?stopPlayback():startPlayback());
$('timeline').addEventListener('input',e=>{stopPlayback();state.followLive=false;updateFrame(Number(e.target.value));});
$('playButton').insertAdjacentHTML('afterend','<button id="followLive" type="button">최신</button>');
$('followLive').addEventListener('click',()=>{stopPlayback();state.followLive=true;if(state.result?.series?.time_s?.length)updateFrame(state.result.series.time_s.length-1);});
$('trendMetric').addEventListener('change',drawChart);
$('exportTrend').addEventListener('click',()=>{
  const s=state.result?.series;if(!s?.time_s?.length){window.notifyOperator?.('내보낼 데이터가 없습니다.');return;}
  if(window.nodeMonitor?.catalog){const node=window.nodeMonitor.selectedNode,metrics=[0,1,2].map(i=>window.nodeMonitor.series(i));const csv=[['time_s',...metrics.map(m=>m.tag||m.label)].join(','),...s.time_s.map((t,i)=>[t,...metrics.map(m=>Number.isFinite(m.values[i])?m.values[i]:'')].join(','))].join('\r\n');const url=URL.createObjectURL(new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`hrs-${node}-ptf.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return;}
  const keys=['time_s','vehicle_pressure_mpa','vehicle_2_pressure_mpa','vehicle_temperature_c','vehicle_2_temperature_c','nozzle_1_flow_g_s','nozzle_2_flow_g_s','total_leak_flow_g_s'];
  const csv=[keys.join(','),...s.time_s.map((_,i)=>keys.map(k=>Number.isFinite(s[k]?.[i])?s[k][i]:'').join(','))].join('\r\n');
  const url=URL.createObjectURL(new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='hrs-telemetry.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
document.querySelectorAll('.process .unit,.process .bank').forEach(node=>node.addEventListener('click',()=>window.openStationCctv?.(node.dataset.bank || node.id || 'site')));
window.addEventListener('resize',()=>{if(state.result){drawChart();drawCursor();}});
setInterval(()=>{if($('calculationMonitor').open)renderCalculationMonitor();},500);
checkHealth();
const monitorJobId = new URLSearchParams(location.search).get('job');
if (monitorJobId) window.connectStationJob(monitorJobId);
window.addEventListener('station-ready',drawChart);
['pressureKpi','temperatureKpi','socKpi'].forEach(id=>$(id).textContent='—');
['vehicle2Pressure','vehicle2Temperature','vehicle2Soc'].forEach(id=>$(id).textContent='2번 —');

// The process schematic supports keyboard selection and has no invented idle readings.
document.querySelectorAll('.flow-map .unit,.flow-map .bank').forEach(unit=>{
  unit.tabIndex=0;unit.setAttribute('role','button');unit.setAttribute('aria-label',unit.querySelector('b')?.textContent+' · CCTV 보기');
  unit.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();unit.click();}});
});
['bankHigh','bankMedium','bankLow','flowLabel','flowSplitLabel'].forEach(id=>$(id).textContent='—');
$('leakStatus').textContent='누출 데이터 대기';

$('detectorStrip').addEventListener('click',e=>{const tag=e.target.closest('[data-detector]')?.dataset.detector;if(tag)window.openStationCctv?.(tag);});
setInterval(checkHealth,30000);
$('detectorStrip').title='가상 H₂ 농도 (vol%). 누출량 기반 대리 신호이며 현장 계측값이 아닙니다.';
