// Detect local temporal sparkle in a static Pixel Streaming image.  This is
// intentionally stricter than the long-run mean-luminance gate: it compares
// pixels inside the upper station/canopy region where thin bright edges live.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.HRS_PLAYWRIGHT_MODULE || 'playwright');

const player = process.argv[2] || 'http://127.0.0.1:18080/hrs-player.html';
const durationS = Number(process.argv[3] || 20);
const out = process.argv[4] || 'output/unreal/static-edge-stability.json';
if (!Number.isFinite(durationS) || durationS < 10 || durationS > 300) {
  throw new Error('duration_s must be between 10 and 300 seconds');
}

function percentile(values, fraction) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * fraction))];
}

(async () => {
  const channel = process.env.HRS_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined);
  const browser = await chromium.launch({headless:true, channel, args:[
    '--autoplay-policy=no-user-gesture-required', '--use-angle=default', '--enable-webgl'
  ]});
  const page = await browser.newPage({viewport:{width:1920,height:1080}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(player, {waitUntil:'domcontentloaded', timeout:30000});
    for (const pattern of [/click to start/i, /start/i, /play/i, /시작/i]) {
      const candidate = page.getByRole('button', {name:pattern}).first();
      if (await candidate.isVisible().catch(() => false)) { await candidate.click(); break; }
    }
    const overlay = page.getByText(/click to start/i, {exact:true}).first();
    if (await overlay.isVisible().catch(() => false)) await overlay.click();
    await page.waitForFunction(() => {
      const video = document.querySelector('video');
      return video && video.readyState >= 2 && video.videoWidth >= 1280;
    }, null, {timeout:120000});
    await page.waitForTimeout(2000);

    const samples = [];
    const endAt = Date.now() + durationS * 1000;
    while (Date.now() < endAt) {
      samples.push(await page.locator('video').evaluate(video => {
        const width = 320, height = 180;
        const canvas = document.createElement('canvas');
        canvas.width = width; canvas.height = height;
        const context = canvas.getContext('2d', {willReadFrequently:true});
        context.drawImage(video, 0, 0, width, height);
        // Upper 62% includes the canopy, vent and equipment edges but avoids
        // most status text that can legitimately update once per second.
        const pixels = context.getImageData(0, 0, width, Math.floor(height * .62)).data;
        const luma = new Uint8Array(pixels.length / 4);
        for (let source=0, target=0; source<pixels.length; source+=4, target+=1) {
          luma[target] = Math.round(.2126*pixels[source] + .7152*pixels[source+1] + .0722*pixels[source+2]);
        }
        return {time:video.currentTime, luma:Array.from(luma)};
      }));
      await page.waitForTimeout(250);
    }

    const changedFractions = [], extremeFractions = [], meanDeltas = [];
    for (let index=1; index<samples.length; index+=1) {
      const previous = samples[index-1].luma, current = samples[index].luma;
      let changed = 0, extreme = 0, sum = 0;
      for (let pixel=0; pixel<current.length; pixel+=1) {
        const delta = Math.abs(current[pixel] - previous[pixel]);
        sum += delta;
        if (delta >= 30) changed += 1;
        if (delta >= 70) extreme += 1;
      }
      changedFractions.push(changed/current.length);
      extremeFractions.push(extreme/current.length);
      meanDeltas.push(sum/current.length);
    }
    const report = {
      status:'PASS', player, duration_s:durationS, sample_count:samples.length,
      sample_resolution:'320x112 upper scene region',
      p95_changed_fraction:percentile(changedFractions, .95),
      max_changed_fraction:Math.max(...changedFractions),
      p95_extreme_fraction:percentile(extremeFractions, .95),
      max_extreme_fraction:Math.max(...extremeFractions),
      p95_mean_luma_delta:percentile(meanDeltas, .95),
      page_errors:errors,
      thresholds:{pixel_delta:30, extreme_delta:70, max_p95_changed_fraction:.003, max_p95_extreme_fraction:.0005},
      claim_boundary:'Static upper-scene temporal edge stability; it does not replace the 60-minute stream/process gate.',
    };
    assert.ok(report.p95_changed_fraction <= report.thresholds.max_p95_changed_fraction,
      `local edge changes are too frequent: ${report.p95_changed_fraction}`);
    assert.ok(report.p95_extreme_fraction <= report.thresholds.max_p95_extreme_fraction,
      `extreme local edge changes are too frequent: ${report.p95_extreme_fraction}`);
    assert.deepEqual(errors, [], `page errors: ${errors.join('; ')}`);
    fs.mkdirSync(path.dirname(out), {recursive:true});
    fs.writeFileSync(out, JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
