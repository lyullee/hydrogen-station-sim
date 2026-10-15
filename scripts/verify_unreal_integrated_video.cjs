// Verify that the live Unreal video is embedded inside the existing dashboard.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.HRS_PLAYWRIGHT_MODULE || 'playwright');

const base = process.argv[2] || 'http://127.0.0.1:8000';
const out = process.argv[3] || 'output/unreal/integrated-video.json';
const screenshot = process.argv[4] || 'output/unreal/integrated-video.png';

(async () => {
  const channel = process.env.HRS_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined);
  const browser = await chromium.launch({headless:true, channel, args:[
    '--autoplay-policy=no-user-gesture-required', '--use-angle=default', '--enable-webgl'
  ]});
  const page = await browser.newPage({viewport:{width:1920,height:1080}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(base, {waitUntil:'domcontentloaded', timeout:30000});
    await page.waitForFunction(() => document.querySelector('#s3Stage')?.classList.contains('unreal-active'), null, {timeout:30000});
    const player = page.frameLocator('.s3-unreal-layer iframe');
    const start = player.locator('#connectOverlay').first();
    if (await start.isVisible().catch(() => false)) await start.click();
    const video = player.locator('video');
    await video.waitFor({state:'visible', timeout:120000});
    await video.evaluate(async element => {
      const started = performance.now();
      while ((element.readyState < 2 || element.videoWidth < 1 || element.currentTime <= 0) && performance.now() - started < 120000)
        await new Promise(resolve => setTimeout(resolve, 200));
      if (element.readyState < 2 || element.videoWidth < 1) throw new Error('embedded Unreal video did not become ready');
    });
    await page.waitForFunction(() => {
      const frame = document.querySelector('.s3-unreal-layer iframe');
      return Boolean(frame?.src);
    });
    const first = await video.evaluate(element => ({time:element.currentTime, width:element.videoWidth, height:element.videoHeight}));
    await page.waitForTimeout(2500);
    const second = await video.evaluate(element => ({time:element.currentTime, width:element.videoWidth, height:element.videoHeight}));
    assert.ok(second.time > first.time + 0.5, `embedded video did not advance: ${first.time} -> ${second.time}`);
    assert.ok(second.width >= 1280 && second.height >= 720, `embedded video resolution is ${second.width}x${second.height}`);
    assert.equal(await page.locator('.masthead').isVisible(), true);
    assert.equal(await page.locator('.side-nav').isVisible(), true);
    assert.equal(await page.locator('.s3-sidebar').isVisible(), true);
    fs.mkdirSync(path.dirname(screenshot), {recursive:true});
    await page.screenshot({path:screenshot, fullPage:false});
    const report = {status:'PASS', dashboard:true, embedded_unreal_video:true, first, second, page_errors:errors};
    assert.deepEqual(errors, []);
    fs.mkdirSync(path.dirname(out), {recursive:true});
    fs.writeFileSync(out, JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
