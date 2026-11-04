<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import type { Point } from './DashboardGrid.vue'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'
import { getVisibleSampleRates, type ChartRenderModel, type ChartSampleRate } from '@/lib/chartData'

interface Viewport {
  start: number
  end: number
}

const props = defineProps<{
  model: ChartRenderModel
  viewport: Viewport | null
  resetViewRevision: number
  syncKey: string
  timeOrigin: number | null
}>()

const emit = defineEmits<{
  sampleRates: [rates: ChartSampleRate[]]
  pointClick: [point: Point]
}>()

const plotHost = ref<HTMLElement>()
const legendHost = ref<HTMLElement>()
const chart = shallowRef<uPlot>()
let resizeObserver: ResizeObserver | null = null
let viewportFrame: number | null = null
let structureKey = ''
let appliedResetRevision = -1

function displayTime(value: number) {
  return `${(value - (props.timeOrigin ?? 0)).toFixed(3)}s`
}

function publishVisibleSampleRates(instance = chart.value) {
  const xScale = instance?.scales.x
  emit('sampleRates', getVisibleSampleRates(props.model, xScale?.min, xScale?.max))
}

function createOptions(): uPlot.Options {
  const scales: uPlot.Scales = { x: { time: false } }
  for (const scale of props.model.scales) {
    scales[scale.key] = { auto: true }
  }

  const series: uPlot.Series[] = [
    {
      label: 'Time',
      value: (_u, value) => (value == null ? '-' : displayTime(value as number)),
    },
    ...props.model.series.map((seriesDefinition) => ({
      label: seriesDefinition.label,
      scale: seriesDefinition.scaleKey,
      stroke: seriesDefinition.color,
      width: 1.5,
      // join() inserts undefined for timestamps belonging to other signals.
      // These are alignment artifacts, not breaks in this signal's samples.
      spanGaps: true,
    })),
  ]

  const axes: uPlot.Axis[] = [
    {
      scale: 'x',
      stroke: '#cbd5e1',
      grid: { stroke: '#2d3342', width: 1 },
      values: (_u, splits) =>
        splits.map((value) => `${(value - (props.timeOrigin ?? 0)).toFixed(1)}s`),
    },
    ...props.model.scales.map((scale, index) => ({
      scale: scale.key,
      side: index % 2 === 0 ? 3 : 1,
      label: scale.unit || 'Value',
      stroke: '#cbd5e1',
      grid: index === 0 ? { stroke: '#2d3342', width: 1 } : { show: false },
    })),
  ]

  return {
    width: Math.max(10, plotHost.value?.clientWidth ?? 10),
    height: Math.max(10, plotHost.value?.clientHeight ?? 10),
    series,
    scales,
    axes,
    cursor: {
      drag: { x: true, y: false },
      sync: { key: props.syncKey, scales: ['x', null] },
      focus: { prox: -1 },
    },
    legend: {
      mount: (_u, legend) => legendHost.value?.appendChild(legend),
    },
    hooks: {
      setScale: [
        (instance) => {
          publishVisibleSampleRates(instance)
        },
      ],
    },
  }
}

function applyViewport() {
  if (!chart.value || !props.viewport) return
  chart.value.setScale('x', { min: props.viewport.start, max: props.viewport.end })
}

function scheduleViewport() {
  if (viewportFrame !== null) cancelAnimationFrame(viewportFrame)
  viewportFrame = requestAnimationFrame(() => {
    viewportFrame = null
    applyViewport()
  })
}

function syncData(resetScales: boolean) {
  if (!chart.value) return
  chart.value.batch(() => {
    chart.value?.setData(props.model.data, resetScales)
    applyViewport()
  })
  publishVisibleSampleRates()
}

function handlePointDataResize() {
}

