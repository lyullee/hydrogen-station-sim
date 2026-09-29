/* SAGA answers come from the local Python service. The browser only presents them. */
(()=>{
  const $=id=>document.getElementById(id);
  const messages=[];
  let lastAt=0,lastAlarm='',lastAlarmAt=0,alarmJob=null,highestSeverity=0,clearSince=0,busy=false,pendingAlarm=false,lastAnswer=null,lastError='',nextId=0;
  const seenAlarmSignals=new Set();
  const autoKey='h2station.saga.autoAnalysis';
  const providerKey='h2station.saga.provider';
  const selectedProvider=()=>localStorage.getItem(providerKey)==='groq'?'groq':'service_hub';
  let autoEnabled=localStorage.getItem(autoKey)!=='off';
  let activeAutoController=null,activeTrigger=null;
  const pendingManual=[];
  const defaultQuestion='현재 공정에서 주의해야 할 센서와 설비 상태를 알려줘.';
  const suggestedQuestions=[
    ['현재 주의 신호는?', '현재 주요 센서 중 주의할 신호와 그 이유를 알려줘.'],
    ['저장뱅크 상태', '고압·중압·저압 저장뱅크 압력과 이상 여부를 비교해줘.'],
    ['압축기 상태', '압축기 입구와 출구의 압력·온도·유량을 요약해줘.'],
    ['프리쿨러 상태', '프리쿨러 출구 온도와 충전 조건을 검토해줘.'],
    ['디스펜서 비교', '디스펜서 1번과 2번의 압력·온도·유량을 비교해줘.'],
    ['가스검지기 확인', '각 구역 가스검지기의 현재 값과 주의 신호를 알려줘.'],
    ['센서 신뢰도', '현재 GOOD 품질이 아닌 센서와 분석에 미치는 영향을 알려줘.'],
    ['ESD 상태', '안전 PLC와 ESD 상태, 최근 차단 조건을 설명해줘.'],
    ['안전 상태', '현재 설비의 안전 상태와 우선 확인할 신호를 알려줘.'],
    ['공정 이상 원인', '현재 이상 징후가 있다면 가능한 원인과 확인 순서를 알려줘.'],
    ['누출 영향 평가', '현재 센서값으로 고압 저장뱅크 1 mm 가정 누출의 피해영향을 알려줘.'],
    ['차량 충전 상태', '두 차량의 충전 진행 상태와 남은 공정 위험을 알려줘.'],
    ['가상 사고 비교', '현재 센서값을 바탕으로 가상 누출 시나리오를 생성해 피해영향을 비교해줘.'],
    ['운전 요약', '현재 충전소의 운전 상태를 핵심 센서 중심으로 간결하게 요약해줘.'],
  ];
  let previousSuggestions=[];
  const publicTerms=value=>String(value??'').replace(/HyRAM\+?/gi,'피해영향예측');
  function current(){const runtime=window.getStation3DState?.(),i=runtime?.index??0;return {job:runtime?.activeJobId,frame:runtime?.result?.hazop?.frames?.[i],analysis:runtime?.result?.series?.analysis?.[i],time:runtime?.result?.series?.time_s?.[i]};}
  function markdown(node,value){
    const display=publicTerms(value);
    if(!window.marked?.parse||!window.DOMPurify?.sanitize){node.textContent=display;return;}
    node.innerHTML=window.DOMPurify.sanitize(window.marked.parse(display,{gfm:true,breaks:true}),{USE_PROFILES:{html:true}});
    node.querySelectorAll('a[href]').forEach(link=>{link.target='_blank';link.rel='noopener noreferrer';});
  }
  function impactCard(row){
    const card=document.createElement('section');card.className='saga-impact-card';
    const actual=row.calculation_basis==='ACTIVE_RELEASE_CURRENT_SENSORS'||Boolean(row.release_id);
    const title=document.createElement('header');
    const heading=document.createElement('b');heading.textContent=`${row.node_name||row.component_id||row.node_id||'설비'}${row.node_id?` · ${row.node_id}`:''}`;
    const badge=document.createElement('span');badge.textContent=String(row.release_id||'').startsWith('relief-')?'안전밸브 방출':actual?'활성 누출':'가정 누출';badge.className=actual?'actual':'hypothetical';title.append(heading,badge);card.append(title);
    const fmt=(value,digits=1)=>value!==null&&value!==undefined&&Number.isFinite(Number(value))?Number(value).toFixed(digits):'—';
    const metrics=document.createElement('div');metrics.className='saga-impact-metrics';
    const fields=[['누출유량',`${fmt(row.mass_flow_g_s,2)} g/s`],['표본 최대 열복사',`${fmt(row.maximum_heat_flux_w_m2==null?null:row.maximum_heat_flux_w_m2/1000,2)} kW/m²`],['표본 최대 과압',`${fmt(row.maximum_overpressure_pa==null?null:row.maximum_overpressure_pa/1000,2)} kPa`]];
    for(const [label,value] of fields){const cell=document.createElement('div');const name=document.createElement('small');name.textContent=label;const amount=document.createElement('strong');amount.textContent=value;cell.append(name,amount);metrics.append(cell);}card.append(metrics);
    const extent=document.createElement('p');extent.className='saga-impact-extent';
    extent.textContent=Number(row.sampled_effect_radius_m)>0?`5 kW/m² 또는 5 kPa 기준: ${fmt(row.sampled_effect_radius_m)} m 표본점 초과${Number(row.sampled_next_distance_m)>Number(row.sampled_effect_radius_m)?` · 다음 ${fmt(row.sampled_next_distance_m)} m 표본점 미달`:row.effect_range_status==='BEYOND_SAMPLED_POINTS'?' · 더 먼 거리 미평가':''} · 안전거리 아님`:row.sampled_max_distance_m==null?'표본 관측 범위 자료 없음 · 영향 반경 미확정':`5 kW/m² 또는 5 kPa 기준: ${fmt(row.sampled_max_distance_m)} m 표본점까지 미달 · 영향 반경 미확정`;
    card.append(extent);
    const basis=document.createElement('small');basis.className='saga-impact-basis';
    const sensorParts=[row.pressure_sensor&&`${row.pressure_sensor} ${fmt(row.current_pressure_mpa,2)} MPa`,row.temperature_sensor&&`${row.temperature_sensor} ${fmt(row.current_temperature_c)} °C`].filter(Boolean);
    basis.textContent=[row.scenario_id,row.orifice_diameter_mm&&`${fmt(row.orifice_diameter_mm)} mm`,...sensorParts,row.sensor_basis==='PROXY'?'대체 센서 적용':''].filter(Boolean).join(' · ');card.append(basis);
    return card;
  }
  function responseGuidancePanel(guidance,animate=false){
    const panel=document.createElement('section');panel.className='saga-response-panel';
    if(animate)panel.classList.add('saga-response-reveal');
    const header=document.createElement('header');header.className='saga-response-header';
    const heading=document.createElement('h3');heading.textContent=guidance.actual_alert?'현재 상황 · 단계별 대응':'가상 상황 · 단계별 대응';
    const count=document.createElement('span');count.textContent=`${guidance.plans.length}개 상황`;header.append(heading,count);panel.append(header);
    const intro=document.createElement('p');intro.className='saga-response-intro';intro.textContent=guidance.intro||'';panel.append(intro);
    function actionList(items){
      const list=document.createElement('ol');list.className='saga-response-actions';
      (items||[]).forEach(item=>{const row=document.createElement('li');row.textContent=item;list.append(row);});
      return list;
    }
    if(guidance.common_steps?.length){
      const common=document.createElement('div');common.className='saga-response-common';
      if(animate){common.classList.add('saga-step-reveal');common.style.animationDelay='0.12s';}
      const title=document.createElement('b');title.textContent='먼저 · 공통 초동대응';common.append(title,actionList(guidance.common_steps));panel.append(common);
    }
    const stages=[['recognition','상황 확인'],['immediate','즉시 조치'],['stabilize','안정화 확인'],['restart','재가동 전 확인'],['prevention','예방·안전관리']];
    (guidance.plans||[]).forEach((plan,index)=>{
      const card=document.createElement('article');card.className='saga-response-plan';
      if(animate){card.classList.add('saga-step-reveal');card.style.animationDelay=`${0.32+index*0.72}s`;}
      const title=document.createElement('div');title.className='saga-response-plan-title';
      const number=document.createElement('span');number.textContent=String(index+1).padStart(2,'0');
      const name=document.createElement('h4');name.textContent=plan.title||'대응 절차';title.append(number,name);card.append(title);
      if(plan.evidence?.length){const evidence=document.createElement('p');evidence.className='saga-response-evidence';evidence.textContent=`판단 근거 · ${plan.evidence.join(' / ')}`;card.append(evidence);}
      const timeline=document.createElement('div');timeline.className='saga-response-timeline';
      stages.forEach(([key,label],stepIndex)=>{
        if(!plan[key]?.length)return;
        const stage=document.createElement('section');stage.className=`saga-response-stage stage-${key}`;
        if(animate){stage.classList.add('saga-step-reveal');stage.style.animationDelay=`${0.55+index*0.72+stepIndex*0.13}s`;}
        const stageTitle=document.createElement('div');stageTitle.className='saga-response-stage-title';
        const badge=document.createElement('span');badge.textContent=String(stepIndex+1).padStart(2,'0');
        const text=document.createElement('b');text.textContent=label;stageTitle.append(badge,text);
        stage.append(stageTitle,actionList(plan[key]));timeline.append(stage);
      });
      card.append(timeline);
      if(plan.sources?.length){
        const sources=document.createElement('div');sources.className='saga-response-sources';sources.append('참고 자료 · ');
        plan.sources.forEach((source,sourceIndex)=>{
          if(sourceIndex)sources.append(' · ');
          if(typeof source.url==='string'&&source.url.startsWith('https://')){
            const link=document.createElement('a');link.href=source.url;link.target='_blank';link.rel='noopener noreferrer';link.textContent=source.title||'자료';sources.append(link);
          }else sources.append(source.title||'자료');
        });card.append(sources);
      }
      panel.append(card);
    });
    return panel;
  }
  function renderBubble(node,message,animate=false){
    markdown(node,message.analysisAnswer||message.content);
    if(message.role!=='assistant')return;
    const risk=message.riskAssessment;
    if(risk&&risk.status!=='NORMAL'){
      const assessment=document.createElement('section');assessment.className='saga-risk-assessment';assessment.dataset.severity=String(risk.status).toLowerCase();
      const label=document.createElement('b');label.textContent=`현재 위험도 · ${{CRITICAL:'긴급',WARNING:'경고',ADVISORY:'주의'}[risk.status]||risk.status}`;
      const detail=document.createElement('span');detail.textContent=(risk.findings||[]).slice(0,2).join(' / ')||'현재 센서 및 설비 신호 기준';
      assessment.append(label,detail);node.prepend(assessment);
    }
    if(message.showImpact){
      const calculated=(message.impactResults||[]).filter(row=>row.calculation_status==='calculated').slice(0,3);
      if(calculated.length){
        const group=document.createElement('section');group.className='saga-impact-group';
        const title=document.createElement('div');title.className='saga-impact-heading';title.textContent='피해영향예측 · 현재 센서 기준';group.append(title);
        calculated.forEach(row=>group.append(impactCard(row)));
        const note=document.createElement('p');note.className='saga-impact-note';note.textContent='표본 관측점 계산이며 실제 누출 여부와 현장 안전반경을 뜻하지 않습니다. 가정 누출은 실제 사고가 아닙니다.';group.append(note);
        if(risk&&risk.status!=='NORMAL')node.querySelector('.saga-risk-assessment').after(group);else node.prepend(group);
      }
    }
    if(message.responseGuidance?.plans?.length)node.append(responseGuidancePanel(message.responseGuidance,animate));
  }
  function scrollToLatest(){const stream=$('sagaMessages');if(stream)requestAnimationFrame(()=>{stream.scrollTop=stream.scrollHeight;});}
  function appendMessage(message){
    const stream=$('sagaMessages');if(!stream)return;
    const article=document.createElement('article');article.className=`saga-message ${message.role}${message.error?' error':''}`;article.dataset.messageId=message.id;
    const label=document.createElement('div');label.className='saga-message-label';
    const speaker=document.createElement('b');speaker.textContent=message.role==='user'?'나':'SAGA';
    const meta=document.createElement('span');meta.textContent=message.meta||'';label.append(speaker,meta);
    const bubble=document.createElement('div');bubble.className='saga-bubble';
    if(message.role==='assistant')renderBubble(bubble,message);else bubble.textContent=message.content;
    article.append(label,bubble);stream.append(article);scrollToLatest();
  }
  function addMessage(role,content,meta='',error=false){
    const message={id:String(++nextId),role,content,meta,error};messages.push(message);
    if(messages.length>100)messages.shift();
    if($('sagaMessages')){if($('sagaWelcome'))$('sagaWelcome').remove();appendMessage(message);}
    return message;
  }
  function updateMessage(message,content,meta,error=false,result=null,animate=false){
    message.content=content;message.meta=meta;message.error=error;message.analysisAnswer=result?.analysis_answer||null;message.responseGuidance=result?.response_guidance||null;message.showImpact=Boolean(result?.show_impact_results);message.impactResults=result?.impact_results||[];message.riskAssessment=result?.risk_assessment||null;
    const article=document.querySelector(`.saga-message[data-message-id="${message.id}"]`);if(!article)return;
    article.classList.toggle('error',error);article.querySelector('.saga-message-label span').textContent=meta;
    article.classList.remove('streaming');renderBubble(article.querySelector('.saga-bubble'),message,animate);scrollToLatest();
  }
  function status(){
    const label=$('sagaStatus');if(label){label.textContent=busy?'분석 중…':lastError||'실시간 센서 연결';label.dataset.state=busy?'busy':lastError?'error':'ready';}
    const toggle=$('sagaAutoToggle');if(toggle){toggle.textContent=autoEnabled?'정기 분석 ON':'정기 분석 OFF';toggle.setAttribute('aria-pressed',String(autoEnabled));toggle.title='정기 분석을 끄면 반복 분석이 중단됩니다. 새 주의·경보 또는 위험도 상승 시에만 1회 자동 평가합니다.';}
    const send=$('sagaSend');if(send)send.disabled=pendingManual.length>=5;
    const scenario=document.querySelector('.saga-scenario-button');if(scenario)scenario.disabled=pendingManual.length>=5;
    if($('sagaAlarmSummary')){
      const liveAlert=['ADVISORY','WARNING','CRITICAL'].includes(current().analysis?.status)||Boolean(current().frame?.active?.length);
      $('sagaAlarmSummary').textContent=lastAnswer&&(lastAnswer.trigger==='manual'||liveAlert)?`모의 ${Number(lastAnswer.time_s||0).toFixed(1)} s 기준\n${publicTerms(lastAnswer.analysis_answer||lastAnswer.answer)}`:lastError||'현재 활성 주의·경보 없음';
    }
  }
  function chatHistory(excludeId){return messages.filter(message=>message.id!==excludeId&&!message.error&&!message.meta.endsWith('중…')&&message.meta!=='대기'&&['user','assistant'].includes(message.role)).slice(-8).map(message=>({role:message.role,content:(message.analysisAnswer||message.content).slice(0,1200)}));}
  async function analyze(trigger='manual',question=defaultQuestion,queued=null,scenarioMode=false){
    if(trigger==='periodic'&&!autoEnabled)return;
    if(busy){
      if(trigger==='alarm'){pendingAlarm=true;if(activeTrigger==='periodic')activeAutoController?.abort();}
      else if(trigger==='manual'&&pendingManual.length<5){const user=addMessage('user',question,scenarioMode?'가상 시나리오 평가':'질문');const pending=addMessage('assistant','앞선 분석이 끝나면 답변합니다.','대기');pendingManual.push({question,user,pending,scenarioMode});status();}
      return;
    }
    const {job}=current();
    if(!job){lastError='연결된 시뮬레이션이 없습니다.';if(trigger==='manual'){addMessage('user',question,'질문');addMessage('assistant','시뮬레이션을 실행한 뒤 다시 질문해 주세요.','연결 필요',true);}status();return;}
    const history=chatHistory(queued?.user?.id);
    if(trigger==='manual'&&!queued)addMessage('user',question,scenarioMode?'가상 시나리오 평가':'질문');
    const pending=queued?.pending||addMessage('assistant',scenarioMode?'시나리오 제안·계산 중…':'분석 중…',scenarioMode?'가상 시나리오 평가 중…':trigger==='alarm'?'경보 자동 분석 중…':trigger==='periodic'?'정기 자동 분석 중…':'분석 중…');
    if(queued)updateMessage(pending,'분석 중…','분석 중…');
    busy=true;activeTrigger=trigger;lastError='';status();
    const controller=trigger==='manual'?null:new AbortController();if(controller)activeAutoController=controller;
    try{
      let draft='',paintScheduled=false,streamFinished=false;
      const paintDraft=()=>{paintScheduled=false;if(streamFinished||current().job!==job)return;const article=document.querySelector(`.saga-message[data-message-id="${pending.id}"]`);if(!article)return;article.classList.add('streaming');markdown(article.querySelector('.saga-bubble'),draft);scrollToLatest();};
      const result=await window.streamStationAnalysis(`/api/simulations/${job}/saga-analysis/stream`,
        {trigger,question,history:history.slice(-8),scenario_mode:scenarioMode,direct:!scenarioMode,provider:selectedProvider()},
        {signal:controller?.signal,onStatus:text=>{if(!draft)updateMessage(pending,text,trigger==='alarm'?'경보·피해영향 계산 중…':'분석 중…');},
         onToken:text=>{draft+=text;if(!paintScheduled){paintScheduled=true;requestAnimationFrame(paintDraft);}}});
      if(controller?.signal.aborted||current().job!==job)return;
      if(!draft){
        const article=document.querySelector(`.saga-message[data-message-id="${pending.id}"]`);
        if(article){article.classList.add('streaming');await window.revealStationText(result.analysis_answer||result.answer||'',text=>{markdown(article.querySelector('.saga-bubble'),text);scrollToLatest();},()=>current().job===job&&!controller?.signal.aborted);}
      }
      streamFinished=true;
      lastAnswer=result;lastAt=Date.now();
      const calculated=(result.impact_results||[]).filter(row=>row.calculation_status==='calculated');
      // A normal/status answer has no new consequence result. Keep the last
      // explicit hypothetical assessment instead of blinking its dome away.
      if(result.scenario_mode||calculated.length){
        const prior=window.stationImpactResults?.jobId===job?window.stationImpactResults.results||[]:[];
        const hypothetical=calculated.filter(row=>!row.release_id);
        const retained=hypothetical.length||result.scenario_mode?hypothetical:prior.filter(row=>!row.release_id);
        window.stationImpactResults={jobId:job,results:[...retained,...calculated.filter(row=>row.release_id)]};
        window.dispatchEvent(new Event('station-impact-results'));
      }
      const source=result.scenario_mode?'가상 시나리오 평가':trigger==='alarm'?'경보 자동 분석':trigger==='periodic'?'정기 자동 분석':'답변';
      updateMessage(pending,result.answer||'SAGA가 빈 답변을 반환했습니다.',`${source} · 모의 ${Number(result.time_s||0).toFixed(1)} s · ${result.model||'SAGA'}`,false,result,true);
    }catch(error){if(current().job!==job)return;if(error.name==='AbortError'){updateMessage(pending,'자동 분석을 중지했습니다.','중지됨');}else{lastError=`SAGA 연결/분석 불가: ${error.message}`;lastAt=Date.now();updateMessage(pending,lastError,'응답 오류',true);}}
    finally{if(current().job!==job)return;if(activeAutoController===controller)activeAutoController=null;busy=false;activeTrigger=null;status();if(pendingAlarm){pendingAlarm=false;analyze('alarm','새 경보의 센서값과 설비 상태, 피해영향예측 결과 및 위험도를 분석해 주세요.');}else if(pendingManual.length){const next=pendingManual.shift();analyze('manual',next.question,next,next.scenarioMode);}}
  }
  function rotateSuggestions(){
    const tray=$('sagaSuggestions');if(!tray)return;
    const pool=suggestedQuestions.map((_,index)=>index).filter(index=>!previousSuggestions.includes(index));
    for(let i=pool.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[pool[i],pool[j]]=[pool[j],pool[i]];}
    previousSuggestions=pool.slice(0,3);tray.replaceChildren();
    previousSuggestions.forEach(index=>{const [label,question]=suggestedQuestions[index],button=document.createElement('button');button.type='button';button.textContent=label;button.title=question;button.addEventListener('click',()=>analyze('manual',question));tray.append(button);});
  }
  function mountChat(){
    const body=$('wallSagaChat');if(!body||$('sagaMessages'))return;
    const top=document.createElement('div');top.className='saga-chat-top';
    const identity=document.createElement('div');identity.className='saga-chat-identity';identity.innerHTML='<span class="saga-avatar">S</span><div><b>SAGA 분석</b><small>센서 · 설비 실시간 대화</small></div>';
    const controls=document.createElement('div');controls.className='saga-top-controls';
    const provider=document.createElement('select');provider.className='saga-provider-select';provider.setAttribute('aria-label','시나리오 생성 제공자 선택');provider.title='시나리오 생성·평가에만 사용합니다. 실시간 관제와 센서 분석은 직답 API를 사용합니다.';provider.innerHTML='<option value="service_hub">Service Hub</option><option value="groq">Groq</option>';provider.value=selectedProvider();provider.addEventListener('change',()=>{localStorage.setItem(providerKey,provider.value);document.querySelectorAll('.saga-provider-select').forEach(select=>{select.value=provider.value;});});controls.append(provider);
    const toggle=document.createElement('button');toggle.id='sagaAutoToggle';toggle.type='button';toggle.className='saga-auto-toggle';toggle.addEventListener('click',()=>{autoEnabled=!autoEnabled;localStorage.setItem(autoKey,autoEnabled?'on':'off');if(!autoEnabled&&activeTrigger==='periodic')activeAutoController?.abort();if(autoEnabled)lastAt=0;frame();status();});
    const expand=document.createElement('button');expand.id='sagaExpand';expand.type='button';expand.className='saga-expand';expand.setAttribute('aria-expanded','false');expand.setAttribute('aria-controls','wallSagaChat');expand.textContent='대화 확대';expand.addEventListener('click',()=>{const expanded=document.querySelector('.wall-board')?.classList.toggle('saga-expanded');expand.setAttribute('aria-expanded',String(Boolean(expanded)));expand.textContent=expanded?'대화 축소':'대화 확대';window.dispatchEvent(new Event('wall-resize'));});
    const statusNode=document.createElement('span');statusNode.id='sagaStatus';statusNode.className='saga-chat-status';controls.append(toggle,expand,statusNode);top.append(identity,controls);
    const stream=document.createElement('div');stream.id='sagaMessages';stream.className='saga-messages';stream.setAttribute('role','log');stream.setAttribute('aria-label','SAGA 대화 내용');
    const form=document.createElement('form');form.className='saga-composer';
    const suggestions=document.createElement('div');suggestions.id='sagaSuggestions';suggestions.className='saga-suggestions';suggestions.setAttribute('aria-label','추천 질문');
    const input=document.createElement('textarea');input.id='sagaQuestion';input.rows=2;input.placeholder='센서, 설비 상태, 사고 영향에 대해 질문하세요…';input.setAttribute('aria-label','SAGA 질문');
    input.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();form.requestSubmit();}});
    const actions=document.createElement('div');actions.className='saga-composer-actions';
    const scenario=document.createElement('button');scenario.type='button';scenario.className='saga-scenario-button';scenario.textContent='시나리오 생성·평가';scenario.title='SAGA가 현재 센서와 운전 상태를 보고 가상 누출을 제안한 뒤 피해영향을 계산합니다';
    scenario.addEventListener('click',()=>{if(pendingManual.length>=5)return;const question=input.value.trim()||'현재 센서값으로 의미 있는 가상 누출 시나리오를 생성하고 피해영향을 비교해줘.';input.value='';analyze('manual',question,null,true);});
    const send=document.createElement('button');send.type='submit';send.id='sagaSend';send.textContent='전송 ↑';
    actions.append(scenario,send);form.append(suggestions,input,actions);
    form.addEventListener('submit',event=>{event.preventDefault();const question=input.value.trim();if(!question||pendingManual.length>=5)return;input.value='';analyze('manual',question);});
    body.append(top,stream,form);
    if(messages.length){messages.forEach(appendMessage);}else{
      const welcome=document.createElement('div');welcome.id='sagaWelcome';welcome.className='saga-welcome';welcome.innerHTML='<span class="saga-avatar">S</span><h3>무엇을 분석해 드릴까요?</h3><p>정기 분석은 상단에서 켜고 끌 수 있습니다. OFF일 때도 새 주의·경보와 위험도 상승은 한 번 자동 평가합니다.</p>';
      const suggestion=document.createElement('button');suggestion.type='button';suggestion.textContent='현재 공정에서 주의할 점 분석';suggestion.addEventListener('click',()=>analyze('manual',defaultQuestion));welcome.append(suggestion);stream.append(welcome);
    }
    rotateSuggestions();status();scrollToLatest();
  }
  window.openSagaPrompt=()=>{mountChat();$('sagaQuestion')?.focus();};
  window.addEventListener('wall-mounted',mountChat);
  function resetChatForJob(job){
    activeAutoController?.abort();activeAutoController=null;busy=false;activeTrigger=null;pendingAlarm=false;pendingManual.length=0;
    messages.length=0;lastAnswer=null;lastError='';lastAt=Date.now();
    alarmJob=job;lastAlarm='';lastAlarmAt=0;highestSeverity=0;clearSince=0;seenAlarmSignals.clear();
    window.stationImpactResults={jobId:job,results:[]};window.dispatchEvent(new Event('station-impact-results'));
    const stream=$('sagaMessages');if(stream){const welcome=document.createElement('div');welcome.className='saga-welcome';welcome.textContent='새 공정에 연결되었습니다. 현재 센서와 설비 상태를 질문할 수 있습니다.';stream.replaceChildren(welcome);}
    status();
  }
  function frame(){
    const {job,frame:hazop,analysis}=current();if(!job)return;
    if(job!==alarmJob)resetChatForJob(job);
    const severity=analysis?.status||'NORMAL';
    const ruleIds=(hazop?.active||[]).map(row=>row.rule_id).filter(Boolean).sort();
    const runtime=window.getStation3DState?.(),open=runtime?.result?.series?.process_operations?.[runtime.index]?.relief_open||{};
    const relief=Object.keys(open).filter(key=>open[key]).sort();
    const faults=[...(runtime?.result?.series?.active_faults?.[runtime.index]||[])].sort();
    const detectedFlames=analysis?.fire_detection?.detector_tags||[];
    const signature=severity==='NORMAL'&&ruleIds.length===0&&!relief.length&&!faults.length&&!detectedFlames.length?'':`${severity}:${ruleIds.join(',')}:${relief.join(',')}:${faults.join(',')}:${detectedFlames.join(',')}`;
    const now=Date.now();
    if(!signature){
      if(!clearSince)clearSince=now;
      if(lastAlarm&&now-clearSince>=3000){lastAlarm='';highestSeverity=0;seenAlarmSignals.clear();status();}
    }else clearSince=0;
    const severityRank={NORMAL:0,ADVISORY:1,WARNING:2,CRITICAL:3}[severity]||0;
    const signals=[...ruleIds.map(id=>`rule:${id}`),...relief.map(id=>`relief:${id}`),...faults.map(id=>`fault:${id}`),...detectedFlames.map(id=>`flame:${id}`)];
    const newEvent=[...relief.map(id=>`relief:${id}`),...faults.map(id=>`fault:${id}`)].some(id=>!seenAlarmSignals.has(id));
    const newFlame=detectedFlames.some(id=>!seenAlarmSignals.has(`flame:${id}`));
    const newRule=ruleIds.some(id=>!seenAlarmSignals.has(`rule:${id}`));
    if(signature&&(!lastAlarm||severityRank>highestSeverity||newEvent||newFlame||newRule&&now-lastAlarmAt>=10000||autoEnabled&&now-lastAlarmAt>=30000)){
      lastAlarm=signature;lastAlarmAt=now;highestSeverity=Math.max(highestSeverity,severityRank);
      signals.forEach(id=>seenAlarmSignals.add(id));
      const question=relief.length?'안전밸브가 열렸습니다. 개방 위치와 압력, 방출량, 현재 피해영향예측 결과, 조치 우선순위를 분석해 주세요.':faults.some(f=>f.startsWith('external-fire:'))?'외부 화재 시나리오 입력 위치와 화염검지기 신호를 구분하고, 센서값·피해영향예측 결과·대응 우선순위를 분석해 주세요.':'발생한 주의/경보의 센서값, 현재 피해영향예측 결과와 조치 우선순위를 분석해 주세요.';
      analyze('alarm',question);
    }
    if(!signature&&autoEnabled&&now-lastAt>=30000&&!busy)analyze('periodic','현재 주요 센서값과 설비 상태를 짧게 분석해 주세요.');
  }
  window.addEventListener('station-frame',frame);
  setInterval(rotateSuggestions,20000);
  window.addEventListener('station-layout-ready',()=>{
    const panel=document.querySelector('.s3-incidents');if(panel){const section=document.createElement('section');section.className='saga-alarm';const h=document.createElement('h3');h.textContent='SAGA 실시간 분석';const p=document.createElement('p');p.id='sagaAlarmSummary';p.textContent='SAGA 분석 대기';section.append(h,p);panel.append(section);}
  });
})();
