import { playerUrlForPage } from './unreal-view-state.mjs';

const stage = document.getElementById('s3Stage');
const tools = document.querySelector('.s3-head-tools');
if (stage && tools) {
  const rendererPreferenceKey = 'hrs-3d-renderer';
  const button = document.createElement('button');
  button.id = 's3UnrealToggle'; button.className = 's3-risk-toggle';
  button.type = 'button'; button.textContent = '렌더러 · 표준 3D';
  button.title = '표준 Web 3D와 Unreal 3D를 전환합니다.';
  button.setAttribute('aria-pressed', 'false');
  tools.insertBefore(button, tools.querySelector('#s3Fullscreen'));

  const layer = document.createElement('div');
  layer.className = 's3-unreal-layer'; layer.hidden = true;
  const toolbar = document.createElement('div'); toolbar.className = 's3-unreal-toolbar';
  toolbar.setAttribute('aria-label', 'Unreal 장면 표시 설정');
  const status = document.createElement('p'); status.className = 's3-unreal-status';
  status.setAttribute('role', 'status');
  const frame = document.createElement('iframe');
  frame.title = 'Unreal 충전소 3D'; frame.allow = 'autoplay; fullscreen';
  layer.append(toolbar, frame, status); stage.append(layer);

  const viewControls = [
    ['roof_cutaway', '캐노피 투시', 's3Roof'],
    ['service_cutaway', '설비 내부', 's3Service'],
    ['vehicle_cutaway', '차량 탱크', 's3VehicleCutaway'],
    ['show_incidents', '사고 연출', null],
    ['show_distance', '위험거리', 's3RiskToggle'],
    ['show_risk', '위험도', 's3RiskLevelToggle'],
    ['show_cameras', 'CCTV', 's3CameraToggle'],
    ['show_detectors', '검지기', 's3DetectorToggle'],
  ];
  let viewState = Object.fromEntries(viewControls.map(([key]) => [key, key === 'show_incidents']));
  const viewButtons = new Map();
  let active = false, boundRun, config, timer, bindPending = false, viewPending = false, viewQueued = false;
  let bindingVersion = 0;
  let requestSerial = Date.now();
  const notify = message => window.notifyOperator?.(message);

  function renderViewControls() {
    for (const [key, control] of viewButtons) {
      control.setAttribute('aria-pressed', String(Boolean(viewState[key])));
      control.classList.toggle('selected', Boolean(viewState[key]));
    }
  }
  async function saveView(patch = {}) {
    viewState = {...viewState, ...patch}; renderViewControls();
    if (viewPending) {
      viewQueued = true;
      return;
    }
    viewPending = true;
    try {
      const response = await fetch('/api/integrations/unreal/session/default/view', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(viewState)
      });
      if (!response.ok) throw new Error(`Unreal 보기 설정 실패 (${response.status})`);
      viewState = await response.json(); renderViewControls();
    } catch (error) { if (active) status.textContent = error.message; }
    finally {
      viewPending = false;
      if (viewQueued) {
        viewQueued = false;
        void saveView();
      }
    }
  }
  for (const [key, label, standardId] of viewControls) {
    const control = document.createElement('button'); control.type = 'button'; control.textContent = label;
    control.dataset.viewOption = key; control.setAttribute('aria-pressed', String(Boolean(viewState[key])));
    control.addEventListener('click', () => {
      const standard = standardId && document.getElementById(standardId);
      if (standard) standard.click();
      else saveView({[key]: !viewState[key]});
    });
    toolbar.append(control); viewButtons.set(key, control);
    if (standardId) document.getElementById(standardId)?.addEventListener('click', () => setTimeout(() => {
      const pressed = document.getElementById(standardId)?.getAttribute('aria-pressed') === 'true';
      saveView({[key]: pressed});
    }, 0));
  }
  renderViewControls();

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
        status.textContent = run ? 'Unreal 표시 대상 연결됨 · 투시·사고 연출 동기화' : '공정 대기 · 초기 설비 화면';
      }
    } catch (error) {
      if (active && version === bindingVersion) status.textContent = error.message;
    } finally { bindPending = false; }
  }
  async function disable({remember = true} = {}) {
    active = false; bindingVersion++; boundRun = undefined;
    clearInterval(timer); layer.hidden = true; frame.removeAttribute('src');
    stage.classList.remove('unreal-active');
    button.setAttribute('aria-pressed', 'false'); button.textContent = '렌더러 · 표준 3D';
    if (remember) localStorage.setItem(rendererPreferenceKey, 'standard');
    try { await bind(null); } catch (error) { notify(error.message); }
  }
  async function enable({silent = false, remember = true} = {}) {
    if (active) return;
    button.disabled = true;
    try {
      const [loadedConfig, loadedView] = await Promise.all([
        fetch('/api/integrations/unreal/config').then(async response => {
          if (!response.ok) throw new Error('Unreal 연결 설정을 확인해 주세요.');
          return response.json();
        }),
        fetch('/api/integrations/unreal/session/default/view').then(response => response.ok ? response.json() : viewState),
      ]);
      config = loadedConfig; viewState = {...viewState, ...loadedView}; renderViewControls();
      const player = playerUrlForPage(config.player_url, location.href);
      if (!player) throw new Error('Unreal 엔진·Pixel Streaming 실행 후 플레이어 주소를 설정해 주세요.');
      active = true; bindingVersion++; layer.hidden = false;
      stage.classList.add('unreal-active'); frame.src = player;
      status.textContent = 'Unreal 플레이어 연결 중 · 영상을 시작해 주세요.';
      button.setAttribute('aria-pressed', 'true'); button.textContent = '렌더러 · Unreal 3D';
      if (remember) localStorage.setItem(rendererPreferenceKey, 'unreal');
      await sync(); timer = setInterval(sync, 500);
    } catch (error) {
      if (active) await disable({remember: false});
      if (!silent) notify(error.message);
      button.title = error.message;
    } finally { button.disabled = false; }
  }
  button.addEventListener('click', async () => active ? disable() : enable());
  window.addEventListener('station-frame', sync);
  window.addEventListener('station-reset', () => disable({remember: false}));
  if (localStorage.getItem(rendererPreferenceKey) !== 'standard') enable({silent: true, remember: false});
}
