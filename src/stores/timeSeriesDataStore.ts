import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useDataSourceStore } from '@/stores/dataSourceStore'
import { useDbcStore } from '@/stores/dbcStore'
import { useLiveDataStore } from '@/stores/liveDataStore'
import { useLogDataStore } from '@/stores/logDataStore'
import { buildChartRenderModel, type ChartRenderModel, type SignalSamples } from '@/lib/chartData'

export interface TimeSeriesViewport {
  start: number
  end: number
}

export interface TimeSeriesSnapshot {
  model: ChartRenderModel
  viewport: TimeSeriesViewport | null
  resetViewRevision: number
  timeOrigin: number | null
}

function uniqueSignals(signals: string[]) {
  return [...new Set(signals.filter(Boolean))]
}

// This store is the optional, source-agnostic access point for widgets that
// render time-series data. Widgets register needs; this store owns batching,
// source choice, and cache selection without knowing anything about layouts.
export const useTimeSeriesDataStore = defineStore('timeSeriesData', () => {
  const dataSourceStore = useDataSourceStore()
  const dbcStore = useDbcStore()
  const liveDataStore = useLiveDataStore()
  const logDataStore = useLogDataStore()
  const consumers = ref<Record<string, string[]>>({})

  const activeSignals = computed(() => uniqueSignals(Object.values(consumers.value).flat()))
  const isReadyLog = computed(() => {
    return dataSourceStore.config.source === 'logfile'
      && logDataStore.status.status === 'ready'
      && logDataStore.status.end_ts > logDataStore.status.start_ts
  })

  watch([activeSignals, () => dataSourceStore.config.source, () => logDataStore.status.status], ([signals, source]) => {
    liveDataStore.setSubscribedSignals(signals)
    if (source === 'logfile' && isReadyLog.value && signals.length > 0) {
      void logDataStore.requestOverviewData(signals)
    }
  }, { immediate: true })

  watch([
    activeSignals,
    isReadyLog,
    () => logDataStore.queryWindow.start_ts,
    () => logDataStore.queryWindow.end_ts,
    () => logDataStore.isQueryWindowDragging,
  ], ([signals, ready, start, end, isDragging]) => {
    if (!ready || signals.length === 0 || isDragging || end <= start) return
    void logDataStore.requestDetailData(signals)
  }, { immediate: true })

  function registerConsumer(id: string, signals: string[]) {
    consumers.value = { ...consumers.value, [id]: uniqueSignals(signals) }
  }

  function unregisterConsumer(id: string) {
    if (!(id in consumers.value)) return
    const { [id]: _removed, ...remaining } = consumers.value
    consumers.value = remaining
  }

  function getLiveBuffers(signalIds: string[]): Record<string, SignalSamples | undefined> {
    // Live buffers are intentionally non-reactive. dataVersion is their
    // invalidation boundary for all time-series consumers.
    void liveDataStore.dataVersion
    const buffers: Record<string, SignalSamples | undefined> = {}
    for (const signal of signalIds) {
      const buffer = liveDataStore.buffers.get(signal)
      if (buffer) buffers[signal] = buffer.getArrays()
    }
    return buffers
  }

  function getSnapshot(signalIds: string[]): TimeSeriesSnapshot {
    const normalizedSignals = uniqueSignals(signalIds)
    if (dataSourceStore.config.source === 'zmq') {
      return {
        model: buildChartRenderModel(normalizedSignals, getLiveBuffers(normalizedSignals), dbcStore.signals),
        viewport: null,
        resetViewRevision: 0,
        timeOrigin: liveDataStore.sessionStartTimestamp,
      }
    }

    const hasCurrentDetail = !logDataStore.isQueryWindowDragging
      && logDataStore.detailWindow?.start_ts === logDataStore.queryWindow.start_ts
      && logDataStore.detailWindow?.end_ts === logDataStore.queryWindow.end_ts
      && normalizedSignals.every(signal => logDataStore.detailSignalIds[signal])

    const buffers = hasCurrentDetail
      ? logDataStore.detailBuffers
      : logDataStore.overviewBuffers
    const revision = hasCurrentDetail
      ? logDataStore.detailVersion
      : logDataStore.overviewVersion
    void revision

    const start = logDataStore.queryWindow.start_ts
    const selectedEnd = logDataStore.queryWindow.end_ts
    const end = logDataStore.isPlaying
      ? Math.min(selectedEnd, Math.max(start + 0.001, logDataStore.currentTime))
      : selectedEnd

    return {
      model: buildChartRenderModel(normalizedSignals, buffers, dbcStore.signals),
      viewport: { start, end: Math.max(start + 0.001, end) },
      resetViewRevision: revision,
      timeOrigin: logDataStore.status.start_ts,
    }
  }

  async function refresh() {
    const signals = activeSignals.value
    if (dataSourceStore.config.source === 'logfile') {
      await logDataStore.requestDetailData(signals)
    } else {
      liveDataStore.sendSubscription()
    }
  }

  return {
    activeSignals,
    registerConsumer,
    unregisterConsumer,
    getSnapshot,
    refresh,
  }
})
