import * as THREE from '/vendor/three/three.module.js';
import { OrbitControls } from '/vendor/three/OrbitControls.js';
import { buildHydrogenTransporter } from '/tube-trailer.js';
import { createStationPipeRoutes, createPipeCurve, buildStationPiping } from '/station-piping.js';
import { buildCoolingPackage, COOLING_PROCESS_PORTS } from '/cooling-package.js';
import { buildCompressorPackage } from '/compressor-package.js?v=20260919-fix1';
import { buildStorageBank } from '/storage-bank.js';
import { buildVentPackage } from '/vent-package.js';
import { buildFcevVehicle } from '/fcev-vehicle.js?v=20260919-vehicle2';

// Geometry is a conceptual visual layout, not an approved engineering drawing.
const panel = document.createElement('section');
panel.className = 'station3d';
panel.id = 'station3d';
panel.innerHTML = `
  <header class="s3-head"><div><div class="s3-eyebrow">SPATIAL OPERATIONS / H70 REFERENCE STATION</div><h2>수소충전소 · 3D 운영 뷰</h2></div><div class="s3-head-tools"><div class="view-switcher" aria-label="모니터 뷰 전환"><button type="button" data-panel-view="3d" class="selected">3D</button><button type="button" data-panel-view="flow">공정 흐름</button></div><button id="s3Fullscreen" class="s3-fullscreen" type="button" aria-label="3D 화면 전체화면" title="3D 화면 전체화면"><span aria-hidden="true">⛶</span><b>전체화면</b></button><div class="s3-live" id="s3Live"><i></i><span>모델 대기</span></div></div></header>
  <div class="s3-monitor-layout">
    <aside class="s3-info-column s3-info-left" aria-label="주요 설비 상태">
      <article class="s3-info-card"><header><span class="s3-info-kicker">STORAGE BANKS</span><b>저장 뱅크</b><i class="s3-status-dot"></i></header><div class="s3-bank-list"><div><span>HIGH</span><strong id="s3BankHigh">0.0</strong><em>MPa</em></div><div><span>MID</span><strong id="s3BankMedium">0.0</strong><em>MPa</em></div><div><span>LOW</span><strong id="s3BankLow">0.0</strong><em>MPa</em></div></div><small class="s3-info-foot" id="s3BankState">압력 신호 대기</small></article>
      <article class="s3-info-card"><header><span class="s3-info-kicker">COMPRESSOR</span><b>압축기</b><i class="s3-status-dot"></i></header><div class="s3-info-value"><strong id="s3CompressorState">대기</strong><span id="s3CompressorDetail">재충전 뱅크 없음</span></div><div class="s3-meter"><i id="s3CompressorMeter"></i></div><small class="s3-info-foot" id="s3CompressorFoot">3단 압축 · 중간 냉각</small></article>
    </aside>
    <div class="s3-stage" id="s3Stage">
    <div class="s3-camera-markers" id="s3CameraMarkers" aria-label="CCTV 카메라 위치"></div>
    <button id="s3StageExit" class="s3-stage-exit" type="button" hidden>× 전체화면 닫기</button>
    <nav class="s3-toolbar" aria-label="3D 시점"><button data-view="overview" class="selected">전체 조감</button><button data-view="fueling">충전 구역</button><button data-view="plant">공정 설비</button><button data-view="top">평면 배치</button><button id="s3AssetsToggle" aria-expanded="false" aria-controls="s3Assets">설비 목록</button></nav>
    <div class="s3-assets" id="s3Assets" hidden role="group" aria-label="설비 선택"></div>
    <div class="s3-compass"><b>↑</b>N / PROCESS</div>
    <div class="s3-options"><button id="s3Pipes" aria-pressed="true">공정 배관</button><button id="s3Roof" aria-pressed="false">캐노피 투시</button><button id="s3Service" aria-pressed="false">설비 내부</button><button id="s3VehicleCutaway" aria-pressed="false">차량 탱크 투시</button><button id="s3Night" aria-pressed="false">야간 조명</button></div>
    <aside class="s3-card"><small id="s3Tag">H70 / DIGITAL OPERATIONS</small><h3 id="s3Title">전체 충전소</h3><p id="s3Description">설비를 클릭하면 역할과 운전값을 확인합니다. 드래그로 회전, 휠로 확대, 오른쪽 드래그로 이동합니다.</p><div class="s3-reading"><span id="s3ReadingLabel">모의 시간</span><strong id="s3Reading">0.0 s</strong></div><button id="s3Focus" class="s3-focus" disabled>선택 설비 확대</button><button id="s3CctvButton" class="s3-cctv-button" type="button">가상 CCTV · 전체 구역</button><img id="s3Cctv" class="s3-cctv" src="/assets/cctv/cctv-storage-banks.png" alt="전체 구역 가상 CCTV"></aside>
    <dialog id="s3CctvDialog" class="s3-cctv-dialog" aria-labelledby="s3CctvDialogTitle"><form method="dialog" class="s3-cctv-dialog-shell"><header><div><span class="s3-info-kicker">VIRTUAL CCTV / LIVE FRAME</span><h3 id="s3CctvDialogTitle">CAM-00 · 전체 구역</h3></div><button class="s3-dialog-close" value="cancel" aria-label="CCTV 닫기">×</button></header><div class="s3-cctv-dialog-body"><img id="s3CctvDialogImage" src="/assets/cctv/cctv-storage-banks.png" alt="가상 CCTV"><div class="s3-cctv-dialog-meta"><b id="s3CctvDialogZone">전체 구역</b><span id="s3CctvDialogState">NORMAL · 모델 연동</span><small id="s3CctvDialogTime">모델 시간 0.0 s</small></div></div></form></dialog>
    </div>
    <aside class="s3-info-column s3-info-right" aria-label="충전 및 안전 상태">
      <article class="s3-info-card"><header><span class="s3-info-kicker">DISPENSER</span><b>디스펜서</b><i class="s3-status-dot"></i></header><div class="s3-dual-values"><div><span>차량 1</span><strong id="s3Dispenser1">0.0</strong><em>g/s</em></div><div><span>차량 2</span><strong id="s3Dispenser2">0.0</strong><em>g/s</em></div></div><small class="s3-info-foot" id="s3DispenserFoot">대기 · 프리쿨러 −40 °C</small></article>
      <article class="s3-info-card"><header><span class="s3-info-kicker">SAFETY MONITOR</span><b>가스·안전</b><i class="s3-status-dot" id="s3SafetyDot"></i></header><div class="s3-safety-row"><strong id="s3SafetyState">정상</strong><span id="s3LeakState">누출 0.00 g/s</span></div><div class="s3-detector-bar"><span>GD-ZONE</span><b id="s3DetectorState">정상</b></div><small class="s3-info-foot" id="s3SafetyFoot">ESD 대기 · 검지기 연결</small></article>
    </aside>
  </div>
  <footer class="s3-footer"><div class="s3-legend"><span>충전 흐름</span><span>압축·재충전</span><span>ESD / 누출</span></div><span>참조 배치 · 치수/안전거리는 설계 승인 대상 아님 · 운전값은 계산 모델 연결</span></footer>`;
const anchor = document.querySelector('.process');
if (anchor) anchor.before(panel);
else document.querySelector('main').append(panel);
// Shared viewport and telemetry rail keep the same footprint in both views.
const layout = panel.querySelector('.s3-monitor-layout');
const stage = panel.querySelector('#s3Stage');
const $ = id => panel.querySelector(`#${id}`);
const visualColumn = document.createElement('div'); visualColumn.className='s3-visual-column';
const surface = document.createElement('div'); surface.className='s3-visual-surface';
const sidebar = document.createElement('aside'); sidebar.className='s3-sidebar'; sidebar.setAttribute('aria-label','운전 상태');
const equipmentCards=document.createElement('div'); equipmentCards.className='s3-equipment-grid';
panel.querySelectorAll('.s3-info-card').forEach(card=>equipmentCards.append(card));
const selectionSlot=document.createElement('div'); selectionSlot.className='s3-selection-slot';
selectionSlot.append(panel.querySelector('.s3-card'));
surface.append(stage); visualColumn.append(surface,selectionSlot);
if(anchor){anchor.id='processPanel';surface.append(anchor);}
sidebar.append(document.querySelector('.analysis-row'),equipmentCards,document.querySelector('#detectorStrip'));
const incidents=document.createElement('div');incidents.className='s3-incidents';
incidents.append(document.querySelector('#hazopPanel'),document.querySelector('#impactPanel'));
incidents.querySelector('#hazopPanel').insertAdjacentHTML('beforeend','<button class="incident-details" type="button" data-nav="hazop">사고 분석 상세 ↗</button>');
sidebar.append(incidents,document.querySelector('.chart-panel'),document.querySelector('.event-panel'));
document.querySelector('.lower-grid')?.remove();
layout.replaceChildren(visualColumn,sidebar);
document.querySelector('.chart-panel').append(document.querySelector('.playback'));
panel.querySelector('.s3-card').insertAdjacentHTML('beforeend','<button id="s3Details" type="button">설비 정보</button>');
window.setMonitorView = view => {
  stage.hidden=view!=='3d'; if(anchor)anchor.hidden=view!=='flow'; panel.hidden=false;
  document.body.dataset.monitorView=view;
  panel.querySelector('.s3-head h2').textContent=view==='flow'?'충전소 공정 흐름':'충전소 공간 모니터';
  document.querySelectorAll('[data-panel-view]').forEach(b=>{b.classList.toggle('selected',b.dataset.panelView===view);b.setAttribute('aria-pressed',String(b.dataset.panelView===view));});
  document.querySelectorAll('.side-nav [data-nav]').forEach(b=>b.classList.toggle('active',b.dataset.nav===(view==='flow'?'flow':'overview')));
};
document.querySelectorAll('[data-panel-view]').forEach(b=>b.addEventListener('click',()=>window.setMonitorView(b.dataset.panelView)));
window.setMonitorView('3d');
const cctvScenes = {
  site:{label:'전체 구역',zone:'전체 충전소',image:'/assets/cctv/normal.png'},
  storage:{label:'CAM-01 · 저장 뱅크',zone:'후면 저장 뱅크 야드',image:'/assets/cctv/equipment/storage-high.png'},
  high:{label:'CAM-06 · 고압 저장뱅크',zone:'고압 저장 용기군',image:'/assets/cctv/equipment/storage-high.png'},
  medium:{label:'CAM-07 · 중압 저장뱅크',zone:'중압 저장 용기군',image:'/assets/cctv/equipment/storage-medium.png'},
  low:{label:'CAM-08 · 저압 저장뱅크',zone:'저압 저장 용기군',image:'/assets/cctv/equipment/storage-low.png'},
  compressor:{label:'CAM-02 · 압축기',zone:'압축 패키지',image:'/assets/cctv/equipment/compressor.png'},
  cooler:{label:'CAM-10 · 프리쿨러',zone:'프리쿨러·냉동기',image:'/assets/cctv/equipment/precooler.png'},
  pcv:{label:'CAM-09 · 압력제어밸브',zone:'PCV 매니폴드',image:'/assets/cctv/equipment/pcv.png'},
  dispenser:{label:'CAM-03 · 디스펜서',zone:'H70 디스펜서',image:'/assets/cctv/equipment/dispenser.png'},
  vehicle:{label:'CAM-11 · 충전 차량',zone:'차량·노즐',image:'/assets/cctv/equipment/vehicle.png'},
  safety:{label:'CAM-04 · 가스 안전',zone:'가스검지기·안전 PLC',image:'/assets/cctv/cctv-safety.png'},
  supply:{label:'CAM-05 · 공급·하역',zone:'튜브트레일러 하역 구역',image:'/assets/cctv/equipment/supply.png'},
};
const cameraFor=id=>{
  if(['high','medium','low'].includes(id))return id;
  if(['pcv','pcvUnit','dispenser.pcv','dispenser_2.pcv'].includes(id))return 'pcv';
  if(['cooler','coolerUnit'].includes(id))return 'cooler';
  if(['vehicle','vehicle2','vehicleUnit','vehicle.tank','vehicle_2.tank'].includes(id))return 'vehicle';
  if(/^(PT|TT|FT)-(11|12|13|14|15|16|17|18)/.test(id))return 'dispenser';
  if(/^(PT|TT|FT)-0[789]/.test(id))return 'storage';
  if(['GD-2301','GD-2302'].includes(id))return 'storage';
  if(['GD-2101','GD-2201','GD-1701'].includes(id))return 'dispenser';
  if(id==='GD-1901')return 'compressor';
  if(['low','medium','high','detector2301','detector2302'].includes(id)||String(id).startsWith('cascade.'))return 'storage';
  if(['compressor','compressorUnit','detector1901'].includes(id))return 'compressor';
  if(['dispenser','standby','detector01','detector02'].includes(id)||/^(dispenser|vehicle)/.test(id))return 'dispenser';
  if(id==='supply')return 'supply';
  if(['safety','header','vent','detector1701','detector2001'].includes(id)||String(id).startsWith('GD-'))return 'safety';
  return cctvScenes[id]?id:'site';
};
let activeCctvId='site', dialogCctvId='site';
function cameraStatus(id){
  const runtime=window.getStation3DState?.(),s=runtime?.result?.series,i=runtime?.index??0;
  const faults=(s?.active_faults?.[i]||[]).filter(f=>id==='site'||cameraFor(f.slice(f.indexOf(':')+1))===id);
  return {time:s?.time_s?.[i],kind:faults.some(f=>f.startsWith('external-fire:'))?'fire':faults.some(f=>f.startsWith('hydrogen-leak:'))?'leak':faults.length?'advisory':s?.time_s?.length?'normal':'waiting'};
}
function refreshCctv(){
  const camera=cctvScenes[activeCctvId];
  if($('s3Cctv').getAttribute('src')!==camera.image)$('s3Cctv').src=camera.image;
  $('s3Cctv').alt=camera.zone+' · AI 생성 참고 이미지';
  $('s3CctvButton').textContent='CCTV · '+camera.label;
  if(!$('s3CctvDialog').open)return;
  const selected=cctvScenes[dialogCctvId],status=cameraStatus(dialogCctvId);
  $('s3CctvDialogTitle').textContent=selected.label;$('s3CctvDialogZone').textContent=selected.zone;
  if($('s3CctvDialogImage').getAttribute('src')!==selected.image)$('s3CctvDialogImage').src=selected.image;
  $('s3CctvDialogImage').alt=selected.zone+' · AI 생성 참고 이미지';
  $('s3CctvDialog').dataset.state=status.kind;
  const labels={fire:'화재 시나리오 활성',leak:'누출 시나리오 활성',advisory:'설비 이상 입력',normal:'해당 구역 사고 입력 없음',waiting:'운전 데이터 대기'};
  $('s3CctvDialogState').textContent=labels[status.kind];
  $('s3CctvDialogTime').textContent=(status.time==null?'모델 대기':`모델 시간 ${status.time.toFixed(1)} s`)+' · AI 생성 정지 이미지 / 상태만 실시간 연동';
  $('s3CameraSelect').value=dialogCctvId;
}
function openStationCctv(id='site'){
  dialogCctvId=cameraFor(id);activeCctvId=dialogCctvId;
  const dialog=$('s3CctvDialog');
  // A hidden flow-view ancestor prevents modal rendering in some browsers.
  if(document.fullscreenElement!==stage&&!stage.classList.contains('is-maximized'))panel.append(dialog);
  if(!dialog.open)dialog.showModal();refreshCctv();
}
window.openStationCctv=openStationCctv;
window.stationCameras=cctvScenes;
window.showCctvFor=id=>{activeCctvId=cameraFor(id);refreshCctv();};
$('s3CctvDialog').querySelector('.s3-cctv-dialog-meta').insertAdjacentHTML('beforeend','<select id="s3CameraSelect" aria-label="CCTV 카메라 선택"></select>');
Object.entries(cctvScenes).forEach(([id,c])=>{const o=document.createElement('option');o.value=id;o.textContent=c.label;$('s3CameraSelect').append(o);});
$('s3CameraSelect').addEventListener('change',e=>{dialogCctvId=e.target.value;refreshCctv();});
$('s3CctvDialog').querySelector('.s3-info-kicker').textContent='VIRTUAL CCTV / AI STILL';
const fullscreenButton=$('s3Fullscreen'),stageExitButton=$('s3StageExit');
function syncFullscreenButton(){
  const active=document.fullscreenElement===stage||stage.classList.contains('is-maximized');
  fullscreenButton.setAttribute('aria-pressed',String(active));stageExitButton.hidden=!active;
  document.body.classList.toggle('viewport-expanded',active);
  fullscreenButton.querySelector('b').textContent=active?'축소':'전체화면';
  if(active)stage.append($('s3CctvDialog'));
}
async function exitStage(){
  if(document.fullscreenElement===stage)await document.exitFullscreen();
  stage.classList.remove('is-maximized');syncFullscreenButton();fullscreenButton.focus();
}
fullscreenButton.addEventListener('click',async()=>{
  if(document.fullscreenElement===stage||stage.classList.contains('is-maximized'))return exitStage();
  window.setMonitorView('3d');
  try{await stage.requestFullscreen();}catch{stage.classList.add('is-maximized');}
  syncFullscreenButton();stageExitButton.focus();
});
stageExitButton.addEventListener('click',exitStage);
document.addEventListener('fullscreenchange',syncFullscreenButton);
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&stage.classList.contains('is-maximized')&&!$('s3CctvDialog').open)exitStage();});
// Fit the canvas to the available area, preserving 16:9 without page overflow.
new ResizeObserver(()=>{
  if(document.fullscreenElement===stage||stage.classList.contains('is-maximized'))return;
  const w=Math.min(surface.clientWidth,surface.clientHeight*16/9);
  stage.style.width=`${Math.max(1,w)}px`;stage.style.height=`${Math.max(1,w*9/16)}px`;
}).observe(surface);
window.addEventListener('station-frame',refreshCctv);

const equipment = new Map();
const pickMeshes = [];
const statusLights = [];
const dynamicPipes = [];
let renderer;

try {
  renderer = new THREE.WebGLRenderer({ antialias:true, alpha:true, powerPreference:'high-performance' });
} catch (error) {
  stage.insertAdjacentHTML('beforeend','<div class="s3-error"><h3>3D 가속을 사용할 수 없습니다.</h3><p>브라우저의 하드웨어 가속을 활성화해 주세요. 기존 공정 화면은 계속 사용할 수 있습니다.</p></div>');
}

if (renderer) {
  try {
    buildStation();
  } catch (error) {
    const message=document.createElement('div');message.className='s3-error';message.setAttribute('role','alert');
    const title=document.createElement('h3');title.textContent='3D 모델 초기화 중 오류가 발생했습니다.';
    const description=document.createElement('p');description.textContent=error instanceof Error?error.message:String(error);
    message.append(title,description);stage.append(message);
    console.error('Hydrogen station 3D initialization failed:',error);
  }
}

// Keep the monitor and flow view available even when WebGL is unavailable.
window.dispatchEvent(new Event('station-layout-ready'));

