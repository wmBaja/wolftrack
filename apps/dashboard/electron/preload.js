const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  backend: {
    getPort: () => ipcRenderer.invoke('get-backend-port'),
    getAuthToken: () => ipcRenderer.invoke('get-backend-auth-token'),
  },
  files: {
    openFile: (filters) => ipcRenderer.invoke('dialog:openFile', filters),
    downloadFromUrl: (url, suggestedFilename) => ipcRenderer.invoke('download:file-from-url', { url, suggestedFilename }),
  },
  daq: {
    discoverServices: () => ipcRenderer.invoke('discover-daq-services'),
  },
})
