import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const main = fs.readFileSync(new URL('../web/saga-bridge.js', import.meta.url), 'utf8');
const sensor = fs.readFileSync(new URL('../web/sensor-workbench.js', import.meta.url), 'utf8');

test('main and sensor assistants use different API and provider namespaces', () => {
  assert.match(main, /\/assistants\/main\/stream/);
  assert.match(sensor, /\/assistants\/sensors\/\$\{encodeURIComponent\(tag\)\}\/stream/);
  assert.match(main, /h2station\.main-assistant\.provider/);
  assert.match(sensor, /h2station\.sensor-assistant\.provider/);
  assert.doesNotMatch(main, /h2station\.sensor-assistant\.provider/);
  assert.doesNotMatch(sensor, /h2station\.main-assistant\.provider/);
  assert.doesNotMatch(main, /saga-analysis\/direct\/stream/);
  assert.doesNotMatch(sensor, /analyze\/direct\/stream/);
});