function buildStation() {
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1,1.5));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;
  stage.prepend(renderer.domElement);
  const scene = new THREE.Scene();
  const markerLayer = stage.querySelector('#s3CameraMarkers');
  const cameraMarkerDefs = [
    { id:'storage', label:'CAM-01', name:'저장 뱅크', position:new THREE.Vector3(3,3.4,-3.6) },
    { id:'compressor', label:'CAM-02', name:'압축기', position:new THREE.Vector3(-6.2,3.1,-3.8) },
    { id:'dispenser', label:'CAM-03', name:'충전 캐노피', position:new THREE.Vector3(4.1,3.6,3.25) },
    { id:'safety', label:'CAM-04', name:'가스 안전', position:new THREE.Vector3(13.5,3.0,-3.3) },
    { id:'supply', label:'CAM-05', name:'공급·하역', position:new THREE.Vector3(-10.7,3.6,-3.1) },
    { id:'high', label:'CAM-06', name:'고압 저장', position:new THREE.Vector3(7,3,-6) },
    { id:'medium', label:'CAM-07', name:'중압 저장', position:new THREE.Vector3(3,3,-6) },
    { id:'low', label:'CAM-08', name:'저압 저장', position:new THREE.Vector3(-1,3,-6) },
    { id:'pcv', label:'CAM-09', name:'PCV', position:new THREE.Vector3(1,2,4) },
    { id:'cooler', label:'CAM-10', name:'프리쿨러', position:new THREE.Vector3(11,2,-6) },
    { id:'vehicle', label:'CAM-11', name:'차량', position:new THREE.Vector3(5,3,7) },
  ];
  const cameraMarkerNodes = [];
  cameraMarkerDefs.forEach(def => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 's3-camera-marker';
    button.dataset.camera = def.id;
    button.title = `${def.label} · ${def.name} CCTV 보기`;
    button.setAttribute('aria-label', `${def.label} ${def.name} CCTV 보기`);
    button.innerHTML = `<span class="s3-camera-icon" aria-hidden="true"><svg viewBox="0 0 24 24" focusable="false"><path d="M4 8.5h10.5l3.4-2.2a1 1 0 0 1 1.6.83v9.74a1 1 0 0 1-1.6.83l-3.4-2.2H4a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2Z"/><circle cx="9" cy="11.5" r="2.35"/></svg></span><b>${def.label}</b><small>${def.name}</small>`;
    button.addEventListener('click', event => {
      event.stopPropagation();
      activeCctvId = def.id;
      const runtime = window.getStation3DState?.();
      const faults = runtime?.result?.series?.active_faults?.[runtime.index] || [];
      
      openStationCctv(def.id);
    });
    markerLayer?.append(button);
    cameraMarkerNodes.push({ def, button });
  });
  function updateCameraMarkers() {
    if (!markerLayer) return;
    const canvasRect = renderer.domElement.getBoundingClientRect();
    const stageRect = stage.getBoundingClientRect();
    const scale = stageRect.width / stage.clientWidth || 1;
    const width = canvasRect.width / scale || stage.clientWidth;
    const height = canvasRect.height / scale || stage.clientHeight;
    cameraMarkerNodes.forEach(({ def, button }) => {
      const projected = def.position.clone().project(camera);
      const visible = projected.z > -1 && projected.z < 1 && Math.abs(projected.x) <= 1.05 && Math.abs(projected.y) <= 1.05;
      button.hidden = !visible;
      if (!visible) return;
      const x = Math.max(22,Math.min(width-22,(canvasRect.left - stageRect.left) / scale + (projected.x + 1) * .5 * width));
      const y = Math.max(65,Math.min(height-60,(canvasRect.top - stageRect.top) / scale + (1 - projected.y) * .5 * height));
      button.style.left = `${x}px`;
      button.style.top = `${y}px`;
    });
  }
  scene.background = new THREE.Color(0x1c2d38);
  scene.fog = new THREE.Fog(0x1c2d38,65,130);
  const camera = new THREE.PerspectiveCamera(40,1,.1,180);
  camera.position.set(29,23,31);
  const controls = new OrbitControls(camera,renderer.domElement);
  const panButton=document.createElement('button');panButton.type='button';panButton.id='s3PanMode';panButton.textContent='이동 모드';panButton.title='클릭하면 왼쪽 드래그로 화면을 상하좌우 이동합니다. 다시 클릭하면 회전합니다.';
  panel.querySelector('.s3-toolbar').append(panButton);
  panButton.addEventListener('click',()=>{const pan=panButton.getAttribute('aria-pressed')!=='true';panButton.setAttribute('aria-pressed',String(pan));panButton.textContent=pan?'회전 모드':'이동 모드';controls.mouseButtons.LEFT=pan?THREE.MOUSE.PAN:THREE.MOUSE.ROTATE;controls.mouseButtons.RIGHT=pan?THREE.MOUSE.ROTATE:THREE.MOUSE.PAN;});
  controls.target.set(0,1,0);
  controls.enableDamping = true;
  controls.dampingFactor = .07;
  controls.zoomSpeed = .85;
  controls.zoomToCursor = true;
  controls.maxPolarAngle = Math.PI*.475;
  controls.minDistance = 1.2;
  controls.maxDistance = 65;
  const hemi = new THREE.HemisphereLight(0xeaf8ff,0x889979,2.2);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xffefcd,3.1);
  sun.position.set(-18,32,15); sun.castShadow = true;
  sun.shadow.mapSize.set(2048,2048);
  Object.assign(sun.shadow.camera,{left:-28,right:28,top:25,bottom:-25,near:1,far:80});
  sun.shadow.bias = -.0005; sun.shadow.normalBias = .04; scene.add(sun);
  const rim = new THREE.DirectionalLight(0xbee8ee,.8); rim.position.set(20,12,-22); scene.add(rim);

  const mat = (color,metalness=0,roughness=.7) => new THREE.MeshStandardMaterial({color,metalness,roughness});
  const M = {
    concrete:mat(0xc5c9be), pavement:mat(0x667475),white:mat(0xf2f4eb,.15,.4),
    green:mat(0x126456,.25,.35), teal:mat(0x248c83,.3,.4), steel:mat(0xb1bec1,.8,.28),
    frame:mat(0x405355,.7,.45), dark:mat(0x173337,.25,.45), black:mat(0x1e292b),
    yellow:mat(0xeeb13d,.1,.45),red:mat(0xc85140),glass:new THREE.MeshStandardMaterial({color:0x284c5b,metalness:.4,roughness:.17}),
    turf:mat(0x75956d),leaf:mat(0x417762),trunk:mat(0x776248),orange:mat(0xe4a338,.4,.3),
    fire:new THREE.MeshStandardMaterial({color:0xff6a1a,emissive:0xff2400,emissiveIntensity:3,transparent:true,opacity:.88}),
    smoke:new THREE.MeshStandardMaterial({color:0x59666a,transparent:true,opacity:.22,depthWrite:false}),
    leak:new THREE.MeshStandardMaterial({color:0x9feaff,emissive:0x3bc7ff,emissiveIntensity:1.8,transparent:true,opacity:.24,depthWrite:false})
  };
  // Local procedural lighting: no external textures or network dependency.
  const environmentFaces=Array.from({length:6},(_,face)=>{
    const canvas=document.createElement('canvas');canvas.width=256;canvas.height=256;
    const ctx=canvas.getContext('2d');const gradient=ctx.createLinearGradient(0,0,0,256);
    gradient.addColorStop(0,face===2?'#eef7ff':'#acc9da');gradient.addColorStop(.48,'#eff4ed');gradient.addColorStop(.55,'#9aa9a0');gradient.addColorStop(1,'#60716d');
    ctx.fillStyle=gradient;ctx.fillRect(0,0,256,256);
    if(face!==3){ctx.fillStyle='#fff6e3';ctx.fillRect(40,20,24,75);ctx.fillStyle='#d7e5e4';ctx.fillRect(170,15,45,100);}
    return canvas;
  });
  const environment=new THREE.CubeTexture(environmentFaces);environment.colorSpace=THREE.SRGBColorSpace;environment.needsUpdate=true;
  const pmrem=new THREE.PMREMGenerator(renderer);const reflection=pmrem.fromCubemap(environment);scene.environment=reflection.texture;environment.dispose();pmrem.dispose();
  M.steel.envMapIntensity=.85;M.glass.envMapIntensity=1.15;
  function surfaceTexture(base,grain,repeat) {
    const canvas=document.createElement('canvas');canvas.width=256;canvas.height=256;
    const ctx=canvas.getContext('2d');ctx.fillStyle=base;ctx.fillRect(0,0,256,256);
    let seed=9173;const random=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
    for(let i=0;i<12000;i++){const value=Math.floor(100+random()*130);ctx.fillStyle=`rgba(${value},${value},${value},${grain})`;ctx.fillRect(random()*256,random()*256,1+random()*2,1+random()*2);}
    const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.repeat.set(repeat,repeat);texture.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());return texture;
  }
  M.pavement.map=surfaceTexture('#596262',.34,9);M.concrete.map=surfaceTexture('#c3c7be',.15,5);
  function mesh(geometry,material,parent=scene) {
    const obj = new THREE.Mesh(geometry,material); obj.castShadow = true; obj.receiveShadow = true; parent.add(obj); return obj;
  }
  function box(w,h,d,x,y,z,material,parent=scene) {
    const obj=mesh(new THREE.BoxGeometry(w,h,d),material,parent); obj.position.set(x,y,z); return obj;
  }
  function cylinder(r,length,x,y,z,material,parent=scene,axis='y') {
    const obj=mesh(new THREE.CylinderGeometry(r,r,length,32),material,parent); obj.position.set(x,y,z);
    if(axis==='z')obj.rotation.x=Math.PI/2; if(axis==='x')obj.rotation.z=Math.PI/2; return obj;
  }
  const accidentLayer=new THREE.Group();accidentLayer.name='physical-accident-visualization';scene.add(accidentLayer);
  const effectLayer=new THREE.Group();effectLayer.name='sampled-hyram-effect';scene.add(effectLayer);
  const effectRings=new Map();const rangeBadge=document.createElement('div');rangeBadge.id='s3RiskRange';rangeBadge.hidden=true;stage.append(rangeBadge);
  const incidentBanner=document.createElement('div');incidentBanner.id='s3IncidentBanner';incidentBanner.hidden=true;incidentBanner.setAttribute('role','status');stage.append(incidentBanner);
  const incidentMarkers=document.createElement('div');incidentMarkers.id='s3IncidentMarkers';stage.append(incidentMarkers);
  const accidentNames={'cascade.low':'저압 저장뱅크','cascade.medium':'중압 저장뱅크','cascade.high':'고압 저장뱅크','vehicle.tank':'1번 차량 탱크','vehicle_2.tank':'2번 차량 탱크','dispenser.hose':'1번 디스펜서 호스','dispenser_2.hose':'2번 디스펜서 호스','compressor':'압축기','cooler':'프리쿨러','dispenser.pcv':'1번 PCV','dispenser_2.pcv':'2번 PCV'};
  const accidentAnchors={
    'cascade.low':[-1,1.8,-6],'cascade.medium':[3,1.8,-6],'cascade.high':[7,1.8,-6],
    'vehicle.tank':[2.8,1.2,7],'vehicle_2.tank':[10.8,1.2,7],
    'dispenser.hose':[1.8,1.2,5.2],'dispenser_2.hose':[9.8,1.2,5.2],
    'compressor':[-6.4,1.8,-6],'cooler':[11,1.5,-6],'dispenser.pcv':[0,1.5,4.2],'dispenser_2.pcv':[8,1.5,4.2]
  };
  const glowCanvas=document.createElement('canvas');glowCanvas.width=128;glowCanvas.height=128;
  const glowContext=glowCanvas.getContext('2d');const glowGradient=glowContext.createRadialGradient(64,64,3,64,64,64);
  glowGradient.addColorStop(0,'rgba(255,255,255,1)');glowGradient.addColorStop(.18,'rgba(255,255,255,.8)');glowGradient.addColorStop(1,'rgba(255,255,255,0)');
  glowContext.fillStyle=glowGradient;glowContext.fillRect(0,0,128,128);
  const glowTexture=new THREE.CanvasTexture(glowCanvas);
  function glow(color,scale,parent){const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTexture,color,transparent:true,opacity:.75,blending:THREE.AdditiveBlending,depthWrite:false}));sprite.scale.set(scale,scale,1);parent.add(sprite);return sprite;}
  function accidentVisual(kind,target){
    const key=`${kind}:${target}`;let found=accidentLayer.getObjectByName(key);if(found)return found;
    const anchor=accidentAnchors[target]||[0,1,0],group=new THREE.Group();group.name=key;group.position.set(...anchor);
    const footprint=new THREE.Mesh(new THREE.RingGeometry(.72,.94,40),new THREE.MeshBasicMaterial({color:kind==='external-fire'?0xff6b31:0x69eaff,transparent:true,opacity:.95,side:THREE.DoubleSide,depthWrite:false,depthTest:false}));
    footprint.rotation.x=-Math.PI/2;footprint.position.y=-anchor[1]+.14;footprint.renderOrder=55;group.add(footprint);
    const particles=[];let light;
    if(kind==='external-fire'){
      const flameColors=[0xff4b18,0xff9a22,0xffd54a,0xffef9a];
      for(let i=0;i<7;i++){
        const height=2.8+(i%3)*.55;const flame=new THREE.Mesh(new THREE.ConeGeometry(.73-(i%3)*.1,height,12,1),new THREE.MeshBasicMaterial({color:flameColors[i%4],transparent:true,opacity:.76,side:THREE.DoubleSide,depthWrite:false}));
        flame.position.set(Math.sin(i*2.4)*.44,height*.43,Math.cos(i*2.4)*.36);flame.rotation.z=Math.sin(i*1.9)*.24;group.add(flame);particles.push({mesh:flame,type:'flame',phase:i*1.74,baseX:flame.position.x,baseZ:flame.position.z});
      }
      for(let i=0;i<14;i++){
        const puff=new THREE.Mesh(new THREE.SphereGeometry(.42,9,7),new THREE.MeshBasicMaterial({color:i%3===0?0x45494b:0x77716b,transparent:true,opacity:.22,depthWrite:false}));group.add(puff);particles.push({mesh:puff,type:'smoke',phase:i/14,offset:i*2.4});
      }
      const halo=glow(0xff732b,5.2,group);halo.position.y=1.4;particles.push({mesh:halo,type:'halo'});
      light=new THREE.PointLight(0xff682d,5,12,2);light.position.y=1.8;group.add(light);
    }else{
      // Hydrogen is normally invisible. Cyan is an explicit false-colour leak indicator.
      const core=new THREE.Mesh(new THREE.ConeGeometry(.5,3.8,14,1,true),new THREE.MeshBasicMaterial({color:0x88ecff,transparent:true,opacity:.32,side:THREE.DoubleSide,depthWrite:false}));core.position.set(.7,1.8,0);core.rotation.z=-.38;group.add(core);
      const sourceGlow=glow(0x6ceaff,3.5,group);sourceGlow.position.y=.6;particles.push({mesh:sourceGlow,type:'halo'});
      for(let i=0;i<34;i++){
        const particle=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTexture,color:i%4===0?0xffffff:0x69e6ff,transparent:true,opacity:.85,blending:THREE.AdditiveBlending,depthWrite:false}));particle.scale.set(.48,.48,1);group.add(particle);particles.push({mesh:particle,type:'jet',phase:i/34,offset:i*2.399});
      }
      light=new THREE.PointLight(0x54dcff,2.5,8,2);light.position.y=1.2;group.add(light);
    }
    const pin=document.createElement('div');pin.className=`s3-incident-pin ${kind==='external-fire'?'fire':'leak'}`;
    const pinKind=document.createElement('b');pinKind.textContent=kind==='external-fire'?'화재':'누출';
    const pinTarget=document.createElement('span');pinTarget.textContent=accidentNames[target]||target;
    pin.append(pinKind,pinTarget);pin.hidden=true;incidentMarkers.append(pin);
    const vfx=document.createElement('div');vfx.className=`s3-incident-vfx ${kind==='external-fire'?'fire':'leak'}`;
    vfx.innerHTML=kind==='external-fire'?'<i class="smoke a"></i><i class="smoke b"></i><i class="flame a"></i><i class="flame b"></i><i class="flame c"></i><i class="ember a"></i><i class="ember b"></i>':'<i class="leak-core"></i><i class="leak-jet a"></i><i class="leak-jet b"></i><i class="leak-jet c"></i><i class="leak-cloud"></i>';
    vfx.hidden=true;incidentMarkers.append(vfx);
    group.userData={kind,target,particles,light,footprint,pin,vfx};group.visible=false;accidentLayer.add(group);return group;
  }
  function updateAccidentVisuals(activeFaults){
    const active=new Set((Array.isArray(activeFaults)?activeFaults:[]).filter(key=>/^(external-fire|hydrogen-leak):/.test(key)));
    for(const child of accidentLayer.children){child.visible=active.has(child.name);child.userData.pin.hidden=!child.visible;child.userData.vfx.hidden=!child.visible;}
    for(const key of active){const [kind,...rest]=key.split(':');const visual=accidentVisual(kind,rest.join(':'));visual.visible=true;visual.userData.pin.hidden=false;visual.userData.vfx.hidden=false;}
    if(!active.size){incidentBanner.hidden=true;return;}
    const entries=[...active].map(key=>{const [kind,...rest]=key.split(':');return {kind,target:rest.join(':')}});
    incidentBanner.hidden=false;incidentBanner.dataset.kind=entries.some(entry=>entry.kind==='external-fire')?'fire':'leak';
    const summary=entries.slice(0,2).map(entry=>`${entry.kind==='external-fire'?'화재':'누출'} · ${accidentNames[entry.target]||entry.target}`).join(' / ');
    const headline=document.createElement('strong');headline.append(document.createElement('i'),`${entries.length}건 사고 시나리오 활성`);
    const detail=document.createElement('span');detail.textContent=summary+(entries.length>2?` 외 ${entries.length-2}건`:'');
    const note=document.createElement('small');note.textContent=`${entries.some(entry=>entry.kind==='hydrogen-leak')?'청록색 누출은 가시화용 가상 색상 · ':''}3D 사고 위치 표시`;
    incidentBanner.replaceChildren(headline,detail,note);
  }
  function animateAccidents(timestamp){
    const time=timestamp*.001;const canvasRect=renderer.domElement.getBoundingClientRect(),stageRect=stage.getBoundingClientRect();
    const scale=stageRect.width/stage.clientWidth||1,width=canvasRect.width/scale||stage.clientWidth,height=canvasRect.height/scale||stage.clientHeight;
    for(const group of accidentLayer.children){if(!group.visible)continue;const {kind,particles,light,footprint,pin,vfx}=group.userData;
      footprint.material.opacity=.65+.28*Math.sin(time*5);footprint.scale.setScalar(1+.12*Math.sin(time*4));light.intensity=(kind==='external-fire'?5:2.5)+1.1*Math.sin(time*11);
      for(const part of particles){const {mesh,type,phase=0,offset=0}=part;
        if(type==='flame'){mesh.position.x=part.baseX+Math.sin(time*4+phase)*.28;mesh.position.z=part.baseZ+Math.cos(time*3+phase)*.18;mesh.scale.y=.88+.22*Math.sin(time*6+phase);mesh.rotation.z=Math.sin(time*3.8+phase)*.18;}
        else if(type==='smoke'){const progress=(time*.24+phase)%1;mesh.position.set(Math.sin(offset+time*.55)*(.3+progress*.8),2.5+progress*5,Math.cos(offset+time*.4)*(.2+progress*.55));const size=.55+progress*1.8;mesh.scale.set(size,size*.75,size);mesh.material.opacity=.22*(1-progress);}
        else if(type==='jet'){const progress=(time*.45+phase)%1;mesh.position.set(progress*3.7,progress*4.9+.35,Math.sin(offset+time*.8)*progress*.75);const size=.27+progress*.55;mesh.scale.set(size,size,1);mesh.material.opacity=.9*(1-progress*.65);}
        else if(type==='halo'){mesh.material.opacity=.55+.18*Math.sin(time*7);mesh.scale.setScalar((kind==='external-fire'?5.2:3.5)*(1+.12*Math.sin(time*5)));}
      }
      const projected=group.position.clone().add(new THREE.Vector3(0,kind==='external-fire'?4.9:4.3,0)).project(camera);
      const visible=projected.z>-1&&projected.z<1&&Math.abs(projected.x)<1.1&&Math.abs(projected.y)<1.1;
      pin.hidden=!visible;if(visible){pin.style.left=`${(canvasRect.left-stageRect.left)/scale+(projected.x+1)*.5*width}px`;pin.style.top=`${(canvasRect.top-stageRect.top)/scale+(1-projected.y)*.5*height}px`;}
      const source=group.position.clone().add(new THREE.Vector3(0,.8,0)).project(camera);
      const sourceVisible=source.z>-1&&source.z<1&&Math.abs(source.x)<1.1&&Math.abs(source.y)<1.1;
      vfx.hidden=!sourceVisible;if(sourceVisible){vfx.style.left=`${(canvasRect.left-stageRect.left)/scale+(source.x+1)*.5*width}px`;vfx.style.top=`${(canvasRect.top-stageRect.top)/scale+(1-source.y)*.5*height}px`;}
    }
  }
  function updateEffectRanges(hazop){
    const releases=(hazop?.releases||[]).filter(r=>r.consequence?.status==='calculated');
    const liveIds=new Set(releases.filter(r=>Number(r.consequence.sampled_effect_radius_m)>0).map(r=>r.release_id));for(const [id,ring] of effectRings){if(!liveIds.has(id)){effectLayer.remove(ring);ring.geometry.dispose();effectRings.delete(id);}}
    for(const release of releases.filter(r=>Number(r.consequence.sampled_effect_radius_m)>0)){
      const radius=Math.min(12,Number(release.consequence.sampled_effect_radius_m));let ring=effectRings.get(release.release_id);
      if(!ring){ring=new THREE.Mesh(new THREE.RingGeometry(.91,1,64),new THREE.MeshBasicMaterial({color:0xff754e,transparent:true,opacity:.82,side:THREE.DoubleSide,depthWrite:false,depthTest:false}));ring.rotation.x=-Math.PI/2;ring.renderOrder=50;effectLayer.add(ring);effectRings.set(release.release_id,ring);}
      const anchor=accidentAnchors[release.component_id]||[0,0,0];ring.position.set(anchor[0],.09,anchor[2]);ring.scale.set(radius,radius,1);
    }
    if(!releases.length){rangeBadge.hidden=true;return;}
    const consequence=releases[0].consequence;rangeBadge.hidden=false;rangeBadge.textContent=Number(consequence.sampled_effect_radius_m)>0?`피해영향예측 표본 영향 ${Number(consequence.sampled_effect_radius_m).toFixed(1)} m${consequence.effect_range_status==='BEYOND_SAMPLED_POINTS'?' 이상':''} · 5 kW/m² / 5 kPa · 배치 개념 표시`:`피해영향예측 관측점 ${Number(consequence.sampled_max_distance_m).toFixed(1)} m까지 5 kW/m²·5 kPa 미달 · 범위 미확정`;
  }
  function capsule(r,length,x,y,z,material,parent=scene,axis='z') {
    const obj=mesh(new THREE.CapsuleGeometry(r,length,8,32),material,parent); obj.position.set(x,y,z);
    if(axis==='z')obj.rotation.x=Math.PI/2; if(axis==='x')obj.rotation.z=Math.PI/2; return obj;
  }
  function textTexture(text,sub='',bg='#163e39',color='#f4fbef') {
    const canvas=document.createElement('canvas'); canvas.width=512;canvas.height=192;
    const ctx=canvas.getContext('2d');ctx.fillStyle=bg;ctx.fillRect(0,0,512,192);
    ctx.fillStyle=color;ctx.textAlign='center';ctx.font='bold 64px sans-serif';ctx.fillText(text,256,92);
    ctx.font='27px monospace';ctx.fillStyle=color;ctx.globalAlpha=.8;ctx.fillText(sub,256,144);
    const tex=new THREE.CanvasTexture(canvas);tex.colorSpace=THREE.SRGBColorSpace;return tex;
  }
  function sign(text,sub,w,h,x,y,z,parent=scene,bg) {
    const obj=mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({map:textTexture(text,sub,bg),side:THREE.DoubleSide}),parent);
    obj.position.set(x,y,z);return obj;
  }
  function label(text,sub,x,y,z,parent=scene) {
    const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:textTexture(text,sub,'#f6f8ef','#214a43'),transparent:true,depthTest:true}));
    sprite.position.set(x,y,z);sprite.scale.set(3.8,1.4,1);parent.add(sprite);return sprite;
  }
  function register(id,group,title,description,tag) {
    group.userData.equipmentId=id;
    group.traverse(obj=>{if(obj.isMesh)pickMeshes.push(obj);});
    equipment.set(id,{group,title,description,tag});return group;
  }
  function led(group,x,y,z,id) {
    const material=new THREE.MeshStandardMaterial({color:0x6a9585,emissive:0x244a3c,emissiveIntensity:.3});
    const obj=mesh(new THREE.SphereGeometry(.085,12,8),material,group);obj.position.set(x,y,z);statusLights.push({material,id});
  }
  function pipe(points,color,id,rad=.065) {
    const curve=createPipeCurve(points);
    const material=mat(color,.65,.3);
    material.transparent=true;material.opacity=.65;material.depthWrite=false;
    const obj=mesh(new THREE.TubeGeometry(curve,48,rad,8,false),material);
    const particles=[];const particleMaterial=new THREE.MeshBasicMaterial({color});
    for(let i=0;i<7;i++){const dot=mesh(new THREE.SphereGeometry(rad*1.7,8,6),particleMaterial);particles.push(dot);}
    dynamicPipes.push({curve,obj,particles,id,color});return obj;
  }

  // Raised landscaped site and two traffic lanes.
  box(36,.55,27,0,-.45,0,M.concrete);
  box(33,.05,24,0,-.145,0,M.pavement);
  box(28,.13,9,2,-.04,6,M.concrete);
  box(28,.13,9,2,-.04,-6,M.concrete);
  box(32,.08,1.1,0,-.03,-11.7,M.turf);
  box(1.1,.08,21,-16,-.03,-1,M.turf);
  for(let x=-13;x<16;x+=3)box(1.6,.02,.10,x,.015,11.4,M.white);
  for(const z of [3.1,9.5])box(23,.02,.12,4,.04,z,M.white);
  for(const x of [-2,5,12])box(.12,.02,6,x,.04,6.3,M.white);
  for(let x=-8;x<14;x+=7){
    const arrow=mesh(new THREE.ConeGeometry(.42,.8,3),M.white);arrow.rotation.x=-Math.PI/2;arrow.position.set(x,.05,10.1);arrow.scale.y=.035;
    box(.16,.02,.8,x,.05,10.6,M.white);
  }

  // Canopy, exposed steel beams, lighting, dispenser islands.
  const canopy=new THREE.Group();scene.add(canopy);
  for(const x of [-3.5,12.5])for(const z of [2.6,8.6]){
    box(.35,5,.35,x,2.5,z,M.white,canopy);box(.58,.24,.58,x,.15,z,M.concrete,canopy);
  }
  const roofMaterial=mat(0xeff4e8,.15,.38);
  box(18.4,.38,7.6,4.5,5.15,5.6,roofMaterial,canopy);
  box(18.5,.52,.12,4.5,5.12,9.44,M.green,canopy);
  box(.12,.52,7.6,-4.74,5.12,5.6,M.green,canopy);
  for(const z of [3,5.6,8.2])box(17.4,.16,.15,4.5,4.92,z,M.frame,canopy);
  sign('H₂ STATION','700 BAR / CLEAN MOBILITY',7,.85,4.5,5.14,9.515,canopy);
  const nightLights=[];
  for(const x of [0,7]){
    box(1.5,.03,.3,x,4.91,5.7,M.white,canopy);
    const light=new THREE.PointLight(0xc0ffed,0,13,2);light.position.set(x,4.7,5.6);scene.add(light);nightLights.push(light);
  }
  function dispenser(x,id) {
    const g=new THREE.Group();g.position.set(x,0,4.25);scene.add(g);
    box(2.8,.2,1.45,0,.1,0,M.white,g);box(.95,2.05,.68,0,1.18,0,M.white,g);
    box(1.01,.46,.72,0,1.98,0,M.green,g);box(.67,.44,.015,0,1.51,.35,M.dark,g);
    sign('H70','700 BAR',.68,.25,0,2,.368,g);
    sign('READY','H2 / DISPENSING',.61,.21,0,1.52,.365,g,'#152f2f');
    box(.15,.12,.025,-.24,1.07,.365,M.red,g);box(.35,.1,.025,.12,1.07,.365,M.frame,g);
    const hoseCurve=new THREE.CatmullRomCurve3([new THREE.Vector3(.5,1.7,0),new THREE.Vector3(.95,1.5,.15),new THREE.Vector3(1.1,.35,.5),new THREE.Vector3(.75,.3,1),new THREE.Vector3(.68,1.0,1.8)]);
    mesh(new THREE.TubeGeometry(hoseCurve,36,.042,8,false),M.black,g);
    const parkedNozzle=box(.08,.16,.32,.68,1,1.8,M.steel,g);parkedNozzle.userData.parkedNozzle=true;led(g,.32,1.1,.37,'fueling');
    for(const dx of [-1.1,1.1])for(const dz of [-.55,.55]){
      cylinder(.10,.8,dx,.55,dz,M.yellow,g);cylinder(.105,.18,dx,.58,dz,M.black,g);
    }
    return register(id,g,'H70 디스펜서','PCV로 충전 유량을 조절하고 프리쿨러를 거친 수소를 호스와 노즐로 차량에 공급합니다.','DISPENSING / 700 BAR');
  }
  dispenser(0,'dispenser');dispenser(8,'standby');

  // Recognizable passenger FCEV silhouette with glass, rims, lamps and inlet.
  const car=new THREE.Group();car.position.set(2.8,.03,7.0);scene.add(car);
  const bodyShape=new THREE.Shape();bodyShape.moveTo(-2.45,.43);bodyShape.quadraticCurveTo(-2.47,.79,-2.28,.95);bodyShape.quadraticCurveTo(-1.92,1.02,-1.35,1.04);bodyShape.quadraticCurveTo(-1.06,1.50,-.75,1.67);bodyShape.quadraticCurveTo(.08,1.80,.78,1.67);bodyShape.quadraticCurveTo(1.13,1.49,1.45,1.09);bodyShape.quadraticCurveTo(2.04,1.02,2.30,.91);bodyShape.quadraticCurveTo(2.48,.76,2.45,.51);bodyShape.lineTo(2.32,.38);bodyShape.lineTo(-2.30,.38);bodyShape.closePath();
  const body=mesh(new THREE.ExtrudeGeometry(bodyShape,{depth:1.7,bevelEnabled:true,bevelThickness:.10,bevelSize:.10,bevelSegments:3,steps:1}),mat(0xe7edf0,.45,.25),car);body.position.z=-.85;
  for(const side of [-1,1]){
    const glassShape=new THREE.Shape();glassShape.moveTo(-1.1,1.08);glassShape.lineTo(-.68,1.55);glassShape.lineTo(.70,1.55);glassShape.lineTo(1.19,1.08);glassShape.closePath();
    const glass=mesh(new THREE.ShapeGeometry(glassShape),M.glass,car);glass.position.z=side*.965;glass.material.side=THREE.DoubleSide;
    box(.055,.48,.04,.15,1.30,side*.99,M.dark,car);
    for(const x of [-1.55,1.52]){
      cylinder(.42,.21,x,.43,side*.90,M.black,car,'z');cylinder(.29,.225,x,.43,side*.91,M.steel,car,'z');
      cylinder(.10,.235,x,.43,side*.91,M.dark,car,'z');
      for(let k=0;k<5;k++){const spoke=box(.045,.50,.01,x,.43,side*1.035,M.white,car);spoke.rotation.z=k*Math.PI/5;}
    }
    box(.26,.05,.03,-.35,1.03,side*.98,M.steel,car);box(.23,.06,.03,.85,1.03,side*.98,M.steel,car);
    box(.23,.1,.18,.99,1.16,side*1.08,M.white,car);
  }
  box(.1,.18,1.1,2.45,.81,0,M.white,car);box(.08,.17,.5,-2.45,.82,.56,M.red,car);
  box(.08,.17,.5,-2.45,.82,-.56,M.red,car);box(.03,.20,.8,2.51,.58,0,M.dark,car);
  sign('H₂','FCEV',.5,.2,.7,.72,.985,car,'#e6edf0');
  register('vehicle',car,'연료전지 차량 · Type IV 탱크','수소 가스·HDPE 라이너·CFRP 쉘의 열관성과 열전달을 계산합니다. 차량 압력과 SOC는 실제 시뮬레이션 결과입니다.','VEHICLE / TYPE IV');

  // Rear equipment yard: concrete skids, cylinder cascade and manifolds.
  function bank(x,name,color,tag) {
    const g=new THREE.Group();g.position.set(x,0,-6);scene.add(g);
    box(3.0,.24,5.0,0,.12,0,M.white,g);
    for(const xx of [-1.1,1.1])for(const zz of [-1.7,1.7])box(.12,3.3,.12,xx,1.75,zz,M.frame,g);
    for(const y of [.65,1.6,2.55]){
      box(2.3,.10,.10,0,y-.3,-1.7,M.frame,g);box(2.3,.10,.10,0,y-.3,1.7,M.frame,g);
      for(const xx of [-.52,.52]){
        capsule(.32,3.2,xx,y,0,M.steel,g);
        for(const zz of [-1.3,1.3])cylinder(.333,.08,xx,y,zz,M.frame,g,'z');
        cylinder(.07,.25,xx,y,1.85,M.steel,g,'z');
        box(.13,.08,.12,xx,y+.08,2.0,M.red,g);
      }
    }
    cylinder(.045,2.9,.99,1.65,2.03,M.steel,g);
    sign(name.toUpperCase(),tag,1.7,.55,0,3.42,1.72,g,color);
    led(g,.96,3.13,1.79,name);
    register(name,g,`${name==='low'?'저압':name==='medium'?'중압':'고압'} 캐스케이드 뱅크`,'세 뱅크를 차량·호스 압력에 따라 순차 선택합니다. 개별 용기는 참조 모델의 집합 저장용적을 시각적으로 표현합니다.','CASCADE / '+tag);
  }
  bank(-1,'low','#437b67','LOW');bank(3,'medium','#257e7c','MID');bank(7,'high','#a97a32','HIGH');

  const compressor=new THREE.Group();compressor.position.set(-6.4,0,-6);scene.add(compressor);
  box(3.4,.25,4.4,0,.125,0,M.white,compressor);
  box(2.9,2.65,3.9,0,1.58,0,M.green,compressor);
  box(2.94,.14,3.94,0,2.96,0,M.white,compressor);
  for(let i=0;i<11;i++)box(1.1,.045,.025,-.62,.72+i*.12,1.963,M.frame,compressor);
  box(.56,.77,.025,.8,1.7,1.966,M.white,compressor);sign('CMP','3-STAGE',1.3,.48,-.3,2.5,1.978,compressor);
  for(let i=0;i<3;i++)cylinder(.15,.35,-.8+i*.65,3.1,-.8,M.steel,compressor);
  led(compressor,.92,2.25,1.99,'compressor');
  register('compressor',compressor,'다단 수소 압축기','3단 압축 및 중간냉각, 등엔트로피 효율, 체적효율과 전동기 전력을 계산해 선택된 저장 뱅크를 재충전합니다.','COMPRESSION / 3 STAGES');

  const cooler=new THREE.Group();cooler.position.set(11,0,-6);scene.add(cooler);
  box(2.7,.24,4.1,0,.12,0,M.white,cooler);box(2.3,2.25,3.5,0,1.37,0,M.white,cooler);
  for(const z of [-.9,.8]){cylinder(.7,.06,0,2.54,z,M.frame,cooler);for(let i=0;i<8;i++){const blade=box(.09,.025,1.25,0,2.58,z,M.black,cooler);blade.rotation.y=i*Math.PI/8;}}
  for(let i=0;i<12;i++)box(1.65,.045,.02,0,.63+i*.10,1.765,M.frame,cooler);
  sign('−40°C','PRECOOLER',1.5,.54,0,2.16,1.785,cooler);led(cooler,.95,2.16,1.79,'fueling');
  register('cooler',cooler,'프리쿨러 · 냉동기','유한 UA와 냉매 열용량으로 수소 출구온도 및 열제거를 계산합니다. 냉동기 팬과 코일은 시각 모델입니다.','THERMAL / PRECOOLING');
  cooler.userData.processPorts=COOLING_PROCESS_PORTS;

  // Delivered-gas tube trailer, unloading skid and tractor.
  const trailer=new THREE.Group();trailer.position.set(-12,0,-5.7);scene.add(trailer);
  box(2.6,.28,7.5,0,.88,0,M.frame,trailer);
  for(const x of [-.83,0,.83])for(const y of [1.45,2.27,3.09])capsule(.34,6.1,x,y,0,M.white,trailer);
  for(const z of [-2.8,0,2.8]){box(2.6,.1,.12,0,3.58,z,M.frame,trailer);for(const x of [-1.2,1.2])box(.12,2.75,.12,x,2.15,z,M.frame,trailer);}
  for(const x of [-1.35,1.35])for(const z of [-2.7,-1.6]){cylinder(.46,.27,x,.49,z,M.black,trailer,'x');cylinder(.24,.29,x,.49,z,M.steel,trailer,'x');}
  box(2.3,1.8,2.0,0,1.72,4.8,M.green,trailer);box(1.9,.70,.03,0,2.03,5.82,M.glass,trailer);
  box(2.35,.18,.18,0,.91,5.9,M.steel,trailer);for(const x of [-1.15,1.15])cylinder(.43,.3,x,.46,4.65,M.black,trailer,'x');
  label('H₂ SUPPLY','TUBE TRAILER',0,4.28,0,trailer);
  register('supply',trailer,'기체수소 공급 · 튜브트레일러','외부 공급 수소를 압축기 흡입으로 연결하는 참조 공급 설비입니다. 현재 계산 모델에서는 지정 압력·온도 경계조건입니다.','SUPPLY / GH2 DELIVERY');

  const cabinet=new THREE.Group();cabinet.position.set(14,0,-4.5);scene.add(cabinet);
  box(1.65,2.5,1.2,0,1.3,0,M.white,cabinet);sign('PLC','SAFETY / ESD',1.1,.42,0,2,.615,cabinet);
  box(.56,.58,.03,0,1.38,.615,M.dark,cabinet);led(cabinet,.5,1.86,.65,'safety');
  register('safety',cabinet,'독립 안전 PLC','압력·온도·유량 불균형·수소농도를 감시하고 래칭 ESD를 수행합니다. 안전 계층은 공정 제어기와 분리되어 있습니다.','PROTECTION / LATCHED ESD');
  const vent=new THREE.Group();vent.position.set(14,0,-9);scene.add(vent);
  box(1.1,.3,1.1,0,.15,0,M.concrete,vent);cylinder(.11,7.8,0,4,0,M.steel,vent);cylinder(.17,.18,0,7.98,0,M.frame,vent);
  for(const x of [-.7,.7]){const support=box(.035,4.9,.035,x/2,2.5,0,M.frame,vent);support.rotation.z=x>0?-.14:.14;}
  register('vent',vent,'벤트스택','방출 계통의 시각적 표시입니다. 실제 벤트스택 상세 배관·배압·분산 설계는 이 3D 배치에 포함되지 않습니다.','VENT / VISUAL REFERENCE');

  // Fence, barrier wall, lane furniture and greenery create a recognizable site.
  for(let x=-15;x<=15;x+=2.5){cylinder(.035,3.1,x,1.55,-11.1,M.frame);}
  for(const y of [.35,1.55,2.75])box(30,.03,.035,0,y,-11.1,M.steel);
  for(let x=-15;x<15;x+=.4)box(.012,2.5,.01,x,1.55,-11.1,M.steel);
  box(23,1.85,.20,3,.93,-1.7,M.concrete);box(23,.06,.35,3,1.9,-1.7,M.white);
  sign('AUTHORIZED PERSONNEL ONLY','HYDROGEN PROCESS AREA',3,.56,10.7,1.15,-1.58);
  for(const x of [-4,12.7]){
    cylinder(.06,1.2,x,.6,2,M.frame);box(.25,.31,.12,x,1.25,2,M.yellow);box(.08,.1,.035,x,1.27,2.08,M.red);
  }
  for(const x of [-14.5,-8,1,10,15]){
    cylinder(.13,1.8,x,.9,-12.05,M.trunk);
    const crown=mesh(new THREE.IcosahedronGeometry(1.25,1),M.leaf);crown.position.set(x,2.35,-12.05);crown.scale.set(1,1.2,1);
  }
  for(const z of [5,10]){
    cylinder(.07,5.9,-15,2.95,z,M.frame);box(.8,.12,.35,-14.7,5.88,z,M.white);
    const light=new THREE.PointLight(0xffe1b0,0,18,2);light.position.set(-14.7,5.7,z);scene.add(light);nightLights.push(light);
  }

  // Detailed perimeter landscaping, contextual buildings and animated pedestrians.
  // These visual-only objects fade automatically when they obstruct the active camera view.
  const ambientOccluders=[];
  const pedestrianActors=[];
  const trafficVehicles=[];
  const ambientMaterial=(color,options={})=>new THREE.MeshStandardMaterial({
    color,roughness:options.roughness??.82,metalness:options.metalness??0,
    emissive:options.emissive??0x000000,emissiveIntensity:options.emissiveIntensity??0,
    transparent:true,opacity:1
  });
  const registerAmbientOccluder=(group,radius,centerY,fadeOpacity)=>{
    group.userData.occlusionRadius=radius;
    group.userData.occlusionCenter=new THREE.Vector3(0,centerY,0);
    group.userData.fadeOpacity=fadeOpacity;
    group.userData.currentOpacity=1;
    ambientOccluders.push(group);
    return group;
  };
  const localBox=(group,w,h,d,x,y,z,material)=>{
    const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material);
    mesh.position.set(x,y,z);mesh.castShadow=true;mesh.receiveShadow=true;group.add(mesh);return mesh;
  };
  const localCylinder=(group,rTop,rBottom,h,x,y,z,material,segments=14)=>{
    const mesh=new THREE.Mesh(new THREE.CylinderGeometry(rTop,rBottom,h,segments),material);
    mesh.position.set(x,y,z);mesh.castShadow=true;mesh.receiveShadow=true;group.add(mesh);return mesh;
  };
  function detailedTree(x,z,scale=1){
    const tree=new THREE.Group();tree.position.set(x,0,z);scene.add(tree);
    const bark=ambientMaterial(0x5d422b,{roughness:1});
    const barkLight=ambientMaterial(0x7a5837,{roughness:1});
    const leafDark=ambientMaterial(0x315b3c,{roughness:1});
    const leafMid=ambientMaterial(0x4f7b4e,{roughness:1});
    const leafLight=ambientMaterial(0x6e9360,{roughness:1});
    localCylinder(tree,.18*scale,.28*scale,2.8*scale,0,1.4*scale,0,bark,18);
    localCylinder(tree,.205*scale,.225*scale,.55*scale,0,1.05*scale,0,barkLight,18);
    const branch=(from,to,radius)=>{
      const direction=to.clone().sub(from);const midpoint=from.clone().add(to).multiplyScalar(.5);
      const mesh=new THREE.Mesh(new THREE.CylinderGeometry(radius*.72,radius,direction.length(),10),bark);
      mesh.position.copy(midpoint);mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),direction.clone().normalize());
      mesh.castShadow=true;tree.add(mesh);
    };
    const branches=[
      [new THREE.Vector3(0,2.05*scale,0),new THREE.Vector3(.72*scale,3.05*scale,.18*scale),.095*scale],
      [new THREE.Vector3(0,2.18*scale,0),new THREE.Vector3(-.68*scale,3.18*scale,.12*scale),.09*scale],
      [new THREE.Vector3(0,2.38*scale,0),new THREE.Vector3(.18*scale,3.5*scale,-.66*scale),.082*scale],
      [new THREE.Vector3(0,2.45*scale,0),new THREE.Vector3(-.16*scale,3.62*scale,.58*scale),.078*scale]
    ];
    branches.forEach(([from,to,r])=>branch(from,to,r));
    const crowns=[
      [-.62,3.35,.12,.92,leafDark],[.62,3.28,.04,.98,leafMid],[0,3.75,-.5,1.02,leafDark],
      [.08,4.02,.34,1.08,leafMid],[-.28,3.65,.62,.84,leafLight],[.42,3.72,.55,.78,leafLight]
    ];
    crowns.forEach(([cx,cy,cz,size,material])=>{
      const crown=new THREE.Mesh(new THREE.IcosahedronGeometry(size*scale,2),material);
      crown.position.set(cx*scale,cy*scale,cz*scale);crown.scale.set(1,.78,1);crown.castShadow=true;crown.receiveShadow=true;tree.add(crown);
    });
    return registerAmbientOccluder(tree,1.2*scale,2.5*scale,.24);
  }
  function contextBuilding(x,z,width,depth,height,color,signText){
    const building=new THREE.Group();building.position.set(x,0,z);scene.add(building);
    const facade=ambientMaterial(color,{roughness:.9});
    const trim=ambientMaterial(0xd7d3c8,{roughness:.72});
    const roof=ambientMaterial(0x384348,{roughness:.62,metalness:.18});
    const glass=ambientMaterial(0x6f98a5,{roughness:.22,metalness:.08,emissive:0x183840,emissiveIntensity:.28});
    localBox(building,width,height,depth,0,height/2,0,facade);
    localBox(building,width+.25,.22,depth+.25,0,height+.08,0,roof);
    localBox(building,width+.08,.20,depth+.10,0,.16,0,trim);
    const cols=Math.max(2,Math.floor(width/1.55));
    for(let floor=0;floor<Math.max(1,Math.floor((height-1)/1.55));floor++){
      for(let col=0;col<cols;col++){
        const wx=-width/2+(col+.5)*width/cols;
        localBox(building,.68,.72,.035,wx,1.15+floor*1.48,depth/2+.022,glass);
      }
    }
    localBox(building,Math.min(width*.55,4.2),.42,.10,0,height-.48,depth/2+.09,trim);
    const signCanvas=document.createElement('canvas');signCanvas.width=512;signCanvas.height=96;
    const ctx=signCanvas.getContext('2d');ctx.fillStyle='#e8e5da';ctx.fillRect(0,0,512,96);ctx.fillStyle='#173a3a';ctx.font='700 34px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(signText,256,50);
    const signMap=new THREE.CanvasTexture(signCanvas);const signMat=new THREE.MeshBasicMaterial({map:signMap,transparent:true,opacity:1});
    localBox(building,Math.min(width*.5,3.8),.48,.025,0,height-.48,depth/2+.151,signMat);
    return registerAmbientOccluder(building,Math.max(width,depth)*.58,height*.52,.16);
  }
  function operationsAnnex(x,z){
    const building=new THREE.Group();building.position.set(x,0,z);scene.add(building);
    const brick=ambientMaterial(0xa88469,{roughness:.96});
    const mortar=ambientMaterial(0xd8d0c1,{roughness:.92});
    const roof=ambientMaterial(0x40545a,{roughness:.62,metalness:.28});
    const glass=ambientMaterial(0x6f99a5,{roughness:.16,metalness:.12,emissive:0x183b42,emissiveIntensity:.25});
    const frame=ambientMaterial(0x26343a,{roughness:.55,metalness:.35});
    localBox(building,6.2,3.05,3.4,0,1.525,0,brick);
    for(let y=.35;y<2.9;y+=.38)localBox(building,6.24,.018,3.43,0,y,0,mortar);
    const leftRoof=localBox(building,3.35,.15,3.75,-1.48,3.30,0,roof);leftRoof.rotation.z=-.23;
    const rightRoof=localBox(building,3.35,.15,3.75,1.48,3.30,0,roof);rightRoof.rotation.z=.23;
    localBox(building,1.15,2.25,.06,1.85,1.16,1.73,glass);
    localBox(building,1.27,.10,.12,1.85,2.31,1.77,frame);
    localBox(building,1.45,.13,.70,1.85,2.48,1.95,roof);
    for(const wx of [-2.1,-.75,.65]){
      localBox(building,.90,.95,.045,wx,1.62,1.735,glass);
      localBox(building,.05,.98,.055,wx,1.62,1.77,frame);
      localBox(building,.93,.05,.055,wx,1.62,1.77,frame);
    }
    localBox(building,2.3,.34,.09,-1.35,2.68,1.79,mortar);
    const annexSign=document.createElement('canvas');annexSign.width=512;annexSign.height=96;
    const ac=annexSign.getContext('2d');ac.fillStyle='#e6dfd0';ac.fillRect(0,0,512,96);ac.fillStyle='#173a3a';ac.font='700 31px sans-serif';ac.textAlign='center';ac.textBaseline='middle';ac.fillText('STATION OPERATIONS',256,50);
    localBox(building,2.15,.28,.025,-1.35,2.68,1.85,new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(annexSign),transparent:true}));
    localBox(building,1.05,.38,.72,-1.72,3.62,-.55,frame);
    for(let i=0;i<6;i++)localBox(building,.055,.30,.74,-2.10+i*.15,3.63,-.55,mortar);
    return registerAmbientOccluder(building,3.5,1.9,.15);
  }
  function serviceWorkshop(x,z){
    const workshop=new THREE.Group();workshop.position.set(x,0,z);scene.add(workshop);
    const wall=ambientMaterial(0x8d9998,{roughness:.72,metalness:.12});
    const dark=ambientMaterial(0x2e393c,{roughness:.58,metalness:.38});
    const shutter=ambientMaterial(0xbfc4c0,{roughness:.58,metalness:.30});
    const safety=ambientMaterial(0xe3a52b,{roughness:.68});
    localBox(workshop,7.4,3.65,4.15,0,1.825,0,wall);
    localBox(workshop,7.7,.22,4.45,0,3.72,0,dark);
    for(const dx of [-2.05,1.25]){
      localBox(workshop,2.55,2.55,.08,dx,1.40,2.105,shutter);
      for(let sy=.28;sy<2.65;sy+=.22)localBox(workshop,2.58,.025,.095,dx,sy,2.16,dark);
      localBox(workshop,.10,2.65,.16,dx-1.34,1.39,2.15,dark);
      localBox(workshop,.10,2.65,.16,dx+1.34,1.39,2.15,dark);
    }
    localBox(workshop,.72,2.2,.07,3.18,1.18,2.11,dark);
    localBox(workshop,.36,.16,.025,3.18,1.38,2.16,safety);
    for(let i=0;i<7;i++)localBox(workshop,.72,.055,.07,-3.25,.52+i*.36,-2.10,dark);
    for(const dx of [-2.4,0,2.4]){
      localCylinder(workshop,.20,.24,.45,dx,4.02,-.55,dark,16);
      localCylinder(workshop,.28,.28,.12,dx,4.27,-.55,shutter,18);
    }
    localBox(workshop,3.4,.30,.12,-.55,3.23,2.18,dark);
    const workshopSign=document.createElement('canvas');workshopSign.width=512;workshopSign.height=80;
    const wc=workshopSign.getContext('2d');wc.fillStyle='#26363a';wc.fillRect(0,0,512,80);wc.fillStyle='#f0b53e';wc.font='700 29px sans-serif';wc.textAlign='center';wc.textBaseline='middle';wc.fillText('SERVICE / INSPECTION',256,42);
    localBox(workshop,3.2,.28,.025,-.55,3.23,2.25,new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(workshopSign),transparent:true}));
    return registerAmbientOccluder(workshop,4.2,2.05,.14);
  }
  function electricalYard(x,z){
    const yard=new THREE.Group();yard.position.set(x,0,z);scene.add(yard);
    const concrete=ambientMaterial(0xa9aaa3,{roughness:1});
    const steel=ambientMaterial(0x566268,{roughness:.48,metalness:.58});
    const transformer=ambientMaterial(0x60756a,{roughness:.61,metalness:.34});
    const ceramic=ambientMaterial(0x784b35,{roughness:.55});
    const warning=ambientMaterial(0xe5b12c,{roughness:.65});
    localBox(yard,5.2,.14,4.3,0,.07,0,concrete);
    for(const px of [-2.55,2.55])for(let pz=-2.05;pz<=2.05;pz+=.68)localCylinder(yard,.035,.035,1.7,px,.86,pz,steel,8);
    for(const pz of [-2.05,2.05])for(let px=-2.55;px<=2.55;px+=.68)localCylinder(yard,.035,.035,1.7,px,.86,pz,steel,8);
    for(const y of [.40,.88,1.36]){
      localBox(yard,5.15,.025,.025,0,y,-2.05,steel);localBox(yard,5.15,.025,.025,0,y,2.05,steel);
      localBox(yard,.025,.025,4.1,-2.55,y,0,steel);localBox(yard,.025,.025,4.1,2.55,y,0,steel);
    }
    for(const tx of [-1.25,1.25]){
      localBox(yard,1.55,1.32,1.25,tx,.77,0,transformer);
      for(let fin=-.55;fin<=.55;fin+=.18)localBox(yard,.04,1.08,1.38,tx+fin,.77,0,steel);
      for(const bx of [-.4,0,.4]){
        localCylinder(yard,.07,.10,.40,tx+bx,1.66,0,ceramic,12);
        localCylinder(yard,.035,.035,.20,tx+bx,1.95,0,steel,10);
      }
      localBox(yard,.28,.22,.035,tx,1.02,.65,warning);
    }
    localBox(yard,.95,1.75,.62,0,.94,-1.52,steel);
    localBox(yard,.50,.28,.035,0,1.12,-1.85,warning);
    return registerAmbientOccluder(yard,3.2,1.0,.20);
  }
  function gateHouse(x,z){
    const gate=new THREE.Group();gate.position.set(x,0,z);scene.add(gate);
    const frame=ambientMaterial(0x25383b,{roughness:.50,metalness:.30});
    const wall=ambientMaterial(0xd6d4c9,{roughness:.88});
    const glass=ambientMaterial(0x729aa5,{roughness:.12,metalness:.10,emissive:0x173b42,emissiveIntensity:.30});
    const barrier=ambientMaterial(0xe8e5dc,{roughness:.62});
    const red=ambientMaterial(0xcf4c3d,{roughness:.65});
    localBox(gate,2.35,2.35,1.85,0,1.175,0,wall);
    localBox(gate,2.72,.18,2.22,0,2.43,0,frame);
    localBox(gate,1.55,1.12,.045,0,1.42,.95,glass);
    localBox(gate,.72,1.95,.055,-.73,1.05,.96,frame);
    localBox(gate,.45,.86,.055,-.73,1.28,.99,glass);
    localBox(gate,.28,1.02,.28,1.55,.51,.35,frame);
    const arm=localBox(gate,3.8,.11,.11,3.38,1.02,.35,barrier);arm.rotation.z=-.04;
    for(let stripe=-1.35;stripe<1.45;stripe+=.58)localBox(gate,.28,.125,.13,3.38+stripe,1.02+stripe*-.04,.35,red);
    localCylinder(gate,.18,.23,.22,1.55,1.15,.35,red,20);
    return registerAmbientOccluder(gate,2.1,1.25,.22);
  }
  function solarParkingCanopy(x,z){
    const canopy=new THREE.Group();canopy.position.set(x,0,z);scene.add(canopy);
    const steel=ambientMaterial(0x59656a,{roughness:.48,metalness:.55});
    const solar=ambientMaterial(0x183d51,{roughness:.22,metalness:.32,emissive:0x071820,emissiveIntensity:.16});
    const line=ambientMaterial(0xe8dfbd,{roughness:.9});
    for(const px of [-3.2,0,3.2]){
      localCylinder(canopy,.09,.12,2.9,px,1.45,0,steel,14);
      const brace=localBox(canopy,.10,1.20,.10,px+.28,2.42,0,steel);brace.rotation.z=-.48;
    }
    localBox(canopy,7.4,.15,3.25,0,3.0,0,steel);
    for(let row=0;row<2;row++)for(let col=0;col<6;col++){
      const panel=localBox(canopy,1.08,.045,1.38,-3.0+col*1.2,3.12,-.76+row*1.52,solar);panel.rotation.z=-.035;
      localBox(canopy,.025,.055,1.40,-3.0+col*1.2,3.15,-.76+row*1.52,steel);
    }
    for(const bay of [-2.4,0,2.4]){
      localBox(canopy,.09,.018,4.7,bay-1.05,.018,.15,line);localBox(canopy,.09,.018,4.7,bay+1.05,.018,.15,line);
      localBox(canopy,1.2,.022,.10,bay,.022,-1.82,line);
    }
    return registerAmbientOccluder(canopy,4.2,2.2,.20);
  }
  function steppedOffice(x,z){
    const office=new THREE.Group();office.position.set(x,0,z);scene.add(office);
    const stone=ambientMaterial(0xb9b5aa,{roughness:.84});
    const dark=ambientMaterial(0x34454a,{roughness:.48,metalness:.30});
    const glass=ambientMaterial(0x527d8d,{roughness:.14,metalness:.18,emissive:0x15333c,emissiveIntensity:.25});
    localBox(office,8.4,2.4,5.5,0,1.2,0,stone);
    localBox(office,6.2,5.0,4.5,.55,4.9,-.20,stone);
    localBox(office,4.4,4.2,3.7,1.1,9.5,-.38,dark);
    for(let floor=0;floor<7;floor++){
      const y=1.45+floor*1.32;const width=floor<2?7.2:(floor<5?5.3:3.6);
      localBox(office,width,.55,.055,floor<2?0:(floor<5?.55:1.1),y,2.78-(floor<2?0:(floor<5?.45:.82)),glass);
      for(let mullion=-width/2+.45;mullion<width/2;mullion+=.9)localBox(office,.045,.62,.08,(floor<2?0:(floor<5?.55:1.1))+mullion,y,2.84-(floor<2?0:(floor<5?.45:.82)),dark);
    }
    localBox(office,2.2,.35,1.1,-2.25,2.62,2.88,dark);
    localBox(office,1.35,2.15,.07,-2.25,1.25,2.79,glass);
    localBox(office,1.8,.65,1.3,1.25,12.0,-.35,dark);
    localCylinder(office,.08,.08,2.3,1.25,13.45,-.35,dark,10);
    return registerAmbientOccluder(office,5.1,6.4,.12);
  }
  function lShapedResearchBuilding(x,z){
    const lab=new THREE.Group();lab.position.set(x,0,z);scene.add(lab);
    const concrete=ambientMaterial(0xd0cbbf,{roughness:.88});
    const accent=ambientMaterial(0x4e716e,{roughness:.58,metalness:.12});
    const glass=ambientMaterial(0x7099a2,{roughness:.18,emissive:0x17363b,emissiveIntensity:.22});
    const roof=ambientMaterial(0x4b5558,{roughness:.62,metalness:.28});
    localBox(lab,8.6,4.4,3.2,0,2.2,0,concrete);
    localBox(lab,3.3,6.8,7.2,-2.65,3.4,-2.0,concrete);
    localBox(lab,8.85,.20,3.45,0,4.52,0,roof);
    localBox(lab,3.55,.20,7.45,-2.65,6.92,-2.0,roof);
    for(let floor=0;floor<4;floor++){
      const y=1.25+floor*1.45;
      for(let wx=-3.45;wx<=3.45;wx+=1.15)localBox(lab,.72,.70,.045,wx,y,1.63,glass);
    }
    for(let floor=0;floor<3;floor++)for(let wz=-4.6;wz<=.5;wz+=1.1)localBox(lab,.045,.68,.70,-4.32,1.3+floor*1.5,wz,glass);
    localBox(lab,2.5,2.75,.10,1.6,1.48,1.69,glass);
    localBox(lab,2.9,.30,1.15,1.6,3.0,2.02,accent);
    localBox(lab,1.2,.8,1.6,-2.6,7.45,-2.2,accent);
    localCylinder(lab,.28,.28,.5,-2.6,8.08,-2.2,roof,18);
    return registerAmbientOccluder(lab,5.7,3.8,.13);
  }
  function sawtoothWarehouse(x,z){
    const warehouse=new THREE.Group();warehouse.position.set(x,0,z);scene.add(warehouse);
    const wall=ambientMaterial(0x9ca7a5,{roughness:.72,metalness:.13});
    const roof=ambientMaterial(0x46565b,{roughness:.55,metalness:.34});
    const translucent=ambientMaterial(0x83aab1,{roughness:.22,emissive:0x18383c,emissiveIntensity:.18});
    const door=ambientMaterial(0x687378,{roughness:.58,metalness:.28});
    localBox(warehouse,12.5,3.25,6.2,0,1.625,0,wall);
    for(let bay=0;bay<5;bay++){
      const cx=-5.0+bay*2.5;
      const panelA=localBox(warehouse,2.75,.14,6.55,cx-.55,3.62,0,roof);panelA.rotation.z=-.23;
      const panelB=localBox(warehouse,1.65,.10,6.55,cx+.72,3.82,0,translucent);panelB.rotation.z=.36;
    }
    for(const dx of [-4.3,-1.45,1.45,4.3]){
      localBox(warehouse,2.25,2.45,.08,dx,1.32,3.13,door);
      for(let sy=.25;sy<2.55;sy+=.25)localBox(warehouse,2.28,.025,.10,dx,sy,3.18,roof);
    }
    localBox(warehouse,.82,2.15,.08,5.6,1.16,3.14,roof);
    for(let vx=-5.5;vx<=5.5;vx+=1.0)localBox(warehouse,.55,.35,.05,vx,2.75,-3.13,translucent);
    return registerAmbientOccluder(warehouse,7.0,2.4,.15);
  }
  function detailedRoadNetwork(){
    const roads=new THREE.Group();roads.name='surrounding-road-network';scene.add(roads);
    const asphalt=ambientMaterial(0x30383a,{roughness:.98});
    const asphaltLight=ambientMaterial(0x3b4344,{roughness:.96});
    const concrete=ambientMaterial(0xb9b8af,{roughness:1});
    const curb=ambientMaterial(0xd5d2c7,{roughness:.94});
    const white=ambientMaterial(0xf1efe4,{roughness:.88});
    const yellow=ambientMaterial(0xe4b83c,{roughness:.88});
    const drain=ambientMaterial(0x41494b,{roughness:.58,metalness:.48});
    const flatRect=(w,d,x,z,material,y=.045,rotation=0)=>{
      const mesh=new THREE.Mesh(new THREE.PlaneGeometry(w,d),material);
      mesh.rotation.set(-Math.PI/2,0,rotation);mesh.position.set(x,y,z);mesh.receiveShadow=true;roads.add(mesh);return mesh;
    };
    // Re-surface the original frontage so the former skewed crossing is completely covered.
    flatRect(78,8.6,0,19,asphalt,.052);
    flatRect(66,5.6,0,-21,asphaltLight,.047);
    flatRect(5.8,39,-27,-1,asphaltLight,.048);
    flatRect(5.8,39,27,-1,asphaltLight,.048);
    // Separate one-way entry and exit throats into the forecourt.
    flatRect(4.3,12.2,-7.2,10.7,asphalt,.057);
    flatRect(4.3,12.2,10.7,10.7,asphalt,.057);
    flatRect(5.2,2.5,-7.2,16.0,asphalt,.060);
    flatRect(5.2,2.5,10.7,16.0,asphalt,.060);
    // Continuous sidewalks and lowered curb sections at both driveways.
    flatRect(78,2.25,0,13.55,concrete,.063);
    flatRect(78,2.25,0,24.45,concrete,.063);
    flatRect(66,1.65,0,-17.35,concrete,.055);
    for(let x=-38;x<=38;x+=1.5){
      flatRect(1.42,.035,x,13.55,curb,.074);flatRect(1.42,.035,x,24.45,curb,.074);
      flatRect(1.42,.028,x,-17.35,curb,.065);
    }
    // Main-road lane edges, center dashes and rear service-road markings.
    flatRect(76,.11,0,15.05,white,.073);flatRect(76,.11,0,22.95,white,.073);
    for(let x=-36;x<=36;x+=5.0)flatRect(2.7,.13,x,19,yellow,.075);
    flatRect(64,.10,0,-18.55,white,.066);flatRect(64,.10,0,-23.45,white,.066);
    for(let x=-29;x<=29;x+=4.5)flatRect(2.4,.11,x,-21,white,.068);
    // A perpendicular zebra crossing, offset from the station driveways.
    for(let x=-20.5;x<=-14.5;x+=.82)flatRect(.48,7.05,x,19,white,.081);
    flatRect(7.1,.32,-17.5,15.7,white,.082);flatRect(7.1,.32,-17.5,22.3,white,.082);
    // Driveway stop lines, lane separators and directional arrows.
    flatRect(3.65,.32,-7.2,15.15,white,.084);flatRect(3.65,.32,10.7,15.15,white,.084);
    flatRect(.12,9.0,-7.2,9.7,yellow,.080);flatRect(.12,9.0,10.7,9.7,yellow,.080);
    const arrow=(x,z,direction)=>{
      flatRect(.28,1.65,x,z,white,.086);
      const tip=z+direction*.96;
      flatRect(.25,.95,x-.30,tip,white,.087,direction*.62);
      flatRect(.25,.95,x+.30,tip,white,.087,-direction*.62);
    };
    arrow(-7.2,11.4,-1);arrow(10.7,9.0,1);
    // Surface detail: storm drains and recessed manhole covers.
    for(const x of [-31,-23,-12,2,16,29]){
      localBox(roads,.72,.035,.28,x,.075,15.27,drain);
      for(let slot=-.25;slot<=.25;slot+=.10)localBox(roads,.025,.018,.30,x+slot,.096,15.27,asphalt);
    }
    for(const [x,z] of [[-3,17.2],[20,20.8],[-17,-20.2]]){
      const cover=localCylinder(roads,.43,.43,.035,x,.077,z,drain,28);
      for(let angle=0;angle<Math.PI*2;angle+=Math.PI/4){
        const bolt=localCylinder(roads,.025,.025,.018,x+Math.cos(angle)*.31,.102,z+Math.sin(angle)*.31,white,8);bolt.castShadow=false;
      }
      cover.castShadow=false;
    }
    // Streetlights remain outside the station boundary.
    const lamp=(x,z)=>{
      localCylinder(roads,.065,.095,4.3,x,2.15,z,drain,14);
      const arm=localBox(roads,1.05,.075,.075,x+.48,4.18,z,drain);arm.rotation.z=-.08;
      localBox(roads,.38,.10,.24,x+.94,4.08,z,white);
    };
    for(const x of [-32,-22,-12,18,28])lamp(x,12.65);
    return roads;
  }
  function createDetailedVehicle(color,style='sedan'){
    const vehicle=new THREE.Group();
    const body=ambientMaterial(color,{roughness:.43,metalness:.30});
    const trim=ambientMaterial(0x263136,{roughness:.42,metalness:.58});
    const glass=ambientMaterial(0x203b47,{roughness:.12,metalness:.18,emissive:0x0a1c24,emissiveIntensity:.20});
    const tyre=ambientMaterial(0x141719,{roughness:1});
    const hub=ambientMaterial(0xaeb4b3,{roughness:.32,metalness:.78});
    const lamp=ambientMaterial(0xf1edd2,{roughness:.22,emissive:0xffe6a5,emissiveIntensity:.60});
    const tail=ambientMaterial(0x9d302b,{roughness:.32,emissive:0x7b0804,emissiveIntensity:.55});
    const plate=ambientMaterial(0xefede3,{roughness:.72});
    const isVan=style==='van';const isSuv=style==='suv';const length=isVan?4.3:(isSuv?4.0:3.65);
    const bodyHeight=isSuv?.56:.46;const cabinHeight=isVan?1.0:(isSuv?.72:.58);
    const roofLength=isVan?2.4:(isSuv?2.15:1.85);
    localBox(vehicle,1.72,bodyHeight,length,0,.56,0,body);
    localBox(vehicle,1.64,.14,length+.12,0,.34,0,trim);
    localBox(vehicle,1.54,cabinHeight,roofLength,0,.98,isVan?-.16:-.12,glass);
    localBox(vehicle,1.58,.10,roofLength+.18,0,1.34,isVan?-.16:-.12,body);
    localBox(vehicle,1.76,.16,.18,0,.57,-length/2-.02,trim);
    localBox(vehicle,1.76,.16,.18,0,.57,length/2+.02,trim);
    localBox(vehicle,.35,.14,.05,-.52,.70,-length/2-.12,lamp);
    localBox(vehicle,.35,.14,.05,.52,.70,-length/2-.12,lamp);
    localBox(vehicle,.32,.13,.05,-.54,.70,length/2+.12,tail);
    localBox(vehicle,.32,.13,.05,.54,.70,length/2+.12,tail);
    localBox(vehicle,.44,.16,.035,0,.49,length/2+.14,plate);
    localBox(vehicle,.44,.16,.035,0,.49,-length/2-.14,plate);
    for(const wx of [-.87,.87])for(const wz of [-length*.28,length*.28]){
      const wheel=localCylinder(vehicle,.27,.27,.19,wx,.34,wz,tyre,18);wheel.rotation.z=Math.PI/2;
      const rim=localCylinder(vehicle,.15,.15,.205,wx+(wx<0?-.012:.012),.34,wz,hub,16);rim.rotation.z=Math.PI/2;
      vehicle.userData.wheels??=[];vehicle.userData.wheels.push(wheel,rim);
    }
    for(const wx of [-.96,.96]){
      const mirror=localBox(vehicle,.16,.09,.20,wx,.98,-.34,trim);mirror.rotation.y=.18*(wx<0?-1:1);
    }
    localBox(vehicle,.05,.05,.48,-.72,.73,-.34,trim);localBox(vehicle,.05,.05,.48,.72,.73,-.34,trim);
    if(isSuv){
      localBox(vehicle,.07,.07,2.0,-.58,1.43,-.08,trim);localBox(vehicle,.07,.07,2.0,.58,1.43,-.08,trim);
      localBox(vehicle,1.56,.10,.44,0,.93,length/2-.25,body);
    }
    if(isVan){
      localBox(vehicle,1.76,.72,1.62,0,1.05,.92,body);
      localBox(vehicle,.035,.70,1.5,0,1.05,.91,trim);
      localBox(vehicle,1.30,.13,.04,0,1.05,1.74,trim);
    }
    vehicle.castShadow=true;return vehicle;
  }
  function roadsideParking(x,z,rotation=0){
    const lot=new THREE.Group();lot.position.set(x,0,z);lot.rotation.y=rotation;scene.add(lot);
    const paving=ambientMaterial(0x4c5454,{roughness:.98});
    const marking=ambientMaterial(0xe9e2c8,{roughness:.90});
    const bodyColors=[0x335d70,0xc3c0b4,0x8a3e36,0x53614c,0x303438];
    localBox(lot,10.8,.10,6.2,0,.05,0,paving);
    for(let bay=-4.2;bay<=4.2;bay+=2.1){
      localBox(lot,.065,.018,5.2,bay,.115,0,marking);
      localBox(lot,1.0,.018,.10,bay+.95,.116,-2.25,marking);
    }
    const styles=['sedan','suv','van','sedan','suv'];
    [-4.2,-2.1,0,2.1,4.2].forEach((px,index)=>{
      const car=createDetailedVehicle(bodyColors[index%bodyColors.length],styles[index]);
      car.position.set(px,.12,index%2?-.15:.15);car.rotation.y=index%2?Math.PI:0;car.scale.setScalar(styles[index]==='van'?.88:.94);lot.add(car);
    });
    return registerAmbientOccluder(lot,5.8,.8,.28);
  }
  function busShelter(x,z){
    const shelter=new THREE.Group();shelter.position.set(x,0,z);scene.add(shelter);
    const frame=ambientMaterial(0x34464a,{roughness:.48,metalness:.48});
    const glass=ambientMaterial(0x76a1a9,{roughness:.12,metalness:.10,emissive:0x17363c,emissiveIntensity:.18});
    const seat=ambientMaterial(0x8c633f,{roughness:.85});
    localBox(shelter,4.3,.16,1.45,0,2.55,0,frame);
    for(const px of [-2.0,2.0])localCylinder(shelter,.055,.075,2.5,px,1.25,0,frame,12);
    localBox(shelter,4.0,2.15,.045,0,1.38,.60,glass);
    localBox(shelter,3.0,.16,.48,0,.64,.12,seat);
    localBox(shelter,3.0,.35,.10,0,.83,.35,seat);
    localBox(shelter,.42,2.15,.08,-1.65,1.38,.54,frame);
    return registerAmbientOccluder(shelter,2.4,1.35,.24);
  }
  function passingRoadVehicle(name,start,end,color,style,phase,speed){
    const vehicle=createDetailedVehicle(color,style);vehicle.name=name;vehicle.position.copy(start);scene.add(vehicle);
    vehicle.userData.traffic={start:start.clone(),end:end.clone(),phase,speed};
    trafficVehicles.push(vehicle);return vehicle;
  }
  function pedestrian(name,start,end,shirtColor,phase,speed){
    const actor=new THREE.Group();actor.name=name;scene.add(actor);
    const skin=ambientMaterial(0xc99572,{roughness:.9});
    const shirt=ambientMaterial(shirtColor,{roughness:.88});
    const trousers=ambientMaterial(0x28323a,{roughness:.9});
    const shoes=ambientMaterial(0x171a1b,{roughness:1});
    localCylinder(actor,.22,.18,.62,0,1.13,0,shirt,16);
    const head=new THREE.Mesh(new THREE.SphereGeometry(.16,16,12),skin);head.position.y=1.58;head.castShadow=true;actor.add(head);
    const armL=localCylinder(actor,.052,.045,.55,-.25,1.13,0,skin,10);
    const armR=localCylinder(actor,.052,.045,.55,.25,1.13,0,skin,10);
    const legL=localCylinder(actor,.07,.06,.67,-.105,.49,0,trousers,10);
    const legR=localCylinder(actor,.07,.06,.67,.105,.49,0,trousers,10);
    localBox(actor,.15,.09,.27,-.105,.10,.06,shoes);localBox(actor,.15,.09,.27,.105,.10,.06,shoes);
    actor.scale.setScalar(.95);actor.position.copy(start);
    actor.userData.walk={start:start.clone(),end:end.clone(),phase,speed,armL,armR,legL,legR};
    pedestrianActors.push(actor);return registerAmbientOccluder(actor,.48,.9,.34);
  }
  detailedTree(-27,-9,1.05);detailedTree(-24,-16,.88);detailedTree(-31,-22,1.12);
  detailedTree(28,-10,.95);detailedTree(24,-17,1.08);detailedTree(31,-23,1.0);
  contextBuilding(-21,-25,8.8,4.8,3.6,0xc6c0ad,'H2 MOBILITY LAB');
  contextBuilding(-8,-28,11.5,5.2,6.8,0xb7c0ba,'ENERGY SERVICE');
  contextBuilding(7,-27,7.5,4.5,4.4,0xc8b8a6,'MAINTENANCE');
  contextBuilding(-29,-16,6.2,8.8,5.8,0xb8aea0,'CONTROL OFFICE');
  contextBuilding(28,-17,6.8,9.2,8.2,0xb5c2c3,'TECH CENTER');
  contextBuilding(-30,-3,7.0,5.8,3.2,0xc8c1b1,'SITE SERVICES');
  contextBuilding(30,-4,7.4,5.8,4.8,0xbfc4b5,'LOGISTICS');
  operationsAnnex(-19,-14);
  serviceWorkshop(17,-14);
  electricalYard(-23,-7);
  gateHouse(-27,-1.5);
  solarParkingCanopy(24,-7);
  steppedOffice(-10,-37);
  lShapedResearchBuilding(4,-35);
  sawtoothWarehouse(22,-29);
  detailedRoadNetwork();
  roadsideParking(-19,5.5,-.08);
  roadsideParking(21,5.0,.07);
  busShelter(18.5,24.0);
  pedestrian('west-sidewalk-a',new THREE.Vector3(-34,0,24.1),new THREE.Vector3(-21,0,24.1),0x2f7181,.10,.060);
  pedestrian('west-sidewalk-b',new THREE.Vector3(-20,0,24.1),new THREE.Vector3(-10,0,24.1),0xc47a3d,.56,.052);
  pedestrian('east-sidewalk-a',new THREE.Vector3(14,0,24.1),new THREE.Vector3(31,0,24.1),0x6c7f48,.32,.057);
  pedestrian('rear-district-a',new THREE.Vector3(-20,0,-17.0),new THREE.Vector3(-7,0,-17.0),0x75577f,.72,.048);
  pedestrian('rear-district-b',new THREE.Vector3(6,0,-17.0),new THREE.Vector3(20,0,-17.0),0x9a5945,.88,.050);
  pedestrian('front-sidewalk-a',new THREE.Vector3(-9,0,24.1),new THREE.Vector3(4,0,24.1),0x3d6a92,.22,.054);
  pedestrian('front-sidewalk-b',new THREE.Vector3(7,0,24.1),new THREE.Vector3(16,0,24.1),0x9a6b45,.68,.051);
  pedestrian('bus-stop-walk',new THREE.Vector3(15.8,0,24.1),new THREE.Vector3(23.5,0,24.1),0x7c4c62,.41,.045);
  pedestrian('west-connector',new THREE.Vector3(-30.5,0,8.5),new THREE.Vector3(-30.5,0,-9.5),0x547a50,.34,.040);
  pedestrian('east-connector',new THREE.Vector3(30.5,0,8.5),new THREE.Vector3(30.5,0,-10.0),0xc2843d,.79,.043);
  pedestrian('research-walk-a',new THREE.Vector3(-14,0,-28.0),new THREE.Vector3(-2,0,-28.0),0x456f7b,.14,.046);
  pedestrian('research-walk-b',new THREE.Vector3(9,0,-28.0),new THREE.Vector3(21,0,-28.0),0x70664b,.62,.044);
  passingRoadVehicle('main-road-sedan-east',new THREE.Vector3(-43,0,17.05),new THREE.Vector3(43,0,17.05),0x2b6581,'sedan',.06,.052);
  passingRoadVehicle('main-road-suv-west',new THREE.Vector3(43,0,20.95),new THREE.Vector3(-43,0,20.95),0x66734e,'suv',.39,.044);
  passingRoadVehicle('main-road-van-east',new THREE.Vector3(-43,0,20.95),new THREE.Vector3(43,0,20.95),0xd7d1c3,'van',.93,.038);
  passingRoadVehicle('service-road-vehicle',new THREE.Vector3(36,0,-21.0),new THREE.Vector3(-36,0,-21.0),0x8b473e,'suv',.57,.035);
  const ambientClock=new THREE.Clock();
  function animateAmbientScene(){
    requestAnimationFrame(animateAmbientScene);
    const elapsed=ambientClock.getElapsedTime();
    pedestrianActors.forEach(actor=>{
      const walk=actor.userData.walk;const cycle=(elapsed*walk.speed+walk.phase)%2;
      const amount=cycle<=1?cycle:2-cycle;
      actor.position.lerpVectors(walk.start,walk.end,amount);
      const direction=walk.end.clone().sub(walk.start).multiplyScalar(cycle<=1?1:-1);
      actor.rotation.y=Math.atan2(direction.x,direction.z);
      const stride=Math.sin(elapsed*walk.speed*Math.PI*12+walk.phase*Math.PI*2)*.52;
      walk.armL.rotation.x=stride;walk.armR.rotation.x=-stride;walk.legL.rotation.x=-stride*.72;walk.legR.rotation.x=stride*.72;
      actor.position.y=Math.abs(Math.sin(elapsed*walk.speed*Math.PI*12+walk.phase*Math.PI*2))*.018;
    });
    trafficVehicles.forEach(vehicle=>{
      const drive=vehicle.userData.traffic;const journey=(elapsed*drive.speed+drive.phase)%1.75;
      vehicle.visible=journey<1;
      if(!vehicle.visible)return;
      vehicle.position.lerpVectors(drive.start,drive.end,journey);
      const direction=drive.end.clone().sub(drive.start);
      vehicle.rotation.y=Math.atan2(direction.x,direction.z);
      vehicle.userData.wheels?.forEach(wheel=>{wheel.rotation.x-=.14;});
    });
    const focus=(controls&&controls.target)?controls.target.clone():new THREE.Vector3(2,1.5,0);
    const cameraToFocus=focus.clone().sub(camera.position);const focusDistance=cameraToFocus.length();
    if(focusDistance>.01){
      const viewDirection=cameraToFocus.clone().normalize();
      ambientOccluders.forEach(object=>{
        const center=object.localToWorld(object.userData.occlusionCenter.clone());
        const cameraToObject=center.sub(camera.position);const along=cameraToObject.dot(viewDirection);
        const perpendicular=cameraToObject.clone().sub(viewDirection.clone().multiplyScalar(along)).length();
        const obstructs=along>1.2&&along<focusDistance-.6&&perpendicular<object.userData.occlusionRadius;
        const desired=obstructs?object.userData.fadeOpacity:1;
        object.userData.currentOpacity=THREE.MathUtils.lerp(object.userData.currentOpacity,desired,.12);
        object.traverse(child=>{
          if(!child.material)return;
          const materials=Array.isArray(child.material)?child.material:[child.material];
          materials.forEach(material=>{material.transparent=true;material.opacity=object.userData.currentOpacity;material.depthWrite=object.userData.currentOpacity>.88;});
        });
      });
    }
  }
  animateAmbientScene();

  scene.updateMatrixWorld(true);
  const pipingRoutes=createStationPipeRoutes(equipment);
  for(const route of pipingRoutes)if(!route.visualOnly)pipe(route.points,route.color,route.id);

  // Detail pass: fittings, serviceable enclosures, road furniture and vehicle trim.
  const detailMetal=mat(0xd7dadd,.92,.23),rubber=mat(0x171c1d,0,.94),coilMetal=mat(0x929f9f,.8,.52);
  const animatedFans=[];const coverMeshes=[compressor.children[1],compressor.children[2],cooler.children[1]];
  // Rounded sheet-metal housings catch edge highlights instead of looking like blocks.
  function roundedHousing(w,h,d,r=.05){
    const shape=new THREE.Shape();const x=-w/2+r,y=-h/2+r,ww=w-2*r,hh=h-2*r;
    shape.moveTo(x+r,y);shape.lineTo(x+ww-r,y);shape.quadraticCurveTo(x+ww,y,x+ww,y+r);
    shape.lineTo(x+ww,y+hh-r);shape.quadraticCurveTo(x+ww,y+hh,x+ww-r,y+hh);
    shape.lineTo(x+r,y+hh);shape.quadraticCurveTo(x,y+hh,x,y+hh-r);
    shape.lineTo(x,y+r);shape.quadraticCurveTo(x,y,x+r,y);
    const geometry=new THREE.ExtrudeGeometry(shape,{depth:Math.max(.01,d-2*r),bevelEnabled:true,bevelSize:r,bevelThickness:r,bevelSegments:3,curveSegments:6,steps:1});
    geometry.translate(0,0,-d/2+r);return geometry;
  }
  function softenHousing(obj,w,h,d,r){const previous=obj.geometry;obj.geometry=roundedHousing(w,h,d,r);previous.dispose();}
  softenHousing(compressor.children[1],2.9,2.65,3.9,.055);
  softenHousing(cooler.children[1],2.3,2.25,3.5,.045);
  softenHousing(cabinet.children[0],1.65,2.5,1.2,.035);
  for(const id of ['dispenser','standby'])softenHousing(equipment.get(id).group.children[1],.95,2.05,.68,.03);
  // Fine brushed-metal roughness, generated locally and shared by the metal surfaces.
  const brushCanvas=document.createElement('canvas');brushCanvas.width=brushCanvas.height=256;
  const brushContext=brushCanvas.getContext('2d');brushContext.fillStyle='#929292';brushContext.fillRect(0,0,256,256);
  for(let row=0;row<256;row++){
    const shade=115+Math.round(25*Math.sin(row*3.17)+15*Math.sin(row*.71));brushContext.fillStyle=`rgb(${shade},${shade},${shade})`;
    brushContext.fillRect(0,row,256,1);
  }
  const brushTexture=new THREE.CanvasTexture(brushCanvas);brushTexture.wrapS=brushTexture.wrapT=THREE.RepeatWrapping;brushTexture.repeat.set(2,4);
  for(const material of [M.steel,detailMetal,coilMetal]){material.roughnessMap=brushTexture;material.needsUpdate=true;}
  // Soft ambient contact is visual shading, independent of the process model.
  const contactCanvas=document.createElement('canvas');contactCanvas.width=contactCanvas.height=128;
  const contactContext=contactCanvas.getContext('2d');const contactGradient=contactContext.createRadialGradient(64,64,10,64,64,63);
  contactGradient.addColorStop(0,'rgba(18,36,34,.42)');contactGradient.addColorStop(.5,'rgba(18,36,34,.26)');contactGradient.addColorStop(1,'rgba(18,36,34,0)');
  contactContext.fillStyle=contactGradient;contactContext.fillRect(0,0,128,128);
  const contactTexture=new THREE.CanvasTexture(contactCanvas);
  const contactMaterial=new THREE.MeshBasicMaterial({map:contactTexture,transparent:true,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-1,toneMapped:false});
  function contactShadow(x,z,w,d,y=.035){const shadow=mesh(new THREE.PlaneGeometry(w,d),contactMaterial);shadow.rotation.x=-Math.PI/2;shadow.position.set(x,y,z);shadow.castShadow=false;shadow.receiveShadow=false;return shadow;}
  contactShadow(2.8,7,6.3,2.9,.085);
  for(const x of [-6.4,-1,3,7,11])contactShadow(x,-6,4.5,6.0,.042);
  contactShadow(-12,-5.7,4.7,9.5,.025);contactShadow(14,-4.5,2.9,2.5,.044);
  function tube(points,r,material,parent=scene) {
    const curve=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)),false,'centripetal');
    return mesh(new THREE.TubeGeometry(curve,24,r,8,false),material,parent);
  }
  function ring(radius,thickness,x,y,z,material,parent,axis='z') {
    const obj=mesh(new THREE.TorusGeometry(radius,thickness,6,24),material,parent);obj.position.set(x,y,z);
    if(axis==='y')obj.rotation.x=Math.PI/2;if(axis==='x')obj.rotation.y=Math.PI/2;return obj;
  }
  const fastenerGeometryCache=new Map();
  function fasteners(points,parent,size=.025) {
    if(!fastenerGeometryCache.has(size))fastenerGeometryCache.set(size,new THREE.CylinderGeometry(size,size,size*.65,6));
    const geometry=fastenerGeometryCache.get(size);
    const screws=new THREE.InstancedMesh(geometry,detailMetal,points.length);const transform=new THREE.Object3D();
    points.forEach((point,i)=>{transform.position.set(...point);transform.rotation.x=Math.PI/2;transform.updateMatrix();screws.setMatrixAt(i,transform.matrix);});
    screws.castShadow=true;parent.add(screws);return screws;
  }
  function flange(x,y,z,parent,r=.12) {
    cylinder(r,.055,x,y,z,detailMetal,parent,'z');ring(r*.7,.012,x,y,z+.032,M.dark,parent);
    fasteners(Array.from({length:6},(_,i)=>[x+Math.cos(i*Math.PI/3)*r*.8,y+Math.sin(i*Math.PI/3)*r*.8,z+.041]),parent,.014);
  }
  function handValve(x,y,z,parent,color=M.red) {
    cylinder(.055,.17,x,y,z,detailMetal,parent,'z');cylinder(.023,.14,x,y+.08,z,detailMetal,parent);
    ring(.095,.014,x,y+.16,z,color,parent,'y');box(.18,.015,.018,x,y+.16,z,color,parent);
  }
  function gauge(x,y,z,parent,r=.15) {
    const dial=new THREE.Group();dial.position.set(x,y,z);parent.add(dial);
    cylinder(r,.08,0,0,0,detailMetal,dial,'z');
    const canvas=document.createElement('canvas');canvas.width=canvas.height=128;const ctx=canvas.getContext('2d');
    ctx.fillStyle='#f5f4e8';ctx.fillRect(0,0,128,128);ctx.strokeStyle='#344443';ctx.lineWidth=2;
    for(let i=0;i<25;i++){const a=(135+i*11.25)*Math.PI/180;ctx.beginPath();ctx.moveTo(64+Math.cos(a)*46,64+Math.sin(a)*46);ctx.lineTo(64+Math.cos(a)*(i%3?41:36),64+Math.sin(a)*(i%3?41:36));ctx.stroke();}
    ctx.strokeStyle='#b54934';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(64,64);ctx.lineTo(91,36);ctx.stroke();ctx.fillStyle='#344443';ctx.font='12px monospace';ctx.textAlign='center';ctx.fillText('MPa',64,88);
    const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
    const face=mesh(new THREE.CircleGeometry(r*.87,24),new THREE.MeshBasicMaterial({map:texture}),dial);face.position.set(0,0,.045);
    return dial;
  }
  function hazard(text,x,y,z,parent,w=.4) {
    sign(text,'HYDROGEN',w,w*.48,x,y,z,parent,'#e9b63e');
  }
  function seams(group,w,h,z,y=1.4) {
    box(w,.012,.012,0,y-h/2,z,M.frame,group);box(w,.012,.012,0,y+h/2,z,M.frame,group);
    for(const x of [-w/2,w/2])box(.012,h,.012,x,y,z,M.frame,group);
    fasteners([[-w/2+.07,y-h/2+.07,z+.012],[w/2-.07,y-h/2+.07,z+.012],[-w/2+.07,y+h/2-.07,z+.012],[w/2-.07,y+h/2-.07,z+.012]],group);
  }
  // Vessel necks, manifold tubing, valves, instruments, saddles and anchor plates.
  for(const name of ['low','medium','high']){
    const g=equipment.get(name).group;
    for(const y of [.65,1.6,2.55])for(const x of [-.52,.52]){
      flange(x,y,1.93,g,.10);handValve(x,y,2.07,g);
      tube([[x,y,2.08],[x,y,2.22],[.99,y,2.22],[.99,y,2.03]],.022,detailMetal,g);
      for(const z of [-1.3,1.3]){box(.58,.1,.22,x,y-.35,z,M.frame,g);box(.66,.035,.33,x,y-.42,z,detailMetal,g);}
      sign('H2','SEAMLESS VESSEL',.4,.13,x,y,1.57,g,'#d6dddd');
    }
    gauge(.7,2.92,2.09,g);handValve(.99,.4,2.03,g,M.green);
    for(const x of [-1.1,1.1])for(const z of [-1.7,1.7]){
      box(.32,.035,.32,x,.26,z,detailMetal,g);for(const dx of [-.10,.10])cylinder(.025,.06,x+dx,.30,z,detailMetal,g);
    }
    hazard('H2 / HIGH PRESSURE',0,.32,2.51,g,1.25);
    box(.04,2.9,.04,0,1.75,-1.72,M.frame,g);
  }
  // Dispenser front panel: card reader, keypad, printer and breakaway coupling.
  for(const id of ['dispenser','standby']){
    const g=equipment.get(id).group;seams(g,.78,.65,.354,.62);
    box(.22,.29,.028,.22,1.12,.389,M.dark,g);box(.13,.015,.01,.22,1.15,.408,detailMetal,g);
    box(.18,.014,.025,-.21,1.12,.4,M.black,g);sign('CARD','PAYMENT',.23,.10,.22,1.36,.409,g,'#f1f4ee');
    for(let row=0;row<3;row++)for(let col=0;col<3;col++)box(.034,.025,.01,.16+col*.052,1.07-row*.042,.412,detailMetal,g);
    cylinder(.055,.018,-.24,1.07,.397,M.yellow,g,'z');cylinder(.032,.025,-.24,1.07,.411,M.red,g,'z');
    box(.015,1.52,.015,-.48,1.25,.345,M.frame,g);box(.015,1.52,.015,.48,1.25,.345,M.frame,g);
    cylinder(.07,.16,.52,1.74,0,detailMetal,g,'x');flange(.51,1.72,.02,g,.08);
    hazard('NO SMOKING',-.12,.74,.379,g,.5);
    box(.16,.08,.07,-.3,1.86,.43,M.frame,g);box(.09,.035,.02,-.3,1.86,.48,M.black,g);
    sign('01 / H70','HYDROGEN',.55,.16,0,.43,.368,g,'#eff2e9');
  }
  const activeDispenser=equipment.get('dispenser').group;
  activeDispenser.children.filter(obj=>obj.geometry?.type==='TubeGeometry').forEach(obj=>obj.visible=false);
  activeDispenser.children.filter(obj=>obj.userData.parkedNozzle).forEach(obj=>obj.visible=false);
  scene.updateMatrixWorld(true);
  const vehiclePort=new THREE.Vector3(-1.95,.84,-.965);
  const nozzleTip=activeDispenser.worldToLocal(car.localToWorld(vehiclePort.clone()));
  const hoseEnd=nozzleTip.clone().add(new THREE.Vector3(0,-.065,-.31));
  tube([[.52,1.75,0],[.79,1.65,.12],[.95,.55,.80],[nozzleTip.x-.12,.28,nozzleTip.z-.65],[nozzleTip.x-.04,.67,nozzleTip.z-.48],hoseEnd.toArray()],.043,rubber,activeDispenser);
  cylinder(.06,.13,nozzleTip.x,nozzleTip.y,nozzleTip.z-.065,detailMetal,activeDispenser,'z');
  box(.085,.13,.20,nozzleTip.x,nozzleTip.y-.045,nozzleTip.z-.20,M.dark,activeDispenser);
  ring(.057,.009,nozzleTip.x,nozzleTip.y,nozzleTip.z-.12,detailMetal,activeDispenser);
  const inletSocket=mesh(new THREE.CircleGeometry(.075,24),M.dark,car);inletSocket.position.copy(vehiclePort);inletSocket.rotation.y=Math.PI;
  const openFuelDoor=box(.08,.20,.025,-1.60,1.04,-1.07,M.white,car);openFuelDoor.rotation.y=.65;
  // Car glazing, lower grille, panel joints, brake discs and tire shoulder grooves.
  const windshield=box(.88,.018,1.53,1.06,1.35,0,M.glass,car);windshield.rotation.z=-.71;
  const rearWindow=box(.71,.018,1.50,-1.02,1.33,0,M.glass,car);rearWindow.rotation.z=.77;
  box(1.32,.025,1.48,.02,1.77,0,mat(0x333f45,.55,.2),car);
  box(.032,.19,1.18,2.55,.6,0,M.black,car);
  for(let i=0;i<8;i++)box(.018,.014,1.13,2.573,.52+i*.025,0,M.frame,car);
  for(const side of [-1,1]){
    box(3.5,.065,.035,0,.50,side*.99,M.dark,car);box(3.30,.018,.026,0,1.07,side*.986,detailMetal,car);
    for(const x of [-1.12,.26,1.20])box(.012,.50,.012,x,.80,side*.992,M.frame,car);
    ring(.11,.012,-1.45,1.02,side*.985,detailMetal,car);
    for(const x of [-1.55,1.52]){
      ring(.405,.036,x,.43,side*1.014,rubber,car);ring(.32,.023,x,.43,side*1.027,M.dark,car);
      cylinder(.235,.008,x,.43,side*1.036,coilMetal,car,'z');box(.07,.16,.03,x+.19,.45,side*1.045,M.red,car);
      fasteners(Array.from({length:5},(_,i)=>[x+Math.cos(i*Math.PI*.4)*.105,.43+Math.sin(i*Math.PI*.4)*.105,side*1.045]),car,.018);
    }
    box(.04,.10,.45,2.51,.82,side*.54,M.white,car);box(.025,.035,.46,2.54,.88,side*.54,detailMetal,car);
  }
  box(.027,.12,.44,2.583,.48,0,M.white,car);sign('H2 070','ZERO EMISSION',.4,.1,2.6,.48,0,car).rotation.y=Math.PI/2;
  const wiper=box(.48,.025,.025,1.33,1.13,.28,M.black,car);wiper.rotation.z=-.3;
  // Compressor service bay: electric motor, cylinder heads, piping and intercoolers.
  box(2.75,.12,3.65,0,.4,0,M.frame,compressor);
  cylinder(.34,1.1,-.50,.93,-.6,M.teal,compressor,'z');cylinder(.39,.08,-.50,.93,-1.2,M.frame,compressor,'z');
  for(let i=0;i<10;i++)cylinder(.36,.025,-.5,.93,-1.08+i*.10,coilMetal,compressor,'z');
  box(.60,.35,.60,-.5,1.35,-.6,M.frame,compressor);box(.9,.48,1.2,.48,.73,-.35,M.frame,compressor);
  for(let i=0;i<3;i++){
    const z=-1+i*1.05;const r=.33-i*.06;
    cylinder(r,.52,.5,1.28,z,detailMetal,compressor);cylinder(r*1.25,.11,.5,1.58,z,M.frame,compressor);
    cylinder(.16,.75,-.55,1.87,z,detailMetal,compressor,'x');
    for(let k=0;k<8;k++)cylinder(.17,.017,-.88+k*.095,1.87,z,coilMetal,compressor,'x');
    tube([[.5,1.64,z],[.5,2.0,z],[-.18,2.0,z],[-.2,1.87,z]],.03,detailMetal,compressor);gauge(.75,2.24,z+.1,compressor,.10);
  }
  seams(compressor,2.68,2.18,1.979,1.55);hazard('HIGH PRESSURE',.70,.57,1.99,compressor,.75);
  for(const x of [-1.28,1.28]){box(.08,.28,.04,x,1.70,1.992,detailMetal,compressor);box(.09,.10,.035,x,1.10,1.99,M.frame,compressor);}
  sign('CMP-101','SERVICE ACCESS',.70,.19,.8,1.77,1.999,compressor,'#eff3eb');
  box(.12,.30,.12,-1.08,3.2,1.15,M.frame,compressor);led(compressor,-1.08,3.36,1.15,'compressor');
  // Finned chiller coil, insulated vessel, refrigeration piping and fan guards.
  box(2.1,.12,3.3,0,.35,0,M.frame,cooler);
  for(let i=0;i<26;i++)box(1.8,.023,.13,0,.62+i*.05,1.63,coilMetal,cooler);
  cylinder(.30,1.3,-.45,1.10,-.65,M.black,cooler);capsule(.22,.74,.56,1.05,-.6,detailMetal,cooler,'y');
  tube([[-.45,1.7,-.65],[-.45,1.95,-.65],[.65,1.95,-.65],[.65,1.9,1.45]],.034,detailMetal,cooler);
  tube([[.55,.65,-.65],[.8,.65,-.65],[.8,.65,1.35],[-.55,.65,1.35]],.07,rubber,cooler);
  seams(cooler,2.10,1.83,1.787,1.35);hazard('ELECTRICAL',-.7,.51,1.80,cooler,.48);
  for(const z of [-.9,.8]){
    const fan=new THREE.Group();fan.position.set(0,2.59,z);cooler.add(fan);
    for(let i=0;i<4;i++){const blade=box(.18,.027,.95,0,0,0,detailMetal,fan);blade.rotation.y=i*Math.PI/2+.4;}
    cylinder(.11,.07,0,0,0,M.black,fan);animatedFans.push(fan);
    for(const r of [.20,.35,.50,.65])ring(r,.012,0,2.69,z,detailMetal,cooler,'y');
    for(let i=0;i<4;i++){const guard=box(.02,.016,1.4,0,2.70,z,detailMetal,cooler);guard.rotation.y=i*Math.PI/4;}
  }
  // Trailer rear manifold, restraint straps, landing legs, mudguards and tractor trim.
  for(const y of [1.45,2.27,3.09])for(const x of [-.83,0,.83]){
    flange(x,y,-3.4,trailer,.09);handValve(x,y,-3.5,trailer);
    tube([[x,y,-3.52],[x,y,-3.73],[1.1,y,-3.73],[1.1,1.3,-3.73]],.022,detailMetal,trailer);
    for(const z of [-2.8,0,2.8])ring(.352,.028,x,y,z,M.frame,trailer);
  }
  box(2.4,.9,.12,0,1.4,-3.8,M.frame,trailer);gauge(.7,1.72,-3.87,trailer,.12).rotation.y=Math.PI;
  for(const x of [-1.1,1.1]){
    box(.12,.76,.12,x,.57,2.15,detailMetal,trailer);box(.36,.06,.32,x,.16,2.15,M.frame,trailer);
    box(.16,.7,1.9,x,.95,-2.20,M.frame,trailer);box(.14,.45,.08,x,.58,-3.25,rubber,trailer);
    box(.1,.17,.30,x,1.0,5.66,M.white,trailer);box(.18,.20,.25,x*1.18,2.13,5.55,M.dark,trailer);
  }
  for(let i=0;i<6;i++)box(1.4,.035,.04,0,1.05+i*.10,5.84,M.dark,trailer);
  box(1.45,.12,.045,0,2.43,5.84,M.white,trailer);box(1.9,.03,.045,0,1.61,5.84,detailMetal,trailer);
  hazard('FLAMMABLE GAS',0,2.4,-3.82,trailer,.9);
  // Cabinet hinges and latch; vent service flanges; ground connections.
  seams(cabinet,1.5,2.25,.616,1.3);
  for(const y of [.45,2.10])box(.06,.17,.04,-.72,y,.648,detailMetal,cabinet);
  box(.04,.21,.05,.58,1.16,.65,M.black,cabinet);hazard('ELECTRICAL',0,.56,.65,cabinet,.7);
  for(const y of [.35,2.1,5.4]){cylinder(.18,.08,0,y,0,detailMetal,vent);for(let i=0;i<6;i++)cylinder(.017,.11,Math.cos(i*Math.PI/3)*.14,y,Math.sin(i*Math.PI/3)*.14,detailMetal,vent);}
  for(let y=.6;y<5.9;y+=.36)box(.37,.025,.025,0,y,-.22,M.frame,vent);
  for(const x of [-.20,.20])cylinder(.016,5.6,x,3.10,-.22,M.frame,vent);
  // Canopy soffit joints, column bases, rainwater drainage and linear LEDs.
  for(let x=-4;x<13;x+=1.1)box(.014,.02,6.8,x,4.949,5.6,M.frame,canopy);
  for(const x of [-3.5,12.5])for(const z of [2.6,8.6]){
    box(.57,.055,.57,x,.29,z,detailMetal,canopy);for(const dx of [-.22,.22])for(const dz of [-.22,.22])cylinder(.025,.07,x+dx,.33,z+dz,detailMetal,canopy);
    cylinder(.037,4.75,x+.24,2.58,z,detailMetal,canopy);
  }
  const luminous=new THREE.MeshStandardMaterial({color:0xd9eee7,emissive:0xb4e8d8,emissiveIntensity:.45});
  for(const z of [3.1,8.2])box(15,.025,.06,4.5,4.91,z,luminous,canopy);
  box(18.5,.065,.06,4.5,5.4,9.46,detailMetal,canopy);
  // Kerb sections, expansion joints, drainage grates and equipment protection.
  for(let x=-12;x<=15;x+=1.5){box(1.46,.18,.20,x,.02,1.36,M.white);box(1.46,.18,.20,x,.02,-10.65,M.white);}
  for(let x=-12;x<16;x+=4)box(.014,.008,8.3,x,.031,6,M.frame);
  for(const x of [-5,14]){
    box(.33,.025,7.0,x,.043,5.8,M.frame);for(let z=2.5;z<9.1;z+=.22)box(.29,.008,.035,x,.062,z,detailMetal);
  }
  for(const x of [-8.4,12.6])for(const z of [-3.0,-8.6]){cylinder(.12,.85,x,.55,z,M.yellow);cylinder(.124,.19,x,.70,z,M.black);box(.34,.04,.34,x,.15,z,M.frame);}
  for(const x of [-.8,.8]){box(.12,.035,4.0,-12+x,.05,3.3,M.yellow);}
  const totem=new THREE.Group();totem.position.set(15.1,0,10.8);scene.add(totem);
  box(1.35,4.3,.38,0,2.15,0,M.green,totem);sign('H2','700 BAR',1.12,.7,0,3.6,.20,totem);sign('OPEN','CLEAN MOBILITY',1.1,.48,0,2.55,.20,totem);
  for(const z of [-.5,.5]){cylinder(.10,.8,15.9,.40,10.8+z,M.yellow);}
  // Surrounding public realm gives the facility believable scale and context.
  const context=new THREE.Group();scene.add(context);
  const asphalt=mat(0x4b5557,0,.96);asphalt.map=M.pavement.map;
  box(82,.12,15,0,-.49,23,M.concrete,context);box(82,.04,11,0,-.40,23,asphalt,context);
  box(82,.15,1.85,0,-.28,15.2,M.concrete,context);box(82,.15,1.85,0,-.28,30.8,M.concrete,context);
  for(let x=-39;x<40;x+=4){box(2.0,.012,.10,x,-.37,23,M.white,context);}
  for(const z of [18.2,27.8])box(82,.012,.10,0,-.37,z,M.white,context);
  for(let x=-39;x<40;x+=1.5){box(.012,.009,1.8,x,-.195,15.2,M.frame,context);box(.012,.009,1.8,x,-.195,30.8,M.frame,context);}
  for(const x of [-13,13]){
    box(4.0,.16,3.0,x,-.30,13.6,M.concrete,context);
    cylinder(.055,2.5,x,1.0,14.0,M.frame,context);
    const signBoard=mesh(new THREE.CircleGeometry(.43,24),M.white,context);signBoard.position.set(x,2.13,14.03);
    ring(.39,.04,x,2.13,14.04,M.red,context);sign('10','km/h',.48,.28,x,2.13,14.06,context,'#f4f4eb');
  }
  // Clear pedestrian crossing and tactile tiles; public road is decorative only.
  for(let x=-2.8;x<3;x+=.65)box(.39,.015,4.4,x,-.365,20.6,M.white,context);
  for(const z of [17.9,23.3]){
    box(4,.017,.45,0,-.36,z,M.yellow,context);
    const points=[];for(let x=-1.8;x<1.9;x+=.15)for(let dz=-.15;dz<=.15;dz+=.15)points.push([x,-.34,z+dz]);
    const tileDots=new THREE.InstancedMesh(new THREE.SphereGeometry(.022,6,4),M.yellow,points.length);const transform=new THREE.Object3D();
    points.forEach((point,i)=>{transform.position.set(...point);transform.scale.set(1,.35,1);transform.updateMatrix();tileDots.setMatrixAt(i,transform.matrix);});context.add(tileDots);
  }
  // Neighboring industrial premises kept unobtrusive behind the station.
  const backgroundBuilding=new THREE.Group();backgroundBuilding.position.set(3,-.32,-23);scene.add(backgroundBuilding);
  box(30,6.0,10,0,3,0,mat(0xafbdb9,.1,.86),backgroundBuilding);
  box(30.3,.17,10.3,0,6.1,0,M.frame,backgroundBuilding);
  for(let x=-13;x<=13;x+=2.6){box(1.65,1.20,.025,x,3.95,5.02,M.glass,backgroundBuilding);box(.06,5.5,.04,x,2.9,5.02,M.white,backgroundBuilding);}
  for(const x of [-7,7]){
    box(5.0,2.5,.05,x,1.25,5.05,M.frame,backgroundBuilding);
    for(let y=.2;y<2.5;y+=.18)box(4.9,.025,.025,x,y,5.09,detailMetal,backgroundBuilding);
  }
  // Fenced utility yard and gate with horizontal rails and welded-wire infill.
  function fenceSegment(x,z,length,rotation=0){
    const g=new THREE.Group();g.position.set(x,0,z);g.rotation.y=rotation;scene.add(g);
    for(let p=-length/2;p<=length/2+.05;p+=2.0){cylinder(.035,2.4,p,1.20,0,M.frame,g);box(.18,.045,.18,p,.07,0,detailMetal,g);}
    for(const y of [.25,1.2,2.25])box(length,.025,.035,0,y,0,M.frame,g);
    const strands=[];for(let p=-length/2;p<length/2;p+=.20)strands.push([p,1.25,0]);
    const verticals=new THREE.InstancedMesh(new THREE.BoxGeometry(.008,2.0,.008),coilMetal,strands.length);const transform=new THREE.Object3D();
    strands.forEach((point,i)=>{transform.position.set(...point);transform.updateMatrix();verticals.setMatrixAt(i,transform.matrix);});g.add(verticals);
    for(let y=.35;y<2.25;y+=.20)box(length,.008,.008,0,y,0,coilMetal,g);return g;
  }
  fenceSegment(-16.55,-5.5,10.5,Math.PI/2);fenceSegment(16.55,-5.5,10.5,Math.PI/2);
  const gate=fenceSegment(-10.7,-1.65,4.8);hazard('NO PUBLIC ACCESS',0,1.25,.04,gate,1.25);
  cylinder(.065,1.95,-8.2,.975,-1.65,M.frame);box(.07,.30,.12,-8.28,1.1,-1.58,detailMetal);
  // Fixed steel process tubing is separate from the colored simulation overlay.
  const staticProcess=buildStationPiping(pipingRoutes);scene.add(staticProcess);
  hazard('GH2 / PROCESS TUBING',3,.95,-2.24,staticProcess,1.3);
  // Earthing conductors and local cable trays are visual installations, not wiring diagrams.
  const earthMaterial=mat(0x79994e,.5,.6);
  for(const [x,z] of [[-6.4,-6],[-1,-6],[3,-6],[7,-6],[11,-6],[14,-4.5]]){
    tube([[x+.9,.55,z+1.5],[x+.9,.12,z+1.5],[x+.9,.08,-9.9]],.012,earthMaterial,staticProcess);
    box(.15,.04,.09,x+.9,.10,-9.9,detailMetal,staticProcess);
  }
  box(21,.05,.24,3,.19,-9.9,M.frame,staticProcess);
  for(let x=-7;x<14;x+=.35)box(.025,.015,.25,x,.23,-9.9,detailMetal,staticProcess);
  // Emergency response station with extinguisher, eyewash-style visual fixture and signs.
  const emergency=new THREE.Group();emergency.position.set(13.8,0,.5);scene.add(emergency);
  box(1.2,.10,.7,0,.05,0,M.concrete,emergency);cylinder(.11,.55,-.26,.62,0,M.red,emergency);cylinder(.025,.12,-.26,.97,0,M.dark,emergency);
  box(.20,.025,.055,-.26,1.04,0,M.dark,emergency);tube([[-.2,1.01,0],[-.06,.89,.08],[-.07,.55,.10]],.015,rubber,emergency);
  cylinder(.025,1.85,.45,.93,0,M.frame,emergency);sign('FIRE / ESD','EMERGENCY POINT',1.0,.38,.1,1.72,.06,emergency,'#b84937');
  // A small attendant figure provides scale without implying a simulated occupant.
  const attendant=new THREE.Group();attendant.position.set(10.7,.04,.9);attendant.rotation.y=-.45;scene.add(attendant);
  const uniform=mat(0x2d5655),vest=mat(0xdac54a);
  capsule(.16,.34,0,1.08,0,uniform,attendant,'y');box(.30,.32,.22,0,1.17,.02,vest,attendant);
  for(const x of [-.105,.105]){capsule(.064,.48,x,.51,0,M.dark,attendant,'y');box(.13,.10,.25,x,.16,.06,rubber,attendant);}
  for(const side of [-1,1]){const arm=capsule(.055,.38,side*.23,1.07,0,uniform,attendant,'y');arm.rotation.z=side*.18;}
  const head=mesh(new THREE.SphereGeometry(.115,12,8),mat(0xc7a185),attendant);head.position.set(0,1.52,0);
  const helmet=mesh(new THREE.SphereGeometry(.13,12,8,0,Math.PI*2,0,Math.PI/2),M.white,attendant);helmet.position.set(0,1.54,0);cylinder(.15,.025,0,1.54,0,M.white,attendant);
  // Landscaped surroundings: static instanced foliage, not a vegetation CFD model.
  const landscape=new THREE.Group();scene.add(landscape);
  const groundMaterial=mat(0x8c9c89,0,.96);groundMaterial.map=surfaceTexture('#a6b09a',.12,16);
  box(92,.08,90,0,-.65,4,groundMaterial,landscape);
  box(33,.10,2.15,0,-.12,-13.4,M.turf,landscape);
  box(2.05,.10,23,-18,-.13,-1.0,M.turf,landscape);
  const foliageGeometry=new THREE.SphereGeometry(1,12,8);
  const foliageMaterial=mat(0x718c59,0,.93);
  const treePositions=[-14.5,-8,1,10,15];const crownCount=treePositions.length*18;
  const foliage=new THREE.InstancedMesh(foliageGeometry,foliageMaterial,crownCount);
  const foliageTransform=new THREE.Object3D();const foliageTint=new THREE.Color();
  let foliageIndex=0;
  for(const x of treePositions){
    for(let i=0;i<18;i++){
      const angle=i*2.399963,layer=i/17,radius=.72*Math.sin(Math.PI*layer);
      foliageTransform.position.set(x+Math.cos(angle)*radius,1.6+layer*1.65,-12.05+Math.sin(angle)*radius);
      const scale=.43+.13*Math.sin(i*3.1+1);foliageTransform.scale.set(scale*1.28,scale,scale*1.12);foliageTransform.rotation.set(i*.21,angle,0);foliageTransform.updateMatrix();
      foliage.setMatrixAt(foliageIndex,foliageTransform.matrix);foliageTint.setHSL(.24+(i%4)*.01,.18+(i%3)*.035,.30+(i%5)*.026);foliage.setColorAt(foliageIndex,foliageTint);foliageIndex++;
    }
  }
  foliage.castShadow=true;foliage.receiveShadow=true;foliage.computeBoundingSphere();landscape.add(foliage);
  const shrubPositions=[];
  for(let x=-15.5;x<=15.5;x+=.68)shrubPositions.push([x,.30,-13.6]);
  for(let z=-10.5;z<=9.5;z+=.68)shrubPositions.push([-18,.30,z]);
  const shrubs=new THREE.InstancedMesh(foliageGeometry,foliageMaterial,shrubPositions.length);
  shrubPositions.forEach((point,i)=>{
    foliageTransform.position.set(...point);foliageTransform.scale.set(.45,.28+(i%3)*.035,.37);foliageTransform.rotation.set(0,i*.4,0);foliageTransform.updateMatrix();
    shrubs.setMatrixAt(i,foliageTransform.matrix);foliageTint.setHSL(.26,.22,.32+(i%5)*.012);shrubs.setColorAt(i,foliageTint);
  });
  shrubs.castShadow=true;shrubs.receiveShadow=true;shrubs.computeBoundingSphere();landscape.add(shrubs);
  // Gradient sky geometry stays outside the facility and follows the day/night switch.
  const skyGeometry=new THREE.SphereGeometry(110,24,16);const skyPositions=skyGeometry.attributes.position;
  const skyColors=new Float32Array(skyPositions.count*3),skyTop=new THREE.Color(0xb6d7e9),skyHorizon=new THREE.Color(0xe8eee4),skyColor=new THREE.Color();
  for(let i=0;i<skyPositions.count;i++){
    const blend=Math.max(0,Math.min(1,skyPositions.getY(i)/110));skyColor.copy(skyHorizon).lerp(skyTop,Math.pow(blend,.55));skyColor.toArray(skyColors,i*3);
  }
  skyGeometry.setAttribute('color',new THREE.BufferAttribute(skyColors,3));
  const skyMaterial=new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.BackSide,depthWrite:false,fog:false,color:0x263c49});
  const sky=mesh(skyGeometry,skyMaterial);sky.castShadow=false;sky.receiveShadow=false;sky.renderOrder=-10;
  // Instrument screens display model values, unlike the decorative analog dials.
  const instrumentScreens=[];
  function instrument(parent,w,h,x,y,z,kind,id) {
    const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=384;
    const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());
    const material=new THREE.MeshBasicMaterial({map:texture,toneMapped:false});
    const screen=mesh(new THREE.PlaneGeometry(w,h),material,parent);screen.position.set(x,y,z);
    instrumentScreens.push({canvas,texture,kind,id});return screen;
  }
  instrument(activeDispenser,.61,.23,0,1.52,.389,'dispenser','dispenser');
  instrument(equipment.get('standby').group,.61,.23,0,1.52,.389,'standby','standby');
  for(const name of ['low','medium','high'])instrument(equipment.get(name).group,.83,.31,-.25,2.97,2.32,'bank',name);
  instrument(cabinet,.52,.40,0,1.38,.649,'safety','safety');
  function drawInstruments(values,connected) {
    for(const item of instrumentScreens){
      const ctx=item.canvas.getContext('2d'),alarm=connected&&values.esd;
      ctx.fillStyle=alarm?'#351c19':'#11292c';ctx.fillRect(0,0,1024,384);
      ctx.fillStyle=alarm?'#ff7665':'#85ebca';ctx.font='bold 40px monospace';
      let title='MODEL DATA',number='--',unit='',foot='WAITING FOR SIMULATION';
      if(item.kind==='dispenser'){
        title=alarm?'ESD / CLOSED':'H70 / NOZZLE FLOW';number=connected?values.flow.toFixed(2):'--';unit='g/s';
        foot=connected?`${values.pressure.toFixed(2)} MPa   SOC ${values.soc.toFixed(1)}%`:'SIMULATION DATA / NOT A REAL METER';
      }
      if(item.kind==='standby'){title='DISPENSER 02';number=connected?values.flow2.toFixed(2):'--';unit='g/s';foot=connected?`${values.pressure2.toFixed(2)} MPa   SOC ${values.soc2.toFixed(1)}%`:'SIMULATION DATA';}
      if(item.kind==='bank'){
        title=`${item.id.toUpperCase()} / PRESSURE`;number=connected?values.banks[item.id].toFixed(2):'--';unit='MPa';
        foot=connected?(values.dispatch===item.id?'DISPATCH SELECTED':values.recharge===item.id?'RECHARGING':'ISOLATED / STANDBY'):'SIMULATION DATA';
      }
      if(item.kind==='safety'){title='SAFETY PLC';number=connected?(alarm?'ESD':'NORMAL'):'WAIT';foot=connected?`MODEL TIME ${values.time.toFixed(1)} s`:'SIMULATION DATA';}
      ctx.fillText(title,42,61);ctx.fillStyle=alarm?'#fff2eb':'#f0faf5';ctx.font=`bold ${number.length>6?90:128}px monospace`;ctx.fillText(number,42,214);
      ctx.font='44px monospace';ctx.fillStyle='#a0bdb6';ctx.fillText(unit,790,205);
      ctx.fillStyle='#294849';ctx.fillRect(42,251,940,3);ctx.fillStyle='#a1c4b9';ctx.font='29px monospace';ctx.fillText(foot,42,302);
      if(item.kind==='dispenser'&&connected){ctx.fillStyle='#274640';ctx.fillRect(42,333,940,16);ctx.fillStyle=alarm?'#ee705d':'#78dfaf';ctx.fillRect(42,333,940*Math.max(0,Math.min(1,values.soc/100)),16);}
      item.texture.needsUpdate=true;
    }
  }
  // Human-readable asset IDs and service-zone markings improve orientation.
  for(const [id,asset] of [['low','V-101'],['medium','V-102'],['high','V-103']]){
    const g=equipment.get(id).group;sign(asset,'CASCADE STORAGE',.78,.24,.33,.31,2.53,g,'#eaf0e9');
  }
  sign('HX-101','PRECOOLING',.69,.18,.62,.38,1.81,cooler,'#eff3ec');
  sign('PLC-101','SAFETY SYSTEM',.72,.17,0,.35,.653,cabinet,'#eff3ec');
  for(const x of [-6.4,11]){
    for(const side of [-1,1])box(.05,.009,1.30,x+side*1.65,.039,-2.78,M.yellow);
    box(3.30,.009,.05,x,.039,-2.1,M.yellow);
    for(let dx=-1.40;dx<1.4;dx+=.32){const stripe=box(.05,.009,.80,x+dx,.039,-2.65,M.yellow);stripe.rotation.y=-.55;}
  }
  const unloading=new THREE.Group();unloading.position.set(-9.2,0,-1.25);scene.add(unloading);
  box(.52,.78,.34,0,.55,0,M.white,unloading);box(.56,.07,.38,0,.98,0,M.green,unloading);
  cylinder(.035,.31,.05,.76,.25,detailMetal,unloading,'z');handValve(.05,.76,.34,unloading,M.green);
  gauge(-.12,.79,.20,unloading,.095);sign('GH2','UNLOADING',.43,.17,0,.48,.182,unloading,'#edf1e8');
  hazard('DELIVERY CONNECTION',0,1.37,.02,unloading,.95);cylinder(.025,.48,0,1.11,0,M.frame,unloading);
  tube([[-11.6,.70,-1.9],[-11.2,.18,-1.7],[-10.1,.16,-.95],[-9.15,.54,-.80],[-9.15,.76,-.90]],.038,rubber);
  // Site CCTV is decorative; it does not imply a security or safety sensor model.
  for(const [x,z] of [[-15.3,-10.5],[15.3,-10.5]]){
    cylinder(.047,4.7,x,2.35,z,M.frame);box(.40,.035,.035,x-.14,4.50,z,detailMetal);
    const cameraBody=box(.30,.16,.14,x-.32,4.5,z,M.white);cameraBody.rotation.y=x>0?.7:-.7;
    const lens=cylinder(.044,.04,0,0,.085,M.dark,cameraBody,'z');lens.castShadow=false;
  }
  // Underfloor tank packaging interpreted from Toyota's public three-tank layout.
  // These meshes represent the aggregate vehicle model, not three new process nodes.
  const vehicleTanks=new THREE.Group();car.add(vehicleTanks);vehicleTanks.visible=false;
  const carbonCanvas=document.createElement('canvas');carbonCanvas.width=carbonCanvas.height=256;
  const carbonContext=carbonCanvas.getContext('2d');carbonContext.fillStyle='#2c3336';carbonContext.fillRect(0,0,256,256);
  for(let i=-256;i<512;i+=12){
    carbonContext.lineWidth=4;carbonContext.strokeStyle='#404b4e';carbonContext.beginPath();carbonContext.moveTo(i,0);carbonContext.lineTo(i+256,256);carbonContext.stroke();
    carbonContext.lineWidth=2;carbonContext.strokeStyle='#1f292c';carbonContext.beginPath();carbonContext.moveTo(i,0);carbonContext.lineTo(i-256,256);carbonContext.stroke();
  }
  const carbonTexture=new THREE.CanvasTexture(carbonCanvas);carbonTexture.colorSpace=THREE.SRGBColorSpace;carbonTexture.wrapS=carbonTexture.wrapT=THREE.RepeatWrapping;carbonTexture.repeat.set(2,3);
  const carbonMaterial=mat(0xe1e6e2,.25,.56);carbonMaterial.map=carbonTexture;
  capsule(.16,1.30,.37,.63,0,carbonMaterial,vehicleTanks,'x');
  for(const x of [-.85,-1.60])capsule(.145,1.05,x,.63,0,carbonMaterial,vehicleTanks,'z');
  for(const x of [-.10,.82]){
    ring(.169,.015,x,.63,0,detailMetal,vehicleTanks,'x');box(.055,.027,.53,x,.44,0,M.frame,vehicleTanks);
  }
  for(const x of [-.85,-1.60])for(const z of [-.36,.36]){
    ring(.154,.012,x,.63,z,detailMetal,vehicleTanks);box(.36,.027,.055,x,.46,z,M.frame,vehicleTanks);
  }
  cylinder(.04,.15,1.21,.63,0,detailMetal,vehicleTanks,'x');
  for(const x of [-.85,-1.60]){cylinder(.036,.12,x,.63,.71,detailMetal,vehicleTanks,'z');handValve(x,.63,.80,vehicleTanks,M.green);}
  tube([[1.29,.63,0],[1.29,.50,.66],[-1.60,.50,.66],[-1.60,.63,.81]],.014,detailMetal,vehicleTanks);
  tube([[-.85,.63,.81],[-.85,.50,.66]],.014,detailMetal,vehicleTanks);
  sign('TYPE IV','AGGREGATE MODEL',.56,.15,.35,.65,.22,vehicleTanks,'#edf1e8');
  equipment.get('vehicle').description+=' 탱크 투시는 종방향 1개·후방 횡방향 2개 배치의 시각적 예시이며, 각 탱크가 독립 계산되는 모델은 아닙니다.';
  // Compact second dispenser: published DI001 envelope is 0.52 x 0.52 x 2.50 m.
  // Visual interpretation only; no manufacturer branding or certification claim.
  const compactDispenser=equipment.get('standby').group;
  compactDispenser.children.forEach((obj,i)=>{if(i!==0)obj.visible=false;});
  const compactBody=box(.52,2.5,.52,0,1.45,0,M.white,compactDispenser);
  softenHousing(compactBody,.52,2.5,.52,.024);
  box(.526,.38,.526,0,2.45,0,M.green,compactDispenser);
  box(.526,.055,.526,0,2.72,0,detailMetal,compactDispenser);
  box(.425,.265,.017,0,1.72,.27,M.dark,compactDispenser);
  instrument(compactDispenser,.40,.19,0,1.72,.284,'standby','standby');
  sign('H70','COMPACT / 700 BAR',.43,.19,0,2.44,.277,compactDispenser);
  sign('02','VISUAL REFERENCE',.38,.13,0,.77,.278,compactDispenser,'#eff2eb');
  seams(compactDispenser,.435,.85,.275,.83);
  for(const [x,material] of [[-.115,M.green],[.115,M.red]]){
    cylinder(.039,.018,x,1.39,.283,detailMetal,compactDispenser,'z');cylinder(.028,.025,x,1.39,.298,material,compactDispenser,'z');
  }
  box(.065,.13,.025,.17,.73,.286,M.frame,compactDispenser);
  cylinder(.055,.15,.29,2.12,0,detailMetal,compactDispenser,'x');
  tube([[.35,2.12,0],[.66,1.97,.05],[.79,.65,.16],[.61,.42,.32],[.40,.75,.39],[.37,1.28,.33]],.032,rubber,compactDispenser);
  capsule(.04,.15,.37,1.34,.30,detailMetal,compactDispenser,'z');box(.052,.11,.15,.37,1.25,.33,M.dark,compactDispenser);
  ring(.063,.012,.37,1.25,.38,detailMetal,compactDispenser);
  box(.09,.14,.09,.275,1.35,.20,M.frame,compactDispenser);
  for(const dx of [-1.1,1.1])for(const dz of [-.55,.55]){
    cylinder(.10,.8,dx,.55,dz,M.yellow,compactDispenser);cylinder(.105,.18,dx,.58,dz,M.black,compactDispenser);
  }
  const compactItem=equipment.get('standby');compactItem.title='컴팩트 H70 디스펜서 · 대기';
  compactItem.description='공개 DI001 자료의 외형 치수 520 × 520 × 2500 mm를 참조한 컴팩트 충전기입니다. 외장·화면·호스 형상은 시각적으로 해석했으며, 이 두 번째 충전기는 공정 계산에 연결되지 않습니다.';
  compactItem.tag='DISPENSING / COMPACT VISUAL REFERENCE';
  // Illustrative high-level detectors above the dispensing equipment.
  for(const [x,number] of [[0,'01'],[8,'02']]){
    const detector=new THREE.Group();detector.position.set(x,4.66,4.25);scene.add(detector);
    box(.25,.12,.20,0,.08,0,M.white,detector);box(.05,.16,.05,0,.02,0,M.frame,detector);
    cylinder(.052,.08,0,-.07,0,detailMetal,detector);cylinder(.04,.018,0,-.116,0,M.dark,detector);
    for(const dx of [-.025,.025])box(.009,.016,.048,dx,-.126,0,detailMetal,detector);
    tube([[.12,.09,0],[.24,.09,0],[.24,.23,0],[.8,.23,0]],.008,M.black,detector);
    sign(number==='01'?'GD-2101':'GD-2201','VIRTUAL H2',.38,.13,0,.055,.108,detector,'#edf2e9');
    register(`detector${number}`,detector,`수소감지기 · 충전구역 ${number}`,'해당 충전 구역의 가상 농도 신호와 연결됩니다. 누출량 기반 대리 신호이며 현장 계측이나 검증된 가스 확산 해석값은 아닙니다.','DETECTION / VIRTUAL SIGNAL');
  }
  // Replace the earlier blocky transporter while preserving its supply equipment group.
  trailer.children.forEach(obj=>obj.visible=false);
  trailer.add(buildHydrogenTransporter());
  const supplyItem=equipment.get('supply');supplyItem.title='기체수소 운송차량 · 튜브트레일러';
  supplyItem.description='공개 튜브트레일러·유럽형 트랙터 자료를 참조한 비브랜드 운송차량입니다. 곡면 운전석, 분리 섀시, 다축 바퀴, 용기 고정 프레임과 후방 매니폴드를 표현합니다. 차량은 시각 모델이며 공급 계산은 기존 지정 압력·온도 경계조건을 유지합니다.';
  // Distinguish refrigeration, HTF circulation and hydrogen HEX visually.
  cooler.children.forEach(obj=>obj.visible=false);
  const coolingPackage=buildCoolingPackage();cooler.add(coolingPackage.group);
  coverMeshes.splice(2,1,...coolingPackage.covers);
  animatedFans.splice(0,animatedFans.length);
  statusLights.push({material:coolingPackage.statusMaterial,id:'fueling'});
  const coolingItem=equipment.get('cooler');coolingItem.title='프리쿨링 패키지 · 냉동기 / 순환 / HEX';
  coolingItem.description='수냉식 냉동기, 냉각유체 버퍼·순환펌프, 고압 수소 열교환기를 구분한 참조 모델입니다. 수소 포트는 공정 배관에 연결되며 냉각유체·시설 냉각수 배관은 시각 모델입니다. 계산은 기존 유한 UA·열용량 모델을 유지하고, 표시 온도는 설정값입니다.';
  // Rebuild the compressor as a coherent skid with removable, attached enclosure skins.
  compressor.children.forEach(obj=>obj.visible=false);
  const compressionPackage=buildCompressorPackage();compressor.add(compressionPackage.group);
  coverMeshes.splice(0,2,...compressionPackage.covers);
  statusLights.push({material:compressionPackage.statusMaterial,id:'compressor'});
  const compressionItem=equipment.get('compressor');compressionItem.title='수소 압축기 · 다이어프램 참조 스키드';
  compressionItem.description='다이어프램 압축기 자료를 참조한 모터·구동부·3단 압축 헤드·중간냉각기·계장 배관의 시각 모델입니다. 외함 패널을 열어 내부를 볼 수 있으며, 기존 압축 효율·재충전·전력 계산을 유지합니다. 다이어프램 변형·구동 유압·내부 계기 응답은 계산하지 않습니다.';
  // Replace the oversized original cylinders without changing bank physics.
  ['low', 'medium', 'high'].forEach((name, index) => {
    const item = equipment.get(name);
    item.group.children.forEach(obj => { obj.visible = false; });
    const storagePackage = buildStorageBank({ name, index });
    item.group.add(storagePackage.group);
    item.group.userData.processPorts = storagePackage.ports;
    statusLights.push({ material: storagePackage.statusMaterial, id: name });
    instrument(storagePackage.group, .83, .31, -.25, 2.49, 1.97, 'bank', name);
    item.description = 'FIBA Type II 공개 자료의 용기 형식을 참조한 6본 랙입니다. 복합재 몸통·금속 끝단·새들·고정 밴드·개별 밸브·매니폴드를 표현합니다. 외경과 지지 구조는 개념 치수이며, 기존 계산 용적·압력·캐스케이드 제어는 그대로 유지합니다.';
  });

  // Reference vent header and stack: deliberately not a new flow/risk model.
  const ventItem = equipment.get('vent');
  ventItem.group.children.forEach(obj => { obj.visible = false; });
  scene.updateMatrixWorld(true);
  ventItem.group.add(buildVentPackage(equipment).group);
  ventItem.description = 'EIGA 211/24와 H2Tools 자료를 참조한 기체 수소 벤트 형상입니다. 저장 뱅크 참조 릴리프 포트·후면 헤더·기초·지지대·접지선·배수 피팅·상향 방출구를 표시합니다. 헤더 유량·배압·분산·구조 하중은 계산하지 않으며 피해영향예측 입력을 추가하지 않습니다. 높이와 안전거리 적합성을 의미하지 않습니다.';

  // Replace the simplified sedan while preserving its group and nozzle port.
  car.children.forEach(obj => { obj.visible = false; });
  const vehiclePackage = buildFcevVehicle();
  car.add(vehiclePackage.group);
  const car2 = new THREE.Group();
  car2.position.set(10.8,.03,7);
  scene.add(car2);
  const vehiclePackage2 = buildFcevVehicle();
  car2.add(vehiclePackage2.group);
  register(
    'vehicle2',
    car2,
    '2번 H70 연료전지 세단',
    '2번 디스펜서의 독립 차량 탱크 상태입니다. 저장 뱅크는 1번 차량과 공유하지만 차량 열역학, 호스 라인팩, PCV, 프리쿨러 상태와 충전 제어는 별도로 계산합니다.',
    'VEHICLE 02',
  );
  scene.updateMatrixWorld(true);
  const vehicle2Port = new THREE.Vector3(-1.95,.84,-.965);
  const nozzleTip2 = compactDispenser.worldToLocal(car2.localToWorld(vehicle2Port.clone()));
  const hoseEnd2 = nozzleTip2.clone().add(new THREE.Vector3(0,-.065,-.31));
  tube([[.52,1.75,0],[.79,1.65,.12],[.95,.55,.80],[nozzleTip2.x-.12,.28,nozzleTip2.z-.65],[nozzleTip2.x-.04,.67,nozzleTip2.z-.48],hoseEnd2.toArray()],.043,rubber,compactDispenser);
  const nozzleVector2 = nozzleTip2.clone().sub(hoseEnd2);
  const nozzle2 = new THREE.Mesh(
    new THREE.CylinderGeometry(.045,.058,nozzleVector2.length(),18),
    detailMetal,
  );
  nozzle2.position.copy(hoseEnd2.clone().add(nozzleTip2).multiplyScalar(.5));
  nozzle2.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),nozzleVector2.clone().normalize());
  nozzle2.castShadow = true;
  compactDispenser.add(nozzle2);
  const standbyItem = equipment.get('standby');
  standbyItem.title = '수소 디스펜서 02';
  standbyItem.description = '독립 PCV·프리쿨러 열용량·호스 라인팩·노즐·차량 탱크 모델을 갖는 두 번째 H70 충전 포인트입니다. 1번 디스펜서와 캐스케이드 저장 및 압축기를 공유합니다.';
  const vehicleItem = equipment.get('vehicle');
  if (vehicleItem) {
    vehicleItem.title = '5인승 H70 연료전지 세단';
    vehicleItem.description = 'Toyota 2세대 Mirai 공개 패키징을 참조한 비상표 시각 모델입니다. 전방 FC 스택·PCU, 센터 터널 종방향 탱크, 후방 횡방향 탱크 2개, 리튬이온 배터리와 후륜 모터를 구분했습니다. 차량 계산은 기존 단일 Type IV 탱크 모델을 유지하며 개별 부품 동역학은 계산하지 않습니다.';
  }

  // Virtual detector heads at the remaining process zones.
  for(const [tag,title,x,y,z] of [
    ['2301','저·중압 저장 구역',1,2.7,-3.8],['2302','고압 저장 구역',5,2.7,-3.8],
    ['1901','압축기 구역',-6.2,2.8,-3.8],['2001','헤더·안전 구역',12,2.6,-3.3],['1701','PCV 구역',6.5,2.5,1.5]
  ]){
    const detector=new THREE.Group();detector.position.set(x,y,z);scene.add(detector);
    box(.25,.14,.2,0,0,0,M.white,detector);cylinder(.05,.08,0,-.1,0,detailMetal,detector);
    sign('GD-'+tag,'VIRTUAL H2',.44,.14,0,.14,.108,detector,'#edf2e9');
    register('detector'+tag,detector,'수소감지기 · '+title,'누출 위치에 연동된 가상 검지 신호입니다. 농도는 누출량 기반 대리값이며 현장 계측이나 검증된 확산 해석값이 아닙니다.','GD-'+tag+' / VIRTUAL SIGNAL');
  }
  // Include the added detail meshes in the existing equipment picker.
  const alreadyPickable=new Set(pickMeshes);
  for(const {group} of equipment.values())group.traverse(obj=>{if(obj.isMesh&&!alreadyPickable.has(obj)){pickMeshes.push(obj);alreadyPickable.add(obj);}});
  // Batch only immutable scenery; never replace picked equipment or animated objects.
  const sceneryBatchStats={objects:0,batches:0};
  function batchScenery(parent){
    const buckets=new Map();
    for(const obj of [...parent.children]){
      if(!obj.isMesh||obj.isInstancedMesh||!obj.visible||Array.isArray(obj.material))continue;
      if(!['BoxGeometry','CylinderGeometry','TorusGeometry'].includes(obj.geometry.type))continue;
      if(obj.material.transparent||obj.userData.equipmentId)continue;
      const key=[obj.geometry.type,JSON.stringify(obj.geometry.parameters),obj.material.uuid,obj.castShadow,obj.receiveShadow].join('|');
      if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(obj);
    }
    for(const objects of buckets.values()){
      if(objects.length<6)continue;
      const first=objects[0],batch=new THREE.InstancedMesh(first.geometry,first.material,objects.length);
      batch.castShadow=first.castShadow;batch.receiveShadow=first.receiveShadow;
      objects.forEach((obj,i)=>{obj.updateMatrix();batch.setMatrixAt(i,obj.matrix);parent.remove(obj);});
      batch.instanceMatrix.setUsage(THREE.StaticDrawUsage);batch.computeBoundingSphere();parent.add(batch);
      sceneryBatchStats.objects+=objects.length;sceneryBatchStats.batches++;
    }
  }
  for(const parent of [scene,context,backgroundBuilding,staticProcess,attendant,emergency,unloading,totem,gate,landscape])batchScenery(parent);
  panel.dataset.sceneryObjects=String(sceneryBatchStats.objects);panel.dataset.sceneryBatches=String(sceneryBatchStats.batches);
  const selection=new THREE.BoxHelper(car,0xe9b547);selection.visible=false;scene.add(selection);
  let selectedId=null,lastIndex=-1,lastResult=null,night=false,pipesVisible=true,visible=true;
  let transition=null,live={time:0,pressure:5,temperature:25,soc:0,flow:0,flow1:0,flow2:0,pressure2:5,temperature2:25,soc2:0,dispatch:null,dispatch2:null,recharge:null,esd:false,leak:0,activeFaults:[],banks:{low:45,medium:65,high:90}};
  const assetMenu=$('s3Assets');
  for(const [id,item] of equipment){
    const button=document.createElement('button');button.type='button';button.dataset.equipment=id;button.setAttribute('aria-pressed','false');
    const name=document.createElement('span');name.textContent=item.title;
    const tag=document.createElement('small');tag.textContent=item.tag;button.append(name,tag);
    button.addEventListener('click',()=>selectEquipment(id));assetMenu.append(button);
  }
  $('s3AssetsToggle').addEventListener('click',()=>{
    const expanded=$('s3AssetsToggle').getAttribute('aria-expanded')!=='true';
    $('s3AssetsToggle').setAttribute('aria-expanded',String(expanded));assetMenu.hidden=!expanded;
  });
  function selectEquipment(id){
    const item=equipment.get(id);if(!item)return;
    selectedId=id;selection.setFromObject(item.group);selection.visible=true;updateCard();
    window.showCctvFor?.(id);
  }
  $('s3CctvButton').addEventListener('click',()=>{
    const stateName=live.activeFaults.some(f=>f.startsWith('external-fire'))?'fire':live.activeFaults.some(f=>f.startsWith('hydrogen-leak'))?'leak':'normal';
    openStationCctv(activeCctvId,stateName,live.time);
  });
  window.selectStationEquipment=id=>{window.setMonitorView('3d');selectEquipment(id);};
  $('s3Details').addEventListener('click',()=>window.showEquipmentDetails?.({...equipment.get(selectedId),id:selectedId}));
  window.stationEquipment=equipment;
  const presets={overview:{p:[29,23,31],t:[0,1,0]},fueling:{p:[17,11,23],t:[4,1.4,5]},plant:{p:[21,16,-24],t:[0,1.4,-5]},top:{p:[0,42,.15],t:[0,0,0]}};
  panel.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{
    const view=presets[button.dataset.view];transition={p:new THREE.Vector3(...view.p),t:new THREE.Vector3(...view.t)};
    panel.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('selected',b===button));
  }));
  controls.addEventListener('start',()=>{transition=null;});
  $('s3Focus').addEventListener('click',()=>{
    const item=equipment.get(selectedId);if(!item)return;
    const bounds=new THREE.Box3().setFromObject(item.group),center=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3());
    const angle=THREE.MathUtils.degToRad(camera.fov/2),span=Math.max(size.y,size.x/Math.max(.5,camera.aspect),size.z/Math.max(.5,camera.aspect));
    const distance=Math.max(4,span/(2*Math.tan(angle))*1.35);
    const direction=camera.position.clone().sub(controls.target).normalize();direction.y=Math.max(.3,direction.y);direction.normalize();
    transition={p:center.clone().addScaledVector(direction,distance),t:center};
    panel.querySelectorAll('[data-view]').forEach(button=>button.classList.remove('selected'));
  });
  $('s3Pipes').addEventListener('click',()=>{pipesVisible=!pipesVisible;$('s3Pipes').setAttribute('aria-pressed',String(pipesVisible));});
  $('s3Roof').addEventListener('click',()=>{
    const transparent=$('s3Roof').getAttribute('aria-pressed')!=='true';roofMaterial.transparent=transparent;roofMaterial.opacity=transparent?.18:1;roofMaterial.depthWrite=!transparent;roofMaterial.needsUpdate=true;$('s3Roof').setAttribute('aria-pressed',String(transparent));
  });
  $('s3Service').addEventListener('click',()=>{
    const opened=$('s3Service').getAttribute('aria-pressed')!=='true';
    coverMeshes.forEach(obj=>obj.visible=!opened);$('s3Service').setAttribute('aria-pressed',String(opened));
  });
  $('s3VehicleCutaway').addEventListener('click',()=>{
    const enabled=$('s3VehicleCutaway').getAttribute('aria-pressed')!=='true';
    vehiclePackage.setCutaway(enabled);vehiclePackage2.setCutaway(enabled);
    vehicleTanks.visible=enabled;body.material.transparent=enabled;body.material.opacity=enabled?.16:1;
    body.material.depthWrite=!enabled;body.material.needsUpdate=true;body.castShadow=!enabled;
    $('s3VehicleCutaway').setAttribute('aria-pressed',String(enabled));
  });
  $('s3Night').addEventListener('click',()=>{
    night=!night;$('s3Night').setAttribute('aria-pressed',String(night));hemi.intensity=night?.45:2.2;sun.intensity=night?.3:3.1;renderer.toneMappingExposure=night?1.35:1.12;
    scene.fog.color.set(night?0x19343e:0x1c2d38);stage.style.background=night?'radial-gradient(ellipse at top,#2a4e5b,#112831)':'';nightLights.forEach(light=>light.intensity=night?75:0);
    skyMaterial.color.set(night?0x142a3a:0x263c49);
  });
  const raycaster=new THREE.Raycaster();const pointer=new THREE.Vector2();let down=null;
  renderer.domElement.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY];});
  renderer.domElement.addEventListener('pointerup',e=>{
    if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;
    const rect=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(pointer,camera);
    const hit=raycaster.intersectObjects(pickMeshes,false).find(hit=>{let obj=hit.object;while(obj){if(!obj.visible)return false;obj=obj.parent;}return true;});if(!hit)return;
    let object=hit.object;while(object&&!object.userData.equipmentId)object=object.parent;if(!object)return;
    selectEquipment(object.userData.equipmentId);
  });
  function readLive() {
    const runtime=window.getStation3DState?.();const result=runtime?.result;const s=result?.series;const index=runtime?.index;
    if(!s?.time_s?.length||index===undefined||(lastIndex===index&&lastResult===result&&live.time===s.time_s[index]))return;
    lastIndex=index;lastResult=result;
    const at=(name,fallback)=>s[name]?.[index]??fallback;
    live={time:at('time_s',0),pressure:at('vehicle_pressure_mpa',0),temperature:at('vehicle_temperature_c',25),soc:at('soc_percent',0),flow:at('nozzle_flow_g_s',0),flow1:at('nozzle_1_flow_g_s',0),flow2:at('nozzle_2_flow_g_s',0),pressure2:at('vehicle_2_pressure_mpa',0),temperature2:at('vehicle_2_temperature_c',25),soc2:at('vehicle_2_soc_percent',0),dispatch:at('dispatch_bank',null),dispatch2:at('dispatch_bank_2',null),recharge:at('recharge_bank',null),esd:at('esd',false),leak:at('total_leak_flow_g_s',0),activeFaults:at('active_faults',[]),banks:Object.fromEntries(['low','medium','high'].map(name=>[name,s.bank_pressure_mpa?.[name]?.[index]??0]))};
    updateAccidentVisuals(live.activeFaults);
    updateEffectRanges(result?.hazop?.frames?.[index]);
    const badge=$('s3Live');badge.classList.toggle('active',!live.esd&&!live.activeFaults.length);badge.querySelector('span').textContent=live.esd?`ESD · ${live.time.toFixed(1)} s`:live.activeFaults.length?`사고 시각화 · ${live.activeFaults.length}건`:`운전 데이터 연결 · ${live.time.toFixed(1)} s`;drawInstruments(live,true);updateCard();refreshCctv();
    updateMonitorCards();
  }
  function updateMonitorCards() {
    const runtime=window.getStation3DState?.(), hasData=Boolean(runtime?.result?.series?.time_s?.length);
    const detectors=runtime?.result?.series?.gas_detectors?.[runtime.index]||{};
    const readings=Object.values(detectors).filter(d=>d?.quality==='GOOD'&&Number.isFinite(d.value));
    const concentration=readings.length?Math.max(...readings.map(d=>d.value)):null;
    const text=(id,value)=>{const node=$(id);if(node)node.textContent=value;};
    text('s3BankHigh',live.banks.high.toFixed(1));text('s3BankMedium',live.banks.medium.toFixed(1));text('s3BankLow',live.banks.low.toFixed(1));
    text('s3BankState',live.esd?'ESD 차단':live.activeFaults.length?'사고 영향 확인':live.dispatch?`${String(live.dispatch).toUpperCase()} 토출`:'압력 신호 정상');
    const compressorActive=Boolean(live.recharge);text('s3CompressorState',compressorActive?'재충전 중':'대기');text('s3CompressorDetail',compressorActive?`${String(live.recharge).toUpperCase()} 뱅크 충전`:'재충전 뱅크 없음');text('s3CompressorFoot',compressorActive?'압축기 운전 신호 연결':'3단 압축 · 중간 냉각');const meter=$('s3CompressorMeter');if(meter)meter.style.width=compressorActive?'100%':'0%';
    text('s3Dispenser1',live.flow1.toFixed(1));text('s3Dispenser2',live.flow2.toFixed(1));text('s3DispenserFoot',live.esd?'ESD 차단':live.flow>0.01?'충전 중 · 프리쿨러 −40 °C':'대기 · 프리쿨러 −40 °C');
    const safety=live.esd?'ESD 차단':live.leak>0.001?'누출 경보':live.activeFaults.length?'사고 감시':'정상';text('s3SafetyState',safety);text('s3LeakState',`누출 ${live.leak.toFixed(2)} g/s`);text('s3DetectorState',concentration==null?'미수신':`${concentration.toFixed(2)} vol%`);text('s3SafetyFoot',live.esd?'ESD 래치 · 공정 격리':live.leak>0.001?'가스검지기 신호 확인':'ESD 대기 · 검지기 연결');
    if(!hasData){['s3BankHigh','s3BankMedium','s3BankLow','s3Dispenser1','s3Dispenser2'].forEach(id=>text(id,'—'));text('s3BankState','모델 데이터 대기');text('s3SafetyState','대기');text('s3SafetyFoot','가스검지기 데이터 미수신');text('s3LeakState','누출 — g/s');}
    const dot=$('s3SafetyDot');if(dot)dot.classList.toggle('alarm',hasData&&safety!=='정상');
  }
  function updateCard() {
    $('s3Focus').disabled=!equipment.has(selectedId);
    assetMenu.querySelectorAll('[data-equipment]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.equipment===selectedId)));
    const item=equipment.get(selectedId);$('s3Title').textContent=item?.title||'전체 충전소';$('s3Tag').textContent=item?.tag||'H70 / DIGITAL OPERATIONS';
    $('s3Description').textContent=item?.description||'설비를 클릭하면 역할과 운전값을 확인합니다. 드래그로 회전, 휠로 확대, 오른쪽 드래그로 이동합니다.';
    let label='모의 시간',value=`${live.time.toFixed(1)} s`;
    if(['low','medium','high'].includes(selectedId)){label='뱅크 압력';value=`${live.banks[selectedId].toFixed(2)} MPa`;}
    if(selectedId==='vehicle'){label=`SOC ${live.soc.toFixed(1)}% / ${live.temperature.toFixed(1)}°C`;value=`${live.pressure.toFixed(2)} MPa`;}
    if(selectedId==='vehicle2'){label=`SOC ${live.soc2.toFixed(1)}% / ${live.temperature2.toFixed(1)}°C`;value=`${live.pressure2.toFixed(2)} MPa`;}
    if(selectedId==='dispenser'){label=live.esd?'ESD 차단':'노즐 유량';value=`${live.flow1.toFixed(2)} g/s`;}
    if(selectedId==='compressor'){label='재충전 대상';value=live.recharge?.toUpperCase()||'대기';}
    if(selectedId==='safety'){label='보호 상태';value=live.esd?'ESD LATCHED':'NORMAL';}
    if(selectedId==='cooler'){label='설정값 · 출구 실측 아님';value='−40 °C';}
    if(selectedId==='supply'){label='공급 모델';value='P / T 경계';}
    if(selectedId==='standby'){label=live.esd?'ESD 차단':'2번 노즐 유량';value=`${live.flow2.toFixed(2)} g/s`;}

    if(selectedId==='vent'){label='상세 유동 모델';value='미연결';}
    if(selectedId?.startsWith('detector')){
      const runtime=window.getStation3DState?.(),tag=selectedId==='detector01'?'GD-2101':selectedId==='detector02'?'GD-2201':'GD-'+selectedId.replace('detector','');
      const signal=runtime?.result?.series?.gas_detectors?.[runtime.index]?.[tag];
      label=tag+' · 가상 검지';value=Number.isFinite(signal?.value)?signal.value.toFixed(2)+' vol%':'미수신';
    }
    if(!window.getStation3DState?.()?.result?.series?.time_s?.length){label='운전 데이터 대기';value='—';}
    $('s3ReadingLabel').textContent=label;$('s3Reading').textContent=value;
    refreshCctv();
  }
  function pipeActive(id) {
    if(live.esd)return false;
    if(id==='fueling')return live.flow>.01;
    if(id==='fueling2')return live.flow2>.01;
    if(id==='compressor')return Boolean(live.recharge);
    if(id.startsWith('recharge:'))return live.recharge===id.split(':')[1];
    return (live.dispatch===id.split(':')[1]||live.dispatch2===id.split(':')[1])&&live.flow>.01;
  }
  function resizeRenderer(){
    const width=stage.clientWidth,height=stage.clientHeight;if(width<1||height<1)return;
    const scale=stage.getBoundingClientRect().width/width||1;
    renderer.setPixelRatio(Math.min((window.devicePixelRatio||1)*scale,3));
    camera.aspect=width/height;camera.updateProjectionMatrix();renderer.setSize(width,height,false);
  }
  new ResizeObserver(resizeRenderer).observe(stage);
  window.addEventListener('wall-resize',resizeRenderer);
  new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;},{rootMargin:'100px'}).observe(stage);
  // Normalize high-resolution wheels and spread the bounded dolly input over frames.
  // Forward small steps to OrbitControls so its native cursor-zoom math remains intact.
  const forwardedWheels=new WeakSet();let pendingWheel=0;let wheelPosition={x:0,y:0};
  renderer.domElement.addEventListener('wheel',event=>{
    if(forwardedWheels.has(event)||!controls.enabled||!controls.enableZoom)return;
    event.preventDefault();event.stopImmediatePropagation();transition=null;
    const units=event.deltaMode===1?16:event.deltaMode===2?stage.clientHeight:1;
    const bounded=THREE.MathUtils.clamp(event.deltaY*units,-120,120);
    pendingWheel=THREE.MathUtils.clamp(pendingWheel+bounded,-480,480);
    wheelPosition={x:event.clientX,y:event.clientY};
  },{capture:true,passive:false});
  let lastRender=0;
  function animate(timestamp) {
    requestAnimationFrame(animate);if(!visible||document.hidden||timestamp-lastRender<33)return;lastRender=timestamp;readLive();
    if(Math.abs(pendingWheel)>.1){
      const step=Math.abs(pendingWheel)<.5?pendingWheel:pendingWheel*.28;pendingWheel-=step;
      const wheel=new WheelEvent('wheel',{deltaY:step,deltaMode:0,clientX:wheelPosition.x,clientY:wheelPosition.y,cancelable:true});
      forwardedWheels.add(wheel);renderer.domElement.dispatchEvent(wheel);
    }else pendingWheel=0;
    if(transition){camera.position.lerp(transition.p,.10);controls.target.lerp(transition.t,.10);if(camera.position.distanceTo(transition.p)<.04)transition=null;}
    for(const light of statusLights){
      const active=light.id==='fueling'?live.flow>.01:light.id==='compressor'?Boolean(live.recharge):light.id==='safety'?true:live.dispatch===light.id;
      light.material.color.set(live.esd?0xe95548:active?0x2de2ac:0x6a9585);light.material.emissive.set(live.esd?0x8c1812:active?0x087c57:0x10291e);light.material.emissiveIntensity=active?1.3:.2;
    }
    for(const segment of dynamicPipes){
      const active=pipeActive(segment.id);segment.obj.visible=pipesVisible;segment.obj.material.color.set(live.esd?0xd65945:segment.color);
      segment.particles.forEach((dot,i)=>{dot.visible=pipesVisible&&active;dot.position.copy(segment.curve.getPointAt((timestamp*.00018+i/segment.particles.length)%1));});
    }
    animatedFans.forEach(fan=>{fan.rotation.y=live.esd?0:timestamp*(live.flow>.01?.006:.0015);});
    controls.update();updateCameraMarkers();animateAccidents(timestamp);renderer.render(scene,camera);
  }
  window.addEventListener('station-frame',readLive);
  drawInstruments(live,false);updateMonitorCards();updateCard();readLive();requestAnimationFrame(animate);
  window.dispatchEvent(new Event('station-ready'));
}
