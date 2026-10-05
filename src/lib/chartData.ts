import uPlot from 'uplot'
import type { DbcSignal } from '@/stores/dbcStore'

export interface SignalSamples {
  timestamps: ArrayLike<number>
  values: ArrayLike<number>
}

export interface ChartSeriesDefinition {
  id: string
  label: string
  unit: string
  color: string
  scaleKey: string
}

export interface ChartScaleDefinition {
  key: string
  unit: string
}

export interface ChartRenderModel {
  data: uPlot.AlignedData
  series: ChartSeriesDefinition[]
  scales: ChartScaleDefinition[]
  structureKey: string
}

const SERIES_COLORS = ['#e11d48', '#3b82f6', '#22c55e', '#f59e0b', '#a855f7', '#14b8a6', '#ec4899']

function scaleKeyForUnit(unit: string) {
  return `unit:${unit || 'value'}`
}

function toNumberArray(values: ArrayLike<number>) {
  return Array.from(values)
}

// uPlot's aligned mode requires one shared x column. join() preserves every
// original sample and inserts undefined only where another series has no value.
export function buildChartRenderModel(
  signalIds: string[],
  buffers: Record<string, SignalSamples | undefined>,
  dbcSignals: DbcSignal[],
): ChartRenderModel {
  const metadata = new Map(dbcSignals.map(signal => [signal.id, signal]))
  const series = signalIds.map((id, index) => {
    const signal = metadata.get(id)
    const unit = signal?.unit ?? ''
    return {
      id,
      label: signal?.name || id,
      unit,
      color: SERIES_COLORS[index % SERIES_COLORS.length]!,
      scaleKey: scaleKeyForUnit(unit),
    }
  })

  const scales = [...new Map(series.map(item => [item.scaleKey, {
    key: item.scaleKey,
    unit: item.unit,
  }])).values()]

  const tables: uPlot.AlignedData[] = signalIds.map(id => {
    const buffer = buffers[id]
    if (!buffer) return [[], []]
    return [toNumberArray(buffer.timestamps), toNumberArray(buffer.values)]
  })

  const data: uPlot.AlignedData = tables.length === 0
    ? [[]]
    : tables.length === 1
      ? tables[0]!
      : uPlot.join(tables)

  return {
    data,
    series,
    scales,
    structureKey: series.map(item => `${item.id}:${item.scaleKey}`).join('|'),
  }
}
