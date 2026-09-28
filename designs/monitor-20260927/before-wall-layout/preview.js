// Isolated design prototype. All readings are illustrative; no process API is called.
import * as THREE from '/vendor/three/three.module.js';
import { OrbitControls } from '/vendor/three/OrbitControls.js';
import { buildStorageBank } from '/storage-bank.js';
import { buildCompressorPackage } from '/compressor-package.js';
import { buildCoolingPackage } from '/cooling-package.js';
import { buildFcevVehicle } from '/fcev-vehicle.js';

const $=id=>document.getElementById(id);
const scene=new THREE.Scene();scene.background=new THREE.Color('#1b2a35');
const camera=new THREE.PerspectiveCamera(35,16/9,.1,150);camera.position.set(24,22,28);
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.35;$('scene').append(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,.7,0);controls.enableDamping=true;controls.enablePan=false;controls.minDistance=21;controls.maxDistance=65;controls.maxPolarAngle=Math.PI*.46;controls.update();
scene.add(new THREE.HemisphereLight(0xd6eaff,0x2b3842,2.4));
const sun=new THREE.DirectionalLight(0xfff0dd,4.5);sun.position.set(-10,25,18);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-20,right:20,top:20,bottom:-20});sun.shadow.bias=-.0003;scene.add(sun);
const fill=new THREE.DirectionalLight(0x85bfd4,1.6);fill.position.set(15,8,-15);scene.add(fill);
const mat=(color,metalness=.15,roughness=.75)=>new THREE.MeshStandardMaterial({color,metalness,roughness});
const concrete=mat('#6c8088'),baseMat=mat('#3f535f'),white=mat('#dee6e4'),dark=mat('#263e48'),teal=mat('#44988d'),steel=mat('#9facb2',.7,.35);
function box(w,h,d,x,y,z,m){const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),m);mesh.position.set(x,y,z);mesh.castShadow=mesh.receiveShadow=true;scene.add(mesh);return mesh;}
function pipe(points,color,r=.07){const curve=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)));const m=new THREE.MeshStandardMaterial({color,emissive:color,emissiveIntensity:.2,metalness:.5,roughness:.35});const o=new THREE.Mesh(new THREE.TubeGeometry(curve,64,r,8,false),m);scene.add(o);return o;}
box(25,.5,20,0,-.5,0,baseMat);box(24.6,.08,19.6,0,-.2,0,concrete);
box(23,.015,.06,0,-.147,8.4,white);box(23,.015,.06,0,-.147,-8.6,white);
const grid=new THREE.GridHelper(80,80,0x29404e,0x243a47);grid.position.y=-.82;scene.add(grid);
for(let i=0;i<3;i++){const unit=buildStorageBank({name:['LOW','MID','HIGH'][i],index:i});unit.group.position.set(-6+i*4.8,0,-5.3);scene.add(unit.group);box(4.25,.16,5,-6+i*4.8,-.07,-5.3,white);}
const compressor=buildCompressorPackage();compressor.group.position.set(-7,0,1.5);scene.add(compressor.group);box(5,.15,5.7,-7,-.06,1.5,white);
const cooler=buildCoolingPackage();cooler.group.position.set(-1.6,0,1.4);scene.add(cooler.group);box(3.7,.15,5.7,-1.6,-.06,1.4,white);
for(let i=0;i<2;i++){const x=4+i*4;box(2,.12,3.2,x,-.06,1.8,white);box(.7,1.6,.75,x,.86,1.8,white);box(.73,.65,.79,x,1.3,1.8,teal);box(.42,.3,.04,x,1.35,2.21,dark);box(.8,.12,.9,x,1.75,1.8,white);pipe([[x+.42,1.4,1.8],[x+.9,.7,1.8],[x+.85,.35,3],[x+.1,.75,4.3]],'#293d45',.045);const car=buildFcevVehicle();car.group.position.set(x,0,5.8);car.group.rotation.y=Math.PI/2;scene.add(car.group);box(2.7,.018,.06,x,-.13,8.45,white);box(.045,.018,5.5,x-1.6,-.13,5.8,white);box(.045,.018,5.5,x+1.6,-.13,5.8,white);}
// An open frame keeps process equipment visible in the default camera.
for(const x of[2.2,10])for(const z of[-.5,8.5])box(.13,3.8,.13,x,1.8,z,steel);
box(8,.2,.25,6.1,3.75,-.5,white);box(8,.2,.25,6.1,3.75,8.5,white);box(.25,.2,9,2.2,3.75,4,white);box(.25,.2,9,10,3.75,4,white);
box(8,.07,1.15,6.1,3.89,-.05,teal);box(8,.07,.55,6.1,3.89,8.3,teal);
pipe([[-7,1.1,-.2],[-7,.4,-1.1],[-6,.35,-1.7],[-1,.35,-1.7],[3.6,.35,-1.7],[3.6,1.1,-3.1]],'#62c3b2');
pipe([[-6,1,-3.1],[-6,.4,-2.4],[0,.4,-2.4],[5,.4,-2.4],[6,.4,-1.1],[6,.4,0]],'#62c3b2');
pipe([[-1.5,1,3.6],[-1.5,.25,4],[.6,.25,4],[.6,.25,1.8],[4,.3,1.8]],'#88b9d6');
pipe([[.6,.25,1.8],[.6,.25,0],[8,.25,0],[8,.4,1.8]],'#88b9d6');
for(let x=-11.5;x<=11.5;x+=1.5){box(.035,1.55,.035,x,.63,-9.3,steel);box(1.4,.026,.028,x+.7,1.1,-9.3,steel);box(1.4,.026,.028,x+.7,.45,-9.3,steel);}
for(const x of[-11,11]){box(.07,5,.07,x,2.25,-6,steel);box(.7,.08,.25,x,4.75,-6,white);}
for(let i=0;i<6;i++){box(.08,.6,.08,-10.5+i*.6,.16,6,teal);}
const anchors={storage:new THREE.Vector3(-1.3,3.5,-5.3),compressor:new THREE.Vector3(-7,3.1,1.5),dispenser:new THREE.Vector3(6,2.2,4)};
function resize(){const r=$('stage').getBoundingClientRect();renderer.setSize(r.width,r.height);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe($('stage'));resize();
function render(){requestAnimationFrame(render);controls.update();renderer.render(scene,camera);for(const [key,anchor]of Object.entries(anchors)){const p=anchor.clone().project(camera),pin=document.querySelector(`[data-camera="${key}"]`);pin.style.left=(p.x*.5+.5)*100+'%';pin.style.top=(-p.y*.5+.5)*100+'%';}}
render();
document.querySelectorAll('[data-angle]').forEach(button=>button.onclick=()=>{document.querySelectorAll('[data-angle]').forEach(b=>b.classList.toggle('selected',b===button));const views={overview:[[24,22,28],[0,.7,0]],plant:[[17,20,18],[-3,1,-3]],fueling:[[23,14,26],[5,1,3]]};const[p,t]=views[button.dataset.angle];camera.position.fromArray(p);controls.target.fromArray(t);controls.update();});
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>{const flow=button.dataset.view==='flow';document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('selected',b===button));$('flowView').hidden=!flow;$('cameraPins').hidden=flow;document.querySelector('.stage-bottom').hidden=flow;document.querySelector('.scene-caption').hidden=flow;document.querySelector('.stage-top').hidden=flow;});
document.querySelectorAll('[data-state]').forEach(button=>button.onclick=()=>{const incident=button.dataset.state==='incident';document.body.classList.toggle('incident-mode',incident);document.querySelectorAll('[data-state]').forEach(b=>b.classList.toggle('selected',b===button));document.querySelector('.incident-panel').hidden=!incident;document.querySelector('.incident-pin').hidden=!incident;$('overall').textContent=incident?'2번 충전 구역 확인 필요':'안정적으로 운전 중';$('assessmentTitle').textContent=incident?'가스 신호 이상 감지':'공정 상태 양호';$('assessmentBadge').textContent=incident?'ATTENTION':'NORMAL';document.querySelector('.assessment-icon').textContent=incident?'!':'✓';$('assessmentText').textContent=incident?'2번 충전 구역의 가상 가스 신호가 시안 임계값을 초과했습니다. 관련 사고 분석을 확인하세요.':'충전 압력·온도가 예시 운전 범위에 있습니다.';$('gasTop').innerHTML=(incident?'1.20':'0.00')+' <small>vol%</small>';$('disp2status').textContent=incident?'구역 확인 필요':'충전 중';});
const cams={storage:['CAM-01 · 저장 뱅크','cctv-storage-banks.png'],compressor:['CAM-02 · 압축기','cctv-compressor.png'],dispenser:['CAM-03 · 충전 구역','cctv-dispenser.png']};
function dialog(title,html,kicker='DESIGN PREVIEW'){$('dialogTitle').textContent=title;$('dialogKicker').textContent=kicker;$('dialogContent').innerHTML=html;$('detailDialog').showModal();}
document.querySelectorAll('[data-camera]').forEach(b=>b.onclick=()=>{const[title,asset]=cams[b.dataset.camera];dialog(title,`<img src="assets/${asset}" alt="${title} AI 생성 가상 CCTV 참고 사진"><p>AI 생성 참고 이미지 · 실제 CCTV 영상이 아닙니다. 디자인 시안에서는 구역별 사진을 확인할 수 있습니다.</p>`,'VIRTUAL CCTV / SAMPLE IMAGE');});
document.querySelectorAll('.close-dialog').forEach(b=>b.onclick=()=>b.closest('dialog').close());
const tables={sensors:['센서 현황','<table class="detail-table"><thead><tr><th>센서</th><th>측정 위치</th><th>예시 값</th><th>상태</th></tr></thead><tbody><tr><td>PT-0901</td><td>고압 저장 뱅크</td><td>89.2 MPa</td><td>샘플</td></tr><tr><td>PT-1401</td><td>1번 차량 탱크</td><td>54.2 MPa</td><td>샘플</td></tr><tr><td>TT-1401</td><td>1번 차량 탱크</td><td>46.8 °C</td><td>샘플</td></tr><tr><td>PT-1801</td><td>2번 차량 탱크</td><td>48.7 MPa</td><td>샘플</td></tr></tbody></table><p>연결 센서 38개 중 화면 구성 예시입니다. 실제 신호와 연결하지 않았습니다.</p>'],history:['이벤트 이력','<table class="detail-table"><tbody><tr><td>10:24:08</td><td>2번 차량 충전 시작</td><td>운전</td></tr><tr><td>10:23:42</td><td>공급 뱅크 전환 · LOW → MID</td><td>설비</td></tr><tr><td>10:22:15</td><td>1번 차량 충전 시작</td><td>운전</td></tr></tbody></table><p>화면 구성을 설명하기 위한 예시 이력입니다.</p>'],hazop:['2번 충전 구역 · 사고 분석','<table class="detail-table"><tbody><tr><th>감지 신호</th><td>GD-2201 · 1.20 vol% H₂</td></tr><tr><th>시안 임계값</th><td>≥ 1.00 vol% H₂</td></tr><tr><th>시나리오 후보</th><td>충전호스 / 연결부 수소 누출</td></tr><tr><th>공정과 비교</th><td>압력·유량 추세 및 가상 CCTV 확인</td></tr><tr><th>피해 영향</th><td>HyRAM 계산 필요</td></tr></tbody></table><p>사고 분석 화면의 디자인 예시입니다. 수치와 임계값은 시안용이며 현장 안전 기준이 아닙니다.</p>']};
document.querySelectorAll('[data-dialog]').forEach(b=>b.onclick=()=>dialog(...tables[b.dataset.dialog]));
$('remoteOpen').onclick=()=>$('remoteDialog').showModal();
document.querySelectorAll('[data-remote-tab]').forEach(button=>button.onclick=()=>{document.querySelectorAll('[data-remote-tab]').forEach(b=>b.classList.toggle('selected',b===button));$('processDraft').hidden=button.dataset.remoteTab!=='process';$('faultDraft').hidden=button.dataset.remoteTab!=='faults';});
document.querySelectorAll('.scenario-demo button').forEach(button=>button.onclick=()=>{const chosen=button.parentElement.classList.toggle('chosen');button.textContent=chosen?'✓ 선택됨':'+ 선택';});
document.querySelector('.remote-search input').oninput=e=>document.querySelectorAll('.scenario-demo').forEach(card=>card.hidden=!card.textContent.includes(e.target.value));
$('previewRun').onclick=()=>{$('previewFeedback').textContent='실행 요청 완료 화면 예시입니다. 실제 공정은 실행하지 않았습니다.';};
const exit=document.createElement('button');exit.textContent='전체화면 닫기 ↙';exit.hidden=true;exit.style.cssText='position:absolute;right:16px;top:16px;z-index:20;background:#eaf3ef;color:#18392f;padding:9px 14px;border-radius:6px;font-size:11px';$('stage').append(exit);exit.onclick=()=>document.exitFullscreen();
$('fullscreen').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen();else $('stage').requestFullscreen().catch(()=>dialog('전체화면','<p>이 브라우저에서 전체화면을 열 수 없습니다.</p>'));};document.addEventListener('fullscreenchange',()=>exit.hidden=!document.fullscreenElement);
