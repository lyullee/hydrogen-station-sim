import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../web/saga-bridge.js', import.meta.url), 'utf8');

function runFrame(autoSetting) {
  const listeners = new Map();
  let analysisCalls = 0;
  const runtime = {
    activeJobId: 'job-1', index: 0,
    result: {
      hazop: {frames: [{active: [{rule_id: 'HZ-TEST'}]}]},
      series: {
        analysis: [{status: 'WARNING', fire_detection: {detector_tags: []}}],
        process_operations: [{relief_open: {}}], active_faults: [[]], time_s: [1],
      },
    },
  };
  const window = {
    getStation3DState: () => runtime,
    addEventListener: (name, callback) => listeners.set(name, callback),
    dispatchEvent: () => {},
    streamStationAnalysis: async () => {
      analysisCalls += 1;
      return {answer: 'ok', time_s: 1, model: 'test'};
    },
  };
  const context = {
    window,
    document: {
      getElementById: () => null,
      querySelector: () => null,
      querySelectorAll: () => [],
    },
    localStorage: {
      getItem: key => key === 'h2station.saga.autoAnalysis' ? autoSetting : null,
      setItem: () => {},
    },
    setInterval: () => 0,
    setTimeout,
    clearTimeout,
    requestAnimationFrame: callback => callback(),
    AbortController,
    Event: class Event { constructor(type) { this.type = type; } },
    console,
  };
  vm.runInNewContext(source, context, {filename: 'saga-bridge.js'});
  listeners.get('station-frame')();
  return analysisCalls;
}

test('regular analysis OFF blocks alarm-triggered automatic LLM calls', () => {
  assert.equal(runFrame('off'), 0);
});

test('regular analysis ON still permits alarm-triggered automatic LLM calls', () => {
  assert.equal(runFrame('on'), 1);
});

test('automatic analysis defaults to OFF when no preference is stored', () => {
  assert.equal(runFrame(null), 0);
});

test('automatic reports stay out of manual question history', () => {
  const inspectable = source.replace(/\}\)\(\);\s*$/, 'window.__test = {addMessage, chatHistory};})();');
  const listeners = new Map();
  const window = {addEventListener: (name, callback) => listeners.set(name, callback)};
  const context = {
    window,
    document: {getElementById: () => null, querySelector: () => null, querySelectorAll: () => []},
    localStorage: {getItem: () => 'off'},
    setInterval: () => 0,
  };
  vm.runInNewContext(inspectable, context, {filename: 'saga-bridge.js'});
  window.__test.addMessage('assistant', '자동 경보 분석', '경보 자동 분석', false, 'automatic');
  window.__test.addMessage('user', '압력은?', '질문');
  window.__test.addMessage('assistant', '현재 20 MPa입니다.', '답변');
  assert.deepEqual(Array.from(window.__test.chatHistory(), row => row.content),
    ['압력은?', '현재 20 MPa입니다.']);
});
