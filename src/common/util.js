'use strict';

import { spawn } from "child_process";

const isDevelopment = process.env.NODE_ENV !== "production";
const staticPath = isDevelopment ? __static : __dirname.replace(/app\.asar$/, 'static');
const spawnServers = () => {
  spawn('python', ['./mini_pytor/server.py', 'a'], { cwd: __dirname });
  spawn('python', ['./mini_pytor/server.py', 'b'], { cwd: __dirname });
  spawn('python', ['./mini_pytor/server.py', 'c'], { cwd: __dirname });
}
const spawnClient  = (website) => {
  return spawn('python',
      ['./mini_pytor/client.py',
       'localhost', '45000', '0', // server a
       'localhost', '45001', '1', // server b
       'localhost', '45002', '2', // server c
      website],
      { cwd: __dirname });
}

export { isDevelopment, staticPath, spawnServers, spawnClient };