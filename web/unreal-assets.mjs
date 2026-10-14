import * as THREE from '/vendor/three/three.module.js';
import { GLTFExporter } from '/vendor/three/exporters/GLTFExporter.js';
import { buildStorageBank } from '/storage-bank.js';
import { buildCompressorPackage } from '/compressor-package.js';
import { buildCoolingPackage } from '/cooling-package.js';
import { buildFcevVehicle } from '/fcev-vehicle.js';
import { buildHydrogenTransporter } from '/tube-trailer.js';

function flattenInstances(root) {
  const instances = []; root.traverse(object => {if (object.isInstancedMesh) instances.push(object);});
  for (const object of instances) {
    const replacement = new THREE.Group(); replacement.name = object.name;
    replacement.position.copy(object.position); replacement.quaternion.copy(object.quaternion); replacement.scale.copy(object.scale);
    for (let i=0;i<object.count;i++) {
      const mesh = new THREE.Mesh(object.geometry, object.material); const transform = new THREE.Matrix4();
      object.getMatrixAt(i, transform); transform.decompose(mesh.position, mesh.quaternion, mesh.scale); replacement.add(mesh);
    }
    object.parent.add(replacement); object.parent.remove(object);
  }
  root.updateMatrixWorld(true);
}

const factories = {
  'storage-low': () => buildStorageBank({name:'low',index:0}).group,
  'storage-medium': () => buildStorageBank({name:'medium',index:1}).group,
  'storage-high': () => buildStorageBank({name:'high',index:2}).group,
  'compressor': () => buildCompressorPackage().group,
  'precooler': () => buildCoolingPackage().group,
  'vehicle': () => buildFcevVehicle().group,
  'tube-trailer': () => buildHydrogenTransporter(),
};

window.hrsExportAsset = async name => {
  if (!Object.hasOwn(factories, name)) throw new Error('Unknown asset');
  const group = factories[name](); group.name = name;
  group.userData.asset_basis = 'illustrative_reference_not_solver_capacity';
  flattenInstances(group);
  const bounds = new THREE.Box3().setFromObject(group); const size = bounds.getSize(new THREE.Vector3());
  const exporter = new GLTFExporter();
  // r160 emits Infinity as JSON null. glTF represents infinite attenuation by
  // omitting this optional field, preserving the original glass appearance.
  exporter.register(() => ({name:'HRSInfiniteAttenuation', writeMaterial(material, definition) {
    const volume = definition.extensions?.KHR_materials_volume;
    if (volume && material.attenuationDistance === Infinity) delete volume.attenuationDistance;
  }}));
  const binary = await exporter.parseAsync(group, {binary:true, onlyVisible:true, maxTextureSize:1024});
  const dataUrl = await new Promise((resolve,reject) => {
    const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject;
    reader.readAsDataURL(new Blob([binary], {type:'model/gltf-binary'}));
  });
  return {name, dimensions_m:size.toArray(), base64:dataUrl.split(',')[1]};
};
window.hrsExportAssetNames = Object.keys(factories);
document.getElementById('status').textContent = '7개 설비 자산 변환 준비 완료';
