<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useDataSourceStore } from '@/stores/dataSourceStore'
import { useLogDataStore } from '@/stores/logDataStore'

const dataSourceStore = useDataSourceStore()
const logDataStore = useLogDataStore()

const isAvailable = computed(() => {
  return dataSourceStore.config.source === 'logfile'
    && logDataStore.status.status === 'ready'
    && logDataStore.status.end_ts > logDataStore.status.start_ts
})

const logDuration = computed(() => Math.max(
  0,
  logDataStore.status.end_ts - logDataStore.status.start_ts,
))
const startOffset = computed(() => Math.max(
  0,
  logDataStore.queryWindow.start_ts - logDataStore.status.start_ts,
))
const endOffset = computed(() => Math.max(
  0,
  logDataStore.queryWindow.end_ts - logDataStore.status.start_ts,
))
const windowDuration = computed(() => Math.max(0, endOffset.value - startOffset.value))

const draftStart = ref(0)
const draftEnd = ref(0)
const timelineRef = ref<HTMLElement | null>(null)
const dragMode = ref<'start' | 'end' | 'window' | null>(null)
let dragPointerStart = 0
let dragWindowStart = 0
let dragWindowEnd = 0

function syncDraft() {
  draftStart.value = compactInputValue(startOffset.value)
  draftEnd.value = compactInputValue(endOffset.value)
}

watch([startOffset, endOffset], syncDraft, { immediate: true })

function clampOffset(value: number) {
  if (!Number.isFinite(value)) return 0
  return Math.min(logDuration.value, Math.max(0, value))
}

// Keep the editable fields readable for long recordings while retaining
// millisecond precision for the normal-sized windows.
function compactInputValue(value: number) {
  if (!Number.isFinite(value)) return 0

  const decimals = Math.abs(value) >= 100_000
    ? 0
    : Math.abs(value) >= 10_000
      ? 1
      : 3
  const factor = 10 ** decimals
  return Math.trunc(value * factor) / factor
}

function applyWindow(start: number, end: number) {
  const normalizedStart = clampOffset(start)
  const normalizedEnd = Math.max(normalizedStart, clampOffset(end))
  logDataStore.selectQueryWindow(
    logDataStore.status.start_ts + normalizedStart,
    logDataStore.status.start_ts + normalizedEnd,
  )
}

function applyDraft() {
  applyWindow(draftStart.value, draftEnd.value)
}

function getOffsetAtPointer(event: PointerEvent) {
  const rect = timelineRef.value?.getBoundingClientRect()
  if (!rect || rect.width === 0) return 0

  const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width))
  return ratio * logDuration.value
}

function beginDrag(mode: 'start' | 'end' | 'window', event: PointerEvent) {
  if (!isAvailable.value) return

  dragMode.value = mode
  dragPointerStart = getOffsetAtPointer(event)
  dragWindowStart = startOffset.value
  dragWindowEnd = endOffset.value
  timelineRef.value?.setPointerCapture(event.pointerId)
}

function moveWindow(event: PointerEvent) {
  if (!dragMode.value) return

  const offset = getOffsetAtPointer(event)
  if (dragMode.value === 'start') {
    applyWindow(offset, dragWindowEnd)
    return
  }
  if (dragMode.value === 'end') {
    applyWindow(dragWindowStart, offset)
    return
  }

  const width = dragWindowEnd - dragWindowStart
  const delta = offset - dragPointerStart
  const nextStart = Math.min(
    logDuration.value - width,
    Math.max(0, dragWindowStart + delta),
  )
  applyWindow(nextStart, nextStart + width)
}

function endDrag(event: PointerEvent) {
  if (!dragMode.value) return
  dragMode.value = null
  if (timelineRef.value?.hasPointerCapture(event.pointerId)) {
    timelineRef.value.releasePointerCapture(event.pointerId)
  }
}

