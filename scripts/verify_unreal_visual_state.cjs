// Verify that the actual Unreal renderer applied safety/process visuals, rather than
// merely receiving the corresponding server state. This script requires a live
// Pixel Streaming player and a dedicated simulation run.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.HRS_PLAYWRIGHT_MODULE || 'playwright');

const player = process.argv[2] || 'http://127.0.0.1:18080/hrs-player.html';
const api = process.argv[3] || 'http://127.0.0.1:8000';
const out = process.argv[4] || 'output/unreal/visual-state-scenario.json';
const screenshot = process.argv[5] || 'output/unreal/visual-state-scenario.png';

async function checked(response, label) {
  const body = await response.json().catch(() => ({}));
  assert.ok(response.ok(), `${label}: ${response.status()} ${JSON.stringify(body)}`);
  return body;
}

async function startVideo(page) {
  await page.goto(player, {waitUntil:'domcontentloaded', timeout:30000});
  for (const pattern of [/click to start/i, /start/i, /play/i, /시작/i]) {
    const candidate = page.getByRole('button', {name:pattern}).first();
    if (await candidate.isVisible().catch(() => false)) { await candidate.click(); break; }
  }
  const overlay = page.getByText(/click to start/i, {exact:true}).first();
  if (await overlay.isVisible().catch(() => false)) await overlay.click();
  await page.waitForFunction(() => {
    const video = document.querySelector('video');
    return video && video.readyState >= 2 && video.videoWidth === 1920 && video.videoHeight === 1080;
  }, null, {timeout:120000});
  await page.locator('video').click({position:{x:20,y:20}}).catch(() => page.mouse.click(20,20));
}

async function visualFeedback(page, runId, predicate, label, timeoutMs=30000) {
  const deadline = Date.now() + timeoutMs;
  let latest = null;
  while (Date.now() < deadline) {
    const response = await page.request.get(`${api}/api/integrations/unreal/session/default/feedback`);
    if (response.ok()) {
      const candidate = await response.json();
      if (candidate.run_id === runId && candidate.visual_state) {
        latest = candidate;
        if (predicate(candidate.visual_state, candidate)) return candidate;
      }
    }
    await page.waitForTimeout(150);
  }
  assert.fail(`${label}; latest=${JSON.stringify(latest?.visual_state || null)}`);
}

async function safetyAction(page, runId, kind, target, visualPredicate, label) {
  const command = await checked(await page.request.post(
    `${api}/api/simulations/${runId}/safety/actions`, {data:{kind,target}}
  ), `${kind} ${target}`);
  const feedback = await visualFeedback(page, runId, visualPredicate, label, 20000);
  return {kind, target, command_status:command.action.status, visual_state:feedback.visual_state};
}

