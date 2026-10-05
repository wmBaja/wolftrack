import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

vi.mock('uplot', () => ({ default: { join: vi.fn() } }))

import { useLiveDataStore } from '@/stores/liveDataStore'
import { useTimeSeriesDataStore } from '@/stores/timeSeriesDataStore'

describe('time series data store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('batches signal requirements from independent consumers', async () => {
    const timeSeries = useTimeSeriesDataStore()
    const liveData = useLiveDataStore()

    timeSeries.registerConsumer('chart-a', ['Vehicle.speed', 'Engine.rpm'])
    timeSeries.registerConsumer('analysis-panel', ['Engine.rpm', 'Battery.voltage'])
    await nextTick()

    expect(timeSeries.activeSignals).toEqual([
      'Vehicle.speed',
      'Engine.rpm',
      'Battery.voltage',
    ])
    expect(liveData.subscribedSignals).toEqual(timeSeries.activeSignals)

    timeSeries.unregisterConsumer('chart-a')
    await nextTick()

    expect(timeSeries.activeSignals).toEqual(['Engine.rpm', 'Battery.voltage'])
  })
})
