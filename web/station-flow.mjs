// Each dispensing route follows its own measured nozzle and selected bank.
export function stationRouteActive(id, live) {
  if (live.esd) return false;
  if (id === 'fueling') return live.flow1 > 0.01;
  if (id === 'fueling2') return live.flow2 > 0.01;
  if (id === 'compressor') return Boolean(live.recharge);
  if (id.startsWith('recharge:')) return live.recharge === id.slice(9);
  if (id.startsWith('dispatch:')) {
    const bank = id.slice(9);
    return (live.dispatch === bank && live.flow1 > 0.01) ||
      (live.dispatch2 === bank && live.flow2 > 0.01);
  }
  return false;
}
