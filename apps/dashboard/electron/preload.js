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
  workspace: {
    load: () => ipcRenderer.invoke('workspace:load'),
    save: (document) => ipcRenderer.invoke('workspace:save', document),
    popoutConfig: () => ipcRenderer.invoke('workspace:popout-config'),
  },
  daq: {
    discoverServices: () => ipcRenderer.invoke('discover-daq-services'),
  },
})
