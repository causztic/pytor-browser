import { app, BrowserWindow, ipcMain } from 'electron';
import * as path from 'path';
import { format as formatUrl } from 'url';
// eslint-disable-next-line import/no-unresolved
import { isDevelopment } from 'common/util';

const psNode = require('ps-node');

// global reference to mainWindow (necessary to prevent window from being garbage collected)
let mainWindow;
const pids = [];

function createMainWindow() {
  const window = new BrowserWindow({
    show: false,
  });
  window.maximize();

  if (isDevelopment) {
    window.webContents.openDevTools();
    window.loadURL(`http://localhost:${process.env.ELECTRON_WEBPACK_WDS_PORT}`);
  } else {
    window.loadURL(formatUrl({
      pathname: path.join(__dirname, 'index.html'),
      protocol: 'file',
      slashes: true,
    }));
  }

  window.once('ready-to-show', () => {
    window.show();
  });

  window.on('closed', () => {
    mainWindow = null;
  });

  window.webContents.on('devtools-opened', () => {
    window.focus();
    setImmediate(() => {
      window.focus();
    });
  });

  return window;
}

ipcMain.on('pid-msg', (_, arg) => {
  pids.push(arg);
});

ipcMain.on('clear-pids', () => {
  pids.forEach((pid) => {
    psNode.kill(pid);
  });
});

app.on('before-quit', () => {
  pids.forEach((pid) => {
    psNode.kill(pid);
  });
});

// quit application when all windows are closed
app.on('window-all-closed', () => {
  // on macOS it is common for applications to stay open until the user explicitly quits
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  // on macOS it is common to re-create a window even after all windows have been closed
  if (mainWindow === null) {
    mainWindow = createMainWindow();
  }
});

// create main BrowserWindow when electron is ready
app.on('ready', () => {
  mainWindow = createMainWindow();
});
