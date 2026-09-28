import * as THREE from '/vendor/three/three.module.js';
import { createPipeCurve } from '/station-piping.js';

// Stable local hydrogen ports shared with the station route builder.
export const COOLING_PROCESS_PORTS=Object.freeze({inlet:[-.44,.85,2.27],outlet:[.44,.85,2.27]});

// Reference-based visual decomposition, not a detailed refrigeration calculation.
export function buildCoolingPackage() {
  const group=new THREE.Group();group.name='Chiller, circulation and hydrogen heat exchanger';
  const covers=[];const geometries=new Map();
  const material=(color,metalness=0,roughness=.6)=>new THREE.MeshStandardMaterial({color,metalness,roughness});
  const M={white:material(0xe9ece4,.25,.4),green:material(0x276b60,.3,.38),steel:material(0xb5c0c2,.85,.28),frame:material(0x425456,.65,.5),black:material(0x283536,0,.9),copper:material(0x9c7654,.75,.35),supply:material(0x4c9cc4,.35,.38),return:material(0xa2beca,.35,.4)};
  function cached(key,make){if(!geometries.has(key))geometries.set(key,make());return geometries.get(key);}
  function mesh(geometry,mat,parent=group){const obj=new THREE.Mesh(geometry,mat);obj.castShadow=true;obj.receiveShadow=true;parent.add(obj);return obj;}
  function box(w,h,d,x,y,z,mat,parent=group){const obj=mesh(cached(`b:${w}:${h}:${d}`,()=>new THREE.BoxGeometry(w,h,d)),mat,parent);obj.position.set(x,y,z);return obj;}
  function cylinder(r,h,x,y,z,mat,axis='y',parent=group){const obj=mesh(cached(`c:${r}:${h}`,()=>new THREE.CylinderGeometry(r,r,h,24)),mat,parent);obj.position.set(x,y,z);if(axis==='z')obj.rotation.x=Math.PI/2;if(axis==='x')obj.rotation.z=Math.PI/2;return obj;}
  function pipe(points,r,mat){return mesh(new THREE.TubeGeometry(createPipeCurve(points,.09),points.length*16,r,8,false),mat);}
  function sign(text,sub,w,h,x,y,z,bg='#eaf0e7',fg='#23564c'){
    const canvas=document.createElement('canvas');canvas.width=768;canvas.height=256;const ctx=canvas.getContext('2d');ctx.fillStyle=bg;ctx.fillRect(0,0,768,256);ctx.fillStyle=fg;ctx.textAlign='center';ctx.font='bold 65px sans-serif';ctx.fillText(text,384,114);ctx.font='27px monospace';ctx.fillText(sub,384,180);
    const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;
    const obj=mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({map,side:THREE.DoubleSide}));obj.position.set(x,y,z);obj.castShadow=false;return obj;
  }
  function flange(x,y,z,r=.065){return cylinder(r,.035,x,y,z,M.steel,'z');}

  box(2.7,.22,4.5,0,.11,.15,M.white);
  // Water-cooled interpretation: roof fans are intentionally absent.
  const cx=-.52,cz=-.65;
  for(const x of [cx-.46,cx+.46])for(const z of [cz-.67,cz+.67]){
    box(.055,1.95,.055,x,1.27,z,M.frame);box(.15,.045,.15,x,.255,z,M.steel);
  }
  box(1.0,.045,1.45,cx,.30,cz,M.frame);box(1.01,.065,1.47,cx,2.27,cz,M.white);
  box(.035,1.88,1.38,cx-.50,1.29,cz,M.white);box(.035,1.88,1.38,cx+.50,1.29,cz,M.white);
  box(.96,1.88,.035,cx,1.29,cz-.71,M.white);
  const lowerDoor=box(.965,1.05,.035,cx,.87,cz+.735,M.white);
  const upperDoor=box(.965,.79,.035,cx,1.82,cz+.735,M.green);covers.push(lowerDoor,upperDoor);
  box(.34,.25,.018,cx,1.91,cz+.762,M.black);
  sign('CH-101','WATER-COOLED CHILLER',.80,.18,cx,1.59,cz+.768);
  sign('-40 C','MODEL SETPOINT',.30,.14,cx,1.91,cz+.779,'#172f32','#a8edd2');
  for(const x of [cx-.39,cx+.39]){box(.027,.18,.027,x,.95,cz+.766,M.frame);box(.025,.14,.02,x,1.64,cz+.766,M.steel);}
  for(let i=0;i<9;i++)box(.70,.017,.014,cx,.48+i*.031,cz+.761,M.frame);
  // Refrigeration and plate-condenser internals visible through service doors.
  cylinder(.17,.61,cx-.16,.66,cz-.14,M.black);
  cylinder(.095,.64,cx+.21,1.38,cz-.08,M.steel);
  for(let i=0;i<12;i++)box(.37,.48,.012,cx+.15,1.08,cz+.08+i*.014,M.steel);
  pipe([[cx-.16,.98,cz-.14],[cx-.16,1.45,cz-.14],[cx+.21,1.45,cz-.14]],.018,M.copper);
  pipe([[cx+.20,.84,cz+.24],[cx-.25,.84,cz+.24],[cx-.25,.60,cz+.24]],.016,M.copper);

  // Independent thermal-fluid reservoir and recirculation pump skid.
  const bx=.65,bz=-.65;
  box(.86,.085,1.35,bx,.32,bz,M.frame);
  for(const x of [bx-.36,bx+.36])for(const z of [bz-.53,bz+.53])box(.04,1.22,.04,x,.97,z,M.frame);
  const reservoir=mesh(new THREE.CapsuleGeometry(.255,.78,8,24),M.black);reservoir.position.set(bx,1.04,bz-.18);
  cylinder(.075,.16,bx,1.76,bz-.18,M.steel);cylinder(.115,.03,bx,1.84,bz-.18,M.frame);
  cylinder(.12,.39,bx,.54,bz+.30,M.green,'z');cylinder(.14,.065,bx,.54,bz+.53,M.steel,'z');
  for(let i=0;i<6;i++)cylinder(.128,.018,bx,.54,bz+.13+i*.05,M.frame,'z');
  pipe([[bx,.54,bz+.09],[bx,.54,bz-.15],[bx,.68,bz-.15]],.034,M.steel);
  box(.13,.38,.07,bx+.29,1.15,bz+.10,M.frame);
  box(.018,.27,.017,bx+.29,1.15,bz+.15,M.return);
  sign('HTF-101','RESERVOIR + PUMP',.85,.23,bx,1.48,.12);

  // High-pressure hydrogen HEX and removable insulating jacket.
  for(const x of [-.54,.54])for(const z of [1.42,1.96])box(.042,1.18,.042,x,.87,z,M.frame);
  box(1.24,.075,.80,0,.31,1.70,M.frame);
  box(.91,.78,.36,0,.94,1.70,M.steel);
  for(let i=0;i<11;i++)box(.94,.009,.37,0,.63+i*.057,1.70,M.frame);
  const jacket=box(1.06,.88,.075,0,.94,1.945,M.black);covers.push(jacket);
  for(const x of [-.44,.44]){
    cylinder(.029,.29,x,.85,2.125,M.steel,'z');flange(x,.85,2.18);
    cylinder(.078,.24,x,1.18,1.50,M.black,'z');
  }
  sign('HX-101','HIGH-PRESSURE H2 / VISUAL HEX',1.13,.25,0,1.57,1.99);
  sign('H2 IN','',.23,.09,-.44,.61,2.04);sign('H2 OUT','',.23,.09,.44,.61,2.04);
  pipe([[bx,.54,bz+.53],[bx,.54,.43],[-.44,.54,.43],[-.44,1.18,.43],[-.44,1.18,1.50]],.046,M.black);
  pipe([[.44,1.18,1.50],[.44,1.18,.66],[cx+.20,1.18,.66],[cx+.20,1.18,.12]],.046,M.black);
  for(const [x,z,mat] of [[-.44,.75,M.supply],[.44,1.09,M.return]]){
    cylinder(.049,.065,x,1.18,z,mat,'z');cylinder(.049,.065,x,1.18,z+.16,mat,'z');
  }
  sign('HTF SUPPLY','VISUAL LOOP',.50,.13,-.48,1.37,.78,'#3b789b','#f0f7f5');
  sign('HTF RETURN','VISUAL LOOP',.50,.13,.40,1.37,1.13,'#b6c8cd','#27434a');
  // Facility-water supply/return ends are shown as a boundary, not a new plant.
  for(const x of [cx-.17,cx+.17])pipe([[x,.66,cz-.71],[x,.66,-1.70],[x,.32,-1.70]],.024,M.steel);
  sign('FACILITY WATER','BOUNDARY / VISUAL ONLY',.90,.17,cx,.47,-1.74).rotation.y=Math.PI;
  const statusMaterial=new THREE.MeshStandardMaterial({color:0x6a9585,emissive:0x244a3c,emissiveIntensity:.3});
  const status=mesh(new THREE.SphereGeometry(.035,12,8),statusMaterial);status.position.set(cx+.32,2.03,cz+.78);
  return {group,covers,statusMaterial,ports:COOLING_PROCESS_PORTS};
}
