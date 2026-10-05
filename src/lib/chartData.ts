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

export interface ChartSampleRate {
  id: string
  label: string
  samplesPerSecond: number | null
}

const SERIES_COLORS = ['#e11d48', '#3b82f6', '#22c55e', '#f59e0b', '#a855f7', '#14b8a6', '#ec4899']

function scaleKeyForUnit(unit: string) {
  return `unit:${unit || 'value'}`
}

function toNumberArray(values: ArrayLike<number>) {
  return Array.from(values)
}

// The aligned y columns contain undefined values at timestamps belonging to
// another series. Use only real values so each rate remains signal-specific.
// Sampling frequency is measured over sample intervals rather than by dividing
// endpoint-inclusive point counts by the viewport duration.
export function getVisibleSampleRates(
  model: ChartRenderModel,
  start: number | null | undefined,
  end: number | null | undefined,
): ChartSampleRate[] {
  const duration = (end ?? NaN) - (start ?? NaN)
  if (!Number.isFinite(duration) || duration <= 0) {
    return model.series.map(({ id, label }) => ({ id, label, samplesPerSecond: null }))
  }

  const timestamps = model.data[0] ?? []
  return model.series.map((series, seriesIndex) => {
    const values = model.data[seriesIndex + 1] ?? []
    let firstTimestamp: number | null = null
    let lastTimestamp: number | null = null
    let count = 0

    for (let index = 0; index < timestamps.length; index++) {
      const timestamp = timestamps[index]
      if (timestamp == null || !Number.isFinite(timestamp) || timestamp < start! || timestamp > end! || values[index] == null) continue
      if (firstTimestamp == null) firstTimestamp = timestamp
      lastTimestamp = timestamp
      count++
    }

    const sampleDuration = lastTimestamp == null || firstTimestamp == null
      ? 0
      : lastTimestamp - firstTimestamp

    return {
      id: series.id,
      label: series.label,
      samplesPerSecond: count < 2 || sampleDuration <= 0
        ? null
        : (count - 1) / sampleDuration,
    }
  })
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
