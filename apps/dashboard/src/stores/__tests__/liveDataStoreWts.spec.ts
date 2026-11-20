import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useLiveDataStore } from '@/stores/liveDataStore'
import { useDbcStore } from '@/stores/dbcStore'

vi.mock('@/lib/visualizer', () => ({
  getVisualizerWsUrl: vi.fn().mockResolvedValue('ws://visualizer.test/ws/stream'),
  getVisualizerBase: vi.fn().mockResolvedValue('http://visualizer.test'),
}))
vi.mock('@/stores/dataSourceStore', () => ({
  useDataSourceStore: () => ({
    config: { source: 'zmq', live_buffer_window_seconds: 15 },
    handleVisualizerMessage: vi.fn(),
  }),
}))
vi.mock('@/stores/daqConnectionStore', () => ({
  useDaqConnectionStore: () => ({ handleVisualizerMessage: vi.fn() }),
}))

class FakeWebSocket {
  static OPEN = 1
  static instances: FakeWebSocket[] = []
  readyState = FakeWebSocket.OPEN
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  sent: unknown[] = []

  constructor() {
    FakeWebSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(JSON.parse(data))
  }

  close() {}

  emit(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) })
  }
}

async function connectedStore() {
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket)
  const store = useLiveDataStore()
  await store.connect()
  const ws = FakeWebSocket.instances[0]!
  ws.onopen?.()
  return { store, ws }
}

describe('liveDataStore live_batch handling', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    FakeWebSocket.instances = []
    vi.unstubAllGlobals()
  })

  it('ingests normal batches', async () => {
    const { store, ws } = await connectedStore()
    ws.emit({
      type: 'live_batch',
      signals: { 'WTS.Total': { timestamps: [10, 11], values: [3, 4] } },
      dropped_batches: 0,
    })
    expect(Array.from(store.buffers.get('WTS.Total')?.getArrays().values ?? [])).toEqual([3, 4])
  })

  it('clock_step clears every buffer then ingests the new-base batch', async () => {
    const { store, ws } = await connectedStore()
    ws.emit({
      type: 'live_batch',
      signals: {
        'WTS.Total': { timestamps: [100, 101], values: [3, 4] },
        'Brakes.Front_Psi': { timestamps: [100, 101], values: [1, 2] },
      },
      dropped_batches: 0,
    })
    expect(store.sessionStartTimestamp).toBe(100)

    ws.emit({
      type: 'live_batch',
      signals: { 'WTS.Total': { timestamps: [98], values: [9] } },
      dropped_batches: 0,
      clock_step: true,
    })

    // old samples (raw and virtual) are gone; the flagged batch's own
    // samples survived on the new time base
    expect(Array.from(store.buffers.get('WTS.Total')?.getArrays().timestamps ?? [])).toEqual([98])
    expect(Array.from(store.buffers.get('WTS.Total')?.getArrays().values ?? [])).toEqual([9])
    expect(Array.from(store.buffers.get('Brakes.Front_Psi')?.getArrays().timestamps ?? [])).toEqual([])
    expect(store.sessionStartTimestamp).toBe(98)
  })

  it('clock_step from older backends: flag absent means no clear', async () => {
    const { store, ws } = await connectedStore()
    ws.emit({
      type: 'live_batch',
      signals: { 'WTS.Total': { timestamps: [100], values: [3] } },
      dropped_batches: 0,
    })
    ws.emit({
      type: 'live_batch',
      signals: { 'WTS.Total': { timestamps: [101], values: [4] } },
      dropped_batches: 0,
    })
    expect(Array.from(store.buffers.get('WTS.Total')?.getArrays().values ?? [])).toEqual([3, 4])
  })

  it('clearSignal removes one buffer and bumps the version', async () => {
    const { store, ws } = await connectedStore()
    ws.emit({
      type: 'live_batch',
      signals: {
        'WTS.Total': { timestamps: [1], values: [3] },
        'WTS.Avg': { timestamps: [1], values: [4] },
      },
      dropped_batches: 0,
    })
    const version = store.dataVersion

    store.clearSignal('WTS.Total')

    expect(store.buffers.has('WTS.Total')).toBe(false)
    expect(store.buffers.has('WTS.Avg')).toBe(true)
    expect(store.dataVersion).toBe(version + 1)

    store.clearSignal('WTS.Total') // no-op for unknown ids
    expect(store.dataVersion).toBe(version + 1)
  })
})

describe('setup filename validation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('accepts .dbc and .wts, rejects traversal and other extensions', () => {
    const dbcStore = useDbcStore()
    expect(dbcStore.isValidSetupFilename('race.wts')).toBe(true)
    expect(dbcStore.isValidSetupFilename('race.dbc')).toBe(true)
    expect(dbcStore.isValidSetupFilename('bad/name.dbc')).toBe(false)
    expect(dbcStore.isValidSetupFilename('x.txt')).toBe(false)
    expect(dbcStore.isValidSetupFilename(' spaced.dbc')).toBe(false)
  })

  it('rename keeps the original extension', () => {
    const dbcStore = useDbcStore()
    expect(dbcStore.isValidRename('race.dbc', 'fast.dbc')).toBe(true)
    expect(dbcStore.isValidRename('race.wts', 'fast.wts')).toBe(true)
    expect(dbcStore.isValidRename('race.dbc', 'race.wts')).toBe(false)
    expect(dbcStore.isValidRename('race.wts', 'race.dbc')).toBe(false)
  })
})
