import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useDaqConnectionStore } from './daqConnectionStore'

const REQUEST_TIMEOUT_MS = 4000
const DEFAULT_DAQ_LOG_API_PATH = '/api/logs'
const LOG_FILE_NAME_PATTERN = /^[^/\\]+\.(blf|log)$/

export interface RemoteLogFileInfo {
  name: string
  url: string
  size?: number
  mtime?: number
  active?: boolean
}

function withTimeout(url: string, init?: RequestInit) {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  return fetch(url, { ...init, signal: controller.signal }).finally(() => {
    window.clearTimeout(timeout)
  })
}

function getDaqLogApiBase() {
  const daqConnection = useDaqConnectionStore()
  const host = daqConnection.target.host?.trim()
  const port = Number(daqConnection.target.port)

  if (!host || !Number.isInteger(port) || port <= 0 || port > 65535) {
    throw new Error('Select a DAQ target before browsing logs.')
  }

  return `http://${host}:${port}${DEFAULT_DAQ_LOG_API_PATH}`
}

function normalizeRemoteLog(
  entry: { name?: string; download_url?: string; url?: string; size?: number; mtime?: number; modified?: number; active?: boolean; current?: boolean },
  apiBase: string,
): RemoteLogFileInfo | null {
  const name = entry.name?.trim()
  if (!name) {
    return null
  }

  const rawUrl = entry.download_url ?? entry.url ?? encodeURIComponent(name)
  const url = new URL(rawUrl, `${apiBase}/`).toString()

  const normalized: RemoteLogFileInfo = {
    name,
    url,
  }

  if (typeof entry.size === 'number') {
    normalized.size = entry.size
  }

  const modifiedTimestamp = entry.mtime ?? entry.modified
  if (typeof modifiedTimestamp === 'number') {
    normalized.mtime = modifiedTimestamp
  }

  if (typeof entry.active === 'boolean') {
    normalized.active = entry.active
  } else if (typeof entry.current === 'boolean') {
    normalized.active = entry.current
  }

  return normalized
}

export const useLogStore = defineStore('logStore', () => {
  const availableLogs = ref<RemoteLogFileInfo[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const downloadingName = ref<string | null>(null)
  const mutatingName = ref<string | null>(null)

  function isValidLogFilename(filename: string) {
    return filename.trim() === filename && LOG_FILE_NAME_PATTERN.test(filename) && !filename.includes('..')
  }

  async function getResponseError(response: Response, fallback: string) {
    try {
      const payload = await response.json() as { error?: string; detail?: string }
      return payload.error ?? payload.detail ?? fallback
    } catch {
      return fallback
    }
  }

  async function fetchLogs() {
    isLoading.value = true
    error.value = null

    try {
      const apiBase = getDaqLogApiBase()
      const response = await withTimeout(apiBase)
      if (!response.ok) {
        throw new Error(`Failed to browse DAQ logs (${response.status}).`)
      }

      const payload = await response.json() as
        | Array<{ name?: string; download_url?: string; url?: string; size?: number; mtime?: number; modified?: number; active?: boolean; current?: boolean }>
        | { files?: Array<{ name?: string; download_url?: string; url?: string; size?: number; mtime?: number; modified?: number; active?: boolean; current?: boolean }> }

      const files = Array.isArray(payload) ? payload : payload.files ?? []
      availableLogs.value = files
        .map((entry) => normalizeRemoteLog(entry, apiBase))
        .filter((value): value is RemoteLogFileInfo => value !== null)
    } catch (e: unknown) {
      availableLogs.value = []
      if (e instanceof DOMException && e.name === 'AbortError') {
        error.value = 'DAQ log browser request timed out. Check the host, port, and network connection.'
      } else {
        error.value = e instanceof Error ? e.message : String(e)
      }
    } finally {
      isLoading.value = false
    }
  }

  async function downloadLog(log: RemoteLogFileInfo) {
    if (!window.electronAPI?.downloadFileFromUrl) {
      error.value = 'Log downloading is unavailable in this build.'
      return false
    }

    downloadingName.value = log.name
    error.value = null

    try {
      return await window.electronAPI.downloadFileFromUrl(log.url, log.name)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
      return false
    } finally {
      downloadingName.value = null
    }
  }

  async function deleteLog(filename: string) {
    if (!isValidLogFilename(filename)) {
      error.value = 'Filename must be a .blf or .log file name.'
      return false
    }

    mutatingName.value = filename
    error.value = null
    try {
      const apiBase = getDaqLogApiBase()
      const response = await withTimeout(`${apiBase}/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        throw new Error(await getResponseError(response, 'Delete failed.'))
      }
      await fetchLogs()
      return true
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
      return false
    } finally {
      mutatingName.value = null
    }
  }

  async function renameLog(filename: string, newName: string) {
    if (!isValidLogFilename(newName)) {
      error.value = 'New filename must be a .blf or .log file name.'
      return false
    }

    mutatingName.value = filename
    error.value = null
    try {
      const apiBase = getDaqLogApiBase()
      const response = await withTimeout(`${apiBase}/${encodeURIComponent(filename)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName }),
      })
      if (!response.ok) {
        throw new Error(await getResponseError(response, 'Rename failed.'))
      }
      await fetchLogs()
      return true
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
      return false
    } finally {
      mutatingName.value = null
    }
  }

  return {
    availableLogs,
    isLoading,
    error,
    downloadingName,
    mutatingName,
    fetchLogs,
    downloadLog,
    deleteLog,
    renameLog,
    isValidLogFilename,
  }
})
