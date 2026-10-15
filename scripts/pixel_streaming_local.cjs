// Keep Unreal's streamer/SFU sockets local. In external mode only the browser
// player port is bound publicly (HRS_PIXEL_STREAMING_PUBLIC_PORTS=18080).
const net = require('node:net');
const path = require('node:path');
const listen = net.Server.prototype.listen;
const publicPorts = new Set(
  String(process.env.HRS_PIXEL_STREAMING_PUBLIC_PORTS || '')
    .split(',').map(value => Number(value.trim())).filter(Number.isFinite)
);
net.Server.prototype.listen = function (...args) {
  const port = args[0] && typeof args[0] === 'object' ? Number(args[0].port) : Number(args[0]);
  const host = publicPorts.has(port) ? '0.0.0.0' : '127.0.0.1';
  if (args[0] && typeof args[0] === 'object') args[0] = {...args[0], host};
  else if (typeof args[0] === 'number' || /^\d+$/.test(String(args[0]))) {
    if (typeof args[1] === 'string') args[1] = host;
    else args.splice(1, 0, host);
  }
  return listen.apply(this, args);
};
const entry = path.resolve(process.argv[2]);
process.argv = [process.argv[0], entry, ...process.argv.slice(3)];
require(entry);
