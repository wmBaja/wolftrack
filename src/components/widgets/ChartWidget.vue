<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import BaseWidget from '@/components/widgets/BaseWidget.vue'
import UplotChart from '@/components/UplotChart.vue'
import { useWidgetStore } from '@/stores/widgetStore'
import { useTimeSeriesData } from '@/composables/useTimeSeriesData'
import type { ChartSampleRate } from '@/lib/chartData'

const props = defineProps<{
  widgetId: string
}>()

const widgetStore = useWidgetStore()
const baseWidgetRef = ref<InstanceType<typeof BaseWidget>>()
const widget = computed(() => widgetStore.getWidgetById(props.widgetId))
const signals = computed(() => widget.value?.signals || [])
const consumerId = computed(() => props.widgetId)
const { snapshot, refresh } = useTimeSeriesData(consumerId, signals)
const chartStatsRef = ref<HTMLElement>()
const isStatsOpen = ref(false)
const sampleRates = ref<ChartSampleRate[]>([])

function formatSamplesPerSecond(rate: number | null) {
  if (rate == null) return '—'
  return `${new Intl.NumberFormat(undefined, { maximumSignificantDigits: 3 }).format(rate)} SPS`
}

function closeStatsOnOutsideClick(event: PointerEvent) {
  if (!chartStatsRef.value?.contains(event.target as Node)) isStatsOpen.value = false
}

function closeStatsOnEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') isStatsOpen.value = false
}

onMounted(() => {
  document.addEventListener('pointerdown', closeStatsOnOutsideClick)
  document.addEventListener('keydown', closeStatsOnEscape)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', closeStatsOnOutsideClick)
  document.removeEventListener('keydown', closeStatsOnEscape)
})

const startEditTitle = () => {
  baseWidgetRef.value?.startEditTitle()
}

defineExpose({ startEditTitle })
</script>

<template>
  <BaseWidget ref="baseWidgetRef" :widget-id="widgetId" icon="📈" @refresh="refresh">
    <template #header-actions>
      <div v-if="widget?.signals?.length" ref="chartStatsRef" class="chart-stats">
        <button
          class="chart-stats__toggle"
          type="button"
          aria-haspopup="dialog"
          :aria-expanded="isStatsOpen"
          :aria-controls="`chart-stats-${widgetId}`"
          @pointerdown.stop
          @click="isStatsOpen = !isStatsOpen"
        >
          Stats
        </button>
        <div
          v-if="isStatsOpen"
          :id="`chart-stats-${widgetId}`"
          class="chart-stats__popover"
          role="dialog"
          aria-label="Visible sample rates"
          @pointerdown.stop
        >
          <p class="chart-stats__heading">Visible sample rate</p>
          <dl class="chart-stats__rates">
            <template v-for="rate in sampleRates" :key="rate.id">
              <dt>{{ rate.label }}</dt>
              <dd>{{ formatSamplesPerSecond(rate.samplesPerSecond) }}</dd>
            </template>
          </dl>
          <p v-if="sampleRates.length === 0" class="chart-stats__empty">Waiting for chart data…</p>
        </div>
      </div>
    </template>
    <template #default>
      <div class="chart-content">
        <div v-if="!widget?.signals?.length" class="empty-state">
          <p>No signals configured.</p>
          <button @click="baseWidgetRef?.toggleConfig()" class="save-btn">Configure</button>
        </div>
        <UplotChart
          v-else
          :model="snapshot.model"
          :viewport="snapshot.viewport"
          :reset-view-revision="snapshot.resetViewRevision"
          sync-key="wolftrack-dashboard-time"
          :time-origin="snapshot.timeOrigin"
          @sample-rates="sampleRates = $event"
        />
      </div>
    </template>
  </BaseWidget>
</template>

<style scoped>
.chart-content {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  background: transparent;
  overflow: hidden;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-muted);
  gap: 10px;
}

.save-btn {
  margin-top: 10px;
  padding: 8px 16px;
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.save-btn:hover {
  opacity: 0.9;
}

.chart-stats {
  position: relative;
}

.chart-stats__toggle {
  padding: 3px 7px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
}

.chart-stats__toggle:hover,
.chart-stats__toggle:focus-visible {
  border-color: var(--color-accent);
  color: var(--color-text);
  outline: none;
}

.chart-stats__popover {
  position: absolute;
  z-index: 20;
  top: calc(100% + 6px);
  right: 0;
  min-width: 190px;
  max-width: min(300px, 75vw);
  padding: 9px 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-panel);
  box-shadow: 0 8px 20px rgb(0 0 0 / 30%);
}

.chart-stats__heading,
.chart-stats__empty {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 11px;
}

.chart-stats__heading {
  margin-bottom: 6px;
  font-weight: 600;
}

.chart-stats__rates {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px 12px;
  margin: 0;
  font-size: 12px;
}

.chart-stats__rates dt {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chart-stats__rates dd {
  margin: 0;
  color: var(--color-text-muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
</style>
