// Renderer lifetime is separate from simulation lifetime.
export function nextBinding(previous, runId) {
  const run = runId || null;
  return {run_id: run, generation: (previous?.generation || 0) + (previous?.run_id !== run ? 1 : 0)};
}

export function validPlayerUrl(value, base) {
  if (!value) return null;
  const url = new URL(value, base);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password)
    throw new Error('Unreal 플레이어 주소를 확인해 주세요.');
  if (new URL(base).protocol === 'https:' && url.protocol !== 'https:')
    throw new Error('HTTPS 화면에는 HTTPS Unreal 플레이어가 필요합니다.');
  return url.href;
}

export function playerUrlForPage(value, base) {
  const valid = validPlayerUrl(value, base);
  if (!valid) return null;
  const player = new URL(valid);
  const page = new URL(base);
  const loopback = new Set(['127.0.0.1', 'localhost', '[::1]']);
  if (loopback.has(player.hostname) && !loopback.has(page.hostname)) player.hostname = page.hostname;
  return player.href;
}
