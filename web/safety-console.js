/* Operator-only virtual response console. No commands leave this simulator. */
(()=>{
  const host=document.getElementById('safetyConsole');if(!host)return;
  let latest=null,lastJob='',busy=false,lastError='',lastNotice='',comparison=null,replay=null;
  const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const fmt=(value,d=1)=>value!==null&&value!==undefined&&Number.isFinite(Number(value))?Number(value).toFixed(d):'—';
  const bankName={low:'저압',medium:'중압',high:'고압'};
  const zoneName={unloading:'하역',compressor:'압축기',storage:'저장',dispenser:'충전'};
  const stageName={recognition:'상황 확인',immediate:'즉시 조치',stabilize:'안정화',restart:'복구 전 점검'};
  const recoveryName={source_removed:'원인 제거',leak_repaired:'누출 수리',tightness_test:'기밀시험',detector_test:'검지기 시험',valve_test:'밸브 기능시험',purge_complete:'퍼지',pressure_test:'단계적 재가압',supervisor_approval:'재가동 승인'};
  const button=(label,kind,target)=>`<button type="button" data-action="${esc(kind)}" data-target="${esc(target)}">${esc(label)}</button>`;
  const jobId=()=>window.getRemoteJobId?.();
  const endpoint=path=>`/api/simulations/${encodeURIComponent(jobId())}/safety${path}`;
  async function json(url,options={}){const response=await fetch(url,options);const data=await response.json();if(!response.ok)throw new Error(data.detail||`서버 오류 ${response.status}`);return data;}
  const stateText=v=>v==='confirmed'?'확인 완료':v==='failed'?'조치 실패':v==='moving'?'밸브 이동 중':v==='awaiting-flow'?'유량 확인 중':v==='commanded'?'명령 대기':v==='fault-injected'?'고장 주입':'대기';
  const evaluation=report=>!report?'':`<div class="safety-evaluation"><b>훈련 참고 점수 ${fmt(report.training_score,0)} / 100</b><span>초동 조치 지연 ${report.response_delay_s==null?'사고/조치 없음':`${fmt(report.response_delay_s)} s`}</span><span>조치 실패 ${report.failed_action_ids?.length||0}건 · 이른 복구 ${report.premature_restore_ids?.length||0}건 · 차단 재검토 ${report.possible_wrong_isolation_ids?.length||0}건 · 2차 위험 중첩 ${report.secondary_hazards?.length||0}건</span><small>${esc(report.score_note||'')}</small></div>`;
  const trainingOutput=()=>{
    if(comparison){const runs=comparison.runs||[];return `<p class="${comparison.same_fault_signature?'':'safety-error'}">${comparison.same_fault_signature?'동일 사고 입력 서명 · 대응 순서 비교':'사고 입력이 달라 결과 비교에 주의가 필요합니다.'}</p><div class="safety-comparison">${runs.map(run=>`<article><b>실행 ${esc(run.job_id)}</b><span>방출 누적 ${fmt(run.released_mass_kg,3)} kg · 최고 가스 ${fmt(run.peak_gas_volpct_h2,3)} vol%</span><span>최대 누출 ${fmt(run.peak_leak_flow_g_s,3)} g/s · ESD ${run.esd_time_s==null?'없음':`${fmt(run.esd_time_s)} s`}</span>${evaluation(run.evaluation)}</article>`).join('')}</div>`;}
    if(replay)return `${evaluation(replay.evaluation)}<p>기록 ${replay.actions.length}건 · 시점 ${replay.frames.length}개 · 슬라이더로 사고 전후 상태를 재생하세요.</p><input type="range" id="replaySlider" min="0" max="${Math.max(0,replay.frames.length-1)}" value="0"><output id="replayOutput"></output>`;
    return '조치 전후 변화와 지연 시간을 아래 사건 기록에서 확인할 수 있습니다.';
  };
  function metrics(before,after){
    if(!before||!after)return '다음 공정 샘플에서 조치 전후 수치를 비교합니다.';
    const b=before.bank_pressure_mpa||{},a=after.bank_pressure_mpa||{};
    const bank=Object.keys(a).map(key=>`${bankName[key]||key} ${fmt(b[key],2)}→${fmt(a[key],2)} MPa`).join(' · ');
    const temperature=Object.keys(after.bank_temperature_c||{}).map(key=>`${bankName[key]||key} ${fmt(before.bank_temperature_c?.[key])}→${fmt(after.bank_temperature_c[key])} °C`).join(' · ');
    const inventory=Object.keys(after.bank_mass_kg||{}).map(key=>`${bankName[key]||key} ${fmt(before.bank_mass_kg?.[key],2)}→${fmt(after.bank_mass_kg[key],2)} kg`).join(' · ');
    return `압력 ${bank}<br>온도 ${temperature}<br>재고 ${inventory}<br>유량 압축기 ${fmt(before.compressor_flow_g_s,2)}→${fmt(after.compressor_flow_g_s,2)}, 차량 1 ${fmt(before.nozzle_1_flow_g_s,2)}→${fmt(after.nozzle_1_flow_g_s,2)}, 차량 2 ${fmt(before.nozzle_2_flow_g_s,2)}→${fmt(after.nozzle_2_flow_g_s,2)} g/s<br>누출 ${fmt(before.total_leak_flow_g_s,3)}→${fmt(after.total_leak_flow_g_s,3)} g/s · 누적 ${fmt(before.released_mass_kg,3)}→${fmt(after.released_mass_kg,3)} kg · 검지 최대 ${fmt(before.gas_max_volpct_h2,3)}→${fmt(after.gas_max_volpct_h2,3)} vol% · 영향 표본 ${fmt(before.effect_radius_m)}→${fmt(after.effect_radius_m)} m`;
  }
  function render(){
    const id=jobId();
    if(!id){host.textContent='공정 모니터링을 시작하면 가상 안전설비를 조작할 수 있습니다.';return;}
    if(!latest){host.textContent=lastError||'가상 안전설비 상태를 읽는 중입니다.';return;}
    const draftRepair=host.querySelector('#repairFaultId')?.value||'';
    const draftCompare=host.querySelector('#compareJob')?.value||'';
    const draftReplayIndex=host.querySelector('#replaySlider')?.value||'0';
    const s=latest,m=s.current_metrics||{},actions=s.actions||[],valves=s.valves||{};
    const failed=actions.filter(a=>a.status==='failed');
    const activeFaults=(window.latestProcessFrame?.active_faults||[]).filter(Boolean);
    const threat=Number(m.total_leak_flow_g_s||0)>0.01||Number(m.gas_max_volpct_h2||0)>=.2||activeFaults.length>0;
    const firstAction=actions.find(a=>['operation.stop','valve.close','esd.trip'].includes(a.kind)&&a.status==='confirmed');
    const evacuation=actions.findLast?.(a=>a.kind==='personnel.evacuate'&&a.target==='storage'&&a.status==='confirmed')
      ||[...actions].reverse().find(a=>a.kind==='personnel.evacuate'&&a.target==='storage'&&a.status==='confirmed');
    const approval=actions.find(a=>a.kind==='restart.approve'&&a.status==='confirmed');
    const storageRemaining=Number(s.personnel?.storage||0),storageEvacuated=Number(s.evacuated?.storage||0);
    const storageClear=storageRemaining===0;
    const stabilizeCondition=!storageClear
      ?`저장구역 잔류 ${storageRemaining}명 대피 필요`
      :threat
        ?`저장구역 ${storageEvacuated}명 대피 완료 · 누출·가스 안정화 대기`
        :`저장구역 ${storageEvacuated}명 대피 및 누출·가스 안정화 확인`;
    const evacuationButton=storageClear
      ?'<button type="button" disabled>저장구역 대피 완료</button>'
      :button(`저장구역 ${storageRemaining}명 대피`,'personnel.evacuate','storage');
    const stages=[
      {name:'recognition',owner:'운전원',done:Boolean(m.time_s!=null),time:m.time_s,condition:'센서·영상·시나리오 확인',action:''},
      {name:'immediate',owner:'현장 책임자',done:Boolean(firstAction),time:firstAction?.completed_s,condition:'공급 정지, 적합한 차단 피드백 및 유량 확인',action:button('모든 공정 정지','operation.stop','all')},
      {name:'stabilize',owner:'안전 담당',done:!threat&&storageClear&&Boolean(evacuation),time:evacuation?.completed_s,condition:stabilizeCondition,action:evacuationButton},
      {name:'restart',owner:'관리 책임자',done:Boolean(s.recovery_approved),time:approval?.completed_s,condition:'수리·시험·퍼지·재가압 후 승인',action:button('재가동 승인','restart.approve','station')},
    ];
    const stageHtml=stages.map((row,index)=>`<article class="safety-stage ${row.done?'done':''}"><span>${String(index+1).padStart(2,'0')}</span><div><b>${stageName[row.name]}</b><small>담당 ${row.owner} · ${row.condition}</small><em>${row.done?`완료 · 모의 ${fmt(row.time)} s`:'미완료 · 성공조건 대기'}</em></div>${row.action}</article>`).join('');
    const suggestions=(s.suggested_actions||[]).map(item=>`<div><small>${esc(item.scenario)}</small>${button(item.label,item.kind,item.target)}</div>`).join('');
    const valveHtml=Object.entries(valves).map(([name,v])=>`<article class="safety-device ${v.status==='failed'?'failed':''}"><div><b>${esc(v.label)}</b><small>${esc(name)} · 명령 ${v.commanded_open?'열림':'닫힘'} → 실제 ${v.actual_open?'열림':'닫힘'} → 피드백 ${v.feedback_open?'열림':'닫힘'} · 유로 ${fmt(v.flow_fraction*100,0)}%</small><em>${stateText(v.status)}${name.startsWith('vent.')?'':` · 격리구간 ${fmt(s.line_pressure_mpa?.[name],2)} MPa`}</em></div><div class="safety-device-actions">${button('열기',name.startsWith('vent.')?'vent.open':'valve.open',name)}${button('닫기',name.startsWith('vent.')?'vent.close':'valve.close',name)}<select data-fault="${esc(name)}" aria-label="${esc(v.label)} 고장"><option value="none">정상</option><option value="stuck_open" ${v.fault==='stuck_open'?'selected':''}>열림 고착</option><option value="stuck_closed" ${v.fault==='stuck_closed'?'selected':''}>닫힘 고착</option><option value="seat_leak" ${v.fault==='seat_leak'?'selected':''}>내부 누설</option><option value="feedback_fault" ${v.fault==='feedback_fault'?'selected':''}>피드백 오류</option></select></div></article>`).join('');
    const auxHtml=[['ventilation',s.ventilation,zoneName,'환기'],['cooling',s.cooling,bankName,'냉각·살수']].map(([kind,values,labels,title])=>`<section><h4>${title}</h4><div class="safety-aux-grid">${Object.entries(values||{}).map(([name,v])=>`<div><b>${labels[name]||name}</b><span class="${v.running?'good':'bad'}">${v.running?'가동':'정지'}${v.fault?' · 고장':''}</span>${button('ON',`${kind}.on`,name)}${button('OFF',`${kind}.off`,name)}<select data-fault="${kind}.${name}"><option value="none">정상</option><option value="failure" ${v.fault?'selected':''}>고장</option></select></div>`).join('')}</div></section>`).join('');
    const zones=Object.keys(zoneName).map(zone=>`<div class="safety-zone"><b>${zoneName[zone]}</b><small>잔류 ${s.personnel[zone]}명 · 대피 ${s.evacuated[zone]}명 · ${s.access_restricted[zone]?'출입 통제':'출입 허용'} · 전원 ${s.power_isolated[zone]?'차단':'공급'}</small><div>${button('출입 통제','access.restrict',zone)}${button('대피','personnel.evacuate',zone)}${button('점화원·전원 차단','power.isolate',zone)}${button('전원 복구','power.restore',zone)}</div></div>`).join('');
    const vehicles=Object.entries(s.vehicles||{}).map(([name,count])=>`<div class="safety-zone"><b>${name==='trailer'?'튜브트레일러':name==='vehicle_1'?'차량 1':'차량 2'}</b><small>현장 ${count}대 · 대피 ${s.vehicles_evacuated?.[name]||0}대 · 연결 공정 정지와 밸브 폐쇄·유량 확인 후 이동</small>${button('차량 대피','vehicle.evacuate',name)}</div>`).join('');
    const tested=new Set(['tightness_test','detector_test','valve_test','purge_complete','pressure_test']);
    const checks=Object.entries(recoveryName).map(([key,label])=>`<div class="safety-check ${s.recovery[key]?'done':''}"><span>${s.recovery[key]?'✓':'○'} ${label}</span>${tested.has(key)?'<small>아래 시험으로 실행</small>':button(key==='leak_repaired'?'누출 없음 확인':'모의 기록','recovery.record',key)}</div>`).join('');
    const actionName={"incident.auto-resolve":'사고 입력 자동 종료'};
    const log=actions.slice(-20).reverse().map(a=>`<article class="safety-log-row ${a.status==='failed'?'failed':''}"><b>${fmt(a.issued_s,1)} s · ${esc(actionName[a.kind]||a.kind)} / ${esc(a.target)}</b><span>${stateText(a.status)}${a.completed_s==null?'':` · ${fmt(a.completed_s-a.issued_s,1)} s`}${a.note?` · ${esc(a.note)}`:''}</span><small>${metrics(a.baseline_metrics,a.after_metrics)}</small></article>`).join('')||'<p>아직 실행한 조치가 없습니다.</p>';
    host.innerHTML=`<div class="safety-overview"><div><small>현재 공정</small><b>모의 ${fmt(m.time_s)} s · 누출 ${fmt(m.total_leak_flow_g_s,3)} g/s · 가스 최고 ${fmt(m.gas_max_volpct_h2,3)} vol%</b></div><div><small>조치 상태</small><b>${actions.length}건 실행 · ${failed.length}건 실패 · ${s.esd_requested||m.esd?'ESD 차단':'운전 감시'}</b></div>${button('가상 ESD 차단','esd.trip','station')}</div>${lastNotice?`<p class="safety-notice" role="status">${esc(lastNotice)}</p>`:''}${lastError?`<p class="safety-error" role="alert">${esc(lastError)}</p>`:''}
      <div class="safety-section"><h3>단계별 대응 진행판</h3><p>현장 책임자가 조치 명령, 실제 위치 피드백, 유량·가스 추세를 각각 확인하는 가상 훈련입니다. 고장 시 다음 단계에서 잔여 위험을 다시 판단하세요.</p><div class="safety-stages">${stageHtml}</div>${failed.length?`<p class="safety-error">악화 분기 · 조치 실패 ${failed.length}건: 상·하류의 다른 차단점 선택, ESD, 대피 범위 확대와 잔여 유량 재확인을 진행하세요.</p>`:''}${suggestions?`<h4>현재 신호에 맞춘 실행 조치</h4><div class="safety-suggestions">${suggestions}</div>`:''}</div>
      <div class="safety-section"><h3>설비별 차단 · 벤트</h3><p>가상 벤트는 저장뱅크에서 지상 6 m 상향 방출구로 이어집니다. 방출 유량과 잔압, 새 위험을 확인하세요. 이 치수는 모의 가정이며 승인 설계치가 아닙니다.</p><div class="safety-vent-readings">${Object.entries(s.vent_releases||{}).map(([name,row])=>`<span>${bankName[name]} · 방출 ${fmt(row.release_flow_g_s,3)} g/s · 잔압 ${fmt(row.residual_pressure_mpa,2)} MPa · 방출구 ${fmt(row.outlet_height_m,0)} m</span>`).join('')}</div><div class="safety-valves">${valveHtml}</div></div>
      <div class="safety-section">${auxHtml}<h4>구역별 출입·대피·전원</h4><div class="safety-zones">${zones}${vehicles}</div><div class="safety-wind"><label>풍향 °<input id="virtualWindDirection" type="number" min="0" max="360" value="${fmt(s.wind_direction_deg,0)}"></label><label>풍속 m/s<input id="virtualWindSpeed" type="number" min="0" max="30" step=".1" value="${fmt(s.wind_speed_m_s,1)}"></label><button type="button" data-environment>환경 반영</button>${button('가상 대응조직 통보','responders.notify','station')}</div></div>
      <div class="safety-section"><h3>복구·재가동 잠금</h3><p>현재 사고가 끝나고 가상 시험·확인 항목을 모두 통과해야 재가동 승인과 ESD 리셋을 시도할 수 있습니다. 라인 시험과 퍼지는 뱅크 입·출구가 닫힌 상태에서 진행합니다. 벤트 감압은 위의 별도 조작입니다.</p><div class="safety-purge">라인 잔류 수소 가상 비율 · ${Object.entries(s.purge_h2_fraction||{}).map(([key,value])=>`${bankName[key]} ${fmt(Number(value)*100,2)}%`).join(' · ')}${s.purge_bank?` · ${bankName[s.purge_bank]} 퍼지 진행`:''}${s.diagnostic?` · ${esc(s.diagnostic.kind)} 시험 진행`:''}</div><div class="safety-checks">${checks}</div><label>수리할 가상 누출 ID <input id="repairFaultId" placeholder="사고 주입 목록의 event ID"></label><button type="button" data-repair>누출 수리·제거</button><div class="safety-recovery-controls">${button('저압 기밀시험','tightness.test','low')}${button('중압 기밀시험','tightness.test','medium')}${button('고압 기밀시험','tightness.test','high')}${button('검지기 자체진단','detector.test','all')}${button('밸브 피드백 시험','valve.test','all')}${button('저압 라인 퍼지','purge.run','low')}${button('중압 라인 퍼지','purge.run','medium')}${button('고압 라인 퍼지','purge.run','high')}${button('저압 단계 재가압','pressure.test','low')}${button('중압 단계 재가압','pressure.test','medium')}${button('고압 단계 재가압','pressure.test','high')}${button('재가동 승인','restart.approve','station')}</div></div>
      <div class="safety-section"><h3>훈련 기록·재생·비교</h3><div class="safety-training"><button type="button" data-replay>사건 재생표 불러오기</button><label>비교할 실행 ID <input id="compareJob" placeholder="이전 실행 ID"></label><button type="button" data-compare>두 실행 비교</button></div><div id="safetyTrainingOutput">${trainingOutput()}</div><div class="safety-log">${log}</div></div>`;
    host.querySelector('#repairFaultId').value=draftRepair;
    host.querySelector('#compareJob').value=draftCompare;
    const slider=host.querySelector('#replaySlider');if(slider){slider.value=draftReplayIndex;const show=()=>{const f=replay.frames[Number(slider.value)];host.querySelector('#replayOutput').textContent=f?`모의 ${fmt(f.time_s)} s · ${Object.entries(f.metrics.bank_pressure_mpa||{}).map(([k,v])=>`${bankName[k]} ${fmt(v)} MPa`).join(' · ')} · 누출 ${fmt(f.metrics.total_leak_flow_g_s,3)} g/s · 가스 ${fmt(f.metrics.gas_max_volpct_h2,3)} vol%`:'';};slider.addEventListener('input',show);show();}
  }
  async function refresh(){const id=jobId();if(!id){latest=null;render();return;}if(busy)return;try{const data=await json(endpoint(''));if(jobId()!==id)return;latest=data;lastJob=id;lastError='';if(!host.contains(document.activeElement)||!['INPUT','SELECT'].includes(document.activeElement.tagName))render();}catch(error){lastError=error.message;render();}}
  host.addEventListener('click',async event=>{
    const target=event.target.closest('button');if(!target||busy)return;
    const id=jobId();if(!id){lastError='공정을 먼저 시작하세요.';render();return;}
    busy=true;target.disabled=true;lastError='';
    try{
      if(target.dataset.action){const action=await window.executeVirtualSafetyAction({kind:target.dataset.action,target:target.dataset.target,label:target.textContent});lastNotice=action.kind==='personnel.evacuate'?`${zoneName[action.target]||action.target}구역 인원 대피 완료 · 잔류 인원과 안정화 조건을 갱신했습니다.`:`${target.textContent} · ${action.status==='confirmed'?'완료':'명령 접수'}`;}
      else if(target.hasAttribute('data-environment'))await json(endpoint('/environment'),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({wind_direction_deg:Number(host.querySelector('#virtualWindDirection').value),wind_speed_m_s:Number(host.querySelector('#virtualWindSpeed').value)})});
      else if(target.hasAttribute('data-repair')){const faultId=host.querySelector('#repairFaultId').value.trim();if(!faultId)throw new Error('누출 사고 ID를 입력하세요.');await window.executeVirtualSafetyAction({kind:'repair.leak',target:faultId,label:'누출 수리'});}
      else if(target.hasAttribute('data-replay')){replay=await json(endpoint('/replay'));comparison=null;}
      else if(target.hasAttribute('data-compare')){const other=host.querySelector('#compareJob').value.trim();if(!other)throw new Error('비교할 실행 ID를 입력하세요.');comparison=await json(endpoint('/compare'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({other_job_id:other})});replay=null;}
      await refreshNow();
    }catch(error){lastNotice='';lastError=error.message;render();}finally{busy=false;}
  });
  host.addEventListener('change',async event=>{
    const select=event.target.closest('[data-fault]');if(!select)return;
    const id=jobId();if(!id)return;
    try{await json(`/api/simulations/${encodeURIComponent(id)}/safety/faults/${encodeURIComponent(select.dataset.fault)}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({fault:select.value})});await refreshNow();}
    catch(error){lastError=error.message;render();}
  });
  async function refreshNow(){const id=jobId();if(!id)return;latest=await json(endpoint(''));lastJob=id;render();}
  window.addEventListener('station-safety-action',()=>setTimeout(refresh,300));
  setInterval(()=>{if(jobId()!==lastJob){latest=null;comparison=null;replay=null;lastJob=jobId();}if(document.querySelector('[data-remote-tab="safety"]')?.getAttribute('aria-selected')==='true')refresh();},1300);
})();
