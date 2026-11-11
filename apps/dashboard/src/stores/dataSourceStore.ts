import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getVisualizerBase } from '@/lib/visualizer'

export type DataSourceMode = 'zmq' | 'logfile'
export type DataSourceStatus = 'stopped' | 'running' | 'loading' | 'error'

export interface DataSourceConfig {
  source: DataSourceMode
  log_file: string | null
  dbc_file: string | null
  playback_speed: number
  live_buffer_window_seconds: number
}

export interface LiveSourceConfig {
  connected: boolean
  flask_host: string | null
  flask_port: number | null
  zmq_host: string | null
  zmq_port: number | null
}

interface VisualizerStatusPayload {
  type: 'status'
  status: DataSourceStatus
  source?: DataSourceMode
  detail?: string | null
}

interface LiveSourceStatusPayload {
  type: 'live_source'
  connected: boolean
  flask_host: string | null
  flask_port: number | null
  zmq_host: string | null
  zmq_port: number | null
}

export const DEFAULT_LIVE_BUFFER_WINDOW_SECONDS = 15

export function normalizeLiveBufferWindowSeconds(value: unknown): number {
  const parsed = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return DEFAULT_LIVE_BUFFER_WINDOW_SECONDS
  }

  return parsed
}

function normalizeDataSourceConfig(value: unknown): DataSourceConfig {
  const raw = value as Partial<DataSourceConfig> | null | undefined

  return {
    source: raw?.source === 'logfile' ? 'logfile' : 'zmq',
    log_file: raw?.log_file ?? null,
    dbc_file: raw?.dbc_file ?? null,
    playback_speed: typeof raw?.playback_speed === 'number' ? raw.playback_speed : 0.0,
    live_buffer_window_seconds: normalizeLiveBufferWindowSeconds(raw?.live_buffer_window_seconds),
  }
}

export const useDataSourceStore = defineStore('dataSource', () => {
  const status = ref<DataSourceStatus>('stopped')
  const error = ref<string | null>(null)
  const config = ref<DataSourceConfig>({
    source: 'zmq',
    log_file: null,
    dbc_file: null,
    playback_speed: 0.0,
    live_buffer_window_seconds: DEFAULT_LIVE_BUFFER_WINDOW_SECONDS,
  })

  const dbcSignals = ref<{ id: string, message: string, name: string, unit: string }[]>([])
  const liveSource = ref<LiveSourceConfig>({
    connected: false,
    flask_host: null,
    flask_port: null,
    zmq_host: null,
    zmq_port: null,
  })

  async function fetchSignals(): Promise<void> {
    try {
      const baseUrl = await getVisualizerBase()
      const res = await fetch(`${baseUrl}/api/signals`)
      if (!res.ok) return
      const data = await res.json()
      dbcSignals.value = data.signals || []
    } catch (e) {
      console.error('Failed to fetch signals', e)
    }
  }

  async function fetchConfig(): Promise<void> {
    try {
      const baseUrl = await getVisualizerBase()
      const res = await fetch(`${baseUrl}/api/config`)
      if (!res.ok) throw new Error(`Failed to fetch config: ${res.statusText}`)
      const data = await res.json()
      config.value = normalizeDataSourceConfig(data)
      status.value = config.value.source === 'logfile' ? 'running' : liveSource.value.connected ? 'running' : 'stopped'
      if (config.value.dbc_file) {
        await fetchSignals()
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
      status.value = 'error'
    }
  }

  async function fetchLiveSource(): Promise<void> {
    try {
      const baseUrl = await getVisualizerBase()
      const res = await fetch(`${baseUrl}/api/live_source`)
      if (!res.ok) throw new Error(`Failed to fetch live source: ${res.statusText}`)

      liveSource.value = await res.json()
      if (liveSource.value.connected) {
        status.value = 'running'
      } else if (status.value !== 'error') {
        status.value = config.value.source === 'logfile' ? status.value : 'stopped'
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
      status.value = 'error'
    }
  }

  async function applyConfig(
    update: Partial<DataSourceConfig>,
    files?: { logFileBlob: File | null }
  ): Promise<void> {
    status.value = 'loading'
    error.value = null
    try {
      const payload = normalizeDataSourceConfig({ ...config.value, ...update })

      const formData = new FormData()
      formData.append('source', payload.source)
      formData.append('playback_speed', payload.playback_speed.toString())
      formData.append('live_buffer_window_seconds', payload.live_buffer_window_seconds.toString())

      if (files?.logFileBlob) {
        formData.append('log_file_upload', files.logFileBlob)
      } else if (payload.log_file) {
        formData.append('existing_log', payload.log_file)
      }

      const baseUrl = await getVisualizerBase()
      const res = await fetch(`${baseUrl}/api/upload_config`, {
        method: 'POST',
        body: formData,
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail ?? 'Unknown error')
      config.value = payload
      status.value = payload.source === 'logfile' ? 'running' : liveSource.value.connected ? 'running' : 'stopped'
      await fetchSignals()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
      status.value = 'error'
    }
  }

  async function stop(): Promise<void> {
    status.value = 'loading'
    error.value = null
    try {
      const baseUrl = await getVisualizerBase()
      await fetch(`${baseUrl}/api/stop`, { method: 'POST' })
      status.value = 'stopped'
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
      status.value = 'error'
    }
  }

  function handleVisualizerMessage(payload: unknown) {
    if (!payload || typeof payload !== 'object' || !('type' in payload)) {
      return
    }

    if (payload.type === 'status') {
      const statusPayload = payload as VisualizerStatusPayload
      status.value = statusPayload.status
      error.value = statusPayload.status === 'error' ? statusPayload.detail ?? 'Visualizer stream error' : null
      return
    }

    if (payload.type === 'live_source') {
      const livePayload = payload as LiveSourceStatusPayload
      liveSource.value = {
        connected: livePayload.connected,
        flask_host: livePayload.flask_host,
        flask_port: livePayload.flask_port,
        zmq_host: livePayload.zmq_host,
        zmq_port: livePayload.zmq_port,
      }
      if (!livePayload.connected && config.value.source === 'zmq' && status.value !== 'error') {
        status.value = 'stopped'
      }
    }
  }

  return {
    status,
    error,
    config,
    dbcSignals,
    liveSource,
    fetchConfig,
    fetchLiveSource,
    applyConfig,
    stop,
    fetchSignals,
    handleVisualizerMessage,
  }
})
