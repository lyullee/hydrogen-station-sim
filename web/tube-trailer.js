import * as THREE from '/vendor/three/three.module.js';

// Unbranded visual interpretation of public tube-trailer and cab-over references.
// One unit is approximately one metre; geometry is not manufacturer CAD.
export function buildHydrogenTransporter() {
  const root=new THREE.Group();root.name='Detailed hydrogen transporter';
  const geometries=new Map();
  const material=(color,metalness=0,roughness=.65)=>new THREE.MeshStandardMaterial({color,metalness,roughness});
  const M={paint:material(0xeeeae1,.3,.28),accent:material(0x1e665c,.35,.32),steel:material(0xaab4b6,.8,.32),frame:material(0x424e50,.65,.48),dark:material(0x222d30,.15,.7),rubber:material(0x161b1c,0,.94),glass:material(0x18313c,.48,.12),tube:material(0xe3e8df,.2,.44),red:material(0xb34436,.15,.4),amber:material(0xdc9c34,.1,.35)};
  const light=new THREE.MeshStandardMaterial({color:0xe5f0ec,emissive:0xbbd8ce,emissiveIntensity:.35,roughness:.25});
  const lens=new THREE.MeshStandardMaterial({color:0xa73b30,emissive:0x68231b,emissiveIntensity:.25,roughness:.2});
  function geometry(key,make){if(!geometries.has(key))geometries.set(key,make());return geometries.get(key);}
  function add(shape,mat,parent=root){const obj=new THREE.Mesh(shape,mat);obj.castShadow=true;obj.receiveShadow=true;parent.add(obj);return obj;}
  function box(w,h,d,x,y,z,mat,parent=root){const obj=add(geometry(`b:${w}:${h}:${d}`,()=>new THREE.BoxGeometry(w,h,d)),mat,parent);obj.position.set(x,y,z);return obj;}
  function cylinder(r,len,x,y,z,mat,axis='y',parent=root){const obj=add(geometry(`c:${r}:${len}`,()=>new THREE.CylinderGeometry(r,r,len,32)),mat,parent);obj.position.set(x,y,z);if(axis==='x')obj.rotation.z=Math.PI/2;if(axis==='z')obj.rotation.x=Math.PI/2;return obj;}
  function ring(r,t,x,y,z,mat,axis='z',parent=root,arc=Math.PI*2){const obj=add(geometry(`r:${r}:${t}:${arc}`,()=>new THREE.TorusGeometry(r,t,8,32,arc)),mat,parent);obj.position.set(x,y,z);if(axis==='x')obj.rotation.y=Math.PI/2;if(axis==='y')obj.rotation.x=Math.PI/2;return obj;}
  function beam(a,b,r=.023,mat=M.frame,parent=root){const start=new THREE.Vector3(...a),end=new THREE.Vector3(...b),direction=end.clone().sub(start);const obj=cylinder(r,direction.length(),0,0,0,mat,'y',parent);obj.position.copy(start.add(end).multiplyScalar(.5));obj.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),direction.normalize());return obj;}
  function quad(points,mat,parent=root){const shape=new THREE.BufferGeometry();shape.setAttribute('position',new THREE.Float32BufferAttribute(points.flat(),3));shape.setIndex([0,1,2,0,2,3]);shape.computeVertexNormals();return add(shape,mat,parent);}
  function placard(text,sub,w,h,x,y,z,angle=0,parent=root,bg='#ecf0e7',fg='#25544b'){
    const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=256;const ctx=canvas.getContext('2d');
    ctx.fillStyle=bg;ctx.fillRect(0,0,1024,256);ctx.fillStyle=fg;ctx.textAlign='center';ctx.font='bold 88px sans-serif';ctx.fillText(text,512,120);ctx.font='34px monospace';ctx.fillText(sub,512,192);
    const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;
    const obj=add(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({map,side:THREE.DoubleSide}),parent);obj.position.set(x,y,z);obj.rotation.y=angle;obj.castShadow=false;return obj;
  }
  function roundedBox(w,h,d,r,x,y,z,mat,parent=root){
    const b=r*.35,xx=w/2-b,yy=h/2-b,rr=r-b;
    const shape=new THREE.Shape();shape.moveTo(-xx+rr,-yy);shape.lineTo(xx-rr,-yy);shape.quadraticCurveTo(xx,-yy,xx,-yy+rr);shape.lineTo(xx,yy-rr);shape.quadraticCurveTo(xx,yy,xx-rr,yy);shape.lineTo(-xx+rr,yy);shape.quadraticCurveTo(-xx,yy,-xx,yy-rr);shape.lineTo(-xx,-yy+rr);shape.quadraticCurveTo(-xx,-yy,-xx+rr,-yy);
    const geo=geometry(`round:${w}:${h}:${d}:${r}`,()=>{const value=new THREE.ExtrudeGeometry(shape,{depth:d-2*b,bevelEnabled:true,bevelSize:b,bevelThickness:b,bevelSegments:3,curveSegments:5});value.translate(0,0,-d/2+b);return value;});
    const obj=add(geo,mat,parent);obj.position.set(x,y,z);return obj;
  }
  const hubBolts=[];
  function wheel(x,z,dual=false){
    const side=Math.sign(x),y=.51;
    cylinder(.49,.215,x,y,z,M.rubber,'x');
    for(const offset of [-.07,0,.07])ring(.475,.015,x+offset,y,z,M.dark,'x');
    const face=x+side*.119;
    cylinder(.32,.026,face,y,z,M.steel,'x');ring(.292,.013,face+side*.018,y,z,M.frame,'x');cylinder(.115,.08,face+side*.027,y,z,M.frame,'x');
    for(let i=0;i<8;i++)hubBolts.push([face+side*.047,y+Math.cos(i*Math.PI/4)*.17,z+Math.sin(i*Math.PI/4)*.17]);
    if(!dual)for(let i=0;i<8;i++){const hole=cylinder(.033,.005,face+side*.018,y+Math.cos(i*Math.PI/4)*.245,z+Math.sin(i*Math.PI/4)*.245,M.dark,'x');hole.castShadow=false;}
  }

  // Separate trailer ladder chassis and tractor rails, rather than a single slab.
  for(const x of [-.85,.85]){
    box(.12,.22,7.90,x,.94,-.5,M.frame);box(.12,.21,3.1,x,.80,3.45,M.frame);
  }
  for(let z=-4.2;z<3.5;z+=.9)box(2.42,.08,.10,0,1.06,z,M.steel);
  box(2.50,.075,7.90,0,1.13,-.5,M.steel);
  for(const z of [-3.32,-2.37,-1.42]){
    cylinder(.07,2.18,0,.51,z,M.frame,'x');
    for(const side of [-1,1]){wheel(side*.97,z,true);wheel(side*1.18,z,true);box(.12,.065,.75,side*.81,.69,z,M.dark);}
  }
  for(const side of [-1,1]){
    wheel(side*1.15,5.10);wheel(side*.97,2.68,true);wheel(side*1.18,2.68,true);
    roundedBox(.19,.09,2.83,.035,side*1.19,1.03,-2.37,M.frame);
    box(.055,.39,.42,side*1.20,.72,-3.95,M.rubber);
    box(.055,.35,.43,side*1.19,.69,2.02,M.rubber);
    ring(.54,.033,side*1.23,.51,5.10,M.paint,'x',root,Math.PI);
  }
  // Load-bearing bulkheads, side rails and diagonal frame braces.
  for(const z of [-4.08,-.5,3.08]){
    for(const x of [-1.19,1.19])box(.085,2.42,.095,x,2.38,z,M.frame);
    box(2.46,.09,.13,0,3.64,z,M.frame);box(2.46,.08,.14,0,1.25,z,M.frame);
  }
  for(const x of [-1.19,1.19]){
    box(.065,.07,7.25,x,3.64,-.5,M.steel);box(.065,.08,7.50,x,1.26,-.5,M.frame);
    beam([x,1.3,-4.05],[x,3.59,-.53],.022);beam([x,3.59,-.47],[x,1.3,3.05],.022);
  }
  const vesselGeometry=geometry('tube',()=>new THREE.CapsuleGeometry(.335,6.60,10,32));
  for(const x of [-.77,0,.77])for(const y of [1.65,2.42,3.19]){
    const vessel=add(vesselGeometry,M.tube);vessel.rotation.x=Math.PI/2;vessel.position.set(x,y,-.5);
    for(const z of [-3.48,2.48]){ring(.346,.022,x,y,z,M.steel);box(.48,.095,.23,x,y-.355,z,M.frame);}
    cylinder(.047,.16,x,y,-4.20,M.steel,'z');cylinder(.053,.10,x,y,3.20,M.steel,'z');
    cylinder(.065,.065,x,y,-4.31,M.frame,'z');
    ring(.086,.012,x,y,-4.40,M.red);box(.13,.016,.02,x,y,-4.405,M.red);
    beam([x,y,-4.36],[x,y,-4.54],.018,M.steel);beam([x,y,-4.54],[1.02,y,-4.54],.015,M.steel);
  }
  beam([1.02,1.30,-4.54],[1.02,3.35,-4.54],.027,M.steel);
  roundedBox(1.65,.50,.30,.035,0,1.42,-4.55,M.paint);
  placard('H2 SUPPLY','UNBRANDED VISUAL MODEL',1.3,.25,0,1.43,-4.711,Math.PI);
  box(2.44,.16,.10,0,.51,-4.49,M.steel);box(2.40,.07,.12,0,.96,-4.49,M.frame);
  for(const x of [-.99,.99]){
    roundedBox(.27,.12,.035,.015,x,.70,-4.60,lens);box(.22,.033,.025,x,.88,-4.60,M.amber);
  }
  for(const x of [-1.18,1.18]){
    cylinder(.046,.75,x,.57,1.60,M.frame);box(.24,.055,.30,x,.16,1.60,M.steel);
    box(.08,.04,.11,x,.95,1.60,M.frame);
  }
  // Side-impact rail, amber markers, reflective strips and clean logistics signage.
  for(const side of [-1,1]){
    const x=side*1.27;
    box(.05,.065,3.15,x,.66,.55,M.steel);box(.04,.04,3.15,x,.84,.55,M.steel);
    for(const z of [-.65,1.65])box(.04,.45,.05,x,.88,z,M.frame);
    box(.065,.025,7.50,side*1.24,1.13,-.5,M.paint);
    for(const z of [-3.8,-1.7,.6,2.8])box(.02,.055,.12,side*1.282,1.12,z,M.amber);
    placard('HYDROGEN','COMPRESSED GAS / GH2',3.30,.48,side*1.245,2.52,-.4,side*Math.PI/2);
  }

  // Sculpted cab-over shell: width and front rake change across horizontal sections.
  const sections=[{y:1.06,w:1.19,f:6.10,b:3.92,c:.18},{y:1.70,w:1.20,f:6.19,b:3.86,c:.23},{y:2.14,w:1.19,f:6.15,b:3.85,c:.23},{y:3.17,w:1.13,f:5.94,b:3.92,c:.23},{y:3.42,w:1.03,f:5.77,b:4.02,c:.24}];
  const vertices=[],indices=[];
  sections.forEach(s=>{
    for(const [x,z] of [[-s.w+s.c,s.f],[s.w-s.c,s.f],[s.w,s.f-s.c],[s.w,s.b+s.c],[s.w-s.c,s.b],[-s.w+s.c,s.b],[-s.w,s.b+s.c],[-s.w,s.f-s.c]])vertices.push(x,s.y,z);
  });
  for(let row=0;row<sections.length-1;row++)for(let i=0;i<8;i++){
    const a=row*8+i,b=row*8+(i+1)%8,c=a+8,d=b+8;indices.push(a,b,c,b,d,c);
  }
  const topIndex=vertices.length/3;vertices.push(0,3.42,4.90);
  for(let i=0;i<8;i++)indices.push(32+i,32+(i+1)%8,topIndex);
  const cabGeometry=new THREE.BufferGeometry();cabGeometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));cabGeometry.setIndex(indices);cabGeometry.computeVertexNormals();add(cabGeometry,M.paint);
  // Broad raked front glass and side glazing sit just outside the painted shell.
  quad([[-.94,2.20,6.165],[.94,2.20,6.165],[.88,3.11,5.972],[-.88,3.11,5.972]],M.glass);
  for(const side of [-1,1]){
    const glass=quad([[side*1.205,2.18,4.12],[side*1.205,2.18,5.67],[side*1.153,3.07,5.58],[side*1.153,3.07,4.16]],M.glass);
    glass.material.side=THREE.DoubleSide;
    beam([side*1.21,2.17,4.06],[side*1.17,3.15,4.11],.012,M.frame);
    beam([side*1.21,1.28,4.02],[side*1.21,2.17,4.06],.008,M.frame);
    beam([side*1.21,1.28,4.02],[side*1.21,1.28,5.46],.008,M.frame);
    box(.024,.045,.24,side*1.22,2.02,4.68,M.dark);
    for(const y of [1.04,.83]){
      roundedBox(.29,.055,.60,.018,side*1.26,y,4.37,M.steel);
      for(let z=4.15;z<4.65;z+=.08)box(.22,.006,.02,side*1.27,y+.032,z,M.dark);
    }
    beam([side*1.19,2.78,5.71],[side*1.49,2.77,5.73],.022,M.frame);
    roundedBox(.17,.46,.18,.055,side*1.49,2.56,5.75,M.dark);
    box(.021,.34,.14,side*1.588,2.56,5.75,M.glass);
    cylinder(.22,.90,side*.94,.83,3.57,M.steel,'z');
    for(const z of [3.22,3.87])ring(.23,.012,side*.94,.83,z,M.frame);
    roundedBox(.16,.75,.83,.06,side*1.20,1.70,3.95,M.paint);
    placard('H2','LOGISTICS',.48,.19,side*1.228,1.90,4.80,side*Math.PI/2);
  }
  // Front mask and lighting signatures, intentionally without a copied brand emblem.
  roundedBox(1.77,.40,.06,.09,0,1.79,6.208,M.dark);
  for(let y=1.65;y<1.97;y+=.07)box(1.50,.018,.027,0,y,6.25,M.frame);
  roundedBox(1.62,.24,.065,.07,0,1.24,6.14,M.dark);
  for(let y=1.16;y<1.33;y+=.055)box(1.40,.016,.02,0,y,6.19,M.steel);
  roundedBox(2.29,.16,.17,.06,0,1.04,6.13,M.paint);
  for(const side of [-1,1]){
    roundedBox(.26,.24,.075,.045,side*.99,1.31,6.145,M.dark);
    beam([side*.94,1.41,6.19],[side*1.075,1.33,6.19],.012,light);
    beam([side*1.075,1.33,6.19],[side*.965,1.22,6.19],.012,light);
    box(.14,.035,.03,side*.99,1.16,6.19,M.amber);
    beam([side*.16,2.19,6.18],[side*.67,2.24,6.17],.011,M.dark);
  }
  placard('H2 LOGISTICS','GH2 TRANSPORT',1.23,.19,0,2.035,6.18);
  placard('H2 210','',.42,.10,0,1.02,6.232,0,root,'#e9ede6','#354745');
  roundedBox(1.90,.10,.22,.035,0,3.23,5.96,M.accent);
  roundedBox(1.77,.08,1.35,.06,0,3.46,4.89,M.paint);
  quad([[-1.02,3.48,4.03],[1.02,3.48,4.03],[1.04,3.75,3.90],[-1.04,3.75,3.90]],M.paint);
  for(const x of [-.81,0,.81])box(.065,.03,.06,x,3.40,5.68,M.amber);
  // Visible articulation and coiled service lines between cab and trailer.
  cylinder(.39,.065,0,1.09,3.25,M.dark);
  for(const x of [-.16,.16]){
    const points=[];for(let i=0;i<=40;i++){const t=i/40;points.push(new THREE.Vector3(x+Math.cos(t*Math.PI*14)*.045,1.90+Math.sin(t*Math.PI*14)*.045,3.52+t*.28));}
    add(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points),80,.009,6,false),x<0?M.red:M.dark);
  }
  // Wheel fasteners are submitted together, with geometry shared by all hubs.
  const screws=new THREE.InstancedMesh(new THREE.CylinderGeometry(.020,.020,.019,6),M.steel,hubBolts.length);const transform=new THREE.Object3D();
  hubBolts.forEach((point,i)=>{transform.position.set(...point);transform.rotation.z=Math.PI/2;transform.updateMatrix();screws.setMatrixAt(i,transform.matrix);});screws.castShadow=true;screws.computeBoundingSphere();root.add(screws);
  return root;
}
