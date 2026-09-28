/* SAGA answers come from the local Python service. The browser only presents them. */
(()=>{
  const $=id=>document.getElementById(id);
  const messages=[];
  let lastAt=0,lastAlarm='',busy=false,pendingAlarm=false,lastAnswer=null,lastError='',nextId=0;
  const pendingManual=[];
  const defaultQuestion='현재 공정에서 주의해야 할 센서와 HAZOP 근거를 알려줘.';
  const publicTerms=value=>String(value??'').replace(/HyRAM\+?/gi,'피해영향예측');
  function current(){const runtime=window.getStation3DState?.(),i=runtime?.index??0;return {job:runtime?.activeJobId,frame:runtime?.result?.hazop?.frames?.[i],analysis:runtime?.result?.series?.analysis?.[i],time:runtime?.result?.series?.time_s?.[i]};}
  function markdown(node,value){
    const display=publicTerms(value);
    if(!window.marked?.parse||!window.DOMPurify?.sanitize){node.textContent=display;return;}
    node.innerHTML=window.DOMPurify.sanitize(window.marked.parse(display,{gfm:true,breaks:true}),{USE_PROFILES:{html:true}});
    node.querySelectorAll('a[href]').forEach(link=>{link.target='_blank';link.rel='noopener noreferrer';});
  }
  function scrollToLatest(){const stream=$('sagaMessages');if(stream)requestAnimationFrame(()=>{stream.scrollTop=stream.scrollHeight;});}
  function appendMessage(message){
    const stream=$('sagaMessages');if(!stream)return;
    const article=document.createElement('article');article.className=`saga-message ${message.role}${message.error?' error':''}`;article.dataset.messageId=message.id;
    const label=document.createElement('div');label.className='saga-message-label';
    const speaker=document.createElement('b');speaker.textContent=message.role==='user'?'나':'SAGA';
    const meta=document.createElement('span');meta.textContent=message.meta||'';label.append(speaker,meta);
    const bubble=document.createElement('div');bubble.className='saga-bubble';
    if(message.role==='assistant')markdown(bubble,message.content);else bubble.textContent=message.content;
    article.append(label,bubble);stream.append(article);scrollToLatest();
  }
  function addMessage(role,content,meta='',error=false){
    const message={id:String(++nextId),role,content,meta,error};messages.push(message);
    if(messages.length>100)messages.shift();
    if($('sagaMessages')){if($('sagaWelcome'))$('sagaWelcome').remove();appendMessage(message);}
    return message;
  }
  function updateMessage(message,content,meta,error=false){
    message.content=content;message.meta=meta;message.error=error;
    const article=document.querySelector(`.saga-message[data-message-id="${message.id}"]`);if(!article)return;
    article.classList.toggle('error',error);article.querySelector('.saga-message-label span').textContent=meta;
    markdown(article.querySelector('.saga-bubble'),content);scrollToLatest();
  }
  function status(){
    const label=$('sagaStatus');if(label){label.textContent=busy?'분석 중…':lastError||'센서·HAZOP 연결';label.dataset.state=busy?'busy':lastError?'error':'ready';}
    const send=$('sagaSend');if(send)send.disabled=pendingManual.length>=5;
    const scenario=document.querySelector('.saga-scenario-button');if(scenario)scenario.disabled=pendingManual.length>=5;
    if($('sagaAlarmSummary'))$('sagaAlarmSummary').textContent=lastAnswer?`모의 ${Number(lastAnswer.time_s||0).toFixed(1)} s 기준\n${publicTerms(lastAnswer.answer)}`:lastError||'SAGA 분석 대기';
  }
  function chatHistory(excludeId){return messages.filter(message=>message.id!==excludeId&&!message.error&&!message.meta.endsWith('중…')&&message.meta!=='대기'&&['user','assistant'].includes(message.role)).slice(-8).map(message=>({role:message.role,content:message.content.slice(0,1200)}));}
  async function analyze(trigger='manual',question=defaultQuestion,queued=null,scenarioMode=false){
    if(busy){
      if(trigger==='alarm')pendingAlarm=true;
      else if(trigger==='manual'&&pendingManual.length<5){const user=addMessage('user',question,scenarioMode?'가상 시나리오 평가':'질문');const pending=addMessage('assistant','앞선 분석이 끝나면 답변합니다.','대기');pendingManual.push({question,user,pending,scenarioMode});status();}
      return;
    }
    const {job}=current();
    if(!job){lastError='연결된 시뮬레이션이 없습니다.';if(trigger==='manual'){addMessage('user',question,'질문');addMessage('assistant','시뮬레이션을 실행한 뒤 다시 질문해 주세요.','연결 필요',true);}status();return;}
    const history=chatHistory(queued?.user?.id);
    if(trigger==='manual'&&!queued)addMessage('user',question,scenarioMode?'가상 시나리오 평가':'질문');
    const pending=queued?.pending||addMessage('assistant',scenarioMode?'시나리오 제안·계산 중…':'분석 중…',scenarioMode?'가상 시나리오 평가 중…':trigger==='alarm'?'경보 자동 분석 중…':trigger==='periodic'?'정기 자동 분석 중…':'분석 중…');
    if(queued)updateMessage(pending,'분석 중…','분석 중…');
    busy=true;lastError='';status();
    try{
      const response=await fetch(`/api/simulations/${job}/saga-analysis`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({trigger,question,history:history.slice(-8),scenario_mode:scenarioMode})});
      const result=await response.json();if(!response.ok)throw new Error(result.detail||`SAGA 응답 ${response.status}`);
      lastAnswer=result;lastAt=Date.now();
      const source=result.scenario_mode?'가상 시나리오 평가':trigger==='alarm'?'경보 자동 분석':trigger==='periodic'?'정기 자동 분석':'답변';
      updateMessage(pending,result.answer||'SAGA가 빈 답변을 반환했습니다.',`${source} · 모의 ${Number(result.time_s||0).toFixed(1)} s · ${result.model||'SAGA'}`);
    }catch(error){lastError=`SAGA 연결/분석 불가: ${error.message}`;lastAt=Date.now();updateMessage(pending,lastError,'응답 오류',true);}
    finally{busy=false;status();if(pendingManual.length){const next=pendingManual.shift();analyze('manual',next.question,next,next.scenarioMode);}else if(pendingAlarm){pendingAlarm=false;analyze('alarm','새 경보의 센서값과 HAZOP 규칙을 검토해 주세요.');}}
  }
  function mountChat(){
    const body=$('wallSagaChat');if(!body||$('sagaMessages'))return;
    const top=document.createElement('div');top.className='saga-chat-top';
    const identity=document.createElement('div');identity.className='saga-chat-identity';identity.innerHTML='<span class="saga-avatar">S</span><div><b>SAGA 분석</b><small>센서 · HAZOP 실시간 대화</small></div>';
    const statusNode=document.createElement('span');statusNode.id='sagaStatus';statusNode.className='saga-chat-status';top.append(identity,statusNode);
    const stream=document.createElement('div');stream.id='sagaMessages';stream.className='saga-messages';stream.setAttribute('role','log');stream.setAttribute('aria-label','SAGA 대화 내용');
    const form=document.createElement('form');form.className='saga-composer';
    const input=document.createElement('textarea');input.id='sagaQuestion';input.rows=2;input.placeholder='센서, HAZOP, 사고 영향에 대해 질문하세요…';input.setAttribute('aria-label','SAGA 질문');
    input.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();form.requestSubmit();}});
    const actions=document.createElement('div');actions.className='saga-composer-actions';
    const scenario=document.createElement('button');scenario.type='button';scenario.className='saga-scenario-button';scenario.textContent='시나리오 생성·평가';scenario.title='SAGA가 현재 센서와 HAZOP를 보고 가상 누출을 제안한 뒤 피해영향을 계산합니다';
    scenario.addEventListener('click',()=>{if(pendingManual.length>=5)return;const question=input.value.trim()||'현재 센서와 HAZOP를 근거로 의미 있는 가상 누출 시나리오를 생성하고 피해영향을 비교해줘.';input.value='';analyze('manual',question,null,true);});
    const send=document.createElement('button');send.type='submit';send.id='sagaSend';send.textContent='전송 ↑';
    actions.append(scenario,send);form.append(input,actions);
    form.addEventListener('submit',event=>{event.preventDefault();const question=input.value.trim();if(!question||pendingManual.length>=5)return;input.value='';analyze('manual',question);});
    body.append(top,stream,form);
    if(messages.length){messages.forEach(appendMessage);}else{
      const welcome=document.createElement('div');welcome.id='sagaWelcome';welcome.className='saga-welcome';welcome.innerHTML='<span class="saga-avatar">S</span><h3>무엇을 분석해 드릴까요?</h3><p>현재 공정의 센서값과 HAZOP 규칙을 근거로 답변합니다. 경보와 정기 분석 결과도 이 대화에 표시됩니다.</p>';
      const suggestion=document.createElement('button');suggestion.type='button';suggestion.textContent='현재 공정에서 주의할 점 분석';suggestion.addEventListener('click',()=>analyze('manual',defaultQuestion));welcome.append(suggestion);stream.append(welcome);
    }
    status();scrollToLatest();
  }
  window.openSagaPrompt=()=>{mountChat();$('sagaQuestion')?.focus();};
  window.addEventListener('wall-mounted',mountChat);
  function frame(){
    const {job,frame:hazop,analysis}=current();if(!job||!hazop)return;
    const severity=analysis?.status||'NORMAL';
    const ruleIds=(hazop.active||[]).map(row=>row.rule_id).filter(Boolean).sort();
    const signature=severity==='NORMAL'&&ruleIds.length===0?'':`${severity}:${ruleIds.join(',')}`;
    if(signature&&signature!==lastAlarm){lastAlarm=signature;analyze('alarm','발생한 주의/경보의 센서 태그, HAZOP 규칙, 현재 센서 기준 피해영향예측 결과와 조치 우선순위를 분석해 주세요.');}
    if(!signature)lastAlarm='';
    if(Date.now()-lastAt>=30000&&!busy)analyze('periodic','현재 주요 센서값과 HAZOP DB를 검토해 운전 상태를 짧게 분석해 주세요.');
  }
  window.addEventListener('station-frame',frame);
  window.addEventListener('station-layout-ready',()=>{
    const panel=document.querySelector('.s3-incidents');if(panel){const section=document.createElement('section');section.className='saga-alarm';const h=document.createElement('h3');h.textContent='SAGA 실시간 분석';const p=document.createElement('p');p.id='sagaAlarmSummary';p.textContent='SAGA 분석 대기';section.append(h,p);panel.append(section);}
  });
})();
