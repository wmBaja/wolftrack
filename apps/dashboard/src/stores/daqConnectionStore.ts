import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getVisualizerBase } from '@/lib/visualizer'
import { useDataSourceStore, type LiveSourceConfig } from './dataSourceStore'
import { useLogStore } from './logStore'

export type DaqConnectionState =
  | 'disconnected'
  | 'ready'
  | 'discovering'
  | 'checking'
  | 'connecting'
  | 'connected'
  | 'error'

export type DaqLoggingStatus = 'idle' | 'starting' | 'active' | 'stopping'

export interface DaqTarget {
  host: string
  port: number
  label?: string
  lastUsedAt?: string
}

export interface DaqDiscoveryResult extends DaqTarget {
  id: string
}

interface DaqStorage {
  lastTarget: DaqTarget | null
  recentTargets: DaqTarget[]
}

interface LoggerHealthResponse {
  status: 'healthy' | 'unhealthy'
  session?: boolean
  can_connected?: boolean
  dbc_loaded?: boolean
  error?: string
}

interface LoggerStreamEndpoint {
  transport: string
  host: string
  port: number
  enabled: boolean
}

interface LoggerSessionResponse {
  success: boolean
  message?: string
  error?: string
}

const STORAGE_KEY = 'dashboard-daq-targets'
const DEFAULT_PORT = 5000
const REQUEST_TIMEOUT_MS = 4000
const MAX_RECENT_TARGETS = 5
export const CONNECTION_POLL_INTERVAL_MS = 5000
export const MAX_MISSED_CONNECTION_POLLS = 2
export const AUTO_RECONNECT_INTERVAL_MS = 10000
const LOST_CONNECTION_MESSAGE = 'Lost connection to the DAQ. Check the network connection and reconnect.'

function hasRememberedLiveSource(liveSource: Partial<LiveSourceConfig>) {
  return Boolean(
    liveSource.flask_host
      || liveSource.flask_port
      || liveSource.zmq_host
      || liveSource.zmq_port
  )
}

function normalizeTarget(target: Partial<DaqTarget>): DaqTarget | null {
  const host = `${target.host ?? ''}`.trim()
  const port = Number(target.port)

  if (!host || !Number.isInteger(port) || port <= 0 || port > 65535) {
    return null
  }

  return {
    host,
    port,
    label: target.label?.trim() || undefined,
    lastUsedAt: target.lastUsedAt,
  }
}

function withTimeout(url: string, init?: RequestInit) {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  return fetch(url, { ...init, signal: controller.signal }).finally(() => {
    window.clearTimeout(timeout)
  })
}

async function parseJsonResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    const text = await response.text()
    const snippet = text.trim().slice(0, 120)
    throw new Error(
      response.ok
        ? fallbackMessage
        : `${fallbackMessage} (${response.status}). ${snippet || 'Response was not JSON.'}`
    )
  }

  return await response.json() as T
}