(async () => {
  const channel = process.env.HRS_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined);
  const browser = await chromium.launch({headless:true, channel, args:[
    '--autoplay-policy=no-user-gesture-required', '--use-angle=default', '--enable-webgl'
  ]});
  const page = await browser.newPage({viewport:{width:1920,height:1080}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  let runId = null;
  let serial = Date.now();
  const checks = [];
  try {
    await startVideo(page);
    const created = await checked(await page.request.post(`${api}/api/simulations`, {data:{
      continuous:true,
      control_period_s:0.2,
      process_settings:{vehicle_1:true, vehicle_2:false, risk_overlay_enabled:true},
      faults:[
        {event_id:'visual-leak', kind:'hydrogen-leak', target:'cascade.high', start_time_s:0,
         leak_diameter_mm:0.8, release_boundary:'flow_limited_line', maximum_release_mass_flow_g_s:8},
        {event_id:'visual-fire', kind:'external-fire', target:'cascade.high', start_time_s:0,
         external_temperature_c:650, heat_transfer_ua_w_k:300}
      ]
    }}), 'create visual scenario');
    runId = created.id;
    await checked(await page.request.post(`${api}/api/integrations/unreal/session/default`, {
      data:{run_id:runId, request_serial:++serial}
    }), 'bind visual scenario');

    let feedback = await visualFeedback(page, runId, state =>
      state.hose_1_mode === 'connected' && state.hose_2_mode === 'parked' &&
      state.visible_jets.includes('visual-leak') &&
      state.visible_highlight_components.includes('cascade.high') &&
      state.visible_fire_components.includes('cascade.high'),
    'Unreal did not apply hose, leak, highlight and fire visuals', 45000);
    checks.push({name:'incident-and-hose-state', status:'PASS', evidence:{
      hose_1_mode:feedback.visual_state.hose_1_mode,
      hose_2_mode:feedback.visual_state.hose_2_mode,
      visible_jets:feedback.visual_state.visible_jets,
      visible_highlight_components:feedback.visual_state.visible_highlight_components,
      visible_fire_components:feedback.visual_state.visible_fire_components,
    }});

    for (const toggle of [
      {key:'KeyC', name:'CCTV', predicate:s=>s.show_cameras && s.visible_cameras.length === 5,
       evidence:s=>({show:s.show_cameras, count:s.visible_cameras.length, ids:s.visible_cameras})},
      {key:'KeyG', name:'detectors', predicate:s=>s.show_detectors && s.visible_detectors.length === 24,
       evidence:s=>({show:s.show_detectors, count:s.visible_detectors.length})},
      {key:'KeyD', name:'consequence-distance', predicate:s=>s.show_distance && s.visible_distances.includes('visual-leak'),
       evidence:s=>({show:s.show_distance, ids:s.visible_distances})},
      {key:'KeyR', name:'risk-floor', predicate:s=>s.show_risk && s.visible_risk_components.length > 0,
       evidence:s=>({show:s.show_risk, count:s.visible_risk_components.length, ids:s.visible_risk_components})},
    ]) {
      await page.keyboard.press(toggle.key);
      feedback = await visualFeedback(page, runId, toggle.predicate, `${toggle.name} toggle was not applied`, 20000);
      checks.push({name:toggle.name, status:'PASS', evidence:toggle.evidence(feedback.visual_state)});
    }

    const actions = [];
    actions.push(await safetyAction(page, runId, 'valve.close', 'bank.high.inlet',
      state=>state.valve_states['bank.high.inlet'] === 'closed',
      'Unreal did not apply confirmed high-bank inlet closure'));
    actions.push(await safetyAction(page, runId, 'ventilation.on', 'storage',
      state=>state.auxiliary_states['fan.storage'] === 'running',
      'Unreal did not apply storage ventilation state'));
    actions.push(await safetyAction(page, runId, 'cooling.on', 'high',
      state=>state.auxiliary_states['cooling.high'] === 'running',
      'Unreal did not apply high-bank cooling state'));
    actions.push(await safetyAction(page, runId, 'access.restrict', 'storage',
      state=>state.auxiliary_states['access.storage'] === 'restricted' &&
             state.visible_auxiliary.includes('access.storage'),
      'Unreal did not apply storage access restriction'));
    actions.push(await safetyAction(page, runId, 'personnel.evacuate', 'storage',
      state=>state.auxiliary_states['personnel.storage'] === 'evacuated' &&
             state.personnel_at_muster.includes('storage'),
      'Unreal did not move storage personnel to the muster point'));
    checks.push({name:'virtual-safety-actions', status:'PASS', actions:actions.map(row=>({
      kind:row.kind, target:row.target, command_status:row.command_status,
      applied_valve:row.visual_state.valve_states['bank.high.inlet'] || null,
      applied_auxiliary:row.visual_state.auxiliary_states,
    }))});

    const currentOperations = await checked(await page.request.get(
      `${api}/api/simulations/${runId}/operations`), 'read process operations');
    const nextSettings = {...currentOperations.settings, vehicle_1:false, vehicle_2:true};
    await checked(await page.request.put(`${api}/api/simulations/${runId}/operations`, {
      data:nextSettings
    }), 'switch to dispenser 2');
    feedback = await visualFeedback(page, runId,
      state=>state.hose_1_mode === 'parked' && state.hose_2_mode === 'connected',
      'Independent dispenser 2 hose state was not applied', 20000);
    checks.push({name:'independent-dispenser-2-hose', status:'PASS', evidence:{
      hose_1_mode:feedback.visual_state.hose_1_mode,
      hose_2_mode:feedback.visual_state.hose_2_mode,
    }});

    const startTime = await page.locator('video').evaluate(video=>video.currentTime);
    await page.waitForTimeout(1200);
    const endTime = await page.locator('video').evaluate(video=>video.currentTime);
    assert.ok(endTime > startTime, 'Pixel Streaming video stopped during visual-state checks');
    assert.deepEqual(errors, []);
    fs.mkdirSync(path.dirname(screenshot), {recursive:true});
    await page.screenshot({path:screenshot, fullPage:true});

    const report = {
      status:'PASS', actual_unreal_stream:true, run_id:runId,
      resolution:{width:1920,height:1080}, checks,
      final_visual_state:feedback.visual_state,
      video_advanced_s:endTime-startTime, page_errors:errors,
      screenshot,
      claim_boundary:'Confirms post-application component visibility and actuator state reported by the running Unreal 5.8 renderer, together with live 1080p video. It does not claim CFD fidelity, field commissioning or human-factors approval.'
    };
    fs.mkdirSync(path.dirname(out), {recursive:true});
    fs.writeFileSync(out, JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));
  } finally {
    if (runId) await page.request.post(`${api}/api/simulations/${runId}/stop`).catch(()=>{});
    await page.request.post(`${api}/api/integrations/unreal/session/default`, {
      data:{run_id:null,request_serial:++serial}
    }).catch(()=>{});
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
