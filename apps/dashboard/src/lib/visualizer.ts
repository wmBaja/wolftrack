let backendPort: number | null = null
let authToken: string | null = null

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

async function getBackendAuthToken() {
  if (!authToken) {
    if (window.electronAPI?.getBackendAuthToken) {
      authToken = await window.electronAPI.getBackendAuthToken()
    } else {
      authToken = import.meta.env.VITE_WOLFTRACK_AUTH_TOKEN || ''
    }
  }
  return authToken
}

export async function visualizerFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const token = (await getBackendAuthToken()) || ''
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  return fetch(input, { ...init, headers })
}

export async function getVisualizerBase() {
  const port = await getBackendPort()
  return `http://127.0.0.1:${port}`
}

export async function getVisualizerWsUrl() {
  const port = await getBackendPort()
  const token = (await getBackendAuthToken()) || ''
  return `ws://127.0.0.1:${port}/ws/stream?token=${encodeURIComponent(token)}`
}
