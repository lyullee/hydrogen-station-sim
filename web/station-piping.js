import * as THREE from '/vendor/three/three.module.js';

// Explicit equipment anchors and conceptual routing, not pressure-piping design.
export function createStationPipeRoutes(equipment) {
  const port=(id,point)=>equipment.get(id).group.localToWorld(new THREE.Vector3(...point)).toArray();
  const inlet=port('compressor',[-.885,.90,2.132]);
  const outlet=port('compressor',[.885,.90,2.132]);
  const supply=port('supply',[1.02,1.30,-6.99]);
  const coolingPorts=equipment.get('cooler').group.userData.processPorts??{inlet:[-.50,.72,1.86],outlet:[.55,.72,1.86]};
  const coolIn=port('cooler',coolingPorts.inlet);
  const coolOut=port('cooler',coolingPorts.outlet);
  const dispenser=port('dispenser',[0,.32,-.45]);
  const standby=port('standby',[0,.32,-.37]);
  const routes=[{id:'compressor',color:0xe5ad45,points:[supply,[supply[0],.75,-10],[-8.9,.75,-10],[-8.9,.75,-3.15],[inlet[0],.75,-3.15],inlet]}];
  ['low','medium','high'].forEach((name,index)=>{
    const fill=port(name,[.99,.40,2.03]),draw=port(name,[.99,.65,2.03]);
    const fillZ=-3.15-index*.10,drawZ=-2.65-index*.10;
    routes.push({id:`recharge:${name}`,color:0xe5ad45,points:[outlet,[outlet[0],.75,fillZ],[fill[0],.75,fillZ],[fill[0],.40,fillZ],fill]});
    routes.push({id:`dispatch:${name}`,color:0x00bba3,points:[draw,[draw[0],.65,drawZ],[coolIn[0],.65,drawZ],[coolIn[0],.72,drawZ],coolIn]});
  });
  // Barrier ends at x=14.5; x=15.2 routes outside it, inside the side fence.
  routes.push({id:'fueling',color:0x00bba3,points:[coolOut,[coolOut[0],.72,-3.20],[15.2,.72,-3.20],[15.2,.72,1.15],[dispenser[0],.72,1.15],[dispenser[0],.72,dispenser[2]],[dispenser[0],dispenser[1],dispenser[2]]]});
  routes.push({id:'fueling2',color:0x00bba3,points:[coolOut,[coolOut[0],.72,-3.35],[14.9,.72,-3.35],[14.9,.72,2.30],[standby[0],.72,2.30],[standby[0],.72,standby[2]],standby]});
  return routes;
}

export function createPipeCurve(points,radius=.14) {
  const vertices=points.map(point=>new THREE.Vector3(...point)),path=new THREE.CurvePath();
  let previous=vertices[0].clone();
  for(let i=1;i<vertices.length-1;i++){
    const before=vertices[i-1],corner=vertices[i],after=vertices[i+1];
    const incoming=corner.clone().sub(before),outgoing=after.clone().sub(corner);
    const size=Math.min(radius,incoming.length()*.35,outgoing.length()*.35);
    if(size<.0001)continue;
    const entry=corner.clone().addScaledVector(incoming.normalize(),-size),exit=corner.clone().addScaledVector(outgoing.normalize(),size);
    if(previous.distanceTo(entry)>.0001)path.add(new THREE.LineCurve3(previous.clone(),entry));
    path.add(new THREE.QuadraticBezierCurve3(entry,corner.clone(),exit));previous=exit;
  }
  const last=vertices[vertices.length-1];
  if(previous.distanceTo(last)>.0001)path.add(new THREE.LineCurve3(previous,last));
  return path;
}

export function buildStationPiping(routes) {
  const group=new THREE.Group();group.name='Physical station piping';
  const metal=new THREE.MeshStandardMaterial({color:0xb8c3c4,metalness:.82,roughness:.32});
  const frame=new THREE.MeshStandardMaterial({color:0x455658,metalness:.65,roughness:.5});
  const capMaterial=new THREE.MeshStandardMaterial({color:0x638d7d,metalness:.3,roughness:.6});
  const flangeGeometry=new THREE.CylinderGeometry(.076,.076,.035,24);
  const portGeometry=new THREE.CylinderGeometry(.032,.032,.15,16);
  const legGeometry=new THREE.BoxGeometry(.033,.64,.033),footGeometry=new THREE.BoxGeometry(.18,.04,.18);
  const fittingPorts=new Set();
  const add=(geometry,material,position)=>{const obj=new THREE.Mesh(geometry,material);obj.position.set(...position);obj.castShadow=true;obj.receiveShadow=true;group.add(obj);return obj;};
  for(const route of routes){
    const curve=createPipeCurve(route.points);
    add(new THREE.TubeGeometry(curve,Math.max(32,route.points.length*16),route.visualOnly?.024:.029,10,false),metal,[0,0,0]);
    for(const end of [0,route.points.length-1]){
      const point=route.points[end],key=point.map(value=>value.toFixed(3)).join(':');if(fittingPorts.has(key))continue;fittingPorts.add(key);
      const adjacent=route.points[end===0?1:end-1],direction=new THREE.Vector3(...adjacent).sub(new THREE.Vector3(...point)).normalize();
      const rotation=new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,1,0),direction);
      add(flangeGeometry,route.visualOnly?capMaterial:metal,point).quaternion.copy(rotation);
      add(portGeometry,metal,point).quaternion.copy(rotation);
    }
  }
  const supports=[[-8.9,.72,-8],[-8.9,.72,-5],[-5,.72,-3.15],[0,.72,-3.15],[5,.72,-3.15],[10,.72,-3.15],[15.2,.72,-2.5],[15.2,.72,0],[12,.72,1.15],[9,.72,1.15],[6,.72,1.15],[3,.72,1.15],[0,.72,2.5],[8,.72,2.5]];
  for(const [x,y,z] of supports){add(legGeometry,frame,[x,y/2,z]);add(footGeometry,metal,[x,.06,z]);add(new THREE.BoxGeometry(.14,.027,.14),frame,[x,y-.025,z]);}
  group.userData.visualOnly=true;return group;
}
