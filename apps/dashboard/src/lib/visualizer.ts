let backendPort: number | null = null

async function getBackendPort() {
  if (!backendPort) {
    if (window.electronAPI?.getBackendPort) {
      backendPort = await window.electronAPI.getBackendPort()
    } else {
      backendPort = 8000
    }
  }

  return backendPort
}

export async function getVisualizerBase() {
  const port = await getBackendPort()
  return `http://127.0.0.1:${port}`
}

export async function getVisualizerWsUrl() {
  const port = await getBackendPort()
  return `ws://127.0.0.1:${port}/ws/stream`
}
