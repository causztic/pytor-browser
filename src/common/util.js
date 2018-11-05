'use strict';

import { spawn } from "child_process";

const isDevelopment = process.env.NODE_ENV !== "production";
const staticPath = isDevelopment ? __static : __dirname.replace(/app\.asar$/, 'static');
const spawnServers = () => {
  for (let instance of ['a', 'b', 'c']) {
    const serverInstance = spawn('python', ['./mini_pytor/server.py', instance], { cwd: __dirname });
    serverInstance.stdout.on('data', (data) => {
      console.log(`stdout: ${data}`);
    });

    serverInstance.stderr.on('data', (data) => {
      console.log(`stderr: ${data}`);
    });

    serverInstance.on('close', (code) => {
      console.log(`child process exited with code ${code}`);
    });
  }
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