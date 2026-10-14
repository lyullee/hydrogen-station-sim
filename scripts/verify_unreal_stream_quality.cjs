// Dedicated-run end-to-end gate for UE Pixel Streaming quality and input path.
// It creates and stops its own simulator run; never point it at an operational run.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.HRS_PLAYWRIGHT_MODULE || 'playwright');

const player = process.argv[2] || 'http://127.0.0.1:18080/hrs-player.html';
const api = process.argv[3] || 'http://127.0.0.1:8000';
const durationS = Number(process.argv[4] || 60);
const out = process.argv[5] || 'output/unreal/stream-quality.json';
if (!Number.isFinite(durationS) || durationS < 30 || durationS > 7200) {
  throw new Error('duration_s must be between 30 and 7200 seconds');
}

function metric(rows, name) { return rows.find(row => row.name === name)?.value ?? null; }

(async () => {
  const channel = process.env.HRS_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined);
  const browser = await chromium.launch({headless:true, channel, args:[
    '--autoplay-policy=no-user-gesture-required', '--use-angle=default', '--enable-webgl'
  ]});
  const page = await browser.newPage({viewport:{width:1920,height:1080}});
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Performance.enable');
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  let runId = null;
  let serial = Date.now();
  try {
    const created = await page.request.post(api + '/api/simulations', {
      data:{continuous:true, control_period_s:.5}
    });
    assert.equal(created.status(), 202, 'dedicated simulation creation failed');
    runId = (await created.json()).id;
    const bind = await page.request.post(api + '/api/integrations/unreal/session/default', {
      data:{run_id:runId, request_serial:serial}
    });
    assert.equal(bind.status(), 200, 'renderer binding failed');
    await page.goto(player, {waitUntil:'domcontentloaded', timeout:30000});
    await page.waitForFunction(() => {
      const video = document.querySelector('video');
      return video && video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0;
    }, {timeout:120000});
    const startVideo = await page.locator('video').evaluate(video => ({
      time:video.currentTime, frames:video.getVideoPlaybackQuality?.().totalVideoFrames ?? null,
      width:video.videoWidth, height:video.videoHeight,
    }));
    const startMetrics = (await cdp.send('Performance.getMetrics')).metrics;
    await page.waitForFunction(async api => {
      const response = await fetch(`${api}/api/integrations/unreal/session/default/feedback`);
      return response.ok && (await response.json()).parity?.matches === true;
    }, api, {timeout:10000});
    const parity = await (await page.request.get(api + '/api/integrations/unreal/session/default/feedback')).json();

    await page.locator('video').click({position:{x:20,y:20}}).catch(() => page.mouse.click(20,20));
    const inputStart = Date.now();
    await page.keyboard.press('KeyE');
    await assert.doesNotReject(async () => {
      await page.waitForFunction(async ({api, runId}) => {
        const response = await fetch(`${api}/api/simulations/${runId}/visualization/snapshot`);
        return response.ok && (await response.json()).esd === true;
      }, {api, runId}, {timeout:5000});
    }, 'Pixel Streaming ESD input did not reach the simulator');
    const inputLatencyMs = Date.now() - inputStart;

    await page.waitForTimeout(durationS * 1000);
    const endVideo = await page.locator('video').evaluate(video => ({
      time:video.currentTime, frames:video.getVideoPlaybackQuality?.().totalVideoFrames ?? null,
      width:video.videoWidth, height:video.videoHeight,
    }));
    const endMetrics = (await cdp.send('Performance.getMetrics')).metrics;
    const elapsed = endVideo.time - startVideo.time;
    const fps = startVideo.frames === null || endVideo.frames === null || elapsed <= 0 ? null :
      (endVideo.frames - startVideo.frames) / elapsed;
    const startHeap = metric(startMetrics, 'JSHeapUsedSize');
    const endHeap = metric(endMetrics, 'JSHeapUsedSize');
    const heapGrowthMb = startHeap === null || endHeap === null ? null : (endHeap-startHeap)/1048576;
    assert.ok(endVideo.time > startVideo.time + durationS * .8, 'video did not advance for the requested soak');
    assert.ok(endVideo.width >= 1920 && endVideo.height >= 1080,
      `expected 1080p stream, received ${endVideo.width}x${endVideo.height}`);
    if (fps !== null) assert.ok(fps >= 28.5, `average decoded FPS ${fps.toFixed(2)} is below 28.5`);
    assert.ok(inputLatencyMs <= 1000, `end-to-end ESD input latency ${inputLatencyMs} ms exceeds 1000 ms`);
    assert.deepEqual(errors, []);
    const report = {
      status:'PASS', actual_unreal_stream:true, dedicated_run_id:runId,
      duration_s:durationS, decoded_fps:fps, input_latency_ms:inputLatencyMs,
      video:startVideo, final_video:endVideo, browser_js_heap_growth_mb:heapGrowthMb,
      telemetry_parity:parity.parity,
      page_errors:errors,
      gates:{resolution:'1920x1080 minimum', decoded_fps:'28.5 minimum when available', input_latency_ms:'1000 maximum'},
      claim_boundary:'Browser decode and E-to-server acknowledgement. Run with duration_s=3600 for the 60-minute gate; UE GPU/process memory must be recorded separately.'
    };
    fs.mkdirSync(path.dirname(out), {recursive:true});
    fs.writeFileSync(out, JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));
  } finally {
    if (runId) {
      await page.request.post(`${api}/api/simulations/${runId}/stop`).catch(()=>{});
      serial += 1;
      await page.request.post(api + '/api/integrations/unreal/session/default', {
        data:{run_id:null, request_serial:serial}
      }).catch(()=>{});
    }
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
