import { spawn } from 'child_process';

const electron = require('electron');

const isDevelopment = process.env.NODE_ENV !== 'production';
// eslint-disable-next-line no-undef
const staticPath = isDevelopment ? __static : __dirname.replace(/app\.asar$/, 'static');

const spawnClient = () => {
  const clientInstance = spawn(
    'python',
    ['./mini_pytor/client.py'],
    { cwd: __dirname },
  );
  electron.ipcRenderer.send('pid-msg', clientInstance.pid);
  return clientInstance;
};

const spawnServers = () => {
  const directory = spawn('python', ['./mini_pytor/directory.py'], { cwd: __dirname });
  const instances = [];
  let client;

  electron.ipcRenderer.send('pid-msg', directory.pid);
  setTimeout(() => {
    ['a', 'b', 'c'].forEach((instance) => {
      const serverInstance = spawn('python', ['./mini_pytor/relay.py', instance], { cwd: __dirname });
      instances.push(serverInstance);
      electron.ipcRenderer.send('pid-msg', serverInstance.pid);
    });
    client = spawnClient();
  }, 1000);
  return { directory, client, servers: instances };
};

// convert milliseconds to seconds in string
const seconds = (milliseconds) => {
  if (milliseconds === 1000) {
    return '1 second';
  }
  return `${milliseconds / 1000} seconds`;
};

export {
  isDevelopment, staticPath, spawnServers, spawnClient, seconds,
};
