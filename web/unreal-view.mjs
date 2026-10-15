import { playerUrlForPage } from './unreal-view-state.mjs';

const stage = document.getElementById('s3Stage');
const tools = document.querySelector('.s3-head-tools');
if (stage && tools) {
  const button = document.createElement('button');
  button.id = 's3UnrealToggle'; button.className = 's3-risk-toggle';
  button.type = 'button'; button.textContent = 'Unreal 3D';
  button.setAttribute('aria-pressed', 'false');
  tools.insertBefore(button, tools.querySelector('#s3Fullscreen'));
  const layer = document.createElement('div');
  layer.className = 's3-unreal-layer'; layer.hidden = true;
  const status = document.createElement('p'); status.className = 's3-unreal-status';
  status.setAttribute('role', 'status');
  const frame = document.createElement('iframe');
  frame.title = 'Unreal 충전소 3D'; frame.allow = 'autoplay; fullscreen';
  layer.append(frame, status); stage.append(layer);
  let active = false, boundRun, config, timer, bindPending = false;
  let bindingVersion = 0;
  let requestSerial = Date.now();
  const notify = message => window.notifyOperator?.(message);
  async function bind(runId, keepalive = false) {
    requestSerial = Math.max(Date.now(), requestSerial + 1);
    const response = await fetch('/api/integrations/unreal/session/default', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({run_id: runId || null, request_serial: requestSerial}), keepalive
    });
    if (!response.ok) throw new Error(`Unreal 상태 연결 실패 (${response.status})`);
    return response.json();
  }
  async function sync() {
    const run = window.getStation3DState?.()?.activeJobId || null;
    if (!active || bindPending || boundRun === run) return;
    const version = bindingVersion;
    bindPending = true;
    try {
      await bind(run);
      if (active && version === bindingVersion) {
        boundRun = run;
        status.textContent = run ? 'Unreal 표시 대상 연결됨 · 영상 상태는 플레이어에서 확인' : '공정 대기 · 초기 설비 화면';
      }
    } catch (error) {
      if (active && version === bindingVersion) status.textContent = error.message;
    } finally { bindPending = false; }
  }
  async function disable() {
    active = false; bindingVersion++; boundRun = undefined;
    clearInterval(timer); layer.hidden = true; frame.removeAttribute('src');
    stage.classList.remove('unreal-active');
    button.setAttribute('aria-pressed', 'false'); button.textContent = 'Unreal 3D';
    try { await bind(null); } catch (error) { notify(error.message); }
  }
  async function enable({silent = false} = {}) {
    if (active) return;
    button.disabled = true;
    try {
      config = await fetch('/api/integrations/unreal/config').then(async response => {
        if (!response.ok) throw new Error('Unreal 연결 설정을 확인해 주세요.');
        return response.json();
      });
      const player = playerUrlForPage(config.player_url, location.href);
      if (!player) throw new Error('Unreal 엔진·Pixel Streaming 실행 후 플레이어 주소를 설정해 주세요.');
      active = true; bindingVersion++; layer.hidden = false;
      stage.classList.add('unreal-active'); frame.src = player;
      status.textContent = 'Unreal 플레이어 연결 중 · 영상을 시작해 주세요.';
      button.setAttribute('aria-pressed', 'true'); button.textContent = '표준 3D로 전환';
      await sync(); timer = setInterval(sync, 500);
    } catch (error) {
      if (active) await disable();
      if (!silent) notify(error.message);
      button.title = error.message;
    } finally { button.disabled = false; }
  }
  button.addEventListener('click', async () => {
    if (active) return disable();
    await enable();
  });
  window.addEventListener('station-frame', sync);
  window.addEventListener('station-reset', () => {
    active = false; bindingVersion++; clearInterval(timer);
    bind(null, true).catch(() => {});
  });
  // Unreal is the primary renderer when its local player is available.  The
  // Three.js view remains an automatic fallback for ordinary web-only runs.
  enable({silent: true});
}