export const useDaqConnectionStore = defineStore('daqConnection', () => {
  const connectionState = ref<DaqConnectionState>('disconnected')
  const error = ref<string | null>(null)
  const target = ref<DaqTarget>({ host: '', port: DEFAULT_PORT })
  const lastTarget = ref<DaqTarget | null>(null)
  const recentTargets = ref<DaqTarget[]>([])
  const discoveries = ref<DaqDiscoveryResult[]>([])
  const health = ref<LoggerHealthResponse | null>(null)
  const loggingActive = ref(false)
  const loggingStatus = ref<DaqLoggingStatus>('idle')
  const reconnectRecoveryActive = ref(false)
  const reconnectInProgress = ref(false)
  const reconnectNextAttemptAt = ref<number | null>(null)
  let daqHealthPollTimer: number | null = null
  let reconnectTimer: number | null = null
  let missedDaqHealthPolls = 0
  let isDaqHealthPollInFlight = false
  let isIntentionalLiveSourceChange = false

  const isConnected = computed(() => connectionState.value === 'connected')
  const isReady = computed(() => connectionState.value === 'ready')
  const hasHealthyDaq = computed(() => {
    return (connectionState.value === 'connected' || connectionState.value === 'ready')
      && health.value?.status === 'healthy'
  })
  const canToggleLogging = computed(() => {
    const nextTarget = normalizeTarget(target.value)

    return Boolean(nextTarget)
      && hasHealthyDaq.value
      && connectionState.value !== 'checking'
      && connectionState.value !== 'connecting'
      && connectionState.value !== 'discovering'
      && loggingStatus.value !== 'starting'
      && loggingStatus.value !== 'stopping'
  })

  function setLoggingStateFromHealth(nextHealth: LoggerHealthResponse | null | undefined) {
    if (typeof nextHealth?.session !== 'boolean') {
      return
    }

    loggingActive.value = nextHealth.session
    loggingStatus.value = nextHealth.session ? 'active' : 'idle'
  }

  function resetDaqHealthPollMisses() {
    missedDaqHealthPolls = 0
  }

  function isDaqHealthPollableState() {
    return connectionState.value === 'ready' || connectionState.value === 'connected'
  }

  function clearDaqConnectionState(nextError: string | null) {
    const dataSourceStore = useDataSourceStore()
    dataSourceStore.liveSource = {
      ...dataSourceStore.liveSource,
      connected: false,
    }
    health.value = null
    loggingActive.value = false
    loggingStatus.value = 'idle'
    connectionState.value = 'disconnected'
    error.value = nextError
  }

  function clearReconnectTimer() {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    reconnectNextAttemptAt.value = null
  }

  function finishReconnectRecovery() {
    clearReconnectTimer()
    reconnectRecoveryActive.value = false
    reconnectInProgress.value = false
  }

  function scheduleReconnectAttempt() {
    if (!reconnectRecoveryActive.value || reconnectInProgress.value || reconnectTimer !== null) {
      return
    }

    reconnectNextAttemptAt.value = Date.now() + AUTO_RECONNECT_INTERVAL_MS
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      reconnectNextAttemptAt.value = null
      void forceReconnect()
    }, AUTO_RECONNECT_INTERVAL_MS)
  }

  async function forceReconnect() {
    if (!reconnectRecoveryActive.value || reconnectInProgress.value) {
      return false
    }

    clearReconnectTimer()
    reconnectInProgress.value = true
    const connected = await connect({ autostart: true })
    reconnectInProgress.value = false

    if (connected) {
      finishReconnectRecovery()
      return true
    }

    scheduleReconnectAttempt()
    return false
  }

  function cancelReconnect() {
    finishReconnectRecovery()
  }

  async function disconnectVisualizerLiveSourceBestEffort() {
    try {
      const visualizerBase = await getVisualizerBase()
      await fetch(`${visualizerBase}/api/live_source/disconnect`, {
        method: 'POST',
      })
    } catch (disconnectError) {
      console.warn('Failed to disconnect visualizer live source after DAQ connection loss:', disconnectError)
    }
  }

  async function markDaqConnectionLost() {
    stopConnectionPolling()
    clearDaqConnectionState(LOST_CONNECTION_MESSAGE)
    reconnectRecoveryActive.value = true
    scheduleReconnectAttempt()
    await disconnectVisualizerLiveSourceBestEffort()
  }

  async function pollDaqHealth() {
    if (isDaqHealthPollInFlight) {
      return
    }

    if (!isDaqHealthPollableState()) {
      if (connectionState.value === 'disconnected' || connectionState.value === 'error') {
        stopConnectionPolling()
      }
      return
    }

    const nextTarget = normalizeTarget(target.value)
    if (!nextTarget) {
      await markDaqConnectionLost()
      return
    }

    isDaqHealthPollInFlight = true

    try {
      await fetchLoggerHealth(nextTarget)
      resetDaqHealthPollMisses()
      error.value = null
    } catch {
      missedDaqHealthPolls++
      if (missedDaqHealthPolls >= MAX_MISSED_CONNECTION_POLLS) {
        await markDaqConnectionLost()
      }
    } finally {
      isDaqHealthPollInFlight = false
    }
  }

  function startConnectionPolling() {
    if (!isDaqHealthPollableState() || !normalizeTarget(target.value)) {
      return
    }

    if (daqHealthPollTimer !== null) {
      return
    }

    resetDaqHealthPollMisses()
    daqHealthPollTimer = window.setInterval(() => {
      void pollDaqHealth()
    }, CONNECTION_POLL_INTERVAL_MS)
  }

  function stopConnectionPolling() {
    if (daqHealthPollTimer === null) {
      return
    }

    window.clearInterval(daqHealthPollTimer)
    daqHealthPollTimer = null
    resetDaqHealthPollMisses()
    isDaqHealthPollInFlight = false
  }

  async function fetchLoggerHealth(nextTarget: DaqTarget) {
    const loggerBase = `http://${nextTarget.host}:${nextTarget.port}`
    const healthResponse = await withTimeout(`${loggerBase}/health`)
    const healthPayload = await parseJsonResponse<LoggerHealthResponse>(
      healthResponse,
      'DAQ health endpoint returned an unexpected response.'
    )
    health.value = healthPayload
    setLoggingStateFromHealth(healthPayload)

    if (!healthResponse.ok || healthPayload.status !== 'healthy') {
      throw new Error(healthPayload.error || 'DAQ health check failed.')
    }

    return healthPayload
  }

  function applyLiveSourceState(liveSource: Partial<LiveSourceConfig>) {
    const wasConnected = connectionState.value === 'connected'
    const liveTarget = normalizeTarget({
      host: liveSource.flask_host ?? '',
      port: liveSource.flask_port ?? DEFAULT_PORT,
    })

    if (liveTarget) {
      target.value = liveTarget
    }

    if (liveSource.connected) {
      connectionState.value = 'connected'
      error.value = null
      startConnectionPolling()
      return
    }

    if (wasConnected && !isIntentionalLiveSourceChange) {
      void markDaqConnectionLost()
      return
    }

    if (hasRememberedLiveSource(liveSource)) {
      connectionState.value = 'ready'
      error.value = null
      startConnectionPolling()
      return
    }

    connectionState.value = 'disconnected'
    error.value = null
    health.value = null
    loggingActive.value = false
    loggingStatus.value = 'idle'
    stopConnectionPolling()
  }

  function loadPersistedTargets() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (!saved) return

      const parsed = JSON.parse(saved) as Partial<DaqStorage>
      lastTarget.value = parsed.lastTarget ? normalizeTarget(parsed.lastTarget) : null
      recentTargets.value = Array.isArray(parsed.recentTargets)
        ? parsed.recentTargets.map(normalizeTarget).filter((value): value is DaqTarget => value !== null)
        : []

      if (lastTarget.value) {
        target.value = { ...lastTarget.value }
      }
    } catch (storageError) {
      console.error('Failed to load DAQ targets:', storageError)
    }
  }

  function persistTargets() {
    try {
      const payload: DaqStorage = {
        lastTarget: lastTarget.value,
        recentTargets: recentTargets.value,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    } catch (storageError) {
      console.error('Failed to persist DAQ targets:', storageError)
    }
  }

  function rememberTarget(nextTarget: DaqTarget) {
    const timestampedTarget: DaqTarget = {
      ...nextTarget,
      lastUsedAt: new Date().toISOString(),
    }

    lastTarget.value = timestampedTarget
    recentTargets.value = [
      timestampedTarget,
      ...recentTargets.value.filter(item => !(item.host === timestampedTarget.host && item.port === timestampedTarget.port)),
    ].slice(0, MAX_RECENT_TARGETS)
    target.value = { ...timestampedTarget }
    persistTargets()
  }

  function selectTarget(nextTarget: DaqTarget) {
    target.value = { ...nextTarget }
    error.value = null
  }

  async function fetchVisualizerLiveSource() {
    const dataSourceStore = useDataSourceStore()
    await dataSourceStore.fetchLiveSource()
    applyLiveSourceState(dataSourceStore.liveSource)

    const nextTarget = normalizeTarget(target.value)
    if (!nextTarget) {
      return
    }

    try {
      await fetchLoggerHealth(nextTarget)
      error.value = null
    } catch (healthError) {
      if (connectionState.value === 'connected' || connectionState.value === 'connecting') {
          if (healthError instanceof DOMException && healthError.name === 'AbortError') {
            error.value = 'DAQ request timed out. Check the host, port, and network connection.'
          } else {
            error.value = healthError instanceof Error ? healthError.message : String(healthError)
          }
      }
    }
  }

  async function discoverServices() {
    if (!window.electronAPI?.discoverDaqServices) {
      connectionState.value = 'error'
      error.value = 'mDNS discovery is unavailable in this build.'
      return
    }

    const previousState = connectionState.value
    connectionState.value = 'discovering'
    error.value = null

    try {
      const services = await window.electronAPI.discoverDaqServices()
      discoveries.value = services
      if (services.length === 0) {
        error.value = 'No DAQ services found. Make sure the logger is running, zeroconf is installed on the DAQ, and both devices are on the same network.'
      }
      connectionState.value = previousState === 'connected' || previousState === 'ready'
        ? previousState
        : 'disconnected'
    } catch (discoverError) {
      connectionState.value = 'error'
      error.value = discoverError instanceof Error ? discoverError.message : String(discoverError)
    }
  }

  async function connect(options?: { autostart?: boolean }) {
    const autostart = options?.autostart ?? true
    const nextTarget = normalizeTarget(target.value)
    if (!nextTarget) {
      connectionState.value = 'error'
      error.value = 'Enter a valid DAQ host and port.'
      return false
    }

    const dataSourceStore = useDataSourceStore()
    const loggerBase = `http://${nextTarget.host}:${nextTarget.port}`
    const canResume = connectionState.value === 'ready' || hasRememberedLiveSource(dataSourceStore.liveSource)
    error.value = null

    try {
      connectionState.value = 'checking'
      await fetchLoggerHealth(nextTarget)

      const streamResponse = await withTimeout(`${loggerBase}/api/stream-endpoint`)
      const streamPayload = await parseJsonResponse<LoggerStreamEndpoint>(
        streamResponse,
        'DAQ stream endpoint lookup failed.'
      )
      if (!streamResponse.ok) {
        throw new Error(`DAQ stream endpoint lookup failed (${streamResponse.status}).`)
      }
      if (!streamPayload.enabled) {
        throw new Error('DAQ live streaming is disabled on the logger.')
      }

      connectionState.value = 'connecting'
      const visualizerBase = await getVisualizerBase()
      const connectResponse = await fetch(`${visualizerBase}/api/live_source/connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          flask_host: nextTarget.host,
          flask_port: nextTarget.port,
          zmq_host: streamPayload.host,
          zmq_port: streamPayload.port,
        }),
      })

      const connectPayload = await parseJsonResponse<{ detail?: string; message?: string }>(
        connectResponse,
        'Visualizer live-source connect returned an unexpected response.'
      )
      if (!connectResponse.ok) {
        throw new Error(connectPayload.detail ?? connectPayload.message ?? 'Failed to connect live source.')
      }

      dataSourceStore.liveSource = {
        connected: true,
        flask_host: nextTarget.host,
        flask_port: nextTarget.port,
        zmq_host: streamPayload.host,
        zmq_port: streamPayload.port,
      }
      rememberTarget(nextTarget)
      connectionState.value = 'connected'
      startConnectionPolling()

      if (!autostart) {
        await stopStreaming()
      }
      finishReconnectRecovery()
      return true
    } catch (connectError) {
      if (connectError instanceof DOMException && connectError.name === 'AbortError') {
        error.value = 'DAQ request timed out. Check the host, port, and network connection.'
      } else {
        error.value = connectError instanceof Error ? connectError.message : String(connectError)
      }
      connectionState.value = canResume ? 'ready' : 'error'
      return false
    }
  }

  async function stopStreaming() {
    isIntentionalLiveSourceChange = true
    try {
      const visualizerBase = await getVisualizerBase()
      const response = await fetch(`${visualizerBase}/api/live_source/stop`, {
        method: 'POST',
      })
      const payload = await parseJsonResponse<{ detail?: string; message?: string }>(
        response,
        'Visualizer live-source stop returned an unexpected response.'
      )
      if (!response.ok) {
        throw new Error(payload.detail ?? payload.message ?? 'Failed to stop live source.')
      }

      const dataSourceStore = useDataSourceStore()
      dataSourceStore.liveSource = {
        ...dataSourceStore.liveSource,
        connected: false,
      }
      connectionState.value = 'ready'
      error.value = null
    } catch (stopError) {
      connectionState.value = 'error'
      error.value = stopError instanceof Error ? stopError.message : String(stopError)
    } finally {
      isIntentionalLiveSourceChange = false
    }
  }

  async function startLogging(filenameTemplate?: string) {
    const nextTarget = normalizeTarget(target.value)
    if (!nextTarget) {
      error.value = 'Enter a valid DAQ host and port.'
      return false
    }
    if (!hasHealthyDaq.value) {
      error.value = 'Connect to a healthy DAQ before starting logging.'
      return false
    }

    const previousActive = loggingActive.value
    const previousStatus = loggingStatus.value
    error.value = null
    loggingActive.value = true
    loggingStatus.value = 'starting'
    const normalizedFilenameTemplate = filenameTemplate?.trim()

    try {
      const response = await withTimeout(`http://${nextTarget.host}:${nextTarget.port}/api/session/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(
          normalizedFilenameTemplate
            ? { filename_template: normalizedFilenameTemplate }
            : {},
        ),
      })
      const payload = await parseJsonResponse<LoggerSessionResponse>(
        response,
        'DAQ logging start returned an unexpected response.'
      )
      if (!response.ok || !payload.success) {
        throw new Error(payload.error ?? payload.message ?? 'Failed to start DAQ logging.')
      }

      await fetchLoggerHealth(nextTarget)
      error.value = null
      return true
    } catch (loggingError) {
      loggingActive.value = previousActive
      loggingStatus.value = previousStatus
      if (loggingError instanceof DOMException && loggingError.name === 'AbortError') {
        error.value = 'DAQ request timed out. Check the host, port, and network connection.'
      } else {
        error.value = loggingError instanceof Error ? loggingError.message : String(loggingError)
      }
      return false
    }
  }

  async function stopLogging() {
    const nextTarget = normalizeTarget(target.value)
    if (!nextTarget) {
      error.value = 'Enter a valid DAQ host and port.'
      return false
    }
    if (!hasHealthyDaq.value) {
      error.value = 'Connect to a healthy DAQ before stopping logging.'
      return false
    }

    const previousActive = loggingActive.value
    const previousStatus = loggingStatus.value
    error.value = null
    loggingActive.value = false
    loggingStatus.value = 'stopping'

    try {
      const response = await withTimeout(`http://${nextTarget.host}:${nextTarget.port}/api/session/stop`, {
        method: 'POST',
      })
      const payload = await parseJsonResponse<LoggerSessionResponse>(
        response,
        'DAQ logging stop returned an unexpected response.'
      )
      if (!response.ok || !payload.success) {
        throw new Error(payload.error ?? payload.message ?? 'Failed to stop DAQ logging.')
      }

      await fetchLoggerHealth(nextTarget)
      error.value = null
      return true
    } catch (loggingError) {
      loggingActive.value = previousActive
      loggingStatus.value = previousStatus
      if (loggingError instanceof DOMException && loggingError.name === 'AbortError') {
        error.value = 'DAQ request timed out. Check the host, port, and network connection.'
      } else {
        error.value = loggingError instanceof Error ? loggingError.message : String(loggingError)
      }
      return false
    }
  }

  async function toggleLogging(filenameTemplate?: string) {
    if (!canToggleLogging.value) {
      return false
    }

    try {
      return loggingActive.value ? await stopLogging() : await startLogging(filenameTemplate)
    } finally {
      try {
        await useLogStore().fetchLogs()
      } catch (logRefreshError) {
        console.warn('Failed to refresh DAQ logs after toggling logging:', logRefreshError)
      }
    }
  }

  async function disconnect() {
    stopConnectionPolling()
    finishReconnectRecovery()
    isIntentionalLiveSourceChange = true
    try {
      const visualizerBase = await getVisualizerBase()
      const response = await fetch(`${visualizerBase}/api/live_source/disconnect`, {
        method: 'POST',
      })
      const payload = await parseJsonResponse<{ detail?: string; message?: string }>(
        response,
        'Visualizer live-source disconnect returned an unexpected response.'
      )
      if (!response.ok) {
        throw new Error(payload.detail ?? payload.message ?? 'Failed to disconnect live source.')
      }

      const dataSourceStore = useDataSourceStore()
      dataSourceStore.liveSource = {
        connected: false,
        flask_host: null,
        flask_port: null,
        zmq_host: null,
        zmq_port: null,
      }
      health.value = null
      loggingActive.value = false
      loggingStatus.value = 'idle'
      connectionState.value = 'disconnected'
      error.value = null
    } catch (disconnectError) {
      connectionState.value = 'error'
      error.value = disconnectError instanceof Error ? disconnectError.message : String(disconnectError)
    } finally {
      isIntentionalLiveSourceChange = false
    }
  }

  function handleVisualizerMessage(payload: unknown) {
    if (!payload || typeof payload !== 'object' || !('type' in payload)) {
      return
    }

    if (payload.type !== 'live_source') {
      return
    }

    applyLiveSourceState(payload as Partial<LiveSourceConfig>)
  }

  loadPersistedTargets()

  // Start polling immediately if we loaded a ready/connected state
  if (connectionState.value === 'ready' || connectionState.value === 'connected') {
    startConnectionPolling()
  }

  return {
    connectionState,
    error,
    target,
    lastTarget,
    recentTargets,
    discoveries,
    health,
    loggingActive,
    loggingStatus,
    reconnectRecoveryActive,
    reconnectInProgress,
    reconnectNextAttemptAt,
    hasHealthyDaq,
    canToggleLogging,
    isConnected,
    isReady,
    loadPersistedTargets,
    selectTarget,
    discoverServices,
    fetchVisualizerLiveSource,
    connect,
    stopStreaming,
    startConnectionPolling,
    stopConnectionPolling,
    startLogging,
    stopLogging,
    toggleLogging,
    disconnect,
    forceReconnect,
    cancelReconnect,
    handleVisualizerMessage,
  }
})
