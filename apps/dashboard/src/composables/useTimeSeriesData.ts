import { computed, onBeforeUnmount, unref, watch, type MaybeRef } from 'vue'
import { useTimeSeriesDataStore } from '@/stores/timeSeriesDataStore'

// Opt-in helper for any component that needs render-ready time-series data.
// Non-chart widgets are free to use another data contract entirely.
export function useTimeSeriesData(
  consumerId: MaybeRef<string>,
  signals: MaybeRef<string[]>,
) {
  const timeSeriesDataStore = useTimeSeriesDataStore()

  watch([() => unref(consumerId), () => unref(signals)], ([id, signalIds]) => {
    timeSeriesDataStore.registerConsumer(id, signalIds)
  }, { immediate: true, deep: true })

  onBeforeUnmount(() => {
    timeSeriesDataStore.unregisterConsumer(unref(consumerId))
  })

  return {
    snapshot: computed(() => timeSeriesDataStore.getSnapshot(unref(signals))),
    refresh: () => timeSeriesDataStore.refresh(),
  }
}
