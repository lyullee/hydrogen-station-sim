// Exercise every virtual valve and every valve failure mode, then complete the
// recovery gate while checking the state actually reported by the packaged UE renderer.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.HRS_PLAYWRIGHT_MODULE || 'playwright');

const player = process.argv[2] || 'http://127.0.0.1:18080/hrs-player.html';
const api = process.argv[3] || 'http://127.0.0.1:8000';
const out = process.argv[4] || 'output/unreal/valves-recovery.json';
const screenshot = process.argv[5] || 'output/unreal/valves-recovery.png';

async function checked(response, label) {
  const body = await response.json().catch(() => ({}));
  assert.ok(response.ok(), `${label}: ${response.status()} ${JSON.stringify(body)}`);
  return body;
}

async function waitFor(read, predicate, label, timeout=20000) {
  const deadline = Date.now() + timeout;
  let latest = null;
  while (Date.now() < deadline) {
    latest = await read();
    if (predicate(latest)) return latest;
    await new Promise(resolve => setTimeout(resolve, 125));
  }
  assert.fail(`${label}; latest=${JSON.stringify(latest)}`);
}

(async () => {
  const browser = await chromium.launch({
    headless:true,
    channel:process.env.HRS_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined),
    args:['--autoplay-policy=no-user-gesture-required'],
  });
  const page = await browser.newPage({viewport:{width:1920,height:1080}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  let serial = Date.now();
  let runId = null;
  const report = {status:'PASS', actual_unreal_stream:true, checks:[], page_errors:errors};

  async function startVideo() {
    await page.goto(player, {waitUntil:'domcontentloaded', timeout:30000});
    for (const pattern of [/click to start/i, /start/i, /play/i, /시작/i]) {
      const button = page.getByRole('button', {name:pattern}).first();
      if (await button.isVisible().catch(() => false)) { await button.click(); break; }
    }
    const overlay = page.getByText(/click to start/i, {exact:true}).first();
    if (await overlay.isVisible().catch(() => false)) await overlay.click();
    await page.waitForFunction(() => {
      const video = document.querySelector('video');
      return video && video.readyState >= 2 && video.videoWidth === 1920 && video.videoHeight === 1080;
    }, null, {timeout:120000});
  }

  async function createRun(faults=[]) {
    const created = await checked(await page.request.post(`${api}/api/simulations`, {data:{
      continuous:true, control_period_s:.2,
      process_settings:{trailer_supply:false, pressure_recharge:false, vehicle_1:false, vehicle_2:false},
      faults,
    }}), 'create continuous operator run');
    runId = created.id;
    await checked(await page.request.post(`${api}/api/integrations/unreal/session/default`, {
      data:{run_id:runId, request_serial:++serial},
    }), 'bind Unreal renderer');
    await waitFor(
      async () => {
        const response = await page.request.get(`${api}/api/integrations/unreal/session/default/feedback`);
        return response.ok() ? response.json() : null;
      },
      value => value?.run_id === runId && value?.visual_state,
      'renderer did not report bound visual state', 30000,
    );
    return runId;
  }

  async function stopRun() {
    if (!runId) return;
    await page.request.post(`${api}/api/simulations/${runId}/stop`).catch(() => {});
    await page.request.post(`${api}/api/integrations/unreal/session/default`, {
      data:{run_id:null, request_serial:++serial},
    }).catch(() => {});
    runId = null;
  }

  async function safety() {
    return checked(await page.request.get(`${api}/api/simulations/${runId}/safety`), 'read safety state');
  }

  async function feedback() {
    const response = await page.request.get(`${api}/api/integrations/unreal/session/default/feedback`);
    return response.ok() ? response.json() : null;
  }

  async function command(kind, target) {
    return checked(await page.request.post(`${api}/api/simulations/${runId}/safety/actions`, {
      data:{kind,target,note:'packaged Unreal acceptance verification'},
    }), `${kind} ${target}`);
  }

  async function waitValve(target, serverState, ueState) {
    const state = await waitFor(safety,
      value => value.valves?.[target]?.status === serverState,
      `${target} did not reach server state ${serverState}`);
    const visual = await waitFor(feedback,
      value => value?.run_id === runId && value.visual_state?.valve_states?.[target] === ueState,
      `${target} did not reach Unreal state ${ueState}`);
    return {server:state.valves[target], unreal:visual.visual_state.valve_states[target]};
  }

  try {
    await startVideo();
    await createRun();
    const normalValves = [
      'trailer.source','trailer.station','compressor.suction','compressor.discharge',
      'bank.low.inlet','bank.low.outlet','bank.medium.inlet','bank.medium.outlet',
      'bank.high.inlet','bank.high.outlet','dispenser.1','dispenser.2',
    ];
    const valveResults = [];
    for (const target of normalValves) {
      await command('valve.close', target);
      const closed = await waitValve(target, 'confirmed', 'closed');
      await command('valve.open', target);
      const opened = await waitValve(target, 'confirmed', 'open');
      valveResults.push({target, closed, opened});
    }
    report.checks.push({name:'all-isolation-valves', status:'PASS', count:valveResults.length,
                        valves:valveResults});

    const ventResults = [];
    for (const bank of ['low','medium','high']) {
      const target = `vent.${bank}`;
      const before = await checked(await page.request.get(
        `${api}/api/simulations/${runId}/visualization/snapshot`), `read ${bank} pre-vent snapshot`);
      const beforeBank = before.equipment.find(row => row.component_id === `cascade.${bank}`);
      await command('vent.open', target);
      const opened = await waitValve(target, 'confirmed', 'open');
      const release = await waitFor(feedback,
        value => value?.visual_state?.visible_jets?.includes(`vent-${bank}`),
        `${target} release jet was not applied by Unreal`, 30000);
      await page.waitForTimeout(1200);
      const after = await checked(await page.request.get(
        `${api}/api/simulations/${runId}/visualization/snapshot`), `read ${bank} vented snapshot`);
      const afterBank = after.equipment.find(row => row.component_id === `cascade.${bank}`);
      assert.ok(afterBank.mass_kg < beforeBank.mass_kg || afterBank.pressure_mpa < beforeBank.pressure_mpa,
        `${target} did not deplete isolated inventory`);
      await command('vent.close', target);
      const closed = await waitValve(target, 'confirmed', 'closed');
      await waitFor(feedback,
        value => value?.run_id === runId && !value.visual_state?.visible_jets?.includes(`vent-${bank}`),
        `${target} release jet remained after confirmed closure`, 30000);
      ventResults.push({target, opened, closed,
        before:{mass_kg:beforeBank.mass_kg,pressure_mpa:beforeBank.pressure_mpa},
        after:{mass_kg:afterBank.mass_kg,pressure_mpa:afterBank.pressure_mpa},
        unreal_release:`vent-${bank}`, applied:release.visual_state.visible_jets.includes(`vent-${bank}`)});
    }
    report.checks.push({name:'vent-path-and-residual-inventory', status:'PASS', vents:ventResults});

    const failureTarget = 'compressor.discharge';
    const failureResults = [];
    for (const fault of ['stuck_open','stuck_closed','partial_closed','seat_leak','feedback_fault']) {
      await checked(await page.request.put(`${api}/api/simulations/${runId}/safety/faults/${failureTarget}`, {
        data:{fault},
      }), `inject ${fault}`);
      const kind = fault === 'stuck_closed' ? 'valve.open' : 'valve.close';
      await command(kind, failureTarget);
      const failed = await waitValve(failureTarget, 'failed', 'failed');
      failureResults.push({fault, command:kind, applied:failed});
      await checked(await page.request.put(`${api}/api/simulations/${runId}/safety/faults/${failureTarget}`, {
        data:{fault:'none'},
      }), `clear ${fault}`);
      await command('valve.open', failureTarget);
      await waitValve(failureTarget, 'confirmed', 'open');
    }
    report.checks.push({name:'all-valve-failure-modes', status:'PASS', failures:failureResults});
    await stopRun();

    await createRun([{
      event_id:'training-release', kind:'hydrogen-leak', target:'cascade.high', start_time_s:0,
      leak_diameter_mm:.5, release_boundary:'flow_limited_line', maximum_release_mass_flow_g_s:4,
    }]);
    await waitFor(
      async () => checked(await page.request.get(
        `${api}/api/simulations/${runId}/visualization/snapshot`), 'read active recovery fault'),
      state => state.releases.some(item => item.release_id === 'training-release'),
      'training leak did not become active');
    await command('esd.trip','station');
    await command('repair.leak','training-release');
    await waitFor(
      async () => checked(await page.request.get(
        `${api}/api/simulations/${runId}/visualization/snapshot`), 'read repaired recovery fault'),
      state => !state.releases.some(item => item.release_id === 'training-release'),
      'repaired training leak remained active');
    await command('recovery.record','source_removed');
    for (const side of ['inlet','outlet']) {
      await command('valve.close',`bank.high.${side}`);
      await waitValve(`bank.high.${side}`,'confirmed','closed');
    }
    await command('tightness.test','high');
    await waitFor(safety, state => state.recovery.tightness_test,
      'tightness test did not pass', 20000);
    await command('detector.test','all');
    await waitFor(safety, state => state.recovery.detector_test,
      'detector test did not pass', 15000);
    await command('valve.test','all');
    await waitFor(safety, state => state.recovery.valve_test,
      'valve test did not pass', 15000);
    await command('purge.run','high');
    await waitFor(safety, state => state.recovery.purge_complete &&
      state.purge_h2_fraction.high <= .005,
      'purge did not reach its completion criterion', 25000);
    await command('pressure.test','high');
    await waitFor(safety, state => state.recovery.pressure_test,
      'pressure test did not pass', 20000);
    await command('recovery.record','supervisor_approval');
    const recovered = await waitFor(safety,
      state => Object.values(state.recovery).every(Boolean),
      'all eight recovery checks were not completed');
    const renderedRecovery = await waitFor(feedback,
      value => value?.visual_state?.recovery_completed === 8 && value.visual_state.recovery_total === 8,
      'Unreal did not apply the completed recovery board', 20000);
    await page.screenshot({path:screenshot});
    const restart = await command('restart.approve','station');
    assert.equal(restart.action.status, 'confirmed');
    report.checks.push({name:'eight-step-recovery-and-restart', status:'PASS',
      recovery:recovered.recovery,
      unreal:{completed:renderedRecovery.visual_state.recovery_completed,
              total:renderedRecovery.visual_state.recovery_total},
      restart_status:restart.action.status});

    const video = await page.locator('video').evaluate(element => ({
      width:element.videoWidth, height:element.videoHeight, time:element.currentTime,
    }));
    assert.deepEqual({width:video.width,height:video.height},{width:1920,height:1080});
    assert.deepEqual(errors, []);
    report.run_id = runId;
    report.resolution = {width:video.width,height:video.height};
    report.screenshot = screenshot;
    report.claim_boundary = 'Virtual command, feedback, residual-inventory and recovery acceptance only; no physical PLC actuation or site commissioning is claimed.';
    fs.mkdirSync(path.dirname(out), {recursive:true});
    fs.writeFileSync(out, JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));
  } finally {
    await stopRun().catch(() => {});
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode=1; });
