import path from 'path'
import { promises as fs } from 'fs'
import { spawn } from 'child_process'
import { randomBytes } from 'crypto'
import { app, BrowserWindow, ipcMain, dialog } from 'electron'
import { fileURLToPath, pathToFileURL } from 'url'
import { waitForBackendReady } from './backendReadiness.js'

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Check if running in development
const isDev = process.env.NODE_ENV === 'development';
const dockviewPopoutsEnabled = process.env.WOLFTRACK_ENABLE_DOCKVIEW_POPOUTS === 'true';

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: app.isPackaged
      ? path.join(process.resourcesPath, 'dist', 'icon.png')
      : path.join(__dirname, '../public/icon.png')
  });

  const rendererEntry = app.isPackaged
    ? path.join(process.resourcesPath, 'dist', 'index.html')
    : path.join(__dirname, '../dist/index.html')
  const appUrl = isDev ? 'http://localhost:3000/' : pathToFileURL(rendererEntry).href
  const popoutUrl = isDev
    ? 'http://localhost:3000/dockview-popout.html'
    : pathToFileURL(path.join(process.resourcesPath, 'dist', 'dockview-popout.html')).href
  win.webContents.setWindowOpenHandler(({ url }) => ({
    action: url.startsWith(appUrl) || (dockviewPopoutsEnabled && url.startsWith(popoutUrl)) ? 'allow' : 'deny',
  }))

  // In development, load from dev server
  // In production, load from built files
  if (isDev) {
    win.loadURL('http://localhost:3000'); // Adjust port to match your Vue dev server
    win.webContents.openDevTools();
  } else {
    win.loadFile(rendererEntry);
  }
}

ipcMain.handle('dialog:openFile', async (_event, filters) => {
  const result = await dialog.showOpenDialog({ properties: ['openFile'], filters })
  if (result.canceled || result.filePaths.length === 0) return null
  return result.filePaths[0]
})

