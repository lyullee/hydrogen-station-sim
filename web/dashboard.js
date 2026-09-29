/* Operator navigation and secondary surfaces. No process controls live here. */
let restoreDialogContent=null;
window.notifyOperator=message=>{const n=document.getElementById('toast');n.textContent=message;n.hidden=false;clearTimeout(n._timer);n._timer=setTimeout(()=>n.hidden=true,5000);};
function closeWorkspace(){document.getElementById('workspaceDialog').close();}
function openWorkspace(title){
  const dialog=document.getElementById('workspaceDialog');
  dialog.classList.remove('saga-chat-dialog');
  if(restoreDialogContent){restoreDialogContent();restoreDialogContent=null;}
  document.getElementById('workspaceDialogTitle').textContent=title;
  const body=document.getElementById('workspaceDialogBody');body.replaceChildren();
  if(!dialog.open)dialog.showModal();return body;
}
function borrowPanel(selector,title){
  const body=openWorkspace(title);
  const node=document.querySelector(selector),parent=node.parentNode,next=node.nextSibling;body.append(node);
  restoreDialogContent=()=>{parent.insertBefore(node,next);window.dispatchEvent(new Event('resize'));};
  requestAnimationFrame(()=>window.dispatchEvent(new Event('resize')));
}
window.showEquipmentDetails=(item,targetBody=null)=>{
  const body=targetBody||openWorkspace(item?.title||'충전소 운전 안내');
  if(targetBody){body.replaceChildren();const heading=document.createElement('h3');heading.textContent=item?.title||'설비 정보';body.append(heading);}
  const description=document.createElement('p');description.textContent=item?.description||'설비를 클릭해 운전값을 확인하세요. 3D 뷰는 드래그로 회전, 휠로 확대할 수 있습니다.';body.append(description);
  if(!item?.id)return;
  const specs={
    supply:[['모델 유형','기체수소 공급 경계'],['압축기 흡입','시나리오 지정 P/T 경계조건']],
    compressor:[['압축 단수','3단 · 중간냉각'],['최대 질량유량','35 g/s'],['최대 토출 압력','100 MPa'],['체적 효율','75%'],['등엔트로피 효율','72%']],
    low:[['모델 집합 용적','0.35 m³'],['목표 압력','45 MPa'],['벽체 열용량','300 kg × 500 J/kg/K']],
    medium:[['모델 집합 용적','0.35 m³'],['목표 압력','65 MPa'],['벽체 열용량','300 kg × 500 J/kg/K']],
    high:[['모델 집합 용적','0.35 m³'],['목표 압력','95 MPa'],['벽체 열용량','300 kg × 500 J/kg/K']],
    cooler:[['수소-냉매 열전달 UA','900 W/K'],['냉동기 UA','3,000 W/K'],['수소 압력강하','0.1 MPa'],['냉매 열용량','150 kJ/K']],
    vehicle:[['탱크 유형','Type IV 참조 모델'],['내부 용적','0.122 m³'],['라이너','HDPE · 8 kg'],['복합재 쉘','CFRP · 70 kg']],
    safety:[['감지기 경보','H₂ 1.0 vol%'],['감지기 차단','H₂ 2.0 vol%'],['차단 방식','래칭 ESD']],
    vent:[['모델 수준','시각 참조'],['배압·확산 설계','모델에 미포함']],
  };
  const id=item.id,rows=specs[id]||(id==='vehicle2'?specs.vehicle:id.startsWith('dispenser')?[['충전 압력 등급','H70'],['PCV 유효 유로면적','1.5 mm²'],['노즐 유로면적','2.0 mm²'],['호스 내부 용적','2.0 L']]:id.startsWith('detector')?[['신호 종류','가상 H₂ 농도'],['실물 센서 연결','없음']]:[['모델 역할','3D 참조 설비'],['상세 정격','제작사 사양 미설정']]);
  const note=document.createElement('p');note.className='spec-note';note.textContent='참조 시뮬레이션의 가상 설비 사양입니다. 실제 제작사 데이터시트·현장 설계값이 아닙니다.';body.append(note);
  const photoKey=id==='vehicle2'?'vehicle':id.startsWith('dispenser')?'dispenser':id.startsWith('detector')?'safety':id==='vent'?'safety':id;
  const photo=window.stationCameras?.[photoKey];
  if(photo){const img=document.createElement('img');img.className='spec-photo';img.src=photo.image;img.alt=photo.zone+' · AI 생성 가상 CCTV';body.append(img);}
  const table=document.createElement('table');table.className='hazop-table';const tbody=document.createElement('tbody');table.append(tbody);rows.forEach(([name,value])=>{const tr=document.createElement('tr');for(const text of [name,value]){const td=document.createElement('td');td.textContent=text;tr.append(td);}tbody.append(tr);});body.append(table);
};
function sensorTable(body){
  const heading=document.createElement('h3');heading.textContent='주요 설비 · 노드별 PT / TT / FT';body.append(heading);
  const matrix=document.createElement('table');matrix.className='hazop-table';body.append(matrix);
  function renderMatrix(){
    const catalog=window.nodeMonitor?.catalog,frame=window.getStation3DState?.()?.result?.hazop?.frames?.[window.getStation3DState?.()?.index];
    if(!catalog){matrix.textContent='노드 DB 연결 중';return;}
    matrix.innerHTML='<thead><tr><th>노드 / 설비</th><th>압력 PT</th><th>온도 TT</th><th>유량 FT</th></tr></thead><tbody></tbody>';
    for(const node of catalog.nodes){const row=document.createElement('tr'),name=document.createElement('td'),link=document.createElement('button');link.type='button';link.textContent=`${node.node_id} · ${node['설비_라인']||''}`;link.addEventListener('click',()=>{window.nodeMonitor?.selectNode(node.node_id);navigateMonitor('trends');});name.append(link);row.append(name);
      for(const prefix of ['PT-','TT-','FT-']){const cell=document.createElement('td'),tags=catalog.sensors.filter(s=>s.node_id===node.node_id&&s.sensor_id?.startsWith(prefix));if(!tags.length)cell.textContent='센서 없음';else{const tag=tags.find(s=>frame?.signals?.[s.sensor_id]?.quality==='GOOD')||tags[0],signal=frame?.signals?.[tag.sensor_id];cell.textContent=`${tag.sensor_id} · ${signal?.quality==='GOOD'&&Number.isFinite(signal.value)?signal.value.toFixed(2)+' '+(signal.unit||''):'미연결'}`;}row.append(cell);}matrix.tBodies[0].append(row);}
  }
  renderMatrix();const matrixTimer=setInterval(renderMatrix,1000);
  const input=document.createElement('input');input.className='sensor-search';input.placeholder='센서 태그 / 연결 상태 검색';input.setAttribute('aria-label','센서 검색');body.append(input);
  const note=document.createElement('p');note.className='empty';body.append(note);
  const wrap=document.createElement('div');wrap.className='hazop-table-wrap';body.append(wrap);
  const table=document.createElement('table');table.className='hazop-table';wrap.append(table);
  function refresh(){
    const runtime=window.getStation3DState?.(),signals=runtime?.result?.hazop?.frames?.[runtime.index]?.signals||{};
    const sensors=runtime?.mapping?.sensors||[];note.textContent=`${sensors.length}개 센서 · 미수신 값은 — 로 표시합니다.`;
    table.innerHTML='<thead><tr><th>센서</th><th>값</th><th>연결 상태</th><th>출처</th></tr></thead><tbody></tbody>';
    sensors.filter(s=>`${s.sensor_id} ${s.mapping_status} ${s.binding}`.toLowerCase().includes(input.value.toLowerCase())).forEach(s=>{
      const signal=signals[s.sensor_id],row=document.createElement('tr');
      [s.sensor_id,Number.isFinite(signal?.value)?`${signal.value.toFixed(3)} ${signal.unit}`:'—',signal?.quality||s.mapping_status,signal?.origin||s.binding].forEach(v=>{const cell=document.createElement('td');cell.textContent=v;row.append(cell);});table.tBodies[0].append(row);
    });
  }
  input.addEventListener('input',refresh);refresh();
  const timer=setInterval(refresh,1000);restoreDialogContent=()=>{clearInterval(timer);clearInterval(matrixTimer);};
}
function navigateMonitor(action){
  if(action==='overview'||action==='flow'){closeWorkspace();window.setMonitorView?.(action==='flow'?'flow':'3d');return;}
  if(action==='hazop'){borrowPanel('.s3-incidents','센서 · 사고 영향 분석');return;}
  if(action==='saga'){window.openSagaPrompt?.();return;}
  if(action==='trends'){borrowPanel('.chart-panel','실시간 추세 · 이력 탐색');return;}
  if(action==='sensors'){sensorTable(openWorkspace('센서 연결 현황'));return;}
  if(action==='alarms'){
    const body=openWorkspace('경보와 운전 기록');
    const title=document.createElement('p');title.textContent=document.body.dataset.alertState==='incident'?'활성 이상이 있습니다. 아래 경보를 선택해 센서·피해영향예측 분석을 확인하세요.':'현재 활성 사고 후보가 없습니다.';body.append(title);
    if(document.body.dataset.alertState==='incident'){const detail=document.createElement('button');detail.type='button';detail.textContent='현재 센서 · 사고 영향 보기 ↗';detail.addEventListener('click',()=>navigateMonitor('hazop'));body.append(detail);}
    const events=window.getStation3DState?.()?.result?.events||[];
    if(!events.length){const p=document.createElement('p');p.className='empty';p.textContent='아직 기록된 운전 이벤트가 없습니다.';body.append(p);}
    events.slice(-100).reverse().forEach(e=>{const p=document.createElement('p');p.textContent=`${Number(e.time_s||0).toFixed(1)} s · ${e.message}`;body.append(p);});return;
  }
  if(action==='cameras'){
    closeWorkspace();window.showStationDomain?.('cameras');return;
  }
  if(action==='equipment'){
    closeWorkspace();window.showStationDomain?.('equipment');return;
  }
}
document.addEventListener('click',event=>{const nav=event.target.closest('[data-nav]');if(nav){event.preventDefault();navigateMonitor(nav.dataset.nav);}});
document.getElementById('workspaceDialogClose').addEventListener('click',closeWorkspace);
document.getElementById('workspaceDialog').addEventListener('close',()=>{if(restoreDialogContent){restoreDialogContent();restoreDialogContent=null;}});
document.getElementById('remoteLink').addEventListener('click',event=>{
  event.preventDefault();const id=window.getStation3DState?.()?.activeJobId;
  const url='/remote.html'+(id?'?job='+encodeURIComponent(id):'');
  if(!window.open(url,'hrs-remote','popup,width=760,height=860'))window.location.href=url;
});
function attachRemoteJob(id){if(typeof id==='string'&&/^[a-f0-9]{32}$/.test(id)&&id!==state.activeJobId)window.connectStationJob?.(id);}
if('BroadcastChannel' in window){const channel=new BroadcastChannel('hrs-monitor');channel.onmessage=e=>{if(e.data?.type==='job-created')attachRemoteJob(e.data.id);};}
window.addEventListener('storage',e=>{if(e.key==='hrs-active-job')attachRemoteJob(e.newValue);});
window.addEventListener('message',e=>{if(e.origin===location.origin&&e.data?.type==='hrs-job-created')attachRemoteJob(e.data.id);});
function tick(){document.getElementById('wallClock').textContent=new Date().toLocaleTimeString('ko-KR',{hour12:false});window.updateConnectionDisplay?.();}
tick();setInterval(tick,1000);
window.addEventListener('station-ready',()=>{if(location.hash==='#processPanel')window.setMonitorView('flow');});
