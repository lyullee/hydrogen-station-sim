import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const main = fs.readFileSync(new URL('../web/saga-bridge.js', import.meta.url), 'utf8');
const sensor = fs.readFileSync(new URL('../web/sensor-workbench.js', import.meta.url), 'utf8');

test('assistants retain separate APIs and share the digital-twin provider', () => {
  assert.match(main, /\/assistants\/main\/stream/);
  assert.match(sensor, /\/assistants\/sensors\/\$\{encodeURIComponent\(tag\)\}\/stream/);
  for (const source of [main, sensor]) {
    assert.match(source, /window\.digitalTwinProvider\.get/);
    assert.match(source, /window\.digitalTwinProvider\.set/);
  }
});

test('shared preference migrates legacy settings and synchronizes mounted controls', () => {
  const values = new Map([['h2station.main-assistant.provider', 'groq'],
    ['h2station.sensor-assistant.provider', 'service_hub'], ['saga.provider', 'untouched']]);
  const selects = [{value: ''}, {value: ''}];
  const listeners = new Map();
  const window = {addEventListener: (event, callback) => listeners.set(event, callback)};
  vm.runInNewContext(fs.readFileSync(new URL('../web/assistant-provider.js', import.meta.url), 'utf8'), {
    window, document: {querySelectorAll: () => selects},
    localStorage: {getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value)},
  });
  assert.equal(window.digitalTwinProvider.get(), 'groq');
  window.digitalTwinProvider.set('service_hub');
  assert.deepEqual(selects.map(item => item.value), ['service_hub', 'service_hub']);
  values.set('h2station.digital-twin.provider', 'groq');
  listeners.get('storage')({key: 'h2station.digital-twin.provider'});
  assert.deepEqual(selects.map(item => item.value), ['groq', 'groq']);
  assert.equal(values.get('saga.provider'), 'untouched');
});
