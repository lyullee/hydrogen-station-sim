// Verify an actual advancing UE Pixel Streaming video; player UI alone is not enough.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.HRS_PLAYWRIGHT_MODULE || 'playwright');

const player = process.argv[2] || 'http://127.0.0.1:18080/hrs-player.html';
const out = process.argv[3] || 'output/unreal/ue-video.json';
const screenshot = process.argv[4] || 'output/unreal/ue-video.png';
const durationS = Number(process.argv[5] || 5);
if (!Number.isFinite(durationS) || durationS < 5 || durationS > 7200) {
  throw new Error('duration_s must be between 5 and 7200 seconds');
}

(async () => {
  const channel = process.env.HRS_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined);
  const browser = await chromium.launch({headless:true, channel, args:[
    '--autoplay-policy=no-user-gesture-required', '--use-angle=default', '--enable-webgl'
  ]});
  const page = await browser.newPage({viewport:{width:1920,height:1080}});
  const pageErrors = [], consoleErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  try {
    await page.goto(player, {waitUntil:'domcontentloaded', timeout:30000});
    // The official frontend has changed button labels between releases. Click
    // only a visible, local start control when one is present.
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
    const first = await page.locator('video').evaluate(video => ({
      currentTime:video.currentTime, width:video.videoWidth, height:video.videoHeight,
      paused:video.paused, ended:video.ended,
      decodedFrames:video.getVideoPlaybackQuality?.().totalVideoFrames ?? video.webkitDecodedFrameCount ?? null,
    }));
    await page.waitForTimeout(durationS * 1000);
    const second = await page.locator('video').evaluate(video => ({
      currentTime:video.currentTime, width:video.videoWidth, height:video.videoHeight,
      paused:video.paused, ended:video.ended,
      decodedFrames:video.getVideoPlaybackQuality?.().totalVideoFrames ?? video.webkitDecodedFrameCount ?? null,
    }));
    assert.ok(second.currentTime > first.currentTime + 1,
      `Pixel stream did not advance: ${first.currentTime} -> ${second.currentTime}`);
    assert.ok(second.width >= 1280 && second.height >= 720,
      `Pixel stream resolution is below the pilot gate: ${second.width}x${second.height}`);
    fs.mkdirSync(path.dirname(screenshot), {recursive:true});
    await page.screenshot({path:screenshot, fullPage:true});
    const decodedFps = Number.isFinite(first.decodedFrames) && Number.isFinite(second.decodedFrames)
      ? (second.decodedFrames - first.decodedFrames) / (second.currentTime - first.currentTime)
      : null;
    const report = {
      status:'PASS', actual_unreal_stream:true, player, duration_s:durationS,
      first, second, measured_resolution:`${second.width}x${second.height}`,
      decoded_fps:decodedFps,
      page_errors:pageErrors, console_errors:consoleErrors,
      claim_boundary:'Confirms one advancing browser video sample. FPS, latency and 60-minute stability require separate gates.'
    };
    assert.deepEqual(pageErrors, []);
    fs.mkdirSync(path.dirname(out), {recursive:true});
    fs.writeFileSync(out, JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
