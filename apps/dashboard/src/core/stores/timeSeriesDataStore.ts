import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useDataSourceStore } from '@/core/stores/dataSourceStore'
import { useDbcStore } from '@/core/stores/dbcStore'
import { useLiveDataStore } from '@/core/stores/liveDataStore'
import { useLogDataStore } from '@/core/stores/logDataStore'
import type { SignalDataSnapshot, SignalSeries } from '@wolftrack/plugin-sdk'

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
    const remaining = { ...consumers.value }
    delete remaining[id]
    consumers.value = remaining
  }

  function getLiveBuffers(signalIds: string[]): Record<string, SignalSeries | undefined> {
    // Live buffers are intentionally non-reactive. dataVersion is their
    // invalidation boundary for all time-series consumers.
    void liveDataStore.dataVersion
    const buffers: Record<string, SignalSeries | undefined> = {}
    for (const signal of signalIds) {
      const buffer = liveDataStore.buffers.get(signal)
      if (buffer) {
        const metadata = dbcStore.signals.find(item => item.id === signal)
        buffers[signal] = { id: signal, name: metadata?.name ?? signal, unit: metadata?.unit ?? '', ...buffer.getArrays() }
      }
    }
    return buffers
  }

  function getSnapshot(signalIds: string[]): SignalDataSnapshot {
    const normalizedSignals = uniqueSignals(signalIds)
    if (dataSourceStore.config.source === 'zmq') {
      // Each WebSocket batch advances this revision. Unlike a log viewport,
      // live data has no fixed range to reapply after setData(), so uPlot must
      // recalculate its scales as the ring buffer advances.
      const liveRevision = liveDataStore.dataVersion
      return {
        source: 'live',
        signals: getLiveBuffers(normalizedSignals),
        viewport: null,
        revision: liveRevision,
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
      source: 'logfile',
      signals: Object.fromEntries(normalizedSignals.map((id) => {
        const metadata = dbcStore.signals.find(item => item.id === id)
        const samples = buffers[id]
        return [id, samples ? { id, name: metadata?.name ?? id, unit: metadata?.unit ?? '', ...samples } : undefined]
      })),
      viewport: { start, end: Math.max(start + 0.001, end) },
      revision,
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
