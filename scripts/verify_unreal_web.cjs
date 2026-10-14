// Browser integration test against the real local API and official player.
// Does not claim an Unreal video stream exists when no UE engine is running.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.HRS_PLAYWRIGHT_MODULE || 'playwright');
const base = process.argv[2] || 'http://127.0.0.1:18015';
const player = process.argv[3] || 'http://127.0.0.1:18080';
const out = process.argv[4] || 'output/unreal/web-smoke.json';

(async () => {
  const channel = process.env.HRS_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined);
  const browser = await chromium.launch({headless:true, channel, args:['--use-angle=swiftshader', '--enable-webgl']});
  const page = await browser.newPage({viewport:{width:1600,height:1000}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  let job;
  try {
    await page.goto(base, {waitUntil:'networkidle', timeout:30000});
    await page.locator('#s3UnrealToggle').waitFor();
    // Config is overridden only in the test page; no production setting is changed.
    await page.route('**/api/integrations/unreal/config', route => route.fulfill({json:{player_url:player, configured:true}}));
    await page.locator('#s3UnrealToggle').click();
    await page.waitForFunction(() => document.querySelector('#s3Stage').classList.contains('unreal-active'));
    assert.equal(await page.locator('.s3-unreal-layer iframe').getAttribute('src'), new URL(player).href);
    const created = await page.request.post(base + '/api/simulations', {data:{continuous:true, control_period_s:.2}});
    assert.equal(created.status(), 202);
    job = (await created.json()).id;
    await page.evaluate(id => {window.connectStationJob(id);}, job);
    await page.waitForFunction(async id => (await fetch('/api/integrations/unreal/session/default').then(r=>r.json())).run_id === id, job);
    await page.waitForFunction(async id => (await fetch(`/api/simulations/${id}/visualization/snapshot`).then(r=>r.json())).data_available, job);
    const snapshot = await page.request.get(`${base}/api/simulations/${job}/visualization/snapshot`);
    assert.equal(snapshot.status(), 200);
    const sample = await snapshot.json();
    assert.equal(sample.run_id, job);
    for (const id of ['cascade.low','cascade.medium','cascade.high']) {
      const bank = sample.equipment.find(row => row.component_id === id);
      assert.equal(typeof bank.pressure_mpa, 'number');
      assert.equal(typeof bank.mass_kg, 'number');
    }
    await page.locator('#s3UnrealToggle').click();
    await page.waitForFunction(() => !document.querySelector('#s3Stage').classList.contains('unreal-active'));
    assert.equal((await page.request.get(`${base}/api/simulations/${job}`)).status(), 200);
    await page.locator('#s3UnrealToggle').click();
    await page.waitForFunction(async id => (await fetch('/api/integrations/unreal/session/default').then(r=>r.json())).run_id === id, job);
    await page.request.post(`${base}/api/simulations/${job}/stop`);
    await page.evaluate(() => window.resetStationMonitor());
    await page.waitForLoadState('networkidle');
    await page.waitForFunction(async () => (await fetch('/api/integrations/unreal/session/default').then(r=>r.json())).run_id === null);
    const report = {status:'PASS', checks:['web_mode_switch','real_run_binding','snapshot_endpoint','fallback_mode','reset_clears_binding'],
      player:'official Epic player', player_config:'test_page_override_only',
      unreal_engine_video_verified:false, page_errors:errors};
    assert.deepEqual(errors, []);
    fs.mkdirSync(path.dirname(out), {recursive:true}); fs.writeFileSync(out, JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));
  } finally {
    if (job) await page.request.post(`${base}/api/simulations/${job}/stop`).catch(()=>{});
    await browser.close();
  }
})().catch(error => {console.error(error); process.exitCode=1;});
