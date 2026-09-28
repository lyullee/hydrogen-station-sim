// Layout only. This script has no connection to process controls or telemetry.
(() => {
  const WIDTH = 1600, HEIGHT = 900;
  function fitDisplay() {
    const width = document.documentElement.clientWidth;
    const height = document.documentElement.clientHeight;
    const scale = Math.min(width / WIDTH, height / HEIGHT);
    document.documentElement.style.setProperty('--wall-scale', String(scale));
    document.documentElement.style.setProperty('--wall-left', `${(width / scale - WIDTH) / 2}px`);
    document.documentElement.style.setProperty('--wall-top', `${(height / scale - HEIGHT) / 2}px`);
  }
  fitDisplay();
  window.addEventListener('resize', fitDisplay);
  window.visualViewport?.addEventListener('resize', fitDisplay);
  document.addEventListener('fullscreenchange', () => {
    fitDisplay();
    const button = document.getElementById('wallFullscreen');
    const active = document.fullscreenElement === document.documentElement;
    button.querySelector('span').textContent = active ? '전체 모니터 종료' : '전체 모니터';
    button.setAttribute('aria-pressed', String(active));
  });
  document.getElementById('wallFullscreen').addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {
      const note = document.createElement('div');
      note.className = 'wall-note'; note.setAttribute('role','status');
      note.textContent = '브라우저의 전체화면(F11)을 사용해 주세요. 화면 맞춤은 자동으로 유지됩니다.';
      document.body.append(note); setTimeout(() => note.remove(), 5000);
    }
  });
})();
