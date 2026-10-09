/* One sensor, its risk basis, and a focused SAGA conversation share one workspace. */
(()=>{
  const node=(tag,className='',content='')=>{const item=document.createElement(tag);if(className)item.className=className;if(content)item.textContent=content;return item;};
  const runtime=()=>window.getStation3DState?.();
  const currentFrame=()=>{const state=runtime();return state?.result?.hazop?.frames?.[state.index??0]||null;};
  const displayTime=()=>{const state=runtime();return state?.result?.series?.time_s?.[state.index??0];};
  const currentSignal=tag=>currentFrame()?.signals?.[tag]||null;
  const issueMap=frame=>{
    const issues=new Map();
    for(const rule of frame?.active||[]){
      if(!rule.active||!rule.sensor_id)continue;
      const retained=rule.state==='LATCHED'||rule.state==='ALARM_HOLD';
      const issue=retained?{label:'경보 이력',rank:2}:rule.severity==='TRIP'?{label:'위험',rank:3}:{label:'경보',rank:2};
      const existing=issues.get(rule.sensor_id);
      if(existing?.rank>=issue.rank){existing.ruleIds.push(rule.rule_id);continue;}
      issues.set(rule.sensor_id,{...issue,ruleIds:[...(existing?.ruleIds||[]),rule.rule_id]});
    }
    for(const [tag,signal] of Object.entries(frame?.signals||{})){
      if(['BAD','STALE','FAULT','INVALID'].includes(signal?.quality)&&!issues.has(tag))
        issues.set(tag,{label:'신호 이상',rank:1,ruleIds:[]});
    }
    return issues;
  };
  const issueKey=issue=>issue?`${issue.label}:${issue.ruleIds.slice().sort().join(',')}`:'';
  const issueSignature=issues=>[...issues].map(([tag,issue])=>`${tag}:${issueKey(issue)}`).sort().join('|');
  const reading=signal=>typeof signal?.value==='number'&&Number.isFinite(signal.value)?
    (signal.unit==='bool'?(signal.value>=0.5?'화염 감지':'정상 · 화염 없음'):`${signal.value.toFixed(signal.unit==='g/s'?2:3)} ${signal.unit||''}`):'—';
  const stateLabel=rule=>rule.active?(['LATCHED','ALARM_HOLD'].includes(rule.state)?'경보 이력 유지':'현재 경보'):rule.state==='UNKNOWN'?'판정 불가':rule.state==='PENDING'?'지속시간 확인':rule.state==='INACTIVE'?'운전조건 대기':'정상 범위';
  function renderMarkdown(target,text){
    if(window.marked?.parse&&window.DOMPurify?.sanitize){target.innerHTML=window.DOMPurify.sanitize(window.marked.parse(text,{gfm:true,breaks:true}),{USE_PROFILES:{html:true}});}
    else target.textContent=text;
    target.querySelectorAll('a[href]').forEach(link=>{link.target='_blank';link.rel='noopener noreferrer';});
    target.querySelectorAll('blockquote').forEach(block=>{
      const content=block.textContent||'';
      block.dataset.tone=/위험|즉시|차단|대피|경보/.test(content)?'danger':/주의|확인|불확실|가정/.test(content)?'caution':/피해영향|계산|관측|근거/.test(content)?'evidence':'safe';
    });
  }
  function formatStage(title,items){
    if(!items?.length)return null;
    const section=node('section','sensor-response-stage');section.append(node('h5','',title));
    const list=node('ol');items.forEach(text=>list.append(node('li','',text)));section.append(list);return section;
  }
  window.mountSensorWorkbench=body=>{
    const dialog=document.getElementById('workspaceDialog');dialog.classList.add('sensor-workspace');body.classList.add('sensor-workbench');
    let catalog=null,selected='',lastQuestion='',closed=false,epoch=0,analysisSequence=0,detailController=null,analysisController=null,analysisTimer=null,observedJob=runtime()?.activeJobId||null,lastIssueSignature='',listRefreshTimer=null,lastValuePaint=0;
    const left=node('aside','sensor-browser'),middle=node('section','sensor-detail'),right=node('section','sensor-assistant');body.append(left,middle,right);
    const listHead=node('div','sensor-browser-head');listHead.append(node('b','','센서 목록'),node('small','sensor-count','불러오는 중'));left.append(listHead);
    const search=node('input','sensor-search');search.type='search';search.placeholder='태그·설비·위치 검색';search.setAttribute('aria-label','센서 검색');left.append(search);
    const issueToggle=node('label','sensor-issue-toggle');
    const issueCheck=node('input');issueCheck.type='checkbox';issueCheck.checked=true;issueCheck.setAttribute('aria-label','이상 센서만 표시');
    const issueCopy=node('span');issueCopy.append(node('b','','이상 센서만'),node('small','','경보 · 위험 · 신호 이상'));
    issueToggle.append(issueCheck,issueCopy);left.append(issueToggle);
    const filters=node('div','sensor-filters');left.append(filters);
    const list=node('div','sensor-browser-list');left.append(list);
    const detailIntro=node('div','sensor-detail-placeholder','센서를 선택하면 현재 신호와 위험분석결과를 표시합니다.');middle.append(detailIntro);
    const assistantHeader=node('div','sensor-assistant-head');assistantHeader.append(node('div','','SAGA · 선택 센서 분석'));
    const sensorProviderKey='h2station.sensor-assistant.provider';
    const selectedSensorProvider=()=>{
      const saved=localStorage.getItem(sensorProviderKey)??localStorage.getItem('h2station.saga.provider');
      return saved==='groq'?'groq':'service_hub';
    };
    const provider=node('select','saga-provider-select sensor-assistant-provider');provider.setAttribute('aria-label','센서 분석 LLM 제공자 선택');provider.title='선택 센서 분석 모델만 바꿉니다. 메인 대화와 8090 SAGA 설정은 유지됩니다.';provider.innerHTML='<option value="service_hub">Service Hub</option><option value="groq">Groq</option>';provider.value=selectedSensorProvider();provider.addEventListener('change',()=>{localStorage.setItem(sensorProviderKey,provider.value);document.querySelectorAll('.sensor-assistant-provider').forEach(select=>{select.value=provider.value;});});assistantHeader.append(provider);
    const deepDive=node('button','sensor-rerun sensor-deep-dive','상세 분석');deepDive.type='button';deepDive.disabled=true;assistantHeader.append(deepDive);
    const rerun=node('button','sensor-rerun','다시 분석');rerun.type='button';rerun.disabled=true;assistantHeader.append(rerun);right.append(assistantHeader);
    const assistantMeta=node('p','sensor-assistant-meta','센서를 선택하면 자동으로 분석합니다.');right.append(assistantMeta);
    const transcript=node('div','sensor-assistant-transcript');transcript.setAttribute('role','log');transcript.setAttribute('aria-live','polite');right.append(transcript);
    const form=node('form','sensor-assistant-form');const question=node('input');question.type='text';question.maxLength=1200;question.placeholder='선택 센서에 관해 추가 질문…';question.setAttribute('aria-label','선택 센서 추가 질문');
    const send=node('button','','전송');send.type='submit';form.append(question,send);right.append(form);

    const nodeById=()=>new Map((catalog?.nodes||[]).map(item=>[item.node_id,item['설비_라인']||item.node_id]));
    function visibleSensors(issues=issueMap(currentFrame())){
      const names=nodeById(),query=search.value.trim().toLowerCase(),kind=filters.dataset.kind||'ALL';
      // Keep the selected row mounted when an alarm clears. Removing and
      // reselecting it on every threshold transition made the whole workbench flash.
      return (catalog?.sensors||[]).filter(item=>(!issueCheck.checked||issues.has(item.sensor_id)||item.sensor_id===selected)&&
        (kind==='ALL'||item.sensor_id.startsWith(kind))&&
        `${item.sensor_id} ${item['설치_측정위치']||''} ${names.get(item.node_id)||''}`.toLowerCase().includes(query))
        .sort((a,b)=>issueCheck.checked?(issues.get(b.sensor_id)?.rank||0)-(issues.get(a.sensor_id)?.rank||0):0);
    }
    function renderList(){
      if(!catalog)return;
      const names=nodeById(),issues=issueMap(currentFrame()),sensors=visibleSensors(issues);list.replaceChildren();
      listHead.querySelector('small').textContent=issueCheck.checked?`이상 ${sensors.length}건 · 전체 ${catalog.sensors.length}`:`${sensors.length} / ${catalog.sensors.length}`;
      if(!sensors.length){list.append(node('p','sensor-browser-empty',issueCheck.checked?
        (currentFrame()?'현재 조건에 해당하는 이상 센서가 없습니다.':'운전 데이터가 들어오면 이상 센서가 여기에 표시됩니다.'):
        '일치하는 센서가 없습니다.'));return;}
      let lastNode='';
      sensors.forEach(item=>{
        if(item.node_id!==lastNode){list.append(node('div','sensor-node-heading',`${item.node_id} · ${names.get(item.node_id)||''}`));lastNode=item.node_id;}
        const button=node('button','sensor-list-item');button.type='button';button.dataset.sensorId=item.sensor_id;button.classList.toggle('selected',item.sensor_id===selected);
        const heading=node('span','sensor-list-heading');heading.append(node('b','',item.sensor_id),node('span','sensor-list-reading',reading(currentSignal(item.sensor_id))));button.append(heading);
        const issue=issues.get(item.sensor_id);if(issue){button.dataset.issue=issue.label;button.dataset.issueKey=issueKey(issue);button.append(node('span','sensor-list-issue',issue.label));}
        button.append(node('small','',item['설치_측정위치']||''));button.dataset.quality=currentSignal(item.sensor_id)?.quality||'UNKNOWN';
        button.addEventListener('click',()=>selectSensor(item.sensor_id));list.append(button);
      });
    }
    function refreshValues(){
      if(closed)return;
      const now=performance.now();
      if(now-lastValuePaint<180)return;
      lastValuePaint=now;
      const job=runtime()?.activeJobId||null;
      if(job!==observedJob){
        observedJob=job;
        const nextIssues=issueMap(currentFrame());lastIssueSignature=issueSignature(nextIssues);
        renderList();
        const next=visibleSensors(nextIssues)[0]?.sensor_id;
        if(issueCheck.checked&&!nextIssues.has(selected)){if(next)selectSensor(next);else clearSelection();}
        else if(selected)selectSensor(selected);
        else if(!issueCheck.checked&&next)selectSensor(next);
        return;
      }
      const issues=issueMap(currentFrame());
      const signature=issueSignature(issues);
      if(signature!==lastIssueSignature){
        lastIssueSignature=signature;
        // Debounce structural list changes. Live values below continue to update,
        // but the selected detail and LLM transcript are never remounted here.
        clearTimeout(listRefreshTimer);
        listRefreshTimer=setTimeout(()=>{listRefreshTimer=null;if(!closed)renderList();},650);
      }
      list.querySelectorAll('[data-sensor-id]').forEach(button=>{const signal=currentSignal(button.dataset.sensorId);button.querySelector('.sensor-list-reading').textContent=reading(signal);button.dataset.quality=signal?.quality||'UNKNOWN';});
      const live=middle.querySelector('.sensor-live-value');if(live&&selected){const signal=currentSignal(selected);live.textContent=reading(signal);const quality=middle.querySelector('.sensor-quality');if(quality){quality.dataset.quality=signal?.quality||'UNKNOWN';quality.textContent=signal?.quality==='GOOD'?'정상 수신':signal?.quality||'신호 대기';}}
    }
    for(const [kind,label] of [['ALL','전체'],['PT-','압력'],['TT-','온도'],['FT-','유량'],['GD-','가스'],['FD-','화염']]){
      const button=node('button','',label);button.type='button';button.dataset.kind=kind;button.setAttribute('aria-pressed',String(kind==='ALL'));
      button.addEventListener('click',()=>{filters.dataset.kind=kind;filters.querySelectorAll('button').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));renderList();});filters.append(button);
    }
    filters.dataset.kind='ALL';search.addEventListener('input',renderList);
    issueCheck.addEventListener('change',()=>{
      renderList();
      if(issueCheck.checked){
        const issues=issueMap(currentFrame());
        if(!issues.has(selected)){const next=visibleSensors(issues)[0]?.sensor_id;if(next)selectSensor(next);else clearSelection();}
      }else if(!selected&&catalog?.sensors?.length)selectSensor(visibleSensors()[0]?.sensor_id||catalog.sensors[0].sensor_id);
    });
    function clearSelection(){
      epoch++;analysisSequence++;clearTimeout(analysisTimer);analysisTimer=null;detailController?.abort();analysisController?.abort();selected='';lastQuestion='';
      transcript.replaceChildren();rerun.disabled=true;deepDive.disabled=true;assistantMeta.textContent='이상 센서를 선택하면 자동으로 분석합니다.';
      middle.replaceChildren(node('p','sensor-detail-placeholder','현재 선택할 이상 센서가 없습니다. 전체 센서를 보려면 왼쪽 스위치를 끄세요.'));
    }
    function scenarioCard(rule){
      const target=node('article','sensor-scenario-card');
      const status=node('div','sensor-rule-status');status.dataset.active='true';status.append(node('b','',stateLabel(rule)),node('span','',rule.scenario));target.append(status);
      const facts=node('dl','sensor-rule-facts');
      for(const [name,value] of [['판정 기준',`${rule.expression} ${rule.operator} ${rule.threshold} ${rule.unit}`],['지속 조건',`${rule.persistence_s} s`],['현재 판정값',typeof rule.evaluated_value==='number'?`${rule.evaluated_value.toFixed(3)} ${rule.unit}`:'판정값 대기'],['판정 상태',rule.state==='LATCHED'||rule.state==='ALARM_HOLD'?'현재 재검출 미확인 · 경보 유지':null],['원인 후보',rule.cause],['사고 전개 조건',rule.progression],['판단 한계',rule.diagnostic_limit]]){
        if(value==null||value==='')continue;const row=node('div');row.append(node('dt','',name),node('dd','',String(value)));facts.append(row);
      }target.append(facts);
      if(rule.active&&rule.executable_actions?.length)window.mountVirtualActionButtons?.(target,rule.executable_actions);
      const guidance=rule.response_guidance||{};
      if(Object.keys(guidance).length){
        const steps=node('details','sensor-scenario-actions');steps.open=true;
        steps.append(node('summary','','이 시나리오의 단계별 대응·안전관리'));
        for(const [name,key] of [['상황 확인','recognition'],['즉시 조치','immediate'],['안정화 확인','stabilize'],['재가동 전 확인','restart'],['예방·안전관리','prevention']]){
          const stage=formatStage(name,guidance[key]);if(stage)steps.append(stage);
        }
        target.append(steps);
      }
      return target;
    }
    function planSteps(plans,key){
      const seen=new Set(),items=[];
      for(const plan of plans)for(const step of plan[key]||[]){
        if(seen.has(step))continue;seen.add(step);items.push(`${plan.title} · ${step}`);
      }
      return items;
    }
    function appendSources(payload,plans){
      const keys=[...new Set(plans.flatMap(plan=>plan.sources||[]))];if(!keys.length)return;
      const sources=node('div','sensor-rule-sources','근거 자료 · ');
      keys.forEach((key,index)=>{const source=payload.response_sources?.[key];if(!source)return;if(index)sources.append(' · ');const link=node('a','',source.title);link.href=source.url;link.target='_blank';link.rel='noopener noreferrer';sources.append(link);});middle.append(sources);
    }
    function appendDataUsed(target,used){
      if(!used||typeof used!=='object')return;
      const tags=Array.isArray(used.signals)?used.signals.filter(Boolean):[];
      const impact=Array.isArray(used.impact)?used.impact:[];
      const forecast=used.station_pressure_forecast&&typeof used.station_pressure_forecast==='object'?used.station_pressure_forecast:null;
      const stationCalibration=used.station_calibration&&typeof used.station_calibration==='object'?used.station_calibration:null;
      const rechargeDynamics=used.station_recharge_dynamics&&typeof used.station_recharge_dynamics==='object'?used.station_recharge_dynamics:null;
      const stationData=used.station_data&&typeof used.station_data==='object'?used.station_data:null;
      const stationIntegrated=used.station_side_integrated_validation&&typeof used.station_side_integrated_validation==='object'?used.station_side_integrated_validation:null;
      const publicEndpoint=used.public_endpoint_benchmark&&typeof used.public_endpoint_benchmark==='object'?used.public_endpoint_benchmark:null;
      const publicInventory=used.public_evidence_inventory?.public_experimental_benchmarks&&typeof used.public_evidence_inventory.public_experimental_benchmarks==='object'?used.public_evidence_inventory.public_experimental_benchmarks:null;
      if(!tags.length&&!impact.length&&!forecast&&!stationCalibration&&!rechargeDynamics&&!stationData&&!stationIntegrated&&!publicEndpoint&&!publicInventory)return;
      const english=window.stationLocale?.language?.()==='en';
      const details=node('details','sensor-data-used');
      details.append(node('summary','',english?'Data used':'사용 데이터'));
      const parts=[];
      if(tags.length)parts.push(`${english?'signals':'센서'}: ${tags.join(', ')}`);
      if(impact.length)parts.push(`${english?'impact':'피해영향'}: ${impact[0]||'—'}${impact[1]!=null?` (${impact[1]})`:''}`);
      if(forecast)parts.push(`${english?'forecast':'압력예측'}: ${forecast.status||'—'}${forecast.bank?` · ${forecast.bank}`:''}`);
      if(stationCalibration){const mode=stationCalibration.status==='active'?(english?'applied':'적용'):(stationCalibration.status==='reference_defaults'?(english?'reference defaults':'기준값'):(english?'requested but unavailable':'요청됐지만 사용 불가'));const profile=stationCalibration.profile_id&&stationCalibration.profile_id!=='reference_defaults'?stationCalibration.profile_id:(stationCalibration.available_profile_id?`${stationCalibration.available_profile_id} · ${english?'opt-in':'선택 적용 가능'}`:'—');parts.push(`${english?'station calibration':'실측 보정'}: ${mode} · ${profile}`);}
      if(rechargeDynamics){const mode=rechargeDynamics.status==='active'?(english?'applied':'적용'):(english?'reference defaults':'기준값');parts.push(`${english?'recharge dwell':'재충전 대기'}: ${mode}`);}
      if(stationData){const rows=stationData.deduplicated_rows!=null?`${(Number(stationData.deduplicated_rows)/1e6).toFixed(2)}M ${english?'rows':'행'}`:'—';const cycles=stationData.pressure_cycles!=null?`${Number(stationData.pressure_cycles).toLocaleString()} ${english?'pressure cycles':'압력 사이클'}`:'—';const loop=stationData.full_loop_validation?(english?'full-loop validated':'full-loop 검증'):(english?'station-side only':'station-side 한정');parts.push(`${english?'station data':'실측 station 데이터'}: ${stationData.csv_files||'—'} CSV · ${rows} · ${cycles} · ${loop}`);}
      if(stationIntegrated){const checks=[stationIntegrated.pressure_boundary_holdout&&(english?'pressure boundary':'압력 경계'),stationIntegrated.cascade_sequence_holdout&&(english?'cascade sequence':'캐스케이드 순서'),stationIntegrated.recharge_pressure_forecast_holdout&&(english?'recharge forecast':'재충전 예측')].filter(Boolean);const mae=stationIntegrated.recharge_forecast_mae_mpa!=null?` · MAE ${Number(stationIntegrated.recharge_forecast_mae_mpa).toFixed(3)} MPa`:'';const negative=stationIntegrated.lifecycle_counter_alignment_negative_retained?(english?' · lifecycle counter negative retained':' · lifecycle 카운터 음성 결과 유지') : '';parts.push(`${english?'measured station-side holdout':'실측 station-side holdout'}: ${checks.length?checks.join(', '):(english?'none':'없음')}${mae}${negative} · ${english?'full-loop locked':'full-loop 잠금'}`);}
      if(publicEndpoint){const cases=publicEndpoint.case_count!=null?`${publicEndpoint.case_count} ${english?'endpoint cases':'종점 사례'}`:'—';const scope=publicEndpoint.full_loop_validation?(english?'full-loop validated':'full-loop 검증'):(english?'endpoint-only · no full-loop':'종점 표만 · full-loop 아님');parts.push(`${english?'public dispenser benchmark':'공개 디스펜서 벤치마크'}: ${cases} · ${scope}`);}
      if(publicInventory){const contexts=Array.isArray(publicInventory.aggregate_operating_context)?publicInventory.aggregate_operating_context:[];const fast=contexts.find(item=>item?.id==='NREL_HD_FAST_FLOW_2024_REPORT')?.aggregate||{};const reference=fast.mass_transfer_kg!=null&&fast.peak_mass_flow_g_s!=null?`${fast.mass_transfer_kg} kg · ${fast.peak_mass_flow_g_s} g/s`:`${contexts.length} ${english?'aggregate sources':'개 집계 출처'}`;parts.push(`${english?'public experiment context':'공개 실험 집계'}: ${reference} · ${english?'operating-range context only':'운영범위 참고 전용'}`);}
      details.append(node('p','',parts.join(' · ')));target.append(details);
    }
    function renderDetail(payload){
      if(closed||payload.sensor.sensor_id!==selected)return;
      middle.replaceChildren();
      const hero=node('div','sensor-detail-hero');const eyebrow=node('small','',`${payload.sensor.node_id} · ${payload.node['설비_라인']||'설비'}`);
      const title=node('div','sensor-detail-title');title.append(node('h3','',payload.sensor.sensor_id),node('span','sensor-quality',payload.signal?.quality==='GOOD'?'정상 수신':payload.signal?.quality||'신호 대기'));title.querySelector('.sensor-quality').dataset.quality=payload.signal?.quality||'UNKNOWN';
      const value=node('strong','sensor-live-value',reading(payload.signal));hero.append(eyebrow,title,value,node('p','',payload.sensor['설치_측정위치']||''));middle.append(hero);
      const meta=node('div','sensor-detail-meta');for(const [key,value] of [['센서 유형',payload.sensor['종류']||'—'],['신호 출처',payload.mapping?.origin||'모의 신호'],['데이터 품질',payload.signal?.quality||'대기'],['모의 시각',`${Number(payload.time_s||0).toFixed(1)} s`]]){const cell=node('div');cell.append(node('small','',key),node('b','',value));meta.append(cell);}middle.append(meta);
      middle.append(node('h3','sensor-risk-heading','위험분석결과 및 대응방안'));
      const rules=payload.rules||[],active=rules.filter(rule=>rule.active),related=payload.related_active_rules||[],signalIssue=payload.sensor_status==='SIGNAL_ISSUE';
      const currentAlerts=active.filter(rule=>rule.state==='TRIGGER');
      const gas=payload.gas_signal_evidence,release=payload.simulated_release_evidence;
      const observed=gas?.hydrogen_observed?`수소 농도 ${Number(gas.value_volpct_h2).toFixed(3)} vol% 관측${gas.alarm_threshold_exceeded?' · 경보 기준 초과':' · 경보 기준 미만'}`:'';
      const releasing=[Number(release?.physical_leak_g_s)>0.001?`모의 공정 누출 ${Number(release.physical_leak_g_s).toFixed(3)} g/s 진행 중`:'',Number(release?.relief_discharge_g_s)>0.001?`안전밸브 방출 ${Number(release.relief_discharge_g_s).toFixed(3)} g/s 진행 중`:''].filter(Boolean).join(' · ');
      const quick=transcript.querySelector('.sensor-chat-quick');
      if(quick){
        const retained=active.length-currentAlerts.length;
        quick.textContent=[observed,releasing,`${currentAlerts.length?`현재 경보 ${currentAlerts.length}건`:retained?`경보 이력 ${retained}건`:'현재 경보 기준 미도달'}`,related.length?`관련 구역 경보·이력 ${related.length}건`:null].filter(Boolean).join(' · ')+'. 상세 판정과 대응은 가운데에서 바로 확인할 수 있습니다.';
      }
      const summary=node('div','sensor-scenario-summary');summary.dataset.status=active.length||related.length?'alert':signalIssue||observed||releasing?'signal':'normal';
      summary.append(node('b','',currentAlerts.length?`현재 경보 ${currentAlerts.length}건${active.length>currentAlerts.length?` · 유지 이력 ${active.length-currentAlerts.length}건`:''}`:active.length?`경보 이력 유지 ${active.length}건`:related.length?`선택 센서 정상 · 관련 구역 경보·이력 ${related.length}건`:signalIssue?'센서 신호 품질 확인 필요':releasing?'모의 공정 방출 진행 중':observed?'수소 농도 관측 · 경보 기준 미만':'현재 정상 범위'),
        node('span','',[observed,releasing,active.length?`현재값과 유지 중인 경보 이력을 구분해 확인합니다. 이 센서의 ${rules.length}개 조건 중 ${active.length}개가 유지 중입니다.`:
          related.length?'선택 센서의 현재값과 다른 센서의 경보 상태를 구분해 확인합니다.':signalIssue?'공정 사고는 확정되지 않았습니다. 계측 상태를 먼저 확인합니다.':`${rules.length}개 시나리오를 감시 중입니다. 현재 비상대응 대상은 없습니다.`].filter(Boolean).join(' · ')));middle.append(summary);
      if(active.length){
        const cards=node('div','sensor-scenario-list');active.forEach(rule=>cards.append(scenarioCard(rule)));middle.append(cards);
        if(active.length===1)middle.append(node('p','sensor-risk-caption','현재 활성 판정은 1건입니다. 원인 후보는 복수일 수 있으므로 같은 설비의 압력·온도·유량·가스 신호를 교차 확인합니다.'));
      }else if(rules.length){
        const watch=node('details','sensor-watch-conditions');watch.append(node('summary','','감시 중인 시나리오와 기준 보기'));
        rules.forEach(rule=>{
          const item=node('section','sensor-watch-item');item.append(node('b','',`${rule.scenario} · ${rule.expression} ${rule.operator} ${rule.threshold} ${rule.unit}`));
          const safe=formatStage('예방·안전관리',rule.response_guidance?.prevention||[]);if(safe)item.append(safe);watch.append(item);
        });middle.append(watch);
      }
      if(related.length){
        const relatedSection=node('div','sensor-related-alert');relatedSection.append(node('b','',`관련 구역의 다른 센서에서 ${related.length}개 경보·이력이 유지 중입니다.`));
        related.forEach(rule=>relatedSection.append(scenarioCard(rule)));middle.append(relatedSection);
      }
      const planIds=[...new Set(active.length?
        [...active,...related].map(rule=>rule.response_plan_id):
        signalIssue?['sensor_fault',...related.map(rule=>rule.response_plan_id)]:[...rules,...related].map(rule=>rule.response_plan_id))];
      const plans=planIds.map(id=>payload.response_plans?.[id]).filter(Boolean).sort((a,b)=>(b.priority||0)-(a.priority||0));
      if(!active.length){
        middle.append(node('h4','sensor-response-heading',signalIssue?'계측 확인과 안전관리':'예방·안전관리'));
        if(signalIssue){const stage=formatStage('계측 확인',planSteps(plans,'recognition'));if(stage)middle.append(stage);}
        const stage=formatStage('상시 관리',planSteps(plans,'prevention'));if(stage)middle.append(stage);
        if(!plans.length)middle.append(node('p','sensor-risk-caption','연결된 예방 절차가 없습니다. 센서 품질과 운전 추세를 확인하세요.'));
      }
      appendSources(payload,plans);
    }
    async function askSensor(extraQuestion='',snapshotTime=displayTime()){
      const job=runtime()?.activeJobId,tag=selected;if(!tag)return;
      if(extraQuestion)lastQuestion=extraQuestion;
      clearTimeout(analysisTimer);analysisTimer=null;
      analysisController?.abort();analysisController=new AbortController();const signal=analysisController.signal,selection=epoch,sequence=++analysisSequence;
      const prompt=extraQuestion||`${tag}의 현재 상태와 관련 시나리오를 함께 분석해줘.`;
      transcript.append(node('div','sensor-chat-question',prompt));
      const answer=node('div','sensor-chat-answer loading','SAGA가 선택 센서와 연결 신호를 분석하고 있습니다…');transcript.append(answer);transcript.scrollTop=transcript.scrollHeight;
      assistantMeta.textContent=`${tag} · 분석 요청 중`;rerun.disabled=true;deepDive.disabled=true;
      if(!job){answer.classList.remove('loading');answer.textContent='시뮬레이션이 연결되면 이 센서를 자동 분석할 수 있습니다.';assistantMeta.textContent='연결된 시뮬레이션 없음';return;}
      try{
        let draft='',paintScheduled=false,streamFinished=false;
        const paintDraft=()=>{paintScheduled=false;if(streamFinished||closed||selection!==epoch||sequence!==analysisSequence)return;answer.classList.remove('loading');answer.classList.add('typing');answer.textContent=draft;transcript.scrollTop=transcript.scrollHeight;};
        const result=await window.streamStationAnalysis(`/api/simulations/${encodeURIComponent(job)}/assistants/sensors/${encodeURIComponent(tag)}/stream`,
          {question:extraQuestion,time_s:Number.isFinite(snapshotTime)?snapshotTime:null,provider:selectedSensorProvider(),language:window.stationLocale?.language()||'ko'},
          {signal,onStatus:text=>{if(!draft)answer.textContent=text;},onToken:text=>{draft+=text;if(!paintScheduled){paintScheduled=true;requestAnimationFrame(paintDraft);}}});
        if(closed||selection!==epoch||sequence!==analysisSequence)return;
        if(!draft){answer.classList.remove('loading');answer.classList.add('typing');await window.revealStationText(result.answer||'분석 결과가 없습니다.',text=>{answer.textContent=text;transcript.scrollTop=transcript.scrollHeight;},()=>!closed&&selection===epoch&&sequence===analysisSequence&&!signal.aborted);}
        streamFinished=true;
        if(closed||selection!==epoch||sequence!==analysisSequence)return;
        answer.classList.remove('loading','typing');assistantMeta.textContent=`${tag} · 모의 ${Number(result.time_s||0).toFixed(1)} s · ${result.model||'SAGA'}`;rerun.disabled=false;deepDive.disabled=false;renderMarkdown(answer,result.answer||'분석 결과가 없습니다.');appendDataUsed(answer,result.data_used);transcript.scrollTop=transcript.scrollHeight;
      }catch(error){if(error.name==='AbortError'||closed||selection!==epoch||sequence!==analysisSequence)return;answer.classList.remove('loading','typing');answer.classList.add('error');answer.textContent=`분석을 표시할 수 없습니다: ${error.message}`;assistantMeta.textContent='SAGA 연결 상태 확인 필요';rerun.disabled=false;deepDive.disabled=false;}
    }
    async function selectSensor(tag){
      if(closed||!catalog?.sensors?.some(item=>item.sensor_id===tag))return;
      epoch++;analysisSequence++;clearTimeout(analysisTimer);analysisTimer=null;detailController?.abort();analysisController?.abort();detailController=new AbortController();selected=tag;lastQuestion='';
      list.querySelectorAll('.sensor-list-item').forEach(button=>button.classList.toggle('selected',button.dataset.sensorId===tag));
      middle.replaceChildren(node('p','sensor-detail-placeholder',`${tag} 현재 신호와 판단 기준을 불러오는 중…`));transcript.replaceChildren(node('div','sensor-chat-quick','현재 신호와 경보 상태를 확인하는 중…'));assistantMeta.textContent=`${tag} · 자동 분석 준비`;rerun.disabled=true;deepDive.disabled=true;
      const job=runtime()?.activeJobId,selection=epoch,snapshotTime=displayTime();
      if(job){
        const query=Number.isFinite(snapshotTime)?`?time_s=${encodeURIComponent(snapshotTime)}`:'';
        fetch(`/api/simulations/${encodeURIComponent(job)}/sensors/${encodeURIComponent(tag)}${query}`,{signal:detailController.signal})
          .then(async response=>{const data=await response.json();if(!response.ok)throw new Error(data.detail||`센서 조회 ${response.status}`);return data;})
          .then(data=>{if(!closed&&selection===epoch)renderDetail(data);})
          .catch(error=>{if(error.name!=='AbortError'&&!closed&&selection===epoch)middle.replaceChildren(node('p','sensor-detail-placeholder',`센서 정보를 불러올 수 없습니다: ${error.message}`));});
      }else middle.replaceChildren(node('p','sensor-detail-placeholder','시뮬레이션을 연결하면 현재값과 위험분석결과를 표시합니다.'));
      analysisTimer=setTimeout(()=>{analysisTimer=null;if(!closed&&selection===epoch)askSensor('',snapshotTime);},220);
    }
    rerun.addEventListener('click',()=>askSensor(lastQuestion));
    deepDive.addEventListener('click',()=>askSensor(`${selected}의 현재 상태, 여러 관련 시나리오, 피해영향 계산의 가정과 한계, 대응 우선순위를 근거와 함께 상세히 분석해줘.`));
    form.addEventListener('submit',event=>{event.preventDefault();const text=question.value.trim();if(!text||!selected)return;question.value='';askSensor(text);});
    window.addEventListener('station-frame',refreshValues);
    (async()=>{
      try{
        catalog=window.nodeMonitor?.catalog||await fetch('/api/hazop/catalog').then(response=>{if(!response.ok)throw new Error('센서 목록 조회 실패');return response.json();});
        if(closed)return;lastIssueSignature=issueSignature(issueMap(currentFrame()));renderList();
        const preferred=visibleSensors()[0]?.sensor_id;
        const nodeId=window.nodeMonitor?.selectedNode;
        const initial=preferred||(!issueCheck.checked?(catalog.sensors.find(item=>item.node_id===nodeId&&item.sensor_id.startsWith('PT-'))?.sensor_id||catalog.sensors[0]?.sensor_id):null);
        if(initial)selectSensor(initial);
      }catch(error){if(!closed)list.replaceChildren(node('p','sensor-browser-empty',error.message));}
    })();
    return ()=>{closed=true;epoch++;analysisSequence++;clearTimeout(analysisTimer);clearTimeout(listRefreshTimer);detailController?.abort();analysisController?.abort();window.removeEventListener('station-frame',refreshValues);dialog.classList.remove('sensor-workspace');body.classList.remove('sensor-workbench');};
  };
})();
