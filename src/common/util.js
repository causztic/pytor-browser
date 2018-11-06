import { spawn } from 'child_process';

const electron = require('electron');

const isDevelopment = process.env.NODE_ENV !== 'production';
// eslint-disable-next-line no-undef
const staticPath = isDevelopment ? __static : __dirname.replace(/app\.asar$/, 'static');

const spawnServers = () => {
  const instances = [];
  ['a', 'b', 'c'].forEach((instance) => {
    const serverInstance = spawn('python', ['./mini_pytor/server.py', instance], { cwd: __dirname });
    instances.push(serverInstance);
    electron.ipcRenderer.send('pid-msg', serverInstance.pid);
  });
  return instances;
};

const spawnClient = (website) => {
  const clientInstance = spawn('python',
    ['./mini_pytor/client.py',
      'localhost', '45000', '0', // server a
      'localhost', '45001', '1', // server b
      'localhost', '45002', '2', // server c
      website],
    { cwd: __dirname });
  electron.ipcRenderer.send('pid-msg', clientInstance.pid);
  return clientInstance;
};

export {
  isDevelopment, staticPath, spawnServers, spawnClient,
};
