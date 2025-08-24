const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const os = require('os');
const pty = require('node-pty');

function createWindow() {
  const win = new BrowserWindow({
    width: 1100,
    height: 720,
    backgroundColor: '#0f1115',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    },
    title: 'Canvas Terminal'
  });
  win.loadFile('renderer/index.html');
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

function defaultShell() {
  const platform = os.platform();
  if (platform === 'win32') {
    const pwsh = process.env.COMSPEC || 'C\\\Windows\\\System32\\\WindowsPowerShell\\\v1.0\\\powershell.exe';
    return [pwsh, ['-NoLogo']];
  }
  const shell = process.env.SHELL || '/bin/bash';
  return [shell, []];
}

ipcMain.handle('terminal:create', (_evt, { cols = 120, rows = 34 } = {}) => {
  const [shell, args] = defaultShell();
  const term = pty.spawn(shell, args, {
    name: 'xterm-256color',
    cols, rows,
    cwd: process.env.HOME,
    env: { ...process.env, TERM: 'xterm-256color', COLORTERM: 'truecolor' }
  });
  const pid = term.pid;
  const channel = `terminal:data:${pid}`;
  term.onData(data => {
    BrowserWindow.getAllWindows().forEach(win => {
      win.webContents.send(channel, data);
    });
  });
  ipcMain.on(`terminal:write:${pid}`, (_e, data) => term.write(data));
  ipcMain.on(`terminal:resize:${pid}`, (_e, size) => term.resize(size.cols, size.rows));
  term.onExit(() => {
    BrowserWindow.getAllWindows().forEach(win => win.webContents.send(channel, '\r\n[process exited]\r\n'));
  });
  return { pid };
});
