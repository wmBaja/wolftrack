import path from "path";
import { promises } from "fs";
import { spawn } from "child_process";
import { ipcMain, dialog, app, BrowserWindow } from "electron";
import { fileURLToPath } from "url";
const DEFAULT_TIMEOUT_MS = 1e4;
const DEFAULT_RETRY_INTERVAL_MS = 100;
function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}
async function waitForBackendReady({
  port,
  fetchImpl = fetch,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  retryIntervalMs = DEFAULT_RETRY_INTERVAL_MS
} = {}) {
  const deadline = Date.now() + timeoutMs;
  const url = `http://127.0.0.1:${port}/api/config`;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const response = await fetchImpl(url);
      if (response.ok) {
        return;
      }
      lastError = new Error(`Backend readiness endpoint returned HTTP ${response.status}.`);
    } catch (error) {
      lastError = error;
    }
    const remainingMs = deadline - Date.now();
    if (remainingMs <= 0) break;
    await delay(Math.min(retryIntervalMs, remainingMs));
  }
  const detail = lastError instanceof Error ? ` ${lastError.message}` : "";
  throw new Error(`Visualizer backend did not become ready within ${timeoutMs} ms.${detail}`);
}
const __filename$1 = fileURLToPath(import.meta.url);
const __dirname$1 = path.dirname(__filename$1);
const isDev = process.env.NODE_ENV === "development";
function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname$1, "preload.js")
    },
    icon: app.isPackaged ? path.join(process.resourcesPath, "dist", "icon.png") : path.join(__dirname$1, "../public/icon.png")
  });
  if (isDev) {
    win.loadURL("http://localhost:3000");
    win.webContents.openDevTools();
  } else {
    const indexPath = app.isPackaged ? path.join(process.resourcesPath, "dist", "index.html") : path.join(__dirname$1, "../dist/index.html");
    win.loadFile(indexPath);
  }
}
ipcMain.handle("dialog:openFile", async (_event, filters) => {
  const result = await dialog.showOpenDialog({ properties: ["openFile"], filters });
  if (result.canceled || result.filePaths.length === 0) return null;
  return result.filePaths[0];
});
ipcMain.handle("download:file-from-url", async (_event, { url, suggestedFilename }) => {
  const result = await dialog.showSaveDialog({
    defaultPath: path.join(app.getPath("downloads"), path.basename(suggestedFilename))
  });
  if (result.canceled || !result.filePath) {
    return false;
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to download file (${response.status}).`);
  }
  const data = Buffer.from(await response.arrayBuffer());
  await promises.writeFile(result.filePath, data);
  return true;
});
async function discoverDaqServices() {
  let Bonjour;
  try {
    ;
    ({ Bonjour } = await import("./index-diSDGU5p.js").then((n) => n.i));
  } catch (error) {
    console.warn("bonjour-service is unavailable:", error);
    return [];
  }
  const bonjour = new Bonjour();
  const browser = bonjour.find({ type: "wolftrack-daq", protocol: "tcp" });
  return await new Promise((resolve) => {
    const services = /* @__PURE__ */ new Map();
    browser.on("up", (service) => {
      const host = service.addresses?.find((address) => /^\d+\.\d+\.\d+\.\d+$/.test(address));
      if (!host) return;
      const id = `${service.name}-${host}-${service.port}`;
      services.set(id, {
        id,
        host,
        port: service.port,
        label: service.name
      });
    });
    setTimeout(() => {
      browser.stop();
      bonjour.destroy();
      resolve(Array.from(services.values()));
    }, 2500);
  });
}
ipcMain.handle("discover-daq-services", async () => {
  return await discoverDaqServices();
});
let backendProcess = null;
let backendPortResolver = null;
let backendPortRejecter = null;
let backendReadinessStarted = false;
let backendReadinessSettled = false;
const backendPortPromise = new Promise((resolve, reject) => {
  backendPortResolver = resolve;
  backendPortRejecter = reject;
});
function resolveBackendPort(port) {
  if (backendReadinessSettled) return;
  backendReadinessSettled = true;
  backendPortResolver(port);
}
function rejectBackendPort(error) {
  if (backendReadinessSettled) return;
  backendReadinessSettled = true;
  backendPortRejecter(error);
}
ipcMain.handle("get-backend-port", async () => {
  return await backendPortPromise;
});
function startBackend() {
  const isWindows = process.platform === "win32";
  const executableName = isWindows ? "wolftrack-visualizer.exe" : "wolftrack-visualizer";
  let backendPath;
  const userDataPath = app.getPath("userData");
  const backendEnv = {
    ...process.env,
    APP_LOG_DIR: path.join(userDataPath, "backend_logs"),
    WOLFTRACK_USER_DATA: userDataPath
  };
  if (app.isPackaged) {
    const backendDir = path.join(process.resourcesPath, "backend");
    backendPath = path.join(backendDir, executableName);
    backendProcess = spawn(backendPath, [], {
      cwd: backendDir,
      env: backendEnv
    });
  } else {
    const visualizerDir = process.env.WOLFTRACK_VISUALIZER_DIR || path.join(__dirname$1, "../../wolftrack-visualizer");
    backendPath = path.join(visualizerDir, "src/app.py");
    backendProcess = spawn("uv", ["run", "python", backendPath], {
      cwd: visualizerDir,
      env: backendEnv
    });
  }
  backendProcess.stdout.on("data", (data) => {
    const output = data.toString();
    console.log(`Backend: ${output}`);
    if (!backendReadinessStarted && output.includes("WOLFTRACK_WS_PORT=")) {
      const match = output.match(/WOLFTRACK_WS_PORT=(\d+)/);
      if (match && match[1]) {
        const port = match[1];
        backendReadinessStarted = true;
        process.env.WOLFTRACK_WS_PORT = port;
        void waitForBackendReady({ port }).then(() => resolveBackendPort(port)).catch((error) => rejectBackendPort(error));
      }
    }
  });
  backendProcess.stderr.on("data", (data) => {
    console.error(`Backend Error: ${data.toString()}`);
  });
  backendProcess.on("error", (error) => {
    rejectBackendPort(error);
  });
  backendProcess.on("exit", (code, signal) => {
    if (!backendReadinessSettled) {
      rejectBackendPort(new Error(
        `Visualizer backend exited before becoming ready (code=${code}, signal=${signal}).`
      ));
    }
  });
}
app.whenReady().then(() => {
  startBackend();
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});
app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