function handlePlotClick() {
  const u = chart.value
  const idx = u?.cursor.idx
  if (!u || idx == null) return

  const time = u.data[0]?.[idx]
  if (time == null) return

  // Aligned data can have gaps for a series at the cursor's timestamp. Pick
  // the first series with a real value and use that series' unit scale.
  const seriesIndex = props.model.series.findIndex((series, index) => {
    return u.data[index + 1]?.[idx] != null && u.scales[series.scaleKey] != null
  })
  if (seriesIndex < 0) return

  const series = props.model.series[seriesIndex]!
  const value = u.data[seriesIndex + 1]?.[idx]
  const xScale = u.scales.x
  const yScale = u.scales[series.scaleKey]
  if (value == null || !xScale || !yScale) return

  const isVisible =
    xScale.min != null && xScale.max != null &&
    yScale.min != null && yScale.max != null &&
    time >= xScale.min && time <= xScale.max &&
    value >= yScale.min && value <= yScale.max
  if (!isVisible) return

  const overlay = u.root.querySelector('.u-over')
  const widget = plotHost.value?.closest('.base-widget')
  if (!overlay || !widget) return

  const plotRect = overlay.getBoundingClientRect()
  const widgetRect = widget.getBoundingClientRect()
  const point: Point = {
    values: { x: time - (props.timeOrigin ?? 0), y: value },
    units: { x: 'secs', y: series.unit },
    coords: {
      x: plotRect.left - widgetRect.left + u.valToPos(time, 'x'),
      y: plotRect.top - widgetRect.top + u.valToPos(value, series.scaleKey),
    },
  }

  emit('pointClick', point)
}

function initChart() {
  if (!plotHost.value) return
  chart.value = new uPlot(createOptions(), props.model.data, plotHost.value)
  plotHost.value.removeEventListener('click', handlePlotClick)
  plotHost.value.addEventListener('click', handlePlotClick)

  structureKey = props.model.structureKey
  appliedResetRevision = props.resetViewRevision
  applyViewport()
  publishVisibleSampleRates()

  resizeObserver ??= new ResizeObserver(() => {
    if (!chart.value || !plotHost.value) return
    handlePointDataResize();
    chart.value.setSize({
      width: Math.max(10, plotHost.value.clientWidth),
      height: Math.max(10, plotHost.value.clientHeight),
    })
  })
  resizeObserver.observe(plotHost.value)
}

function rebuildChart() {
  chart.value?.destroy()
  chart.value = undefined
  initChart()
}

function syncChartRect() {
  chart.value?.syncRect()
}

onMounted(initChart)

watch([() => props.model, () => props.resetViewRevision], ([model, resetRevision]) => {
  if (!chart.value) return
  if (model.structureKey !== structureKey) {
    rebuildChart()
    return
  }

  const shouldReset = resetRevision !== appliedResetRevision
  syncData(shouldReset)
  appliedResetRevision = resetRevision
})

watch(() => props.viewport, scheduleViewport, { deep: true })

onBeforeUnmount(() => {
  if (viewportFrame !== null) cancelAnimationFrame(viewportFrame)
  resizeObserver?.disconnect()
  plotHost.value?.removeEventListener('click', handlePlotClick)
  chart.value?.destroy()
})
</script>

<template>
  <div class="uplot-chart" @mouseenter="syncChartRect">
    <div ref="legendHost" class="uplot-legend" />
    <div ref="plotHost" class="uplot-plot" />
  </div>
</template>

<style scoped>
.uplot-chart {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 150px;
}

.uplot-legend {
  flex: 0 0 auto;
  min-height: 0;
}

.uplot-plot {
  flex: 1 1 auto;
  min-height: 0;
}

:deep(.u-axis text) {
  fill: #a1a1aa !important;
}
:deep(.u-legend) {
  color: #e4e4e7;
}
:deep(.u-legend .u-series th),
:deep(.u-legend .u-series td) {
  padding: 2px 4px;
}
:deep(.u-legend .u-value) {
  color: #e4e4e7;
}
:deep(.u-legend .u-marker) {
  width: 12px !important;
  height: 12px !important;
  border-width: 6px !important;
  box-sizing: border-box !important;
}

:deep(.u-select) {
  background: rgba(59, 130, 246, 0.2);
}
</style>
