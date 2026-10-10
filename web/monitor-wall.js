// Presentation adapter: all readings use the selected simulation frame.
(() => {
  const $ = id => document.getElementById(id);
  const make = (tag, className, html='') => { const el=document.createElement(tag);el.className=className;el.innerHTML=html;return el; };
  const number = (v,d=1) => Number.isFinite(v)?v.toFixed(d):'—';
  function fit() {
    const w=document.documentElement.clientWidth,h=document.documentElement.clientHeight,scale=Math.min(w/1600,h/900);
    for(const [key,value] of Object.entries({'--wall-scale':scale,'--wall-left':`${(w/scale-1600)/2}px`,'--wall-top':`${(h/scale-900)/2}px`}))document.documentElement.style.setProperty(key,value);
    window.dispatchEvent(new Event('wall-resize'));
  }
  window.addEventListener('resize',fit);document.addEventListener('fullscreenchange',fit);fit();
  function mount() {
    if($('wallBoard'))return;
    const panel=$('station3d');if(!panel)return;
    document.body.classList.add('wall-monitor');
    const board=make('div','wall-board');board.id='wallBoard';document.body.prepend(board);
    const header=document.querySelector('.masthead'),nav=document.querySelector('.side-nav'),right=header.querySelector('.masthead-right');
    header.insertBefore(nav,right);right.append($('monitorButton'),$('remoteLink'));
    const fullscreen=make('button','wall-fullscreen','⛶ <span>전체 모니터</span>');fullscreen.id='wallFullscreen';fullscreen.type='button';right.append(fullscreen);
    fullscreen.addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{window.notifyOperator?.('브라우저 전체화면(F11)을 사용하세요. 화면 맞춤은 자동 유지됩니다.');}});
    document.addEventListener('fullscreenchange',()=>{const active=document.fullscreenElement===document.documentElement;fullscreen.querySelector('span').textContent=active?'전체 모니터 종료':'전체 모니터';fullscreen.setAttribute('aria-pressed',String(active));});
    const processes=[['trailer_supply','트레일러 공급'],['pressure_recharge','압력 보완'],['vehicle_1','차량 1 충전'],['vehicle_2','차량 2 충전']];
    const processRail=processes.map(([key,label])=>`<div class="wall-process-chip" data-wall-process="${key}" data-state="off"><span>${label}</span><b>정지</b></div>`).join('');
    const overview=make('section','wall-overview',`<div class="wall-connection"></div><div class="wall-process-rail" aria-label="공정별 실시간 상태">${processRail}</div><div><span>가스 최대</span><b id="wallGas">—</b><small>vol%</small></div><div><span>안전 PLC</span><b id="wallEsd">대기</b></div><div><span>활성 사고</span><b id="wallFaults">—</b></div>`);
    overview.firstElementChild.append(document.querySelector('.side-nav-live'),$('connectionStatus'));overview.append($('systemBadge'));
    const footer=document.querySelector('body > footer');footer.classList.add('wall-footer');
    board.append(header,overview,panel,footer);
    // Retain bound DOM nodes and detail panels, including their event handlers.
    const archive=make('div','wall-archive');panel.append(archive);
    archive.append(document.querySelector('.s3-equipment-grid'),document.querySelector('.s3-incidents'),document.querySelector('.chart-panel'),document.querySelector('.event-panel'));
    document.querySelector('.control-room-shell').hidden=true;
    const visual=panel.querySelector('.s3-visual-column'),surface=panel.querySelector('.s3-visual-surface');
    visual.prepend(panel.querySelector('.s3-head'));
    const selection=panel.querySelector('.s3-selection-slot');surface.append(selection);
    const trends=make('section','wall-trends','<div class="wall-trend-title"><b>실시간 추세</b><small>최근 120초 · 모델 시간</small><span><i></i>차량 1 <i></i>차량 2</span><button type="button" data-nav="trends">이력 / CSV ↗</button></div>'+['압력 · MPa','온도 · °C','유량 · g/s'].map((label,i)=>`<article><header>${label}<b id="wallTrendValue${i}">—</b></header><canvas id="wallTrend${i}" aria-label="${label} 실시간 추세" role="img"></canvas></article>`).join(''));
    visual.append(trends);
    const sidebar=panel.querySelector('.s3-sidebar'),analysis=panel.querySelector('.analysis-row'),detectors=$('detectorStrip');
    const storage=make('section','wall-card wall-storage','<header><h2>저장 뱅크</h2><span>압력 · MPa</span></header>'+[['high','H','고압'],['medium','M','중압'],['low','L','저압']].map(([key,tag,label])=>`<div class="wall-bank"><span class="wall-bank-tag">${tag}</span><div><span>${label} 저장 뱅크</span><small id="wallBankState-${key}">대기</small><div class="wall-bar"><i id="wallBankBar-${key}"></i></div></div><b id="wallBank-${key}">—</b></div>`).join(''));
    const process=make('section','wall-card wall-machinery','<header><h2>압축기 · 프리쿨러</h2><span>실시간 공정</span></header><div class="wall-process-values"><div><small>압축기 운전</small><b id="wallCompressor">대기</b></div><div><small>재충전 뱅크</small><b id="wallRecharge">—</b></div><div><small>냉각 출구 1 / 2 · °C</small><b id="wallCooler">— / —</b></div></div>');
    const dispensers=make('section','wall-card wall-dispensers','<header><h2>디스펜서</h2><span>DUAL H70</span></header><div class="wall-dispenser-grid">'+[1,2].map(n=>`<article><header><span>0${n} <b>차량 ${n}</b></span><small id="wallDispStatus${n}">대기</small></header><div class="wall-pressure"><b id="wallPressure${n}">—</b><small>MPa</small></div><div class="wall-disp-secondary"><span><b id="wallTemp${n}">—</b> °C</span><span><b id="wallDispFlow${n}">—</b> g/s</span></div><div class="wall-soc"><div class="wall-bar"><i id="wallSocBar${n}"></i></div><span id="wallSoc${n}">—</span><small>% SOC</small></div></article>`).join('')+'</div>');
    const gas=make('section','wall-card wall-gas','<header><h2>가스·화염 감시</h2><span>가상 검지 · 모델 추정</span></header>');gas.append(detectors);gas.insertAdjacentHTML('beforeend','<div class="wall-gas-foot"><span>가스 <b id="wallDetectorCount">— / 15</b> · 화염 <b id="wallFlameCount" title="감지 수 / 수신 수">— / 9</b></span><button type="button" data-nav="sensors">센서 전체 ↗</button></div>');
    const saga=make('section','wall-saga-chat');saga.id='wallSagaChat';saga.setAttribute('aria-label','SAGA 센서·설비 채팅');
    sidebar.replaceChildren(analysis,storage,process,dispensers,gas,saga);
    analysis.tabIndex=0;analysis.setAttribute('role','button');analysis.setAttribute('aria-label','현재 경보와 센서 분석 보기');analysis.addEventListener('click',()=>window.navigateMonitor?.(document.body.dataset.alertState==='incident'?'hazop':'alarms'));analysis.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();analysis.click();}});
    // Stop controls belong to the remote; the overview remains read-only.
    selection.setAttribute('aria-label','선택 설비 정보');surface.setAttribute('aria-label','3D와 공정 흐름 공통 화면');
    let renderTimer=null,renderPending=false,lastRenderAt=0;
    const scheduleRender=(immediate=false)=>{
      const now=performance.now(),wait=Math.max(0,120-(now-lastRenderAt));
      if(immediate||wait===0){if(renderTimer){clearTimeout(renderTimer);renderTimer=null;}renderPending=false;lastRenderAt=now;render();return;}
      if(renderPending)return;
      renderPending=true;renderTimer=setTimeout(()=>{renderTimer=null;renderPending=false;lastRenderAt=performance.now();render();},wait);
    };
    window.addEventListener('station-frame',()=>scheduleRender());
    window.addEventListener('wall-resize',()=>scheduleRender(true));
    render();lastRenderAt=performance.now();fit();
    window.dispatchEvent(new Event('wall-mounted'));
  }
  function render() {
    if(!$('wallBoard'))return;
    const runtime=window.getStation3DState?.(),s=runtime?.result?.series,i=runtime?.index??0,has=Boolean(s?.time_s?.length),at=k=>has?s[k]?.[i]:undefined;
    const put=(id,v)=>$(id).textContent=v,esd=at('esd'),faults=at('active_faults')||[];
    put('wallEsd',has?(esd?'차단 / ESD':'대기 / READY'):'대기');put('wallFaults',has?`${faults.length}건`:'—');
    const activities=at('process_activity')||runtime?.lastFrame?.process_activity||{},settings=at('process_operations')?.settings||runtime?.lastFrame?.process_operations?.settings||{};
    for(const key of ['trailer_supply','pressure_recharge','vehicle_1','vehicle_2']){
      const chip=document.querySelector(`[data-wall-process="${key}"]`),activity=activities[key],requested=Boolean(settings[key]);
      const bankOver=['low','medium','high'].some(bank=>{
        const pressure=s?.bank_pressure_mpa?.[bank]?.[i],target=settings[`recharge_target_${bank}_mpa`];
        return Number.isFinite(pressure)&&Number.isFinite(target)&&pressure>target+.05;
      });
      const vehiclePressure=key==='vehicle_1'?at('vehicle_pressure_mpa'):at('vehicle_2_pressure_mpa');
      const vehicleOver=Number.isFinite(vehiclePressure)&&Number.isFinite(settings[`${key}_target_pressure_mpa`])&&vehiclePressure>settings[`${key}_target_pressure_mpa`]+.05;
      const overTarget=(key==='vehicle_1'||key==='vehicle_2')
        ?settings[`${key}_auto_stop`]===false&&vehicleOver
        :settings.recharge_auto_stop===false&&bankOver;
      const baseState=activity?.state||(!has?'off':requested?'pending':'off');
      const state=requested&&!esd&&baseState!=='blocked'&&overTarget?'overfill':baseState;
      chip.dataset.state=state;
      chip.querySelector('b').textContent=state==='overfill'?'설정 목표 초과':state==='flowing'?`${number(Number(activity.flow_g_s),1)} g/s`:state==='waiting'?'흐름 대기':state==='blocked'?'안전 차단':state==='auto-stopped'?'자동 종료':state==='pending'?'요청 반영 중':'정지';
      chip.title=state==='overfill'?`${key} · 목표 초과 운전 · ${number(Number(activity?.flow_g_s),2)} g/s`:activity?.reason?`${key} · ${activity.reason}`:'';
    }
    const detectorValues=at('gas_detectors')||{},ds=Object.values(detectorValues).filter(d=>d?.quality==='GOOD'&&Number.isFinite(d.value));put('wallGas',number(ds.length?Math.max(...ds.map(d=>d.value)):undefined,2));put('wallDetectorCount',`${ds.length} / ${Math.max(15,Object.keys(detectorValues).length)}`);
    const flameValues=at('flame_detectors')||{},fs=Object.values(flameValues).filter(d=>d?.quality==='GOOD'&&Number.isFinite(d.value));
    put('wallFlameCount',`${fs.filter(d=>d.value>=.5).length} / ${fs.length}`);
    for(const key of ['high','medium','low']){const v=has?s.bank_pressure_mpa?.[key]?.[i]:undefined;put(`wallBank-${key}`,number(v));put(`wallBankState-${key}`,!has?'미수신':at('recharge_bank')===key?'재충전':at('dispatch_bank')===key||at('dispatch_bank_2')===key?'토출 중':'대기');$(`wallBankBar-${key}`).style.width=`${Math.min(100,Math.max(0,(v||0)/100*100))}%`;}
    put('wallCompressor',has?(at('recharge_bank')?'재충전 중':'대기'):'미수신');put('wallRecharge',at('recharge_bank')?.toUpperCase()||'—');
    const signals=runtime?.result?.hazop?.frames?.[i]?.signals||{};
    const signal=id=>signals[id]?.quality==='GOOD'?signals[id].value:undefined;
    put('wallCooler',`${number(signal('TT-1201'))} / ${number(signal('TT-1601'))}`);
    for(const n of [1,2]){const suffix=n===1?'':'_2',flow=at(`nozzle_${n}_flow_g_s`),soc=at(n===1?'soc_percent':'vehicle_2_soc_percent');put(`wallPressure${n}`,number(at(`vehicle${suffix}_pressure_mpa`)));put(`wallTemp${n}`,number(at(`vehicle${suffix}_temperature_c`)));put(`wallDispFlow${n}`,number(flow));put(`wallSoc${n}`,number(soc));$(`wallSocBar${n}`).style.width=`${Math.max(0,Math.min(100,soc||0))}%`;put(`wallDispStatus${n}`,!has?'미수신':esd?'ESD 차단':flow>.01?'충전 중':'대기');}
    drawTrends();
  }
  function drawTrends(){
    if(!$('wallTrend0'))return;
    const runtime=window.getStation3DState?.(),s=runtime?.result?.series,index=runtime?.index??0,times=s?.time_s||[],end=times[index];
    const definitions=[['vehicle_pressure_mpa','vehicle_2_pressure_mpa'],['vehicle_temperature_c','vehicle_2_temperature_c'],['nozzle_1_flow_g_s','nozzle_2_flow_g_s']];
    definitions.forEach((keys,n)=>{
      const canvas=$(`wallTrend${n}`),rect=canvas.getBoundingClientRect(),w=canvas.clientWidth,h=canvas.clientHeight;if(!w||!h)return;
      const pixelWidth=Math.max(1,Math.round(rect.width*devicePixelRatio)),pixelHeight=Math.max(1,Math.round(rect.height*devicePixelRatio));
      if(canvas.width!==pixelWidth||canvas.height!==pixelHeight){canvas.width=pixelWidth;canvas.height=pixelHeight;}
      const c=canvas.getContext('2d');c.setTransform(canvas.width/w,0,0,canvas.height/h,0,0);
      let start=0;while(start<index&&times[start]<end-120)start++;const values=keys.map(k=>s?.[k]||[]);let lo=Infinity,hi=-Infinity;
      for(const arr of values)for(let j=start;j<=index;j++)if(Number.isFinite(arr[j])){lo=Math.min(lo,arr[j]);hi=Math.max(hi,arr[j]);}
      if(!Number.isFinite(lo)){lo=0;hi=1;}const pad=Math.max(1,(hi-lo)*.15);lo-=pad;hi+=pad;
      c.strokeStyle='#e8eeef';c.lineWidth=1;for(const y of [10,h/2,h-10]){c.beginPath();c.moveTo(0,y);c.lineTo(w,y);c.stroke();}
      values.forEach((arr,k)=>{c.strokeStyle=k?'#849dbc':'#238f7c';c.lineWidth=1.8;c.beginPath();let started=false;for(let j=start;j<=index;j++){if(!Number.isFinite(arr[j])){started=false;continue;}const x=(times[j]-times[start])/Math.max(.001,end-times[start])*(w-4)+2,y=h-5-(arr[j]-lo)/(hi-lo)*(h-10);if(started)c.lineTo(x,y);else {c.moveTo(x,y);started=true;}}c.stroke();});
      $(`wallTrendValue${n}`).textContent=`${number(values[0][index])} / ${number(values[1][index])}`;
    });
  }
  window.addEventListener('station-ready',mount,{once:true});
  window.addEventListener('station-layout-ready',mount,{once:true});
})();
