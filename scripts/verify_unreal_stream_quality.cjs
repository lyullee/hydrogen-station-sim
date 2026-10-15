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

async function sampleVideo(page) {
  return page.locator('video').evaluate(video => {
    const canvas = document.createElement('canvas');
    canvas.width = 64; canvas.height = 36;
    const context = canvas.getContext('2d', {willReadFrequently:true});
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    let luma = 0, dark = 0, bright = 0;
    for (let index=0; index<pixels.length; index+=4) {
      const value = .2126*pixels[index] + .7152*pixels[index+1] + .0722*pixels[index+2];
      luma += value;
      if (value < 4) dark += 1;
      if (value > 250) bright += 1;
    }
    const count = pixels.length / 4;
    return {
      elapsed_s:video.currentTime, ready_state:video.readyState,
      width:video.videoWidth, height:video.videoHeight,
      mean_luma:luma/count, dark_fraction:dark/count, bright_fraction:bright/count,
    };
  });
}

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
    for (const pattern of [/click to start/i, /start/i, /play/i, /시작/i]) {
      const candidate = page.getByRole('button', {name:pattern}).first();
      if (await candidate.isVisible().catch(() => false)) { await candidate.click(); break; }
    }
    const startOverlay = page.getByText(/click to start/i, {exact:true}).first();
    if (await startOverlay.isVisible().catch(() => false)) await startOverlay.click();
    await page.waitForFunction(() => {
      const video = document.querySelector('video');
      return video && video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0;
    }, null, {timeout:120000});
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

    const visualSamples = [];
    const sampleIntervalMs = 2000;
    const soakDeadline = Date.now() + durationS * 1000;
    while (Date.now() < soakDeadline) {
      visualSamples.push(await sampleVideo(page));
      await page.waitForTimeout(Math.min(sampleIntervalMs, Math.max(0, soakDeadline-Date.now())));
    }
    visualSamples.push(await sampleVideo(page));
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
    const nearBlackFrames = visualSamples.filter(row => row.mean_luma < 2 || row.dark_fraction > .995);
    const resolutionFailures = visualSamples.filter(row => row.width < 1920 || row.height < 1080 || row.ready_state < 2);
    const lumaJumps = visualSamples.slice(1).map((row,index) => ({
      from_s:visualSamples[index].elapsed_s, to_s:row.elapsed_s,
      delta:Math.abs(row.mean_luma-visualSamples[index].mean_luma),
      threshold:Math.max(20, visualSamples[index].mean_luma*.35),
    })).filter(row => row.delta > row.threshold);
    assert.ok(endVideo.time > startVideo.time + durationS * .8, 'video did not advance for the requested soak');
    assert.ok(endVideo.width >= 1920 && endVideo.height >= 1080,
      `expected 1080p stream, received ${endVideo.width}x${endVideo.height}`);
    if (fps !== null) assert.ok(fps >= 28.5, `average decoded FPS ${fps.toFixed(2)} is below 28.5`);
    assert.ok(inputLatencyMs <= 1000, `end-to-end ESD input latency ${inputLatencyMs} ms exceeds 1000 ms`);
    assert.equal(nearBlackFrames.length, 0, 'near-black video frames indicate a visible stream blink');
    assert.equal(resolutionFailures.length, 0, 'video readiness or resolution changed during the soak');
    assert.equal(lumaJumps.length, 0, 'abrupt frame-luminance transitions indicate visible flicker');
    assert.deepEqual(errors, []);
    const report = {
      status:'PASS', actual_unreal_stream:true, dedicated_run_id:runId,
      duration_s:durationS, decoded_fps:fps, input_latency_ms:inputLatencyMs,
      video:startVideo, final_video:endVideo, browser_js_heap_growth_mb:heapGrowthMb,
      telemetry_parity:parity.parity,
      temporal_visual:{sample_interval_s:sampleIntervalMs/1000, sample_count:visualSamples.length,
        near_black_frames:nearBlackFrames.length, resolution_failures:resolutionFailures.length,
        abrupt_luma_transitions:lumaJumps.length,
        mean_luma_range:[Math.min(...visualSamples.map(row=>row.mean_luma)),
                         Math.max(...visualSamples.map(row=>row.mean_luma))],
        samples:visualSamples},
      page_errors:errors,
      gates:{resolution:'1920x1080 minimum', decoded_fps:'28.5 minimum when available',
        input_latency_ms:'1000 maximum', near_black_frames:'0',
        abrupt_luma_transitions:'0 using max(20 luma, 35% previous luma)'},
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
