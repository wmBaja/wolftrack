// Cross-store invalidation used after WTS mutations (Part 5.6). Lives in
// its own module so wtsStore does not import the data stores directly
// (they import each other freely; this keeps the graph a DAG rooted here).
import { useLiveDataStore } from '@/stores/liveDataStore'
import { useLogDataStore } from '@/stores/logDataStore'

/**
 * Invalidate chart caches for edited/deleted virtual signals (and their
 * dependents) in both modes:
 * - log: drop overview/detail entries; the logDataStore retry machinery
 *   re-requests and shows "calculating…" while the backend recomputes.
 * - live: drop each RingBuffer so old-definition samples never mix with
 *   new, then re-send the subscription.
 */
export function invalidateSignalsEverywhere(signalIds: string[]) {
  if (signalIds.length === 0) return
  const logDataStore = useLogDataStore()
  logDataStore.invalidateSignals(signalIds)
  const liveDataStore = useLiveDataStore()
  for (const id of signalIds) {
    liveDataStore.clearSignal(id)
  }
  liveDataStore.sendSubscription()
}
