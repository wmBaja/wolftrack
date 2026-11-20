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

import { buildChartRenderModel } from '@/lib/chartData'
import type { DbcSignal } from '@/stores/dbcStore'

describe('buildChartRenderModel with virtual signals', () => {
  const virtual: DbcSignal = {
    id: 'WTS.Brake_Bias',
    node: 'WT Signals',
    message: 'Custom',
    name: 'Brake_Bias',
    unit: '%',
    is_virtual: true,
    display_name: 'Brake bias',
  }
  const raw: DbcSignal = {
    id: 'Brakes.Front_Psi',
    node: 'ECU',
    message: 'Brakes',
    name: 'Front_Psi',
    unit: 'psi',
  }

  it('uses virtual metadata for label/unit and keeps raw signals working', () => {
    const model = buildChartRenderModel(
      ['WTS.Brake_Bias', 'Brakes.Front_Psi'],
      {
        'WTS.Brake_Bias': { timestamps: [1, 2], values: [50, 55] },
        'Brakes.Front_Psi': { timestamps: [1, 2], values: [100, 120] },
      },
      [raw, virtual],
    )
    expect(model.series[0]).toMatchObject({
      id: 'WTS.Brake_Bias',
      label: 'Brake bias',  // display_name wins
      unit: '%',
      scaleKey: 'unit:%',
    })
    expect(model.series[1]).toMatchObject({ unit: 'psi' })
    expect(Array.from(model.data[0] ?? [])).toEqual([1, 2])
  })

  it('prefers display_name for the series label when present', () => {
    const model = buildChartRenderModel(
      ['WTS.Brake_Bias'],
      { 'WTS.Brake_Bias': { timestamps: [1], values: [50] } },
      [{ ...virtual, display_name: 'Bias (filtered)' }],
    )
    // chartData uses signal?.name; display_name must win for the label
    expect(model.series[0]!.label).toBe('Bias (filtered)')
  })

  it('renders unknown ids as empty series without crashing', () => {
    const model = buildChartRenderModel(
      ['WTS.Deleted', 'Brakes.Front_Psi'],
      { 'Brakes.Front_Psi': { timestamps: [1], values: [1] } },
      [raw],
    )
    expect(model.series).toHaveLength(2)
    expect(model.series[0]!.label).toBe('WTS.Deleted')
  })
})
