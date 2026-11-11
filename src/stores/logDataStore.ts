import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getVisualizerBase } from '@/lib/visualizer'

export interface LogStatus {
  status: 'idle' | 'loading' | 'ready' | 'error'
  progress: number
  start_ts: number
  end_ts: number
}

export interface LogTimeWindow {
  start_ts: number
  end_ts: number
}

// A chart should receive enough points to reproduce common CAN signal rates
// when a user is looking at a short time range, without making a full-day log
// expensive to transfer or render. These limits are deliberately exported so
// a later time-range UI can share and tune the same policy.
export const LOG_QUERY_TARGET_POINTS_PER_SECOND = 2_000
export const LOG_QUERY_MIN_POINTS = 2_000
export const LOG_QUERY_MAX_POINTS = 20_000
export const LOG_OVERVIEW_MAX_POINTS = 3_000

export function getLogQueryPointBudget(startTs: number, endTs: number): number {
  const durationSeconds = Math.max(0, endTs - startTs)
  const requestedPoints = Math.ceil(durationSeconds * LOG_QUERY_TARGET_POINTS_PER_SECOND)

  return Math.min(
    LOG_QUERY_MAX_POINTS,
    Math.max(LOG_QUERY_MIN_POINTS, requestedPoints),
  )
}

export const useLogDataStore = defineStore('logData', () => {
  const status = ref<LogStatus>({
    status: 'idle',
    progress: 0,
    start_ts: 0,
    end_ts: 0
  })

  type LogBuffer = { timestamps: number[], values: number[] }

  // The overview is the complete log at a bounded resolution. It is kept in
  // memory so moving the timeline changes only the uPlot viewport, never the
  // network or data transformation path.
  const overviewBuffers = ref<Record<string, LogBuffer>>({})
  const detailBuffers = ref<Record<string, LogBuffer>>({})
  const overviewVersion = ref(0)
  const detailVersion = ref(0)
  const detailWindow = ref<LogTimeWindow | null>(null)
  const detailSignalIds = ref<Record<string, true>>({})
  const isQueryWindowDragging = ref(false)
  const dataVersion = ref(0)
  // This defaults to the complete log. A time navigator or chart zoom handler
  // can narrow it later without changing the query/rendering contract.
  const queryWindow = ref<LogTimeWindow>({ start_ts: 0, end_ts: 0 })

  const playbackSpeed = ref(0.0)
  const currentTime = ref(0)
  const isPlaying = ref(false)

  let pollInterval: number | null = null
  let reqFrame = 0
  let lastFrameTime = 0
  let overviewController: AbortController | null = null
  let detailController: AbortController | null = null
  let overviewRequestId = 0
  let detailRequestId = 0
  let sessionId = 0

  function clearQueryCaches() {
    overviewController?.abort()
    detailController?.abort()
    overviewController = null
    detailController = null
    overviewRequestId++
    detailRequestId++
    sessionId++
    overviewBuffers.value = {}
    detailBuffers.value = {}
    overviewVersion.value++
    detailVersion.value++
    detailWindow.value = null
    detailSignalIds.value = {}
    isQueryWindowDragging.value = false
  }

  function startPlayback(speed: number) {
    playbackSpeed.value = speed
    if (speed <= 0) {
      isPlaying.value = false
      currentTime.value = status.value.end_ts
      dataVersion.value++
      return
    }

    isPlaying.value = true
    lastFrameTime = performance.now()

    function loop(now: number) {
      if (!isPlaying.value) return

      const dt = (now - lastFrameTime) / 1000
      lastFrameTime = now

      currentTime.value += dt * playbackSpeed.value

      if (currentTime.value >= status.value.end_ts) {
        currentTime.value = status.value.end_ts
        isPlaying.value = false
      }

      dataVersion.value++
      if (isPlaying.value) {
        reqFrame = requestAnimationFrame(loop)
      }
    }

    reqFrame = requestAnimationFrame(loop)
  }

  function clearBuffers() {
    clearQueryCaches()
    isPlaying.value = false
    if (reqFrame) cancelAnimationFrame(reqFrame)
    status.value = { status: 'idle', progress: 0, start_ts: 0, end_ts: 0 }
    queryWindow.value = { start_ts: 0, end_ts: 0 }
    dataVersion.value++
  }

  function setQueryWindow(startTs: number, endTs: number) {
    const logStart = status.value.start_ts
    const logEnd = status.value.end_ts
    const start = Math.max(logStart, Math.min(startTs, logEnd))
    const end = Math.max(start, Math.min(endTs, logEnd))

    queryWindow.value = { start_ts: start, end_ts: end }
  }

  function selectQueryWindow(startTs: number, endTs: number) {
    setQueryWindow(startTs, endTs)
    stopPlayback()
    // Selecting a range is an explicit request to inspect it, rather than to
    // wait for playback to reach it.
    currentTime.value = queryWindow.value.end_ts
  }

  function beginQueryWindowDrag() {
    stopPlayback()
    isQueryWindowDragging.value = true
  }

  function endQueryWindowDrag() {
    isQueryWindowDragging.value = false
  }

  function stopPlayback() {
    isPlaying.value = false
    if (reqFrame) cancelAnimationFrame(reqFrame)
  }

  async function checkStatus() {
    try {
      const base = await getVisualizerBase()
      const res = await fetch(`${base}/api/logfile/status`)
      if (res.ok) {
        const data = await res.json()
        const hasNewReadyLog = data.status === 'ready' && (
          status.value.status !== 'ready'
          || status.value.start_ts !== data.start_ts
          || status.value.end_ts !== data.end_ts
        )
        status.value = data

        if (hasNewReadyLog) clearQueryCaches()

        if (data.status === 'ready' && pollInterval) {
          clearInterval(pollInterval)
          pollInterval = null

          currentTime.value = data.start_ts
          setQueryWindow(data.start_ts, data.end_ts)
          import('./dataSourceStore').then(m => {
            const ds = m.useDataSourceStore()
            startPlayback(ds.config.playback_speed ?? 0.0)
          })
        }
      }
    } catch (e) {
      console.error("Error checking logfile status", e)
    }
  }

  function startPollingStatus() {
    if (pollInterval) clearInterval(pollInterval)
    pollInterval = window.setInterval(checkStatus, 1000)
    checkStatus()
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  async function fetchQuery(
    signals: string[],
    start_ts: number,
    end_ts: number,
    max_points: number,
    target: 'overview' | 'detail',
  ) {
    if (status.value.status !== 'ready' || signals.length === 0 || end_ts <= start_ts) return

    const controller = new AbortController()
    const requestId = target === 'overview' ? ++overviewRequestId : ++detailRequestId
    const requestSession = sessionId
    if (target === 'overview') {
      overviewController?.abort()
      overviewController = controller
    } else {
      detailController?.abort()
      detailController = controller
    }

    try {
      const base = await getVisualizerBase()
      const res = await fetch(`${base}/api/logfile/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          signals,
          start_ts,
          end_ts,
          max_points
        })
      })
      if (res.ok) {
        const data = await res.json()
        const isLatest = target === 'overview'
          ? requestId === overviewRequestId
          : requestId === detailRequestId
        if (controller.signal.aborted || requestSession !== sessionId || !isLatest) return
        if (data.data) {
          const targetBuffers = target === 'overview' ? overviewBuffers : detailBuffers
          for (const [sig, buf] of Object.entries(data.data)) {
            targetBuffers.value[sig] = buf as LogBuffer
          }
          if (target === 'overview') {
            overviewVersion.value++
          } else {
            const extendsCurrentDetail = detailWindow.value?.start_ts === start_ts
              && detailWindow.value?.end_ts === end_ts
            detailWindow.value = { start_ts, end_ts }
            detailSignalIds.value = {
              ...(extendsCurrentDetail ? detailSignalIds.value : {}),
              ...Object.fromEntries(signals.map(signal => [signal, true])),
            }
            detailVersion.value++
          }
          dataVersion.value++
        }
      }
    } catch (e) {
      if (controller.signal.aborted) return
      console.error("Error querying log data", e)
    } finally {
      if (target === 'overview' && overviewController === controller) overviewController = null
      if (target === 'detail' && detailController === controller) detailController = null
    }
  }

  async function requestOverviewData(signals: string[]) {
    const missingSignals = [...new Set(signals)].filter(signal => !overviewBuffers.value[signal])
    if (missingSignals.length === 0) return
    await fetchQuery(
      missingSignals,
      status.value.start_ts,
      status.value.end_ts,
      LOG_OVERVIEW_MAX_POINTS,
      'overview',
    )
  }

  async function requestDetailData(signals: string[]) {
    const { start_ts, end_ts } = queryWindow.value
    await fetchQuery(
      [...new Set(signals)],
      start_ts,
      end_ts,
      getLogQueryPointBudget(start_ts, end_ts),
      'detail',
    )
  }

  return {
    status,
    overviewBuffers,
    detailBuffers,
    overviewVersion,
    detailVersion,
    detailWindow,
    detailSignalIds,
    isQueryWindowDragging,
    dataVersion,
    queryWindow,
    currentTime,
    isPlaying,
    startPollingStatus,
    stopPolling,
    requestOverviewData,
    requestDetailData,
    setQueryWindow,
    selectQueryWindow,
    beginQueryWindowDrag,
    endQueryWindowDrag,
    getQueryPointBudget: getLogQueryPointBudget,
    clearBuffers,
    stopPlayback
  }
})
