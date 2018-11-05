'use strict';

import { spawn } from "child_process";

const isDevelopment = process.env.NODE_ENV !== "production";
const staticPath = isDevelopment ? __static : __dirname.replace(/app\.asar$/, 'static');
const spawnServers = () => {
  let instances = []
  for (let instance of ['a', 'b', 'c']) {
    const serverInstance = spawn('python', ['./mini_pytor/server.py', instance], { cwd: __dirname });
    instances.push(serverInstance);
  }
  return instances;
}
const spawnClient = website =>
  spawn('python',
      ['./mini_pytor/client.py',
       'localhost', '45000', '0', // server a
       'localhost', '45001', '1', // server b
       'localhost', '45002', '2', // server c
      website],
      { cwd: __dirname });

export { isDevelopment, staticPath, spawnServers, spawnClient };