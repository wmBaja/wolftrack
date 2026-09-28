<script setup lang="ts">
import { ref, computed } from 'vue'
import BaseWidget from '@/components/widgets/BaseWidget.vue'
import UplotChart from '@/components/UplotChart.vue'
import { useWidgetStore } from '@/stores/widgetStore'
import { useLiveDataStore } from '@/stores/liveDataStore'
import { useLogDataStore } from '@/stores/logDataStore'
import { useDataSourceStore } from '@/stores/dataSourceStore'
import type { AlignedData } from 'uplot'
import type { RingBuffer } from '@/stores/liveDataStore'

type LogBuffer = { timestamps: number[], values: number[] }

const props = defineProps<{
  widgetId: string
}>()

const widgetStore = useWidgetStore()
const liveDataStore = useLiveDataStore()
const logDataStore = useLogDataStore()
const dataSourceStore = useDataSourceStore()

const baseWidgetRef = ref<InstanceType<typeof BaseWidget>>()
const widget = computed(() => widgetStore.getWidgetById(props.widgetId))

function getAlignedData(): AlignedData {
  const isLive = dataSourceStore.config.source === 'zmq'
  const signalsToPlot = widget.value?.signals || []
  if (signalsToPlot.length === 0) return [[]]

  if (signalsToPlot.length === 1) {
    const firstSig = signalsToPlot[0]
    if (!firstSig) return [[]]

    if (isLive) {
        const buf = liveDataStore.buffers.get(firstSig)
        if (!buf || buf.length === 0) return [[], []]
        const { timestamps, values } = buf.getArrays()
        return [Array.from(timestamps), Array.from(values)]
    } else {
        const buf = logDataStore.buffers[firstSig]
        if (!buf) return [[], []]

        const cutoff = logDataStore.currentTime
        let validLen = 0
        for (let i = 0; i < buf.timestamps.length; i++) {
            const ts = buf.timestamps[i]
            if (ts !== undefined && ts > cutoff) break
            validLen++
        }

        return [buf.timestamps.slice(0, validLen), buf.values.slice(0, validLen)]
    }
  }

  let minTime = Infinity
  let maxTime = -Infinity
  let largestBufferLength = 0

  const activeBuffers = isLive
    ? signalsToPlot.map(sig => liveDataStore.buffers.get(sig))
    : signalsToPlot.map(sig => logDataStore.buffers[sig])

  activeBuffers.forEach(buf => {
    if (isLive) {
        const liveBuf = buf as RingBuffer | undefined
        if (liveBuf && liveBuf.length > 0) {
          largestBufferLength = Math.max(largestBufferLength, liveBuf.length)
          const firstTime = liveBuf.timestamps[liveBuf.tail]!
          const lastIdx = (liveBuf.head - 1 + liveBuf.capacity) % liveBuf.capacity
          const lastTime = liveBuf.timestamps[lastIdx]!
          if (firstTime < minTime) minTime = firstTime
          if (lastTime > maxTime) maxTime = lastTime
        }
    } else {
        const logBuf = buf as LogBuffer | undefined
        if (logBuf && logBuf.timestamps.length > 0) {
          largestBufferLength = Math.max(largestBufferLength, logBuf.timestamps.length)
          const firstTime = logBuf.timestamps[0]!
          const lastFileTime = logBuf.timestamps[logBuf.timestamps.length - 1]!
          const lastTime = Math.min(lastFileTime, logDataStore.currentTime)
          if (firstTime < minTime) minTime = firstTime
          if (lastTime > maxTime) maxTime = lastTime
        }
    }
  })

  if (minTime === Infinity) return [[]]

  const pointBudget = isLive
    ? 1_000
    : logDataStore.getQueryPointBudget(minTime, maxTime)
  const numBuckets = Math.max(1, Math.min(pointBudget, largestBufferLength))
  const bucketSize = (maxTime - minTime) / numBuckets || 0.001

  const alignedTimestamps = new Array(numBuckets)
  for (let i = 0; i < numBuckets; i++) {
    alignedTimestamps[i] = minTime + i * bucketSize
  }

  const aligned: (number | null)[][] = [alignedTimestamps]

  activeBuffers.forEach(buf => {
    const values = new Array(numBuckets).fill(null)

    if (buf) {
      const ts = isLive ? (buf as RingBuffer).getArrays().timestamps : (buf as LogBuffer).timestamps
      const vs = isLive ? (buf as RingBuffer).getArrays().values : (buf as LogBuffer).values

      const cutoff = isLive ? Infinity : logDataStore.currentTime

      if (ts.length > 0) {
          for (let i = 0; i < ts.length; i++) {
            const t = ts[i]!
            if (t > cutoff) break

            const v = vs[i]
            let bucketIdx = Math.floor((t - minTime) / bucketSize)
            if (bucketIdx >= numBuckets) bucketIdx = numBuckets - 1
            if (bucketIdx >= 0) {
                values[bucketIdx] = v // keep last value in bucket
            }
          }
      }
    }
    aligned.push(values)
  })

  return aligned as AlignedData
}

const startEditTitle = () => {
  baseWidgetRef.value?.startEditTitle()
}

defineExpose({ startEditTitle })
</script>

<template>
  <BaseWidget
    ref="baseWidgetRef"
    :widget-id="widgetId"
    icon="📈"
  >
    <template #default>
      <div class="chart-content">
        <div v-if="!widget?.signals?.length" class="empty-state">
          <p>No signals configured.</p>
          <button @click="baseWidgetRef?.toggleConfig()" class="save-btn">Configure</button>
        </div>
        <UplotChart
          v-else
          :signals="widget?.signals || []"
          :get-data="getAlignedData"
          :update-version="dataSourceStore.config.source === 'zmq' ? liveDataStore.dataVersion : logDataStore.dataVersion"
          :time-origin="dataSourceStore.config.source === 'zmq' ? liveDataStore.sessionStartTimestamp : logDataStore.status.start_ts"
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
