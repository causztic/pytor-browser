import { spawn } from 'child_process';

const electron = require('electron');

const isDevelopment = process.env.NODE_ENV !== 'production';
// eslint-disable-next-line no-undef
const staticPath = isDevelopment ? __static : __dirname.replace(/app\.asar$/, 'static');

// set up listeners at the start of each spawn ASAP to avoid missing out
const setUpListeners = (instance) => {
  instance.stdout.on('data', (data) => {
    console.log(`stdout: ${data}`);
  });

  instance.stderr.on('data', (data) => {
    console.log(`stderr: ${data}`);
    throw data;
  });

  instance.on('close', (code) => {
    console.log(`child process exited with code ${code}`);
  });
};

const spawnClientAndServers = () => {
  const directory = spawn('python', ['./mini_pytor/directory.py'], { cwd: __dirname });
  setUpListeners(directory);
  electron.ipcRenderer.send('pid-msg', directory.pid);

  return new Promise((resolve, _) => {
    setTimeout(() => {
      ['a', 'b', 'c'].forEach((instance) => {
        const serverInstance = spawn('python', ['./mini_pytor/relay.py', instance], { cwd: __dirname });
        setUpListeners(serverInstance);
        electron.ipcRenderer.send('pid-msg', serverInstance.pid);
      });

      const client = spawn(
        'python',
        ['./mini_pytor/client.py'],
        { cwd: __dirname },
      );
      setUpListeners(client);
      electron.ipcRenderer.send('pid-msg', client.pid);

      resolve();
    }, 3000);
  });
};

// convert milliseconds to seconds in string
const seconds = (milliseconds) => {
  if (milliseconds === 1000) {
    return '1 second';
  }
  return `${milliseconds / 1000} seconds`;
};

export {
  isDevelopment, staticPath, spawnClientAndServers, seconds,
};
