import * as THREE from '/vendor/three/three.module.js';
import { createPipeCurve } from '/station-piping.js';

// Reference appearance, not a pressure-vessel design or solver volume.
// FIBA Type II brochure: 2.9 m nominal length, 202 L water capacity.
// Outer diameter, rack, saddles and fittings below are illustrative.
export const STORAGE_PROCESS_PORTS = Object.freeze({
  fill: Object.freeze([.99, .40, 2.03]),
  draw: Object.freeze([.99, .65, 2.03]),
  relief: Object.freeze([.99, 2.42, 2.03]),
});

let windingTexture;
function compositeTexture() {
  if (windingTexture) return windingTexture;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 128;
  const context = canvas.getContext('2d');
  context.fillStyle = '#b4b8ad'; context.fillRect(0, 0, 128, 128);
  context.strokeStyle = '#888e83'; context.lineWidth = 2;
  for (let offset = -128; offset <= 256; offset += 16) {
    context.beginPath(); context.moveTo(offset, 0); context.lineTo(offset + 128, 128); context.stroke();
    context.beginPath(); context.moveTo(offset, 0); context.lineTo(offset - 128, 128); context.stroke();
  }
  windingTexture = new THREE.CanvasTexture(canvas);
  windingTexture.wrapS = windingTexture.wrapT = THREE.RepeatWrapping;
  windingTexture.repeat.set(3, 12);
  windingTexture.colorSpace = THREE.SRGBColorSpace;
  return windingTexture;
}

