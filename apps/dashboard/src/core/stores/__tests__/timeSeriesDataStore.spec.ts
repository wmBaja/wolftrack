import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

import { RingBuffer, useLiveDataStore } from '@/core/stores/liveDataStore'
import { useTimeSeriesDataStore } from '@/core/stores/timeSeriesDataStore'

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

  it('advances the chart reset revision for each live data batch', () => {
    const timeSeries = useTimeSeriesDataStore()
    const liveData = useLiveDataStore()

    const beforeBatch = timeSeries.getSnapshot(['Vehicle.speed'])
    liveData.dataVersion++
    const afterBatch = timeSeries.getSnapshot(['Vehicle.speed'])

    expect(afterBatch.revision).toBe(beforeBatch.revision + 1)
  })

  it('returns source-neutral per-signal samples without a chart render model', () => {
    const timeSeries = useTimeSeriesDataStore()
    const liveData = useLiveDataStore()
    const buffer = new RingBuffer(4)
    buffer.push(10, 42)
    liveData.buffers.set('Vehicle.speed', buffer)

    const snapshot = timeSeries.getSnapshot(['Vehicle.speed'])

    expect(snapshot).toMatchObject({ source: 'live', viewport: null, timeOrigin: null })
    expect(snapshot.signals['Vehicle.speed']).toMatchObject({ id: 'Vehicle.speed', name: 'Vehicle.speed', unit: '' })
    expect(Array.from(snapshot.signals['Vehicle.speed']!.timestamps)).toEqual([10])
    expect(Array.from(snapshot.signals['Vehicle.speed']!.values)).toEqual([42])
    expect(snapshot).not.toHaveProperty('model')
  })
})