function formatSeconds(seconds: number) {
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 3 : 1)} s`
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds - minutes * 60
  return `${minutes}m ${remainder.toFixed(1)}s`
}
</script>

<template>
  <section v-if="isAvailable" class="log-window-control" aria-label="Log chart window">
    <div class="log-window-control__timeline-wrap">
      <div
        ref="timelineRef"
        class="log-window-control__timeline"
        :class="{ 'is-dragging': dragMode }"
        aria-label="Selected log time window"
        @pointermove="moveWindow"
        @pointerup="endDrag"
        @pointercancel="endDrag"
      >
        <div class="log-window-control__timeline-grid" aria-hidden="true">
          <span v-for="tick in 9" :key="tick" />
        </div>
        <div
          class="log-window-control__selection"
          :style="{
            left: `${(startOffset / logDuration) * 100}%`,
            width: `${((endOffset - startOffset) / logDuration) * 100}%`,
          }"
          @pointerdown.prevent="beginDrag('window', $event)"
        >
          <span class="log-window-control__selection-label">{{ formatSeconds(windowDuration) }}</span>
        </div>
        <button
          class="log-window-control__handle log-window-control__handle--start"
          :style="{ left: `${(startOffset / logDuration) * 100}%` }"
          type="button"
          aria-label="Drag window start"
          @pointerdown.stop.prevent="beginDrag('start', $event)"
        />
        <button
          class="log-window-control__handle log-window-control__handle--end"
          :style="{ left: `${(endOffset / logDuration) * 100}%` }"
          type="button"
          aria-label="Drag window end"
          @pointerdown.stop.prevent="beginDrag('end', $event)"
        />
      </div>
      <div class="log-window-control__timeline-labels" aria-hidden="true">
        <span>0 s</span>
        <span>{{ formatSeconds(logDuration / 2) }}</span>
        <span>{{ formatSeconds(logDuration) }}</span>
      </div>
    </div>

    <div class="log-window-control__actions">
      <label>
        Start
        <input
          v-model.number="draftStart"
          type="number"
          min="0"
          :max="draftEnd"
          step="0.001"
          @change="applyDraft"
          @keyup.enter="applyDraft"
        >
      </label>
      <label>
        End
        <input
          v-model.number="draftEnd"
          type="number"
          :min="draftStart"
          :max="logDuration"
          step="0.001"
          @change="applyDraft"
          @keyup.enter="applyDraft"
        >
      </label>
    </div>
  </section>
</template>

<style scoped>
.log-window-control {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto;
  align-items: center;
  gap: 6px 10px;
  padding: 8px 10px;
  background: var(--color-panel);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-text);
  font-size: 12px;
}

.log-window-control__duration {
  color: var(--color-muted);
  font-size: 11px;
  font-weight: 500;
}

.log-window-control__timeline-wrap {
  min-width: 0;
}

.log-window-control__timeline {
  position: relative;
  width: 100%;
  height: 24px;
  overflow: visible;
  border-radius: 4px;
  background: color-mix(in srgb, var(--color-panel-header) 70%, transparent);
  border: 1px solid var(--color-border);
  touch-action: none;
  user-select: none;
}

.log-window-control__timeline-grid {
  position: absolute;
  inset: 0;
  display: flex;
  justify-content: space-between;
  padding: 0 10%;
  pointer-events: none;
}

.log-window-control__timeline-grid span {
  width: 1px;
  height: 100%;
  background: color-mix(in srgb, var(--color-border) 70%, transparent);
}

.log-window-control__selection {
  position: absolute;
  top: 0;
  bottom: 0;
  min-width: 2px;
  background: color-mix(in srgb, var(--color-accent) 40%, transparent);
  border-top: 1px solid color-mix(in srgb, var(--color-accent) 85%, white);
  border-bottom: 1px solid color-mix(in srgb, var(--color-accent) 85%, white);
  cursor: grab;
}

.log-window-control__selection:active {
  cursor: grabbing;
}

.log-window-control__selection-label {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--color-text);
  font-size: 12px;
  font-weight: 700;
  pointer-events: none;
  white-space: nowrap;
  text-shadow: 0 1px 2px rgb(0 0 0 / 60%);
}

.log-window-control__handle {
  position: absolute;
  z-index: 2;
  top: -4px;
  bottom: -4px;
  width: 5px;
  padding: 0;
  transform: translateX(-50%);
  border: 1px solid color-mix(in srgb, var(--color-accent) 80%, white);
  border-radius: 2px;
  background: var(--color-accent);
  box-shadow: 0 0 0 1px rgb(0 0 0 / 25%), 0 1px 5px rgb(0 0 0 / 35%);
  cursor: ew-resize;
}

.log-window-control__handle:hover,
.log-window-control__handle:focus-visible {
  width: 7px;
  outline: none;
}

.log-window-control__timeline.is-dragging .log-window-control__selection {
  cursor: grabbing;
}

.log-window-control__timeline-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 3px;
  color: var(--color-muted);
  font-size: 10px;
}

.log-window-control__actions {
  display: flex;
  align-items: end;
  flex-wrap: wrap;
  gap: 4px;
}

.log-window-control label {
  display: grid;
  gap: 1px;
  color: var(--color-muted);
  font-size: 10px;
}

.log-window-control input[type='number'] {
  width: 66px;
  min-width: 0;
  padding: 3px 4px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-input, #171b26);
  color: var(--color-text);
  font-size: 11px;
  text-overflow: ellipsis;
}

@media (max-width: 900px) {
  .log-window-control {
    grid-template-columns: 1fr;
  }
}
</style>
