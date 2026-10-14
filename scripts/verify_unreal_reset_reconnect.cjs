// Exercise repeated run binding, ESD state reset, and Pixel Streaming continuity.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.HRS_PLAYWRIGHT_MODULE || 'playwright');

const player = process.argv[2] || 'http://127.0.0.1:18080/hrs-player.html';
const api = process.argv[3] || 'http://127.0.0.1:8000';
const cycles = Number(process.argv[4] || 3);
const out = process.argv[5] || 'output/unreal/reset-reconnect.json';
if (!Number.isInteger(cycles) || cycles < 3 || cycles > 20) throw new Error('cycles must be 3..20');

(async () => {
  const channel = process.env.HRS_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined);
  const browser = await chromium.launch({headless:true, channel, args:['--autoplay-policy=no-user-gesture-required']});
  const page = await browser.newPage({viewport:{width:1920,height:1080}});
  const records = [];
  let serial = Date.now(), runId = null;
  try {
    await page.goto(player, {waitUntil:'domcontentloaded', timeout:30000});
    await page.waitForFunction(() => {
      const video=document.querySelector('video'); return video && video.readyState>=2 && video.videoWidth>0;
    }, {timeout:120000});
    for (let cycle=1; cycle<=cycles; cycle++) {
      const created = await page.request.post(api + '/api/simulations', {data:{continuous:true,control_period_s:.2}});
      assert.equal(created.status(), 202); runId=(await created.json()).id;
      serial += 1;
      const bind = await page.request.post(api + '/api/integrations/unreal/session/default', {
        data:{run_id:runId,request_serial:serial}
      });
      assert.equal(bind.status(),200);
      await page.waitForFunction(async ({api,runId}) => {
        const response=await fetch(`${api}/api/simulations/${runId}/visualization/snapshot`);
        return response.ok && (await response.json()).data_available;
      }, {api,runId}, {timeout:30000});
      const initial = await (await page.request.get(`${api}/api/simulations/${runId}/visualization/snapshot`)).json();
      assert.notEqual(initial.esd, true, `cycle ${cycle} inherited ESD`);
      const before = await page.locator('video').evaluate(video=>video.currentTime);
      await page.locator('video').click({position:{x:20,y:20}}).catch(()=>{});
      await page.keyboard.press('KeyE');
      await page.waitForFunction(async ({api,runId}) => {
        const response=await fetch(`${api}/api/simulations/${runId}/visualization/snapshot`);
        return response.ok && (await response.json()).esd===true;
      }, {api,runId}, {timeout:5000});
      await page.waitForTimeout(1200);
      const after = await page.locator('video').evaluate(video=>video.currentTime);
      assert.ok(after > before, `cycle ${cycle} video stopped`);
      await page.request.post(`${api}/api/simulations/${runId}/stop`);
      serial += 1;
      const clear = await page.request.post(api + '/api/integrations/unreal/session/default', {
        data:{run_id:null,request_serial:serial}
      });
      assert.equal(clear.status(),200);
      const session = await (await page.request.get(api + '/api/integrations/unreal/session/default')).json();
      assert.equal(session.run_id,null);
      records.push({cycle,run_id:runId,initial_esd:initial.esd,esd_received:true,video_advanced_s:after-before});
      runId=null;
    }
    const report={status:'PASS',cycles,actual_unreal_stream:true,records,
      claim_boundary:'Repeated renderer binding, virtual ESD and stream continuity; visual QA still requires captured frame review.'};
    fs.mkdirSync(path.dirname(out),{recursive:true}); fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));
  } finally {
    if (runId) await page.request.post(`${api}/api/simulations/${runId}/stop`).catch(()=>{});
    serial += 1;
    await page.request.post(api + '/api/integrations/unreal/session/default', {data:{run_id:null,request_serial:serial}}).catch(()=>{});
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
