import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useLogDataStore } from '@/stores/logDataStore'

vi.mock('@/lib/visualizer', () => ({
  getVisualizerBase: vi.fn().mockResolvedValue('http://visualizer.test'),
}))

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body }
}

function stubFetch(queue: (() => Promise<unknown>)[]) {
  const fetchMock = vi.fn(async () => {
    const next = queue.shift()
    return next ? next() : jsonResponse(200, { data: {} })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('logDataStore virtual-signal handling', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('marks ids reported pending and retries them with backoff', async () => {
    const fetchMock = stubFetch([
      async () =>
        jsonResponse(200, {
          data: { 'WTS.Total': { timestamps: [], values: [] } },
          pending: ['WTS.Total'],
        }),
      async () =>
        jsonResponse(200, {
          data: { 'WTS.Total': { timestamps: [1], values: [42] } },
          pending: [],
        }),
    ])
    const store = useLogDataStore()
    store.status = { status: 'ready', progress: 100, start_ts: 0, end_ts: 10 }

    await store.requestOverviewData(['WTS.Total'])
    expect(store.pendingSignals['WTS.Total']).toBe(true)

    // backoffed retry fires and resolves the id
    await vi.advanceTimersByTimeAsync(1_000)
    expect(store.pendingSignals['WTS.Total']).toBeUndefined()
    expect(store.overviewBuffers['WTS.Total']?.values).toEqual([42])
    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)
  })

  it('invalidateSignals drops cached entries and schedules a refetch', async () => {
    const fetchMock = stubFetch([
      async () =>
        jsonResponse(200, { data: { 'WTS.Total': { timestamps: [2], values: [7] } }, pending: [] }),
    ])
    const store = useLogDataStore()
    store.status = { status: 'ready', progress: 100, start_ts: 0, end_ts: 10 }
    store.overviewBuffers['WTS.Total'] = { timestamps: [1], values: [1] }
    store.detailBuffers['WTS.Total'] = { timestamps: [1], values: [1] }
    store.detailSignalIds['WTS.Total'] = true

    store.invalidateSignals(['WTS.Total'])

    expect(store.overviewBuffers['WTS.Total']).toBeUndefined()
    expect(store.detailBuffers['WTS.Total']).toBeUndefined()
    expect(store.detailSignalIds['WTS.Total']).toBeUndefined()

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchMock).toHaveBeenCalled()
  })

  it('switching logs cancels pending retry timers', async () => {
    stubFetch([
      async () => jsonResponse(200, { data: {}, pending: ['WTS.Total'] }),
    ])
    const store = useLogDataStore()
    store.status = { status: 'ready', progress: 100, start_ts: 0, end_ts: 10 }
    store.markPending(['WTS.Total'])

    store.clearBuffers()

    // no timer should remain: advancing time must not throw or refetch
    await vi.advanceTimersByTimeAsync(30_000)
    expect(store.pendingSignals['WTS.Total']).toBeUndefined()
  })

  it('status polling marks derived-pending ids', async () => {
    stubFetch([
      async () =>
        jsonResponse(200, {
          status: 'ready',
          progress: 100,
          start_ts: 0,
          end_ts: 10,
          derived: { status: 'computing', progress: 50, pending: ['WTS.Total'] },
        }),
    ])
    const store = useLogDataStore()
    // already ready at the same window: no cache-clear, pending must stick
    store.status = { status: 'ready', progress: 100, start_ts: 0, end_ts: 10 }
    await store.checkStatus()
    expect(store.pendingSignals['WTS.Total']).toBe(true)
  })

  it('accepts older status payloads without the derived block', async () => {
    stubFetch([
      async () => jsonResponse(200, { status: 'ready', progress: 100, start_ts: 0, end_ts: 10 }),
    ])
    const store = useLogDataStore()
    await store.checkStatus()
    expect(store.status.status).toBe('ready')
  })
})
