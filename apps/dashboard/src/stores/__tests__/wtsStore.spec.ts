import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWtsStore } from '@/stores/wtsStore'
import { useDbcStore } from '@/stores/dbcStore'
import { useLogDataStore } from '@/stores/logDataStore'
import { useLiveDataStore } from '@/stores/liveDataStore'
import type { VirtualSignalDefinition } from '@/types/wts'

vi.mock('@/lib/visualizer', () => ({
  getVisualizerBase: vi.fn().mockResolvedValue('http://visualizer.test'),
}))

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

const TOTAL: VirtualSignalDefinition = {
  name: 'Total',
  inputs: ['Brakes.Front_Psi', 'Brakes.Rear_Psi'],
  operations: [{ type: 'combine', operator: 'add' }],
  def_hash: 'hash-1',
}

function mockFetch(handlers: Record<string, (req: { url: string; init?: RequestInit }) => unknown>) {
  const calls: { url: string; init?: RequestInit }[] = []
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const request = { url: String(url), init }
    calls.push(request)
    for (const [pattern, handler] of Object.entries(handlers)) {
      if (String(url).includes(pattern)) return handler(request) ?? jsonResponse(200, {})
    }
    return jsonResponse(404, { detail: 'not mocked' })
  })
  vi.stubGlobal('fetch', fetchMock)
  return { fetchMock, calls }
}

