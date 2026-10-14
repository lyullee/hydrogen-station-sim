const fs = require('node:fs');
const path = require('node:path');
const validator = require(process.env.HRS_GLTF_VALIDATOR || '../unreal/.tooling/gltf-validation/node_modules/gltf-validator');
(async () => {
  const root = process.argv[2] || 'output/unreal/assets';
  const reports = [];
  for (const file of fs.readdirSync(root).filter(file=>file.endsWith('.glb'))) {
    const report = await validator.validateBytes(new Uint8Array(fs.readFileSync(path.join(root,file))), {uri:file});
    reports.push({file, errors:report.issues.numErrors, warnings:report.issues.numWarnings,
      messages:report.issues.messages.map(row=>({code:row.code,severity:row.severity,pointer:row.pointer}))});
  }
  const summary = {validator:'Khronos glTF Validator 2.0.0-dev.3.10',
    status:reports.length && reports.every(row=>row.errors===0)?'PASS':'FAIL',
    unreal_import_verified:false, assets:reports};
  fs.writeFileSync(path.join(root,'validation.json'),JSON.stringify(summary,null,2)+'\n');
  console.log(JSON.stringify({status:summary.status, assets:reports.map(({file,errors,warnings})=>({file,errors,warnings}))}));
  if (summary.status!=='PASS') process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
