const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  sendMessage: (message) => ipcRenderer.send('toMain', message),
  onMessage: (callback) => {
    ipcRenderer.on('fromMain', (event, args) => callback(args))
  },
  openFile: (filters) => ipcRenderer.invoke('dialog:openFile', filters),
  getBackendPort: () => ipcRenderer.invoke('get-backend-port'),
  getBackendAuthToken: () => ipcRenderer.invoke('get-backend-auth-token'),
  discoverDaqServices: () => ipcRenderer.invoke('discover-daq-services'),
  downloadFileFromUrl: (url, suggestedFilename) => ipcRenderer.invoke('download:file-from-url', { url, suggestedFilename }),
})