export function buildStorageBank({ name, index = 0 }) {
  const group = new THREE.Group(); group.name = `${name}-reference-storage-rack`;
  const palette = ['#437b67', '#b08446', '#aa6453'];
  const steel = new THREE.MeshStandardMaterial({ color: '#bcc6c7', metalness: .8, roughness: .31 });
  const frame = new THREE.MeshStandardMaterial({ color: '#485f5d', metalness: .55, roughness: .48 });
  const concrete = new THREE.MeshStandardMaterial({ color: '#d6d6c8', roughness: .96 });
  const rubber = new THREE.MeshStandardMaterial({ color: '#343c38', roughness: .92 });
  const wrap = new THREE.MeshStandardMaterial({ color: '#d9dcd0', map: compositeTexture(), roughness: .73, metalness: .1 });
  const accent = new THREE.MeshStandardMaterial({ color: palette[index] ?? palette[0], metalness: .3, roughness: .5 });
  const valve = new THREE.MeshStandardMaterial({ color: '#924b38', metalness: .35, roughness: .48 });
  const geometry = new Map();
  function cached(key, factory) { if (!geometry.has(key)) geometry.set(key, factory()); return geometry.get(key); }
  function mesh(shape, material, x, y, z) {
    const object = new THREE.Mesh(shape, material); object.position.set(x, y, z);
    object.castShadow = object.receiveShadow = true; group.add(object); return object;
  }
  function box(w, h, d, x, y, z, material = frame) {
    return mesh(cached(`b:${w}:${h}:${d}`, () => new THREE.BoxGeometry(w, h, d)), material, x, y, z);
  }
  function cylinder(radius, length, x, y, z, material = steel, axis = 'z') {
    const object = mesh(cached(`c:${radius}:${length}`, () => new THREE.CylinderGeometry(radius, radius, length, 24)), material, x, y, z);
    if (axis === 'z') object.rotation.x = Math.PI / 2;
    if (axis === 'x') object.rotation.z = Math.PI / 2;
    return object;
  }
  function tube(points, radius = .018, material = steel) {
    return mesh(new THREE.TubeGeometry(createPipeCurve(points), 36, radius, 8, false), material, 0, 0, 0);
  }
  function panel(text, w, h, x, y, z, background = '#edf0e6') {
    const canvas = document.createElement('canvas'); canvas.width = 768; canvas.height = 192;
    const context = canvas.getContext('2d'); context.fillStyle = background; context.fillRect(0, 0, 768, 192);
    context.fillStyle = '#263d3b'; context.font = 'bold 58px sans-serif'; context.textAlign = 'center'; context.textBaseline = 'middle';
    context.fillText(text, 384, 96, 728);
    const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace;
    return mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: texture, side: THREE.DoubleSide }), x, y, z);
  }
  function strut(a, b, radius = .022) {
    const start = new THREE.Vector3(...a), end = new THREE.Vector3(...b);
    const object = cylinder(radius, start.distanceTo(end), 0, 0, 0, frame, 'y');
    object.position.copy(start.clone().add(end).multiplyScalar(.5));
    object.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), end.sub(start).normalize());
  }

  box(2.65, .24, 4.6, 0, .12, 0, concrete);
  for (const x of [-.84, .84]) for (const z of [-1.55, 1.55]) {
    box(.13, 2.39, .13, x, 1.435, z);
    box(.28, .045, .28, x, .277, z, steel);
    for (const dx of [-.09, .09]) for (const dz of [-.09, .09]) cylinder(.025, .055, x + dx, .31, z + dz, steel, 'y');
  }
  for (const z of [-1.55, 1.55]) {
    box(1.82, .10, .11, 0, .36, z); box(1.82, .10, .11, 0, 2.61, z);
  }
  for (const x of [-.84, .84]) {
    box(.10, .10, 3.21, x, 2.61, 0);
    strut([x, .38, -1.55], [x, 2.56, 1.55]);
    strut([x, 2.56, -1.55], [x, .38, 1.55]);
  }
  // Six illustrative vessels; existing lumped bank capacity is unchanged.
  const rows = [.66, 1.36, 2.06];
  const shoulder = cached('shoulder', () => new THREE.SphereGeometry(.205, 24, 16));
  for (const y of rows) {
    for (const z of [-1.10, 1.10]) box(1.74, .08, .18, 0, y - .26, z);
    for (const x of [-.45, .45]) {
      cylinder(.205, 2.49, x, y, 0);
      mesh(shoulder, steel, x, y, -1.245); mesh(shoulder, steel, x, y, 1.245);
      cylinder(.214, 2.20, x, y, 0, wrap);
      for (const z of [-1.10, 1.10]) {
        box(.40, .09, .20, x, y - .22, z, rubber);
        box(.46, .045, .25, x, y - .285, z, steel);
        const band = mesh(cached('band', () => new THREE.TorusGeometry(.223, .015, 6, 32)), steel, x, y, z);
        band.rotation.z = Math.PI / 2;
        for (const dx of [-.205, .205]) cylinder(.019, .10, x + dx, y - .24, z, steel, 'y');
      }
      cylinder(.049, .15, x, y, 1.47);
      cylinder(.040, .11, x, y, -1.49);
      box(.105, .105, .15, x, y, 1.62, steel);
      cylinder(.018, .13, x, y + .08, 1.62, steel, 'y');
      const wheel = mesh(cached('wheel', () => new THREE.TorusGeometry(.066, .012, 6, 20)), valve, x, y + .15, 1.62);
      wheel.rotation.x = Math.PI / 2;
      box(.11, .015, .015, x, y + .15, 1.62, valve);
      tube([[x, y, 1.69], [x, y, 1.82], [.99, y, 1.82], [.99, y, 2.03]]);
      panel(`V-${index + 1}${rows.indexOf(y) + 1}${x < 0 ? 'A' : 'B'}`, .23, .07, x, y + .12, 1.452);
    }
  }
  cylinder(.027, 2.08, .99, 1.39, 2.03, steel, 'y');
  // These two boundary coordinates match the existing station pipe routes.
  for (const [key, y] of [['fill', .40], ['draw', .65]]) {
    box(.095, .08, .09, .99, y, 1.94, steel);
    cylinder(.033, .15, .99, y, 1.955);
    cylinder(.072, .04, .99, y, 2.015);
    panel(key.toUpperCase(), .27, .075, .73, y, 2.07);
  }
  box(.12, .14, .12, .99, 2.35, 2.03, steel);
  panel('RELIEF / VISUAL', .51, .085, .72, 2.58, 2.08);
  box(.11, .62, .10, 0, 2.82, 1.55);
  box(1.18, .28, .06, 0, 2.90, 1.79, accent);
  panel(`${name.toUpperCase()} / V-${101 + index}`, 1.07, .20, 0, 2.90, 1.824);
  panel('REFERENCE RACK / SOLVER VOLUME UNCHANGED', 1.65, .09, 0, .28, 2.305);
  const statusMaterial = new THREE.MeshStandardMaterial({ color: '#a7ba94', emissive: '#8fbb7b', emissiveIntensity: .3 });
  mesh(new THREE.SphereGeometry(.042, 12, 8), statusMaterial, .73, 2.50, 1.97);
  group.userData.visualOnly = true;
  group.userData.reference = 'FIBA Type II brochure; illustrative OD and rack';
  return { group, statusMaterial, ports: STORAGE_PROCESS_PORTS };
}
