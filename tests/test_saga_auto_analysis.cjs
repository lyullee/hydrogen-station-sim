const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../web/saga-bridge.js'), 'utf8');

function harness(autoEnabled) {
  let now = 100_000;
  const calls = [];
  const events = {};
  const state = {
    activeJobId: 'job-1', index: 0,
    result: { hazop: { frames: [{ active: [{ rule_id: 'HZ-1' }] }] },
      series: { analysis: [{ status: 'WARNING' }], process_operations: [{ relief_open: {} }], active_faults: [[]] } },
  };
  class TestDate extends Date { static now() { return now; } }
  const context = {
    Date: TestDate, AbortController, setInterval() {},
    localStorage: { getItem() { return autoEnabled ? 'on' : 'off'; }, setItem() {} },
    document: { getElementById() { return null; }, querySelector() { return null; } },
    window: { getStation3DState() { return state; }, addEventListener(name, fn) { events[name] = fn; } },
    async fetch(url, options) { calls.push({ url, trigger: JSON.parse(options.body).trigger }); return { ok: true, async json() { return { answer: '평가 완료', time_s: 1 }; } }; },
  };
  vm.runInNewContext(source, context);
  return { state, calls, advance(ms) { now += ms; }, async frame() { events['station-frame'](); await new Promise(setImmediate); } };
}

test('periodic OFF analyzes a new alarm once, then only genuinely new conditions', async () => {
  const app = harness(false);
  await app.frame();
  await app.frame();
  await app.frame();
  assert.equal(app.calls.length, 1);
  app.state.result.hazop.frames[0].active.push({ rule_id: 'HZ-2' });
  await app.frame();
  assert.equal(app.calls.length, 1, 'related rules are grouped during the short cooldown');
  app.advance(10_000);
  await app.frame();
  assert.equal(app.calls.length, 2);
  app.advance(90_000);
  await app.frame();
  assert.equal(app.calls.length, 2);
  assert.deepEqual(app.calls.map(call => call.trigger), ['alarm', 'alarm']);
});

test('periodic ON permits continued assessment of a persistent warning', async () => {
  const app = harness(true);
  await app.frame();
  app.advance(30_000);
  await app.frame();
  assert.equal(app.calls.length, 2);
});
