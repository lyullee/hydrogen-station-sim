// Local pilot: keep every signalling listener on loopback until deployment is designed.
const net = require('node:net');
const path = require('node:path');
const listen = net.Server.prototype.listen;
net.Server.prototype.listen = function (...args) {
  if (args[0] && typeof args[0] === 'object') args[0] = {...args[0], host:'127.0.0.1'};
  else if (typeof args[0] === 'number' || /^\d+$/.test(String(args[0]))) {
    if (typeof args[1] === 'string') args[1] = '127.0.0.1';
    else args.splice(1, 0, '127.0.0.1');
  }
  return listen.apply(this, args);
};
const entry = path.resolve(process.argv[2]);
process.argv = [process.argv[0], entry, ...process.argv.slice(3)];
require(entry);
