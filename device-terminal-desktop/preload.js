const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('terminalAPI', {
  create: (opts) => ipcRenderer.invoke('terminal:create', opts),
  onData: (pid, cb) => ipcRenderer.on(`terminal:data:${pid}`, (_e, data) => cb(data)),
  write: (pid, data) => ipcRenderer.send(`terminal:write:${pid}`, data),
  resize: (pid, size) => ipcRenderer.send(`terminal:resize:${pid}`, size),
});
