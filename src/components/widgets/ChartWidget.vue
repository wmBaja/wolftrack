<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseWidget from '@/components/widgets/BaseWidget.vue'
import UplotChart from '@/components/UplotChart.vue'
import { useWidgetStore } from '@/stores/widgetStore'
import { useTimeSeriesData } from '@/composables/useTimeSeriesData'

const props = defineProps<{
  widgetId: string
}>()

const widgetStore = useWidgetStore()
const baseWidgetRef = ref<InstanceType<typeof BaseWidget>>()
const widget = computed(() => widgetStore.getWidgetById(props.widgetId))
const signals = computed(() => widget.value?.signals || [])
const consumerId = computed(() => props.widgetId)
const { snapshot, refresh } = useTimeSeriesData(consumerId, signals)

const startEditTitle = () => {
  baseWidgetRef.value?.startEditTitle()
}

defineExpose({ startEditTitle })
</script>

<template>
  <BaseWidget ref="baseWidgetRef" :widget-id="widgetId" icon="📈" @refresh="refresh">
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
</style>
