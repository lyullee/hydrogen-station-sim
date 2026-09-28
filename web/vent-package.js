import * as THREE from '/vendor/three/three.module.js';
import { createPipeCurve } from '/station-piping.js';

// GH2 reference arrangement only. EIGA Doc 211/24 sections 5, 7 and 9.
// No relief/backpressure, dispersion, structural or grounding calculation.
export function buildVentPackage(equipment) {
  const group = new THREE.Group(); group.name = 'reference-gh2-vent-system';
  const vent = equipment.get('vent').group;
  const metal = new THREE.MeshStandardMaterial({ color: '#bbc8cb', metalness: .83, roughness: .28 });
  const support = new THREE.MeshStandardMaterial({ color: '#566a64', metalness: .58, roughness: .5 });
  const concrete = new THREE.MeshStandardMaterial({ color: '#d7d5c7', roughness: .94 });
  const copper = new THREE.MeshStandardMaterial({ color: '#a77c4c', metalness: .7, roughness: .46 });
  const dark = new THREE.MeshStandardMaterial({ color: '#37403d', metalness: .35, roughness: .56 });
  const geometry = new Map();
  function cached(key, make) { if (!geometry.has(key)) geometry.set(key, make()); return geometry.get(key); }
  function mesh(shape, material, x, y, z) {
    const object = new THREE.Mesh(shape, material); object.position.set(x, y, z);
    object.castShadow = object.receiveShadow = true; group.add(object); return object;
  }
  function box(w, h, d, x, y, z, material = support) {
    return mesh(cached(`b:${w}:${h}:${d}`, () => new THREE.BoxGeometry(w, h, d)), material, x, y, z);
  }
  function cylinder(radius, length, x, y, z, material = metal, axis = 'y') {
    const object = mesh(cached(`c:${radius}:${length}`, () => new THREE.CylinderGeometry(radius, radius, length, 24)), material, x, y, z);
    if (axis === 'x') object.rotation.z = Math.PI / 2;
    if (axis === 'z') object.rotation.x = Math.PI / 2;
    return object;
  }
  function pipe(points, radius = .055, material = metal) {
    return mesh(new THREE.TubeGeometry(createPipeCurve(points), 64, radius, 10, false), material, 0, 0, 0);
  }
  function strut(a, b, radius = .035) {
    const start = new THREE.Vector3(...a), end = new THREE.Vector3(...b);
    const object = cylinder(radius, start.distanceTo(end), 0, 0, 0, support);
    object.position.copy(start.clone().add(end).multiplyScalar(.5));
    object.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), end.sub(start).normalize());
  }
  function label(text, w, h, x, y, z) {
    const canvas = document.createElement('canvas'); canvas.width = 1024; canvas.height = 192;
    const context = canvas.getContext('2d'); context.fillStyle = '#edf0dd'; context.fillRect(0, 0, 1024, 192);
    context.fillStyle = '#354740'; context.font = 'bold 53px sans-serif'; context.textAlign = 'center'; context.textBaseline = 'middle';
    context.fillText(text, 512, 96, 984);
    const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace;
    return mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: texture, side: THREE.DoubleSide }), x, y, z);
  }
  function flange(y) {
    cylinder(.17, .055, 0, y, 0);
    for (let i = 0; i < 8; i++) {
      const angle = i * Math.PI / 4;
      cylinder(.014, .085, Math.cos(angle) * .142, y, Math.sin(angle) * .142, dark);
    }
  }

  box(1.55, .30, 1.55, 0, .15, 0, concrete);
  box(.68, .055, .68, 0, .327, 0, metal);
  cylinder(.15, .24, 0, .47, 0);
  for (const x of [-.25, .25]) for (const z of [-.25, .25]) cylinder(.03, .12, x, .365, z);
  // Open-ended wall and outlet rim, not a capped solid cylinder.
  mesh(new THREE.CylinderGeometry(.11, .11, 7.32, 32, 1, true), metal, 0, 4.31, 0);
  cylinder(.11, .035, 0, .63, 0);
  flange(.82); flange(4.30);
  const lip = mesh(new THREE.TorusGeometry(.105, .008, 8, 32), metal, 0, 7.97, 0);
  lip.rotation.x = Math.PI / 2;
  // Sparse anti-debris bars: appearance reference, not a certified protector.
  cylinder(.004, .20, 0, 7.965, 0, metal, 'x');
  cylinder(.004, .20, 0, 7.965, 0, metal, 'z');
  box(.12, 4.65, .12, .50, 2.635, -.20);
  box(.32, .05, .34, .50, .34, -.20, metal);
  for (const y of [1.10, 2.60, 4.75]) {
    strut([.50, y, -.20], [0, y, 0], .027);
    const clamp = mesh(new THREE.TorusGeometry(.123, .018, 6, 24), support, 0, y, 0);
    clamp.rotation.x = Math.PI / 2;
    box(.075, .075, .10, .12, y, 0, metal);
  }
  for (const x of [-.51, .51]) strut([x, .34, .38], [0, 2.22, 0]);
  // Low-point water drain is a visual fitting, not an isolation valve on the header.
  pipe([[0, .54, 0], [0, .54, .28], [0, .39, .28]], .014);
  box(.06, .06, .07, 0, .39, .28, metal);
  label('DRAIN / VISUAL', .60, .085, 0, .29, .786);
  pipe([[.12, 1.10, 0], [.30, 1.10, .13], [.30, .33, .13], [.65, .33, .13]], .008, copper);
  box(.12, .018, .13, .65, .32, .13, copper);
  label('GH2 VENT / REFERENCE ONLY', 1.4, .16, 0, 1.38, .30);
  label('NO FLOW / SAFETY CALCULATION', 1.4, .10, 0, 1.18, .30);

  function local(world) { return vent.worldToLocal(new THREE.Vector3(...world)).toArray(); }
  const rearZ = -9.85;
  const bankPorts = [];
  for (const name of ['low', 'medium', 'high']) {
    const bank = equipment.get(name).group;
    const anchor = bank.userData.processPorts?.relief ?? [.99, 2.42, 2.03];
    const point = bank.localToWorld(new THREE.Vector3(...anchor));
    bankPorts.push(point);
    pipe([
      local(point.toArray()), local([point.x + .22, point.y, point.z]),
      local([point.x + .22, point.y, rearZ]), local([point.x + .22, .72, rearZ]),
    ], .025);
    const foot = local([point.x + .22, .43, rearZ]);
    cylinder(.026, .55, ...foot, support);
    const plate = local([point.x + .22, .18, rearZ]); box(.23, .045, .23, ...plate, metal);
  }
  const firstX = bankPorts[0].x + .22;
  const stackWorld = vent.localToWorld(new THREE.Vector3(0, .72, 0));
  pipe([
    local([firstX, .72, rearZ]), local([stackWorld.x - .45, .72, rearZ]),
    [-.45, .72, 0], [0, .72, 0],
  ]);
  for (const x of [3, 7, 11]) {
    const foot = local([x, .43, rearZ]); cylinder(.026, .55, ...foot, support);
    const plate = local([x, .18, rearZ]); box(.23, .045, .23, ...plate, metal);
  }
  const marker = local([5, .99, rearZ + .085]);
  label('GH2 RELIEF HEADER / VISUAL ONLY', 2.6, .17, ...marker);
  group.userData.visualOnly = true;
  return { group };
}
