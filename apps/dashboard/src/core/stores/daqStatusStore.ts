import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface DaqTargetSummary {
  host: string
  port: number
  label?: string
}

export type DaqLoggingStatus = 'idle' | 'starting' | 'active' | 'stopping'

/** Read-only cross-feature projection published by the data-source feature. */
export const useDaqStatusStore = defineStore('daqStatus', () => {
  const target = ref<DaqTargetSummary>({ host: '', port: 5000 })
  const loggingActive = ref(false)
  const loggingStatus = ref<DaqLoggingStatus>('idle')
  const logRefreshRevision = ref(0)

  function publishStatus(next: {
    target: DaqTargetSummary
    loggingActive: boolean
    loggingStatus: DaqLoggingStatus
  }) {
    target.value = { ...next.target }
    loggingActive.value = next.loggingActive
    loggingStatus.value = next.loggingStatus
  }

  function requestLogRefresh() {
    logRefreshRevision.value++
  }

  return { target, loggingActive, loggingStatus, logRefreshRevision, publishStatus, requestLogRefresh }
})
