import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  LOG_OVERVIEW_MAX_POINTS,
  LOG_QUERY_MAX_POINTS,
  getLogQueryPointBudget,
  useLogDataStore,
} from '@/stores/logDataStore'

vi.mock('@/lib/visualizer', () => ({
  getVisualizerBase: vi.fn().mockResolvedValue('http://visualizer.test'),
}))

describe('log data store caches', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('keeps overview and detail data separate', async () => {
    const store = useLogDataStore()
    store.status = { status: 'ready', progress: 100, start_ts: 10, end_ts: 20 }
    store.setQueryWindow(12, 14)
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ data: { speed: { timestamps: [12], values: [55] } } }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await store.requestOverviewData(['speed'])
    await store.requestDetailData(['speed'])

    expect(JSON.parse(fetchMock.mock.calls[0]![1].body).max_points).toBe(LOG_OVERVIEW_MAX_POINTS)
    expect(JSON.parse(fetchMock.mock.calls[1]![1].body).max_points).toBe(getLogQueryPointBudget(12, 14))
    expect(store.overviewBuffers.speed?.values).toEqual([55])
    expect(store.detailBuffers.speed?.values).toEqual([55])
    expect(store.detailWindow).toEqual({ start_ts: 12, end_ts: 14 })
    expect(store.detailSignalIds).toEqual({ speed: true })
  })

  it('caps detailed requests and does not redraw solely for window selection', () => {
    const store = useLogDataStore()
    store.status = { status: 'ready', progress: 100, start_ts: 0, end_ts: 20 }
    const version = store.dataVersion

    store.selectQueryWindow(2, 6)

    expect(store.dataVersion).toBe(version)
    expect(getLogQueryPointBudget(0, 60)).toBe(LOG_QUERY_MAX_POINTS)
  })
})
