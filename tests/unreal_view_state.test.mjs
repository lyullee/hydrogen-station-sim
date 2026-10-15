import test from 'node:test';
import assert from 'node:assert/strict';
import { nextBinding, validPlayerUrl, playerUrlForPage } from '../web/unreal-view-state.mjs';

test('new run and reset invalidate old visual state; repeated run does not', () => {
  const initial = {run_id:null, generation:0};
  const first = nextBinding(initial, 'run-1');
  assert.deepEqual(first, {run_id:'run-1', generation:1});
  assert.deepEqual(nextBinding(first, 'run-1'), first);
  const second = nextBinding(first, 'run-2');
  assert.deepEqual(nextBinding(second, null), {run_id:null, generation:3});
});

test('only credential-free compatible player URLs are allowed', () => {
  assert.equal(validPlayerUrl(null, 'http://localhost:8000'), null);
  assert.equal(validPlayerUrl('http://localhost:8080', 'http://localhost:8000'), 'http://localhost:8080/');
  for (const url of ['javascript:alert(1)', 'data:text/html,x', 'http://user:password@localhost'])
    assert.throws(() => validPlayerUrl(url, 'http://localhost:8000'));
  assert.throws(() => validPlayerUrl('http://localhost:8080', 'https://example.test'));
});

test('external dashboard host replaces loopback in the player URL', () => {
  assert.equal(
    playerUrlForPage('http://127.0.0.1:18080/hrs-player.html', 'http://61.96.174.29:8000/'),
    'http://61.96.174.29:18080/hrs-player.html'
  );
  assert.equal(
    playerUrlForPage('http://127.0.0.1:18080/hrs-player.html', 'http://127.0.0.1:8000/'),
    'http://127.0.0.1:18080/hrs-player.html'
  );
});
