import * as THREE from '/vendor/three/three.module.js';
import { createPipeCurve } from '/station-piping.js';

// Diaphragm-skid visual reference; not manufacturer CAD or diaphragm mechanics.
export function buildCompressorPackage() {
  const group=new THREE.Group();group.name='Hydrogen compressor skid and service enclosure';
  const covers=[],boltPositions=[],geometryCache=new Map();
  const material=(color,metalness=0,roughness=.6)=>new THREE.MeshStandardMaterial({color,metalness,roughness});
  const M={white:material(0xe9eee5,.25,.4),green:material(0x24665b,.3,.38),steel:material(0xbac5c6,.85,.27),frame:material(0x425557,.7,.45),dark:material(0x223337,0,.8),red:material(0xbf5746,.2,.5),cooling:material(0x80a5b3,.35,.5)};
  function cached(key,make){if(!geometryCache.has(key))geometryCache.set(key,make());return geometryCache.get(key);}
  function add(geometry,mat,parent=group){const obj=new THREE.Mesh(geometry,mat);obj.castShadow=true;obj.receiveShadow=true;parent.add(obj);return obj;}
  function box(w,h,d,x,y,z,mat,parent=group){const obj=add(cached(`b:${w}:${h}:${d}`,()=>new THREE.BoxGeometry(w,h,d)),mat,parent);obj.position.set(x,y,z);return obj;}
  function cylinder(r,len,x,y,z,mat,axis='y',parent=group){const obj=add(cached(`c:${r}:${len}`,()=>new THREE.CylinderGeometry(r,r,len,32)),mat,parent);obj.position.set(x,y,z);if(axis==='x')obj.rotation.z=Math.PI/2;if(axis==='z')obj.rotation.x=Math.PI/2;return obj;}
  function ring(r,t,x,y,z,mat,axis='z',parent=group){const obj=add(cached(`r:${r}:${t}`,()=>new THREE.TorusGeometry(r,t,8,32)),mat,parent);obj.position.set(x,y,z);if(axis==='x')obj.rotation.y=Math.PI/2;if(axis==='y')obj.rotation.x=Math.PI/2;return obj;}
  function pipe(points,r,mat=M.steel){return add(new THREE.TubeGeometry(createPipeCurve(points,.09),points.length*16,r,8,false),mat);}
  function sign(text,sub,w,h,x,y,z,parent=group,bg='#eaf1e7',fg='#28594d'){
    const canvas=document.createElement('canvas');canvas.width=768;canvas.height=256;const ctx=canvas.getContext('2d');ctx.fillStyle=bg;ctx.fillRect(0,0,768,256);ctx.fillStyle=fg;ctx.textAlign='center';ctx.font='bold 66px sans-serif';ctx.fillText(text,384,114);ctx.font='27px monospace';ctx.fillText(sub,384,182);
    const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;
    const obj=add(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({map,side:THREE.DoubleSide}),parent);obj.position.set(x,y,z);obj.castShadow=false;return obj;
  }
  function valve(x,y,z){cylinder(.045,.12,x,y,z,M.steel,'z');cylinder(.018,.11,x,y+.075,z,M.steel);ring(.072,.01,x,y+.13,z,M.red,'y');box(.13,.015,.014,x,y+.13,z,M.red);}
  function pressureDial(x,y,z){
    cylinder(.10,.07,x,y,z,M.steel,'z');
    const canvas=document.createElement('canvas');canvas.width=canvas.height=128;const ctx=canvas.getContext('2d');ctx.fillStyle='#f0f1e7';ctx.fillRect(0,0,128,128);ctx.strokeStyle='#405456';ctx.lineWidth=2;
    for(let i=0;i<19;i++){const angle=(135+i*15)*Math.PI/180;ctx.beginPath();ctx.moveTo(64+Math.cos(angle)*48,64+Math.sin(angle)*48);ctx.lineTo(64+Math.cos(angle)*(i%3?42:37),64+Math.sin(angle)*(i%3?42:37));ctx.stroke();}
    ctx.strokeStyle='#b45140';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(64,64);ctx.lineTo(84,34);ctx.stroke();ctx.fillStyle='#405456';ctx.font='11px monospace';ctx.textAlign='center';ctx.fillText('VISUAL',64,92);
    const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
    const face=add(new THREE.CircleGeometry(.089,24),new THREE.MeshBasicMaterial({map:texture}));face.position.set(x,y,z+.037);
  }

  // Plinth and supported skid with actual visible rails and anchor feet.
  box(3.4,.24,4.4,0,.12,0,M.white);
  for(const x of [-1.12,1.12])box(.10,.14,3.60,x,.40,0,M.frame);
  for(const z of [-1.56,-.52,.52,1.56])box(2.32,.10,.12,0,.40,z,M.frame);
  for(const x of [-1.12,1.12])for(const z of [-1.56,1.56]){
    box(.31,.035,.31,x,.27,z,M.steel);cylinder(.022,.085,x-.10,.32,z,M.steel);cylinder(.022,.085,x+.10,.32,z,M.steel);
  }
  // Electric motor, finned body, coupling guard and common drive/hydraulic case.
  cylinder(.27,.72,-.79,.93,.12,M.green,'x');cylinder(.30,.055,-1.18,.93,.12,M.frame,'x');
  for(let i=0;i<11;i++)cylinder(.286,.018,-1.12+i*.060,.93,.12,M.frame,'x');
  box(.34,.20,.34,-.80,1.26,.12,M.frame);box(.55,.08,.52,-.80,.63,.12,M.steel);
  cylinder(.065,.30,-.28,.93,.12,M.steel,'x');cylinder(.13,.25,-.28,.93,.12,M.dark,'x');
  box(.76,.59,2.20,.22,.80,.10,M.frame);box(.77,.045,2.21,.22,1.12,.10,M.steel);
  for(const z of [-.75,.12,1.00])box(.12,.27,.12,.22,.55,z,M.frame);
  // Decreasing stage-head size, with layered diaphragm heads and bolted circular faces.
  const stages=[{z:-.85,r:.34},{z:.12,r:.28},{z:1.03,r:.22}];
  stages.forEach((stage,i)=>{
    const y=1.23;
    cylinder(.12,.33,.69,y,stage.z,M.frame,'x');cylinder(stage.r,.15,.95,y,stage.z,M.steel,'x');
    cylinder(stage.r*1.08,.055,1.06,y,stage.z,M.frame,'x');cylinder(stage.r*.94,.036,1.11,y,stage.z,M.steel,'x');
    ring(stage.r*.72,.011,1.133,y,stage.z,M.frame,'x');
    for(let j=0;j<12;j++)boltPositions.push([1.138,y+Math.cos(j*Math.PI/6)*stage.r*.90,stage.z+Math.sin(j*Math.PI/6)*stage.r*.90]);
    cylinder(.038,.14,1.12,y+stage.r*.48,stage.z,M.steel);
    sign(`STAGE ${i+1}`,'ILLUSTRATIVE HEAD',.46,.14,.78,1.70,stage.z+.17);
    // Instrumented shell-and-tube cooling interpretation and cooling-service branches.
    cylinder(.095,.76,-.43,1.99,stage.z,M.steel,'x');
    for(const x of [-.77,-.09])cylinder(.114,.035,x,1.99,stage.z,M.frame,'x');
    box(.04,.54,.04,-.77,1.68,stage.z,M.frame);box(.04,.54,.04,-.09,1.68,stage.z,M.frame);
    pipe([[1.12,y+stage.r*.52,stage.z],[1.12,2.17,stage.z],[-.04,2.17,stage.z],[-.04,1.99,stage.z]],.022);
    pressureDial(.61,2.20,stage.z+.15);
    pipe([[-.62,1.99,stage.z],[-1.04,1.99,stage.z],[-1.04,.65,stage.z]],.018,M.cooling);
  });
  // Hydrogen cabinet ports match the existing station route anchors.
  for(const x of [-.75,.75]){
    cylinder(.031,.26,x,.75,1.95,M.steel,'z');cylinder(.072,.035,x,.75,2.05,M.steel,'z');
    ring(.044,.009,x,.75,2.072,M.dark);
  }
  pipe([[-.75,.75,1.82],[-.75,.75,1.55],[-.75,1.73,1.55],[.86,1.73,1.55],[.86,1.73,-.85],[1.12,1.45,-.85]],.024);
  pipe([[-.04,1.99,-.85],[-.04,2.38,-.85],[.92,2.38,-.85],[.92,2.38,.12],[1.12,1.39,.12]],.021);
  pipe([[-.04,1.99,.12],[-.04,2.48,.12],[.91,2.48,.12],[.91,2.48,1.03],[1.12,1.36,1.03]],.018);
  pipe([[-.04,1.99,1.03],[-.04,2.20,1.38],[.75,2.20,1.38],[.75,.75,1.38],[.75,.75,1.82]],.020);
  valve(-.75,.75,1.64);valve(.75,.75,1.64);
  // Local leak-detection and instrument manifold are marked as visual accessories.
  box(.43,.38,.22,-1.04,1.42,1.50,M.white);
  sign('INSTRUMENTS','VISUAL ONLY',.40,.13,-1.04,1.43,1.625);
  for(const z of [-.85,.12,1.03])pipe([[.98,1.15,z],[.98,.59,z],[-1.04,.59,z],[-1.04,.59,1.5],[-1.04,1.28,1.5]],.009);

  // Enclosure frame stays visible when all attached service skins are removed.
  for(const x of [-1.40,1.40])for(const z of [-1.88,1.88])box(.07,2.59,.07,x,1.61,z,M.frame);
  for(const y of [.32,2.92]){box(2.86,.07,.07,0,y,-1.88,M.frame);box(2.86,.07,.07,0,y,1.88,M.frame);for(const x of [-1.40,1.40])box(.07,.07,3.80,x,y,0,M.frame);}
  box(2.77,2.49,.035,0,1.61,-1.93,M.white);
  const roof=box(2.94,.095,3.94,0,2.98,0,M.white);covers.push(roof);
  for(const side of [-1,1]){
    const skin=box(.035,2.46,3.74,side*1.435,1.62,0,M.green);covers.push(skin);
    for(let z=-1.50;z<1.51;z+=.14)box(.014,.46,.055,side*.022,-.51,z,M.frame,skin);
  }
  for(const x of [-.70,.70]){
    const door=box(1.36,2.45,.045,x,1.62,1.945,M.green);covers.push(door);
    box(.055,.25,.035,x<0?.56:-.56,-.02,.043,M.steel,door);
    for(const y of [-.85,.85])box(.045,.17,.028,x<0?-.63:.63,y,.035,M.frame,door);
    sign(x<0?'CMP-101':'HYDROGEN','SERVICE PANEL',1.04,.27,0,.91,.035,door);
    for(let i=0;i<10;i++)box(.84,.022,.012,0,-.93+i*.048,.029,M.frame,door);
    if(x>0){box(.40,.42,.018,0,.37,.038,M.white,door);box(.25,.18,.019,0,.43,.052,M.dark,door);sign('CONTROL','MODEL LINK',.32,.09,0,.24,.066,door);}
  }
  sign('H2 IN','',.30,.10,-.75,.53,2.075);sign('H2 OUT','',.30,.10,.75,.53,2.075);
  sign('3-STAGE SKID','VISUAL REFERENCE / MODEL UNCHANGED',1.55,.20,0,.26,2.22);
  const statusMaterial=new THREE.MeshStandardMaterial({color:0x6a9585,emissive:0x244a3c,emissiveIntensity:.3});
  const status=add(new THREE.SphereGeometry(.047,12,8),statusMaterial);status.position.set(1.25,2.80,1.99);
  const screws=new THREE.InstancedMesh(new THREE.CylinderGeometry(.019,.019,.019,6),M.steel,boltPositions.length),transform=new THREE.Object3D();
  boltPositions.forEach((point,i)=>{transform.position.set(...point);transform.rotation.z=Math.PI/2;transform.updateMatrix();screws.setMatrixAt(i,transform.matrix);});screws.castShadow=true;screws.computeBoundingSphere();group.add(screws);
  return {group,covers,statusMaterial};
}
