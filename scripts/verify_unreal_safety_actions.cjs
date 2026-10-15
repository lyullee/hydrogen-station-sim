// Verify the packaged Unreal renderer while exercising representative virtual safety actions.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.HRS_PLAYWRIGHT_MODULE || 'playwright');

const player = process.argv[2] || 'http://127.0.0.1:18080/hrs-player.html';
const api = process.argv[3] || 'http://127.0.0.1:8000';
const out = process.argv[4] || 'output/unreal/safety-actions.json';

async function json(response) {
  const body = await response.json();
  assert.ok(response.ok(), `${response.status()} ${JSON.stringify(body)}`);
  return body;
}

(async () => {
  const channel = process.env.HRS_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined);
  const browser = await chromium.launch({headless:true, channel, args:['--autoplay-policy=no-user-gesture-required']});
  const page = await browser.newPage({viewport:{width:1920,height:1080}});
  let runId = null;
  let serial = Date.now();
  const checks = [];
  try {
    await page.goto(player, {waitUntil:'domcontentloaded', timeout:30000});
    for (const pattern of [/click to start/i, /start/i, /play/i, /시작/i]) {
      const candidate = page.getByRole('button', {name:pattern}).first();
      if (await candidate.isVisible().catch(() => false)) { await candidate.click(); break; }
    }
    const overlay = page.getByText(/click to start/i, {exact:true}).first();
    if (await overlay.isVisible().catch(() => false)) await overlay.click();
    await page.waitForFunction(() => {
      const video=document.querySelector('video');
      return video && video.readyState>=2 && video.videoWidth===1920 && video.videoHeight===1080;
    }, null, {timeout:120000});

    const created = await page.request.post(`${api}/api/simulations`, {
      data:{continuous:true, control_period_s:.2, process_settings:{}}
    });
    assert.equal(created.status(), 202);
    runId = (await created.json()).id;
    const bound = await page.request.post(`${api}/api/integrations/unreal/session/default`, {
      data:{run_id:runId, request_serial:++serial}
    });
    assert.equal(bound.status(), 200);
    await page.waitForFunction(async ({api,runId}) => {
      const response=await fetch(`${api}/api/simulations/${runId}/visualization/snapshot`);
      return response.ok && (await response.json()).data_available;
    }, {api,runId}, {timeout:30000});
    const feedbackDeadline = Date.now() + 30000;
    let feedback;
    do {
      const response = await page.request.get(`${api}/api/integrations/unreal/session/default/feedback`);
      if (response.ok()) {
        const candidate = await response.json();
        if (candidate.run_id === runId && candidate.received_at) { feedback = candidate; break; }
      }
      await page.waitForTimeout(100);
    } while (Date.now() < feedbackDeadline);
    assert.ok(feedback, 'Packaged Unreal renderer did not send feedback for the bound run');
    const initialFeedbackSequence = feedback.sequence;
    const startVideoTime = await page.locator('video').evaluate(video=>video.currentTime);

    async function action(kind, target, predicate, description) {
      const response = await page.request.post(`${api}/api/simulations/${runId}/safety/actions`, {
        data:{kind,target}
      });
      const command = await json(response);
      const deadline = Date.now() + 10000;
      let state;
      do {
        state = await json(await page.request.get(`${api}/api/simulations/${runId}/safety`));
        if (predicate(state)) break;
        await page.waitForTimeout(100);
      } while (Date.now() < deadline);
      assert.ok(predicate(state), `${kind} ${target} did not reach its confirmation state`);
      checks.push({kind,target,description,command_status:command.action.status,state_confirmed:true});
      return state;
    }

    await action('valve.close','bank.high.inlet',
      state=>state.valves['bank.high.inlet'].status==='confirmed' && state.valves['bank.high.inlet'].actual_open===false,
      'High-bank inlet valve reached closed feedback');
    await action('ventilation.off','storage',
      state=>state.ventilation.storage.commanded===false && state.ventilation.storage.running===false,
      'Storage ventilation stopped');
    await action('ventilation.on','storage',
      state=>state.ventilation.storage.commanded===true && state.ventilation.storage.running===true,
      'Storage ventilation restarted');
    await action('cooling.on','high',
      state=>state.cooling.high.commanded===true && state.cooling.high.running===true,
      'High-bank cooling confirmed');
    await action('access.restrict','storage',
      state=>state.access_restricted.storage===true,
      'Storage-zone access restriction confirmed');
    await action('personnel.evacuate','storage',
      state=>state.personnel.storage===0 && state.evacuated.storage>=2,
      'Storage-zone personnel evacuation confirmed');
    await action('esd.trip','station',
      state=>state.esd_requested===true,
      'Station ESD confirmed');
    await action('operation.stop','all',
      state=>state.actions.some(item=>item.kind==='operation.stop' && item.target==='all' && item.status==='confirmed'),
      'All operations stopped');

    await page.waitForFunction(async ({api,initialFeedbackSequence}) => {
      const response=await fetch(`${api}/api/integrations/unreal/session/default/feedback`);
      if (!response.ok) return false;
      return (await response.json()).sequence > initialFeedbackSequence;
    }, {api,initialFeedbackSequence}, {timeout:15000});
    feedback = await json(await page.request.get(`${api}/api/integrations/unreal/session/default/feedback`));
    await page.waitForTimeout(1200);
    const endVideoTime = await page.locator('video').evaluate(video=>video.currentTime);
    assert.ok(endVideoTime > startVideoTime, 'Pixel Streaming video stopped during safety actions');

    const report={
      status:'PASS', actual_unreal_stream:true, run_id:runId,
      resolution:{width:1920,height:1080}, checks,
      renderer_feedback_advanced:feedback.sequence > initialFeedbackSequence,
      renderer_feedback_sequence:{before:initialFeedbackSequence,after:feedback.sequence},
      video_advanced_s:endVideoTime-startVideoTime,
      claim_boundary:'Confirms API command/feedback state, Unreal telemetry feedback and live video continuity. It does not substitute for site commissioning or safety certification.'
    };
    fs.mkdirSync(path.dirname(out),{recursive:true});
    fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));
  } finally {
    if (runId) await page.request.post(`${api}/api/simulations/${runId}/stop`).catch(()=>{});
    await page.request.post(`${api}/api/integrations/unreal/session/default`, {
      data:{run_id:null,request_serial:++serial}
    }).catch(()=>{});
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
