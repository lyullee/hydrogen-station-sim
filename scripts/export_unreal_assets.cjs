const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.HRS_PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const channel = process.env.HRS_BROWSER_CHANNEL || (process.platform==='win32' ? 'msedge' : undefined);
  const browser = await chromium.launch({headless:true, channel});
  const page = await browser.newPage();
  const output = process.argv[3] || 'output/unreal/assets';
  try {
    await page.goto((process.argv[2] || 'http://127.0.0.1:18015') + '/unreal-assets.html');
    await page.waitForFunction(() => !!window.hrsExportAssetNames);
    const names = await page.evaluate(() => window.hrsExportAssetNames);
    const manifest = {source:'existing public-reference Three.js model builders', coordinates:'glTF right-handed Y-up metres; import converts axes and units once',
      physics_capacity_changed:false, unreal_import_verified:false, assets:[]};
    fs.mkdirSync(output,{recursive:true});
    for (const name of names) {
      const data = await page.evaluate(name => window.hrsExportAsset(name), name);
      const binary = Buffer.from(data.base64,'base64');
      if (binary.readUInt32LE(0)!==0x46546c67 || binary.readUInt32LE(4)!==2 || binary.readUInt32LE(8)!==binary.length)
        throw new Error('Invalid GLB container: '+name);
      const jsonLength = binary.readUInt32LE(12);
      const gltf = JSON.parse(binary.subarray(20,20+jsonLength).toString('utf8').trim());
      if (!gltf.meshes?.length) throw new Error('No mesh in '+name);
      fs.writeFileSync(path.join(output,name+'.glb'),binary);
      manifest.assets.push({name, bytes:binary.length, dimensions_m:data.dimensions_m,
        mesh_count:gltf.meshes.length, sha256:crypto.createHash('sha256').update(binary).digest('hex')});
      console.log(name+': '+binary.length+' bytes, '+gltf.meshes.length+' meshes');
    }
    fs.writeFileSync(path.join(output,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
  } finally {await browser.close();}
})().catch(error => {console.error(error);process.exitCode=1;});