ipcMain.handle('download:file-from-url', async (_event, { url, suggestedFilename }) => {
  const result = await dialog.showSaveDialog({
    defaultPath: path.join(app.getPath('downloads'), path.basename(suggestedFilename)),
  })

  if (result.canceled || !result.filePath) {
    return false
  }

  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Failed to download file (${response.status}).`)
  }

  const data = Buffer.from(await response.arrayBuffer())
  await fs.writeFile(result.filePath, data)
  return true
})

function getWorkspaceFilePath() {
  return path.join(app.getPath('userData'), 'workspace.json')
}

function isWorkspaceEnvelope(value) {
  return value && typeof value === 'object'
    && value.format === 'wolftrack-workspace'
    && (value.version === 2 || value.version === 3)
    && Array.isArray(value.tabs)
}

ipcMain.handle('workspace:load', async () => {
  const workspacePath = getWorkspaceFilePath()
  const backupPath = `${workspacePath}.bak`
  try {
    return JSON.parse(await fs.readFile(workspacePath, 'utf8'))
  } catch {
    try {
      const backup = await fs.readFile(backupPath, 'utf8')
      const recovered = JSON.parse(backup)
      if (!isWorkspaceEnvelope(recovered)) return null
      await fs.copyFile(backupPath, workspacePath)
      return recovered
    } catch {
      return null
    }
  }
})

ipcMain.handle('workspace:popout-config', async () => ({
  enabled: dockviewPopoutsEnabled,
  url: isDev
    ? 'http://localhost:3000/dockview-popout.html'
    : pathToFileURL(path.join(process.resourcesPath, 'dist', 'dockview-popout.html')).href,
}))

ipcMain.handle('workspace:save', async (_event, value) => {
  if (!isWorkspaceEnvelope(value)) throw new Error('Invalid workspace document')
  const workspacePath = getWorkspaceFilePath()
  const backupPath = `${workspacePath}.bak`
  const temporaryPath = `${workspacePath}.tmp`
  const serialized = JSON.stringify(value)
  let hasLastGoodCopy = false

  try {
    const previous = JSON.parse(await fs.readFile(workspacePath, 'utf8'))
    if (isWorkspaceEnvelope(previous)) {
      await fs.copyFile(workspacePath, backupPath)
      hasLastGoodCopy = true
    }
  } catch {
    // A last-good backup may still be available when the current file is unreadable.
  }

  if (!hasLastGoodCopy) {
    try {
      const backup = JSON.parse(await fs.readFile(backupPath, 'utf8'))
      hasLastGoodCopy = isWorkspaceEnvelope(backup)
    } catch {
      hasLastGoodCopy = false
    }
  }

  await fs.writeFile(temporaryPath, serialized, 'utf8')
  await fs.rename(temporaryPath, workspacePath)
  if (!hasLastGoodCopy) await fs.copyFile(workspacePath, backupPath)
  return true
})

async function discoverDaqServices() {
  let Bonjour

  try {
    ;({ Bonjour } = await import('bonjour-service'))
  } catch (error) {
    console.warn('bonjour-service is unavailable:', error)
    return []
  }

  const bonjour = new Bonjour()
  const browser = bonjour.find({ type: 'wolftrack-daq', protocol: 'tcp' })

  return await new Promise((resolve) => {
    const services = new Map()

    browser.on('up', (service) => {
      const host = service.addresses?.find((address) => /^\d+\.\d+\.\d+\.\d+$/.test(address))
      if (!host) return

      const id = `${service.name}-${host}-${service.port}`
      services.set(id, {
        id,
        host,
        port: service.port,
        label: service.name,
      })
    })

    setTimeout(() => {
      browser.stop()
      bonjour.destroy()
      resolve(Array.from(services.values()))
    }, 2500)
  })
}

ipcMain.handle('discover-daq-services', async () => {
  return await discoverDaqServices()
})

let backendProcess = null;
const backendAuthToken = randomBytes(32).toString('hex')
let backendPortResolver = null;
let backendPortRejecter = null;
let backendReadinessStarted = false;
let backendReadinessSettled = false;
const backendPortPromise = new Promise((resolve, reject) => {
  backendPortResolver = resolve;
  backendPortRejecter = reject;
});

function resolveBackendPort(port) {
  if (backendReadinessSettled) return
  backendReadinessSettled = true
  backendPortResolver(port)
}

function rejectBackendPort(error) {
  if (backendReadinessSettled) return
  backendReadinessSettled = true
  backendPortRejecter(error)
}

ipcMain.handle('get-backend-port', async () => {
  return await backendPortPromise;
});

ipcMain.handle('get-backend-auth-token', async () => backendAuthToken)

function startBackend() {
  const isWindows = process.platform === 'win32';
  const executableName = isWindows ? 'wolftrack-visualizer.exe' : 'wolftrack-visualizer';

  let backendPath;
  const userDataPath = app.getPath('userData');
  const backendEnv = { 
    ...process.env,
    APP_LOG_DIR: path.join(userDataPath, 'backend_logs'),
    WOLFTRACK_USER_DATA: userDataPath,
    WOLFTRACK_AUTH_TOKEN: backendAuthToken
  };

  if (app.isPackaged) {
    // In production, point to the packaged executable
    const backendDir = path.join(process.resourcesPath, 'backend');
    backendPath = path.join(backendDir, executableName);
    backendProcess = spawn(backendPath, [], {
      cwd: backendDir,
      env: backendEnv
    });
  } else {
    // In development, run the python script directly
    const visualizerDir = process.env.WOLFTRACK_VISUALIZER_DIR || path.join(__dirname, '../../visualizer');
    backendPath = path.join(visualizerDir, 'src/app.py');
    backendProcess = spawn('uv', ['run', 'python', backendPath], {
      cwd: visualizerDir,
      env: backendEnv
    });
  }

  backendProcess.stdout.on('data', (data) => {
    const output = data.toString();
    console.log(`Backend: ${output}`);

    // Parse the port if needed by your renderer
    if (!backendReadinessStarted && output.includes('WOLFTRACK_WS_PORT=')) {
      const match = output.match(/WOLFTRACK_WS_PORT=(\d+)/);
      if (match && match[1]) {
        const port = match[1];
        backendReadinessStarted = true
        process.env.WOLFTRACK_WS_PORT = port;
        void waitForBackendReady({ port, token: backendAuthToken })
          .then(() => resolveBackendPort(port))
          .catch((error) => rejectBackendPort(error))
      }
    }
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`Backend Error: ${data.toString()}`);
  });

  backendProcess.on('error', (error) => {
    rejectBackendPort(error)
  })

  backendProcess.on('exit', (code, signal) => {
    if (!backendReadinessSettled) {
      rejectBackendPort(new Error(
        `Visualizer backend exited before becoming ready (code=${code}, signal=${signal}).`
      ))
    }
  })
}

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
