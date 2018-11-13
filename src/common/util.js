import { spawn } from 'child_process';

const electron = require('electron');
const readline = require('readline');

const isDevelopment = process.env.NODE_ENV !== 'production';
// eslint-disable-next-line no-undef
const staticPath = isDevelopment ? __static : __dirname.replace(/app\.asar$/, 'static');

const spawnClient = () => new Promise((resolve, _) => {
  setTimeout(() => {
    const client = spawn(
      'python',
      ['./mini_pytor/client.py'],
      { cwd: __dirname },
    );
    electron.ipcRenderer.send('pid-msg', client.pid);
    resolve(client);
  }, 500);
});

const getDirectoryStatus = () => new Promise((resolve, reject) => {
  const directory = spawn('python', ['./mini_pytor/console.py', 'directory'], { cwd: __dirname });
  const relays = [];
  directory.stderr.on('data', (data) => {
    console.log(`stderr: ${data}`);
    reject(data);
  });

  readline.createInterface({
    input: directory.stdout,
    terminal: false,
  }).on('line', (line) => {
    relays.push(line);
  });

  directory.on('close', (code) => {
    console.log(`child process exited with code ${code}`);
    resolve(relays);
  });
});

// convert milliseconds to seconds in string
const seconds = (milliseconds) => {
  if (milliseconds === 1000) {
    return '1 second';
  }
  return `${milliseconds / 1000} seconds`;
};

export {
  isDevelopment, staticPath, spawnClient, seconds, getDirectoryStatus,
};
