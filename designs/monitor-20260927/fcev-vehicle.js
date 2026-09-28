import * as THREE from '/vendor/three/three.module.js';
import { createPipeCurve } from '/station-piping.js';

// Second-generation Mirai packaging reference. This is an unbranded visual model,
// not manufacturer CAD, a crash model, or an additional vehicle dynamics model.
export function buildFcevVehicle() {
  const group = new THREE.Group(); group.name = 'reference-five-seat-fcev';
  const exterior = new THREE.Group(); exterior.name = 'vehicle-exterior'; group.add(exterior);
  const interior = new THREE.Group(); interior.name = 'vehicle-cutaway-systems'; group.add(interior);
  const paint = new THREE.MeshPhysicalMaterial({ color: '#e8eee9', metalness: .58, roughness: .23, clearcoat: .9, clearcoatRoughness: .18 });
  const paintDark = new THREE.MeshStandardMaterial({ color: '#cad6d1', metalness: .62, roughness: .30 });
  const black = new THREE.MeshStandardMaterial({ color: '#151d1e', metalness: .18, roughness: .72 });
  const trim = new THREE.MeshStandardMaterial({ color: '#435352', metalness: .75, roughness: .30 });
  const glass = new THREE.MeshPhysicalMaterial({ color: '#7b9fa2', roughness: .12, metalness: .05, transmission: .22, transparent: true, opacity: .62, side: THREE.DoubleSide });
  const lamp = new THREE.MeshStandardMaterial({ color: '#e9f7ed', emissive: '#d9fff0', emissiveIntensity: .8, roughness: .18 });
  const tail = new THREE.MeshStandardMaterial({ color: '#b83f35', emissive: '#6c100c', emissiveIntensity: .75, roughness: .22 });
  const steel = new THREE.MeshStandardMaterial({ color: '#aebbbc', metalness: .82, roughness: .30 });
  const frame = new THREE.MeshStandardMaterial({ color: '#354646', metalness: .62, roughness: .47 });
  const carbon = new THREE.MeshStandardMaterial({ color: '#313a38', metalness: .15, roughness: .64, transparent: true, opacity: .80 });
  const liner = new THREE.MeshStandardMaterial({ color: '#e6d7bc', roughness: .72 });
  const hydrogen = new THREE.MeshStandardMaterial({ color: '#efb149', emissive: '#6b4311', emissiveIntensity: .18, roughness: .34 });
  const orange = new THREE.MeshStandardMaterial({ color: '#e06d2d', roughness: .48 });
  const coolant = new THREE.MeshStandardMaterial({ color: '#58a7b8', roughness: .48 });
  const seatMat = new THREE.MeshStandardMaterial({ color: '#685d50', roughness: .86 });
  const geometry = new Map();
  const shellMaterials = [paint, paintDark];
  function cached(key, make) { if (!geometry.has(key)) geometry.set(key, make()); return geometry.get(key); }
  function add(shape, material, parent = exterior) {
    const object = new THREE.Mesh(shape, material); object.castShadow = object.receiveShadow = true; parent.add(object); return object;
  }
  function box(w, h, d, x, y, z, material, parent = exterior) {
    const object = add(cached(`b:${w}:${h}:${d}`, () => new THREE.BoxGeometry(w, h, d)), material, parent);
    object.position.set(x, y, z); return object;
  }
  function cylinder(radius, length, x, y, z, material, axis = 'y', parent = exterior, segments = 24) {
    const object = add(cached(`c:${radius}:${length}:${segments}`, () => new THREE.CylinderGeometry(radius, radius, length, segments)), material, parent);
    object.position.set(x, y, z); if (axis === 'x') object.rotation.z = Math.PI / 2; if (axis === 'z') object.rotation.x = Math.PI / 2; return object;
  }
  function tube(points, radius, material, parent = interior) {
    return add(new THREE.TubeGeometry(createPipeCurve(points), 42, radius, 8, false), material, parent);
  }
  function panel(text, color, w, h, x, y, z, parent = interior, rotateY = 0) {
    const canvas = document.createElement('canvas'); canvas.width = 768; canvas.height = 192;
    const context = canvas.getContext('2d'); context.fillStyle = '#edf0e7'; context.fillRect(0, 0, 768, 192);
    context.strokeStyle = color; context.lineWidth = 18; context.strokeRect(5, 5, 758, 182);
    context.fillStyle = '#283a38'; context.font = 'bold 48px sans-serif'; context.textAlign = 'center'; context.textBaseline = 'middle'; context.fillText(text, 384, 96, 720);
    const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace;
    const object = add(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: texture, side: THREE.DoubleSide }), parent);
    object.position.set(x, y, z); object.rotation.y = rotateY; object.castShadow = false; return object;
  }
  function strut(a, b, radius, material = frame, parent = interior) {
    const start = new THREE.Vector3(...a), end = new THREE.Vector3(...b);
    const object = cylinder(radius, start.distanceTo(end), 0, 0, 0, material, 'y', parent);
    object.position.copy(start.clone().add(end).multiplyScalar(.5));
    object.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), end.sub(start).normalize()); return object;
  }

  // Smooth wide-and-low sedan envelope: 4.975 x 1.885 x 1.470 m reference.
  const sections = [
    [-2.487, .73, .31, .66, .28, .91], [-2.24, .89, .27, .78, .42, 1.02],
    [-1.68, .94, .25, .88, .60, 1.25], [-1.10, .942, .24, .93, .68, 1.42],
    [-.35, .94, .23, .96, .72, 1.47], [.50, .94, .23, .95, .70, 1.45],
    [1.15, .93, .24, .89, .60, 1.30], [1.72, .92, .25, .76, .43, .91],
    [2.25, .89, .28, .66, .24, .76], [2.487, .72, .34, .62, .10, .66],
  ];
  const rings = [], pointsPerRing = 9;
  for (const [x, width, low, shoulder, roofWidth, roof] of sections) {
    rings.push([
      [x, low, -.48 * width], [x, low + .12, -width], [x, shoulder, -width], [x, roof, -roofWidth],
      [x, roof + .025, 0], [x, roof, roofWidth], [x, shoulder, width], [x, low + .12, width], [x, low, .48 * width],
    ]);
  }
  const vertices = [], indices = [];
  rings.flat().forEach(p => vertices.push(...p));
  for (let r = 0; r < rings.length - 1; r++) for (let p = 0; p < pointsPerRing - 1; p++) {
    const a = r * pointsPerRing + p, b = a + pointsPerRing, c = b + 1, d = a + 1;
    indices.push(a, b, d, b, c, d);
  }
  const bodyGeometry = new THREE.BufferGeometry(); bodyGeometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3)); bodyGeometry.setIndex(indices); bodyGeometry.computeVertexNormals();
  add(bodyGeometry, paint);
  box(4.55, .12, 1.64, 0, .29, 0, black);
  box(1.05, .24, 1.69, 1.88, .39, 0, paintDark);
  box(.72, .25, 1.68, -2.10, .42, 0, paintDark);

  // Windows are separate swept surfaces over the body shell.
  function sideWindow(path, z) {
    const shape = new THREE.Shape(); shape.moveTo(path[0][0], path[0][1]); for (let i = 1; i < path.length; i++) shape.lineTo(path[i][0], path[i][1]); shape.closePath();
    const object = add(new THREE.ShapeGeometry(shape), glass); object.position.z = z; return object;
  }
  for (const side of [-1, 1]) {
    const z = side * .946;
    sideWindow([[-1.24,.96],[-.55,1.37],[-.10,1.40],[-.10,.91]], z);
    sideWindow([[.02,.91],[.02,1.40],[.50,1.38],[1.08,.96]], z);
    box(.78, .018, .035, -.62, .89, z, trim); box(.82, .018, .035, .52, .89, z, trim);
    box(.018, .50, .035, -.05, 1.14, z, trim);
    box(.24, .045, .038, -.68, .78, z, trim); box(.24, .045, .038, .57, .78, z, trim);
    box(.22, .10, .17, 1.13, 1.02, side * 1.02, paintDark);
    box(.13, .065, .19, 1.12, 1.04, side * 1.12, glass);
    // Fuel receptacle remains aligned with the existing dispenser hose endpoint.
    if (side < 0) {
      cylinder(.10, .050, -1.95, .84, -.935, trim, 'z');
      cylinder(.052, .060, -1.95, .84, -.965, black, 'z');
      const door = box(.24, .018, .20, -1.84, .95, -1.015, paintDark); door.rotation.x = -.72;
    }
  }
  // Windscreen and panoramic roof.
  const windVertices = new Float32Array([1.10,.94,-.70, 1.10,.94,.70, .53,1.43,-.66, .53,1.43,.66]);
  const windGeometry = new THREE.BufferGeometry(); windGeometry.setAttribute('position', new THREE.BufferAttribute(windVertices,3)); windGeometry.setIndex([0,1,2,1,3,2]); windGeometry.computeVertexNormals(); add(windGeometry, glass);
  const rearVertices = new Float32Array([-1.18,.96,-.68, -.55,1.42,-.67, -1.18,.96,.68, -.55,1.42,.67]);
  const rearGeometry = new THREE.BufferGeometry(); rearGeometry.setAttribute('position', new THREE.BufferAttribute(rearVertices,3)); rearGeometry.setIndex([0,1,2,1,3,2]); rearGeometry.computeVertexNormals(); add(rearGeometry, glass);
  box(.88, .025, 1.16, -.05, 1.475, 0, glass);
  const hoodPivot = new THREE.Group(); hoodPivot.position.set(1.10, .91, 0); exterior.add(hoodPivot);
  const hood = box(1.38, .045, 1.56, .68, .04, 0, paint, hoodPivot); hood.rotation.z = -.035;
  for (const z of [-.73, .73]) box(1.28, .018, .025, .68, .055, z, trim, hoodPivot);
  // Lamps, grilles and aerodynamic trim.
  for (const z of [-.61,.61]) { box(.035,.08,.48,2.475,.68,z,lamp); box(.035,.045,.54,2.455,.58,z,lamp); }
  box(.035,.24,1.18,2.47,.43,0,black); for (let z=-.48; z<=.48; z+=.12) box(.045,.018,.055,2.493,.43,z,trim);
  box(.035,.055,1.46,-2.48,.75,0,tail); box(.05,.13,.26,-2.47,.48,0,black);
  box(1.35,.035,.06,-1.70,.96,0,trim);

  // 20-inch-style wheels, brake discs and calipers.
  for (const x of [-1.52,1.49]) for (const z of [-.84,.84]) {
    const tyre = add(cached('tyre', () => new THREE.TorusGeometry(.355,.105,14,36)), black); tyre.position.set(x,.43,z);
    const rim = cylinder(.235,.052,x,.43,z,steel,'z');
    cylinder(.145,.058,x,.43,z,trim,'z'); cylinder(.085,.065,x,.43,z,black,'z');
    for (let i=0;i<10;i++) { const a=i*Math.PI/5; const spoke=box(.19,.025,.026,x+Math.cos(a)*.105,.43+Math.sin(a)*.105,z+(z<0?-.035:.035),steel); spoke.rotation.z=a; }
    box(.08,.15,.075,x+(x>0?.10:-.10),.47,z+(z<0?-.055:.055),tail);
  }
  for (const x of [-1.52,1.49]) strut([x,.43,-.72],[x,.43,.72],.035,frame,exterior);

  // Structural rails and protected underfloor equipment envelope.
  box(3.75,.075,.09,0,.31,-.72,frame,interior); box(3.75,.075,.09,0,.31,.72,frame,interior);
  for (const x of [-1.85,-.95,0,.95,1.80]) box(.07,.07,1.47,x,.31,0,frame,interior);
  for (const x of [-2.15,2.15]) strut([x,.37,-.70],[x+(x<0?.38:-.38),.63,-.70],.035,frame,interior);

  function tank({ x, y, z, length, radius, axis, id }) {
    const tankGroup = new THREE.Group(); tankGroup.name = id; tankGroup.position.set(x,y,z); interior.add(tankGroup);
    cylinder(radius*.78,length*.91,0,0,0,liner,axis,tankGroup);
    cylinder(radius,length,0,0,0,carbon,axis,tankGroup);
    const end = length/2;
    for (const direction of [-1,1]) {
      const px = axis==='x' ? direction*end : 0, pz = axis==='z' ? direction*end : 0;
      const boss = cylinder(radius*.20,.13,px,0,pz,steel,axis,tankGroup);
      const disk = cylinder(radius*.80,.012,axis==='x'?direction*(end+.071):0,0,axis==='z'?direction*(end+.071):0,hydrogen,axis,tankGroup);
      disk.userData.layerSection = true;
    }
    for (const offset of [-.32,.32]) {
      const ring = add(new THREE.TorusGeometry(radius*1.03,.022,8,32),frame,tankGroup);
      if(axis==='x'){ring.position.x=offset*length;ring.rotation.y=Math.PI/2;} else {ring.position.z=offset*length;}
    }
    return tankGroup;
  }
  tank({x:.15,y:.49,z:0,length:2.55,radius:.205,axis:'x',id:'H2-TANK-1-LONGITUDINAL'});
  tank({x:-1.16,y:.57,z:0,length:1.48,radius:.235,axis:'z',id:'H2-TANK-2-TRANSVERSE'});
  tank({x:-1.78,y:.75,z:0,length:1.30,radius:.205,axis:'z',id:'H2-TANK-3-TRANSVERSE'});
  // Tank shutoff/pressure-reduction appearance and stainless hydrogen feed.
  box(.24,.16,.26,-1.90,.75,-.62,steel,interior); cylinder(.045,.11,-1.90,.90,-.62,hydrogen,'y',interior);
  tube([[-1.78,.75,-.66],[-1.90,.75,-.66],[-1.90,.66,-.43],[-1.16,.66,-.43],[-.35,.63,-.43],[1.20,.63,-.43]],.022,steel);
  tube([[1.20,.63,-.43],[1.31,.72,-.43],[1.31,.72,-.25]],.018,hydrogen);

  // Front integrated FC unit: stack plates, boost converter/PCU and air system.
  box(.98,.43,1.18,1.52,.70,0,frame,interior); box(.88,.05,1.08,1.52,.94,0,steel,interior);
  const plateGeometry = new THREE.BoxGeometry(.012,.31,.76), plateMaterial = new THREE.MeshStandardMaterial({color:'#628785',metalness:.62,roughness:.36});
  const plates = new THREE.InstancedMesh(plateGeometry,plateMaterial,46), transform = new THREE.Object3D();
  for(let i=0;i<46;i++){transform.position.set(1.18+i*.015,.70,0);transform.updateMatrix();plates.setMatrixAt(i,transform.matrix);} plates.castShadow=true; interior.add(plates);
  box(.11,.37,.83,1.13,.70,0,steel,interior); box(.11,.37,.83,1.91,.70,0,steel,interior);
  box(.58,.22,.46,1.48,1.08,.25,orange,interior); box(.38,.18,.34,1.70,1.05,-.33,trim,interior);
  cylinder(.12,.38,2.02,.68,-.36,trim,'z',interior); cylinder(.08,.28,2.02,.68,-.36,steel,'z',interior);
  tube([[2.19,.68,-.36],[2.27,.68,-.36],[2.27,.78,0],[2.01,.78,0]],.035,coolant);
  panel('FUEL CELL POWER UNIT', '#57918b', 1.08,.17,1.55,1.34,-.60,interior);
  panel('NO COMBUSTION ENGINE', '#57918b', .98,.13,1.55,1.17,-.60,interior);

  // Rear traction system and compact lithium-ion battery.
  cylinder(.25,.56,-1.96,.47,0,trim,'z',interior); cylinder(.13,.70,-1.96,.47,0,steel,'z',interior);
  for (const z of [-.74,.74]) strut([-1.96,.47,z],[-1.96,.43,z*.97],.045,frame,interior);
  box(.64,.19,1.08,-1.42,1.02,0,orange,interior);
  for(let z=-.43;z<=.43;z+=.145) box(.50,.12,.09,-1.42,1.02,z,hydrogen,interior);
  box(.23,.22,.30,-1.73,.98,.48,frame,interior);
  tube([[-1.42,1.12,.46],[-1.42,1.24,.61],[-.15,1.24,.61],[1.30,1.17,.61]],.031,orange);
  tube([[-1.73,.96,.48],[-1.96,.82,.48],[-1.96,.63,.30]],.031,orange);
  panel('LI-ION BATTERY', '#dc762f', .70,.13,-1.43,1.32,-.55,interior);
  panel('REAR MOTOR', '#506b68', .58,.13,-1.96,.84,-.52,interior);

  // Cooling loop, hydrogen detector references and passenger-space cues.
  tube([[1.82,.48,.52],[1.82,.38,.66],[.20,.38,.66],[-1.74,.42,.57]],.024,coolant);
  tube([[-1.74,.46,.53],[-.80,.52,.53],[1.42,.52,.53],[1.42,.63,.45]],.018,coolant);
  for (const x of [-1.62,1.56]) { cylinder(.038,.055,x,1.20,0,hydrogen,'y',interior); panel('H2 SENSOR','#d8a03a',.34,.08,x,1.31,-.36,interior); }
  // Five-seat cabin cues are visual context and not occupant/crash geometry.
  for (const z of [-.48,.48]) {
    box(.46,.13,.43,.48,.67,z,seatMat,interior); const frontBack=box(.18,.56,.44,.20,.98,z,seatMat,interior); frontBack.rotation.z=-.12;
    box(.44,.13,.43,-.69,.78,z,seatMat,interior); const rearBack=box(.17,.48,.44,-.94,1.02,z,seatMat,interior); rearBack.rotation.z=-.18;
  }
  box(.58,.13,.32,-.69,.78,0,seatMat,interior); box(.18,.48,.30,-.94,1.02,0,seatMat,interior);
  box(.12,.28,.50,.96,1.03,0,black,interior); cylinder(.16,.035,.89,1.12,-.43,trim,'z',interior);
  panel('TYPE IV: LINER / CFRP / BOSS', '#d39b37', 1.32,.13,-.12,.90,-.72,interior);
  panel('VISUAL PACKAGING REFERENCE', '#607e79', 1.34,.12,.18,.39,-.76,interior);

  function setCutaway(enabled) {
    interior.visible = enabled;
    hoodPivot.rotation.z = enabled ? .78 : 0;
    shellMaterials.forEach(material => { material.transparent = enabled; material.opacity = enabled ? .14 : 1; material.depthWrite = !enabled; });
    glass.opacity = enabled ? .10 : .62; glass.depthWrite = !enabled;
    exterior.traverse(object => { if (object.isMesh && object.material === black) object.visible = !enabled; });
  }
  setCutaway(false);
  return { group, setCutaway };
}
