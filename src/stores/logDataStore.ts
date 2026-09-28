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
export const LOG_QUERY_TARGET_POINTS_PER_SECOND = 1_000
export const LOG_QUERY_MIN_POINTS = 1_000
export const LOG_QUERY_MAX_POINTS = 100_000

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

  const buffers = ref<Record<string, { timestamps: number[], values: number[] }>>({})
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
    buffers.value = {}
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
        status.value = data
        
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

  async function queryData(
    signals: string[],
    start_ts: number,
    end_ts: number,
    max_points: number = getLogQueryPointBudget(start_ts, end_ts),
  ) {
    if (status.value.status !== 'ready') return
    try {
      const base = await getVisualizerBase()
      const res = await fetch(`${base}/api/logfile/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          signals,
          start_ts,
          end_ts,
          max_points
        })
      })
      if (res.ok) {
        const data = await res.json()
        if (data.data) {
          for (const [sig, buf] of Object.entries(data.data)) {
            buffers.value[sig] = buf as { timestamps: number[], values: number[] }
          }
          dataVersion.value++
        }
      }
    } catch (e) {
      console.error("Error querying log data", e)
    }
  }

  return {
    status,
    buffers,
    dataVersion,
    queryWindow,
    currentTime,
    isPlaying,
    startPollingStatus,
    stopPolling,
    queryData,
    setQueryWindow,
    getQueryPointBudget: getLogQueryPointBudget,
    clearBuffers,
    stopPlayback
  }
})