describe('wtsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('fetches catalog and definitions', async () => {
    mockFetch({
      '/api/wts/operations': () =>
        jsonResponse(200, { operations: [], combine_operators: ['add'] }),
      '/api/wts/signals': () =>
        jsonResponse(200, { signals: [TOTAL], issues: [], wts_version: 3 }),
    })
    const store = useWtsStore()
    await store.fetchCatalog()
    await store.fetchDefinitions()
    expect(store.catalog?.combine_operators).toEqual(['add'])
    expect(store.definitions).toEqual([TOTAL])
    expect(store.wtsVersion).toBe(3)
  })

  it('treats a missing /api/wts (older backend) as empty, not an error', async () => {
    mockFetch({ '/api/wts/signals': () => jsonResponse(404, { detail: 'no route' }) })
    const store = useWtsStore()
    await store.fetchDefinitions()
    expect(store.definitions).toEqual([])
    expect(store.error).toBeNull()
  })

  it('saves a definition and refreshes definitions + signal list', async () => {
    const { calls } = mockFetch({
      '/api/wts/signals/Total': (req) =>
        req.init?.method === 'PUT'
          ? jsonResponse(200, { signal: 'Total', wts_version: 2, promoted_to: null })
          : jsonResponse(200, { signals: [TOTAL], issues: [], wts_version: 2 }),
      '/api/wts/signals': () => jsonResponse(200, { signals: [TOTAL], issues: [], wts_version: 2 }),
      '/api/signals': () => jsonResponse(200, { signals: [{ id: 'WTS.Total', is_virtual: true }] }),
    })
    const store = useWtsStore()
    const dbcStore = useDbcStore()

    const result = await store.save(TOTAL)

    expect(result.ok).toBe(true)
    const put = calls.find(c => c.init?.method === 'PUT')
    expect(put?.url).toContain('/api/wts/signals/Total')
    expect(JSON.parse(String(put?.init?.body))).toEqual({ definition: TOTAL })
    // signal list refetched for charts
    expect(calls.some(c => c.url.includes('/api/signals'))).toBe(true)
    expect(dbcStore.signals).toEqual([{ id: 'WTS.Total', is_virtual: true }])
  })

  it('returns 422 validation detail without mutating state', async () => {
    const validation = {
      errors: [{ signal: 'Total', code: 'param_missing', message: 'combine requires operator' }],
      warnings: [],
    }
    mockFetch({
      '/api/wts/signals/Total': () => jsonResponse(422, { detail: validation }),
    })
    const store = useWtsStore()

    const result = await store.save(TOTAL)

    expect(result.ok).toBe(false)
    expect(result.validation).toEqual(validation)
    expect(store.isSaving).toBe(false)
  })

  it('surfaces 409 dependents on delete', async () => {
    mockFetch({
      '/api/wts/signals/Total': () =>
        jsonResponse(409, { detail: { dependents: ['WTS.Bias'] } }),
    })
    const store = useWtsStore()

    const result = await store.remove('Total')

    expect(result.ok).toBe(false)
    expect(result.dependents?.dependents).toEqual(['WTS.Bias'])
  })

  it('promotes a legacy dbc without triggering a log re-index', async () => {
    const { fetchMock } = mockFetch({
      '/api/wts/signals/Total': () =>
        jsonResponse(200, { signal: 'Total', wts_version: 2, promoted_to: 'race.wts' }),
      '/api/wts/signals': () => jsonResponse(200, { signals: [TOTAL], issues: [], wts_version: 2 }),
      '/api/signals': () => jsonResponse(200, { signals: [] }),
      '/api/dbc': () =>
        jsonResponse(200, { available: [{ name: 'race.wts', size: 1, mtime: 2, type: 'wts' }], active: 'race.wts' }),
    })
    const store = useWtsStore()
    const dbcStore = useDbcStore()

    const result = await store.save(TOTAL)

    expect(result.promotedTo).toBe('race.wts')
    expect(store.promotionNotice).toContain('race.wts')
    expect(dbcStore.activeDbc).toBe('race.wts')
    // no upload_config / re-index call was made from the frontend
    const urls = fetchMock.mock.calls.map(call => String(call[0]))
    expect(urls.some(url => url.includes('upload_config'))).toBe(false)
    expect(urls.some(url => url.includes('/api/dbc/select'))).toBe(false)
  })

  it('invalidates changed signals in both stores on save', async () => {
    mockFetch({
      '/api/wts/signals/Total': () => jsonResponse(200, { signal: 'Total', wts_version: 2 }),
      '/api/wts/signals': () =>
        jsonResponse(200, { signals: [{ ...TOTAL, def_hash: 'hash-2' }], issues: [], wts_version: 2 }),
      '/api/signals': () => jsonResponse(200, { signals: [] }),
    })
    const store = useWtsStore()
    store.definitions = [TOTAL]  // previous state: hash-1
    const logStore = useLogDataStore()
    logStore.status = { status: 'ready', progress: 100, start_ts: 0, end_ts: 10 }
    logStore.overviewBuffers['WTS.Total'] = { timestamps: [1], values: [1] }
    const liveStore = useLiveDataStore()

    // Seed a live ring buffer through the public-ish map used by the store.
    liveStore.buffers.set('WTS.Total', {
      timestamps: new Float64Array(4),
      values: new Float64Array(4),
      head: 0,
      tail: 0,
      length: 0,
      capacity: 4,
      push() {},
      trim() {},
      getArrays: () => ({ timestamps: new Float64Array(0), values: new Float64Array(0) }),
    } as never)

    await store.save(TOTAL)

    expect(logStore.overviewBuffers['WTS.Total']).toBeUndefined()
    expect(liveStore.buffers.has('WTS.Total')).toBe(false)
    // a retry was scheduled; clean it up so no timer leaks into other tests
    logStore.invalidateSignals([])
  })

  it('computes transitive dependents', async () => {
    setActivePinia(createPinia())
    const store = useWtsStore()
    store.definitions = [
      TOTAL,
      { name: 'Bias', inputs: ['WTS.Total', 'Brakes.Front_Psi'], operations: [] },
      { name: 'Deep', inputs: ['WTS.Bias'], operations: [] },
      { name: 'Other', inputs: ['Brakes.Rear_Psi'], operations: [] },
    ]
    expect(store.dependentsOf('WTS.Total').sort()).toEqual(['WTS.Bias', 'WTS.Deep'])
    // Rear_Psi feeds Total and Other directly; Total feeds Bias; Bias feeds Deep
    expect(store.dependentsOf('Brakes.Rear_Psi').sort()).toEqual([
      'WTS.Bias', 'WTS.Deep', 'WTS.Other', 'WTS.Total',
    ])
    // Front_Psi does not feed Other
    expect(store.dependentsOf('Brakes.Front_Psi').sort()).toEqual([
      'WTS.Bias', 'WTS.Deep', 'WTS.Total',
    ])
  })
})
