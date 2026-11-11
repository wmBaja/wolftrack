const DEFAULT_TIMEOUT_MS = 10_000
const DEFAULT_RETRY_INTERVAL_MS = 100

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

/**
 * Wait until the visualizer HTTP server is accepting requests.
 *
 * The child process announces its port before Uvicorn has finished binding it,
 * so resolving the Electron port promise directly from stdout is not enough.
 */
export async function waitForBackendReady({
  port,
  fetchImpl = fetch,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  retryIntervalMs = DEFAULT_RETRY_INTERVAL_MS,
} = {}) {
  const deadline = Date.now() + timeoutMs
  const url = `http://127.0.0.1:${port}/api/config`
  let lastError = null

  while (Date.now() < deadline) {
    try {
      const response = await fetchImpl(url)
      if (response.ok) {
        return
      }

      lastError = new Error(`Backend readiness endpoint returned HTTP ${response.status}.`)
    } catch (error) {
      lastError = error
    }

    const remainingMs = deadline - Date.now()
    if (remainingMs <= 0) break
    await delay(Math.min(retryIntervalMs, remainingMs))
  }

  const detail = lastError instanceof Error ? ` ${lastError.message}` : ''
  throw new Error(`Visualizer backend did not become ready within ${timeoutMs} ms.${detail}`)
}
