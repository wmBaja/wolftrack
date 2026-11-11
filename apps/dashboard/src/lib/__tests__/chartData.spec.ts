import { describe, expect, it, vi } from 'vitest'

vi.mock('uplot', () => ({
  default: {
    join: (tables: number[][][]) => {
      const timestamps = [...new Set(tables.flatMap(table => table[0]!))].sort((a, b) => a - b)
      return [
        timestamps,
        ...tables.map(table => timestamps.map(timestamp => {
          const index = table[0]!.indexOf(timestamp)
          return index === -1 ? undefined : table[1]![index]
        })),
      ]
    },
  },
}))

import { buildChartRenderModel, getVisibleSampleRates } from '@/lib/chartData'

describe('buildChartRenderModel', () => {
  it('outer-joins unequal sample times without client-side bucketing', () => {
    const model = buildChartRenderModel(
      ['Vehicle.speed', 'Engine.rpm'],
      {
        'Vehicle.speed': { timestamps: [1, 3], values: [10, 30] },
        'Engine.rpm': { timestamps: [2, 3], values: [20, 40] },
      },
      [
        { id: 'Vehicle.speed', name: 'speed', unit: 'km/h', node: '', message: '' },
        { id: 'Engine.rpm', name: 'rpm', unit: 'rpm', node: '', message: '' },
      ],
    )

    expect(model.data[0]).toEqual([1, 2, 3])
    expect(model.data[1]).toEqual([10, undefined, 30])
    expect(model.data[2]).toEqual([undefined, 20, 40])
  })

  it('groups matching units onto one y scale and keeps stable series order', () => {
    const model = buildChartRenderModel(
      ['a', 'b', 'c'],
      {
        a: { timestamps: [1], values: [1] },
        b: { timestamps: [1], values: [2] },
        c: { timestamps: [1], values: [3] },
      },
      [
        { id: 'a', name: 'A', unit: 'V', node: '', message: '' },
        { id: 'b', name: 'B', unit: 'V', node: '', message: '' },
        { id: 'c', name: 'C', unit: 'A', node: '', message: '' },
      ],
    )

    expect(model.series.map(series => series.id)).toEqual(['a', 'b', 'c'])
    expect(model.series.map(series => series.scaleKey)).toEqual(['unit:V', 'unit:V', 'unit:A'])
    expect(model.scales).toEqual([
      { key: 'unit:V', unit: 'V' },
      { key: 'unit:A', unit: 'A' },
    ])
  })

  it('calculates interval-based sample rates without counting alignment gaps', () => {
    const model = buildChartRenderModel(
      ['a', 'b'],
      {
        a: { timestamps: [1, 2, 4], values: [10, 20, 40] },
        b: { timestamps: [1, 3], values: [100, 300] },
      },
      [
        { id: 'a', name: 'A', unit: '', node: '', message: '' },
        { id: 'b', name: 'B', unit: '', node: '', message: '' },
      ],
    )

    expect(getVisibleSampleRates(model, 1, 4)).toEqual([
      { id: 'a', label: 'A', samplesPerSecond: 2 / 3 },
      { id: 'b', label: 'B', samplesPerSecond: 0.5 },
    ])
    expect(getVisibleSampleRates(model, 1, 3)).toEqual([
      { id: 'a', label: 'A', samplesPerSecond: 1 },
      { id: 'b', label: 'B', samplesPerSecond: 0.5 },
    ])
    expect(getVisibleSampleRates(model, 2, 2)).toEqual([
      { id: 'a', label: 'A', samplesPerSecond: null },
      { id: 'b', label: 'B', samplesPerSecond: null },
    ])
  })
})
