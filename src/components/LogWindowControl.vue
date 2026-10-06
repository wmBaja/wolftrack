<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
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
const isExpanded = ref(true)
const timelineRef = ref<HTMLElement | null>(null)
const dragMode = ref<'start' | 'end' | 'window' | null>(null)
const focusStart = ref(0)
const focusEnd = ref(0)
const isFocusTransitioning = ref(false)
const MIN_USABLE_WINDOW_WIDTH_PX = 72
const PRECISION_FOCUS_LOG_FRACTION = 0.1
const TIMELINE_GRID_DIVISIONS = 16
const PRECISION_GRID_DIVISIONS = 20
const TIMELINE_LABEL_POSITIONS = [0, 0.25, 0.5, 0.75, 1]
const FOCUS_TRANSITION_DURATION_MS = 420
const FOCUS_CHANGE_DELAY_MS = 1000
let dragPointerStart = 0
let dragWindowStart = 0
let dragWindowEnd = 0
let focusTransitionTimer: number | undefined
let focusChangeTimer: number | undefined
let pendingFocusChange: 'focus' | 'reset' | undefined

const focusDuration = computed(() => Math.max(0, focusEnd.value - focusStart.value))
const selectionStartPercent = computed(() => focusDuration.value > 0
  ? ((startOffset.value - focusStart.value) / focusDuration.value) * 100
  : 0)
const selectionEndPercent = computed(() => focusDuration.value > 0
  ? ((endOffset.value - focusStart.value) / focusDuration.value) * 100
  : 0)
const selectionWidthPercent = computed(() => Math.max(
  0,
  selectionEndPercent.value - selectionStartPercent.value,
))
const isPrecisionFocused = computed(() => (
  logDuration.value > 0 && focusDuration.value < logDuration.value
))
const timelineGridTicks = computed(() => {
  const divisions = isPrecisionFocused.value
    ? PRECISION_GRID_DIVISIONS
    : TIMELINE_GRID_DIVISIONS

  return Array.from({ length: divisions - 1 }, (_, index) => ({
    id: index + 1,
    position: ((index + 1) / divisions) * 100,
  }))
})
const timelineLabelMarkers = computed(() => TIMELINE_LABEL_POSITIONS.map(position => ({
  position,
  time: focusStart.value + focusDuration.value * position,
})))

function resetFocus() {
  focusStart.value = 0
  focusEnd.value = logDuration.value
}

function isFocusReset() {
  return focusStart.value === 0 && focusEnd.value === logDuration.value
}

function clearPendingFocusChange() {
  if (focusChangeTimer !== undefined) window.clearTimeout(focusChangeTimer)
  focusChangeTimer = undefined
  pendingFocusChange = undefined
}

function scheduleFocusChange(kind: 'focus' | 'reset', change: () => void) {
  clearPendingFocusChange()
  pendingFocusChange = kind
  focusChangeTimer = window.setTimeout(() => {
    change()
    focusChangeTimer = undefined
    pendingFocusChange = undefined
  }, FOCUS_CHANGE_DELAY_MS)
}

onBeforeUnmount(() => {
  if (focusTransitionTimer !== undefined) window.clearTimeout(focusTransitionTimer)
  clearPendingFocusChange()
})

watch(
  [() => logDataStore.status.start_ts, () => logDataStore.status.end_ts],
  resetFocus,
  { immediate: true },
)

function syncDraft() {
  draftStart.value = compactInputValue(startOffset.value)
  draftEnd.value = compactInputValue(endOffset.value)
}

watch([startOffset, endOffset], () => {
  syncDraft()
}, { immediate: true })

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
  resetFocus()
}

function clampFocusStart(value: number, duration: number) {
  return Math.min(logDuration.value - duration, Math.max(0, value))
}

function focusSelection() {
  if (windowDuration.value <= 0 || logDuration.value <= 0) return

  const timelineWidth = timelineRef.value?.getBoundingClientRect().width ?? 0
  const maxDurationForUsableSelection = timelineWidth > 0
    ? windowDuration.value * timelineWidth / MIN_USABLE_WINDOW_WIDTH_PX
    : logDuration.value

  // Keep the zoomed timeline at a predictable scale by default. For a tiny
  // selection in a very long log, zoom further only until it is 72 px wide.
  // A larger current selection remains fully visible instead of being clipped.
  const duration = Math.min(
    logDuration.value,
    Math.max(
      windowDuration.value,
      Math.min(
        logDuration.value * PRECISION_FOCUS_LOG_FRACTION,
        maxDurationForUsableSelection,
      ),
    ),
  )
  setFocusAround((startOffset.value + endOffset.value) / 2, duration)
}

function setFocusAround(center: number, duration: number) {
  const start = clampFocusStart(center - duration / 2, duration)
  focusStart.value = start
  focusEnd.value = start + duration
}

function zoomOutAtFocusEdge(edge: 'start' | 'end', start: number, end: number) {
  const reachedTimelineEdge = start <= 0 || end >= logDuration.value
  const duration = reachedTimelineEdge
    ? logDuration.value
    : Math.min(
      logDuration.value,
      Math.max(focusDuration.value * 2, windowDuration.value * 4),
    )
  const boundedStart = edge === 'start'
    ? clampFocusStart(start, duration)
    : clampFocusStart(end - duration, duration)
  focusStart.value = boundedStart
  focusEnd.value = boundedStart + duration

  isFocusTransitioning.value = true
  if (focusTransitionTimer !== undefined) window.clearTimeout(focusTransitionTimer)
  focusTransitionTimer = window.setTimeout(() => {
    isFocusTransitioning.value = false
    focusTransitionTimer = undefined
  }, FOCUS_TRANSITION_DURATION_MS)
}

function needsPrecisionFocus() {
  const width = timelineRef.value?.getBoundingClientRect().width ?? 0
  return windowDuration.value > 0
    && logDuration.value > 0
    && width > 0
    && (windowDuration.value / logDuration.value) * width < MIN_USABLE_WINDOW_WIDTH_PX
}

function beginPrecisionFocus(immediate = false) {
  if (pendingFocusChange === 'reset') clearPendingFocusChange()
  if (!needsPrecisionFocus() || !isFocusReset()) return

  if (immediate) {
    clearPendingFocusChange()
    focusSelection()
    return
  }

  if (pendingFocusChange !== 'focus') {
    scheduleFocusChange('focus', focusSelection)
  }
}

function endPrecisionFocus() {
  if (dragMode.value) return
  if (pendingFocusChange === 'focus') clearPendingFocusChange()
  if (isFocusReset() || pendingFocusChange === 'reset') return

  scheduleFocusChange('reset', resetFocus)
}

function getOffsetAtPointer(event: PointerEvent) {
  const rect = timelineRef.value?.getBoundingClientRect()
  if (!rect || rect.width === 0) return 0

  const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width))
  return focusStart.value + ratio * focusDuration.value
}

function beginDrag(mode: 'start' | 'end' | 'window', event: PointerEvent) {
  if (!isAvailable.value) return

  // Preserve the current timeline scale once the user has found a control.
  // This prevents a queued hover zoom from moving it out from under the pointer.
  clearPendingFocusChange()
  dragMode.value = mode
  dragPointerStart = getOffsetAtPointer(event)
  dragWindowStart = startOffset.value
  dragWindowEnd = endOffset.value
  timelineRef.value?.setPointerCapture(event.pointerId)
  logDataStore.beginQueryWindowDrag()
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
  const nextStart = dragWindowStart + delta

  // Zoom out at the edge being dragged. Anchoring the focus at that edge keeps
  // the selected window under the pointer throughout the transition.
  if (nextStart < focusStart.value || nextStart + width > focusEnd.value) {
    const boundedStart = Math.min(
      logDuration.value - width,
      Math.max(0, nextStart),
    )
    const boundedEnd = boundedStart + width
    applyWindow(boundedStart, boundedEnd)
    zoomOutAtFocusEdge(
      nextStart < focusStart.value ? 'start' : 'end',
      boundedStart,
      boundedEnd,
    )
    dragPointerStart = getOffsetAtPointer(event)
    dragWindowStart = boundedStart
    dragWindowEnd = boundedEnd
    return
  }

  applyWindow(nextStart, nextStart + width)
}

function endDrag(event: PointerEvent) {
  if (!dragMode.value) return
  dragMode.value = null
  if (timelineRef.value?.hasPointerCapture(event.pointerId)) {
    timelineRef.value.releasePointerCapture(event.pointerId)
  }
  logDataStore.endQueryWindowDrag()
}

function adjustHandle(mode: 'start' | 'end', event: KeyboardEvent) {
  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
  event.preventDefault()

  const direction = event.key === 'ArrowLeft' ? -1 : 1
  const increment = focusDuration.value / (event.shiftKey ? 10 : 100)
  const nextValue = mode === 'start'
    ? startOffset.value + direction * increment
    : endOffset.value + direction * increment

  applyWindow(
    mode === 'start' ? nextValue : startOffset.value,
    mode === 'end' ? nextValue : endOffset.value,
  )
}

function formatSeconds(seconds: number) {
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 3 : 1)} s`
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds - minutes * 60
  return `${minutes}m ${remainder.toFixed(1)}s`
}
</script>

<template>
  <section
    v-if="isAvailable"
    class="log-window-control"
    :class="{ 'is-expanded': isExpanded }"
    :style="{ '--focus-transition-duration': `${FOCUS_TRANSITION_DURATION_MS}ms` }"
    aria-label="Log chart window"
  >
    <button
      class="log-window-control__tab"
      type="button"
      :aria-expanded="isExpanded"
      aria-controls="log-window-drawer"
      :aria-label="isExpanded ? 'Collapse timeline' : 'Expand timeline'"
      @click="isExpanded = !isExpanded"
    >
      <span>Timeline</span>
      <span class="log-window-control__tab-icon" aria-hidden="true">{{ isExpanded ? '⌄' : '⌃' }}</span>
    </button>

    <div class="log-window-control__drawer-body" :aria-hidden="!isExpanded">
      <div id="log-window-drawer" class="log-window-control__panel">
        <div class="log-window-control__timeline-wrap">
          <div
            ref="timelineRef"
            class="log-window-control__timeline"
            :class="{
              'is-dragging': dragMode,
              'is-focus-transitioning': isFocusTransitioning,
            }"
            aria-label="Selected log time window"
            @pointermove="moveWindow"
            @pointerup="endDrag"
            @pointercancel="endDrag"
          >
            <div class="log-window-control__timeline-grid" aria-hidden="true">
              <span
                v-for="tick in timelineGridTicks"
                :key="tick.id"
                class="is-minor"
                :style="{ left: `${tick.position}%` }"
              />
              <span
                v-for="marker in timelineLabelMarkers"
                :key="`major-${marker.position}`"
                class="is-major"
                :style="marker.position === 1
                  ? { right: '0' }
                  : { left: `${marker.position * 100}%` }"
              />
            </div>
            <div
              class="log-window-control__selection"
              :style="{
                left: `${selectionStartPercent}%`,
                width: `${selectionWidthPercent}%`,
              }"
              @pointerenter="beginPrecisionFocus()"
              @pointerleave="endPrecisionFocus"
              @pointerdown.prevent="beginDrag('window', $event)"
            >
              <span class="log-window-control__selection-label">{{ formatSeconds(windowDuration) }}</span>
            </div>
            <button
              class="log-window-control__handle log-window-control__handle--start"
              :style="{ left: `${selectionStartPercent}%` }"
              type="button"
              aria-label="Drag window start. Use left and right arrow keys for precise adjustment."
              @pointerenter="beginPrecisionFocus()"
              @pointerleave="endPrecisionFocus"
              @pointerdown.stop.prevent="beginDrag('start', $event)"
              @focus="beginPrecisionFocus(true)"
              @blur="endPrecisionFocus"
              @keydown="adjustHandle('start', $event)"
            />
            <button
              class="log-window-control__handle log-window-control__handle--end"
              :style="{ left: `${selectionEndPercent}%` }"
              type="button"
              aria-label="Drag window end. Use left and right arrow keys for precise adjustment."
              @pointerenter="beginPrecisionFocus()"
              @pointerleave="endPrecisionFocus"
              @pointerdown.stop.prevent="beginDrag('end', $event)"
              @focus="beginPrecisionFocus(true)"
              @blur="endPrecisionFocus"
              @keydown="adjustHandle('end', $event)"
            />
          </div>
          <div class="log-window-control__timeline-labels">
            <span v-for="marker in timelineLabelMarkers" :key="marker.position">
              {{ formatSeconds(marker.time) }}
            </span>
          </div>
        </div>
        <div
          class="log-window-control__actions"
        >
          <label>
            Start
            <input
              v-model.number="draftStart"
              type="number"
              min="0"
              :max="draftEnd"
              step="0.010"
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
              step="0.010"
              @change="applyDraft"
              @keyup.enter="applyDraft"
            >
          </label>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.log-window-control {
  position: fixed;
  z-index: 40;
  bottom: 0;
  left: 0;
  right: 0;
  pointer-events: none;
}

.log-window-control__drawer-body {
  max-height: 0;
  overflow: hidden;
  pointer-events: auto;
  transition: max-height 260ms cubic-bezier(0.22, 1, 0.36, 1);
}

.log-window-control.is-expanded .log-window-control__drawer-body {
  max-height: 160px;
}

.log-window-control__panel {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto;
  align-items: center;
  gap: 6px 10px;
  padding: 8px 10px;
  background: var(--color-panel);
  border: 1px solid var(--color-border);
  border-bottom: 0;
  border-radius: 0 10px 0 0;
  box-shadow: 0 -8px 24px rgb(0 0 0 / 25%);
  color: var(--color-text);
  font-size: 12px;
  pointer-events: auto;
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 180ms ease, transform 240ms cubic-bezier(0.22, 1, 0.36, 1);
}

.log-window-control.is-expanded .log-window-control__panel {
  opacity: 1;
  transform: translateY(0);
}

.log-window-control__tab {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  margin-bottom: -1px;
  padding: 5px 11px 6px 8px;
  border: 1px solid var(--color-border);
  border-bottom: 0;
  border-radius: 8px 8px 0 0;
  background: var(--color-panel);
  color: var(--color-text);
  box-shadow: none;
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
  pointer-events: auto;
}

.log-window-control__tab:hover,
.log-window-control__tab:focus-visible {
  color: var(--color-accent);
  outline: none;
}

.log-window-control__tab-icon {
  font-size: 14px;
  line-height: 1;
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
  overflow: hidden;
  border-radius: inherit;
  pointer-events: none;
}

.log-window-control__timeline-grid span {
  position: absolute;
  transition: left var(--focus-transition-duration) cubic-bezier(0.22, 1, 0.36, 1);
}

.log-window-control__timeline-grid span.is-minor {
  top: 4px;
  bottom: 4px;
  width: 2px;
  background: color-mix(in srgb, var(--color-border) 70%, var(--color-text));
  opacity: 1.0;
}

.log-window-control__timeline-grid span.is-major {
  top: 0;
  bottom: 0;
  width: 2px;
  background: color-mix(in srgb, var(--color-border) 55%, var(--color-text));
  opacity: 1.0;
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
  transition: left var(--focus-transition-duration) cubic-bezier(0.22, 1, 0.36, 1), width var(--focus-transition-duration) cubic-bezier(0.22, 1, 0.36, 1);
  will-change: left, width;
}

.log-window-control__selection:active {
  cursor: grabbing;
}

.log-window-control__selection-label {
  position: absolute;
  z-index: 3;
  top: 2px;
  left: 50%;
  transform: translateX(-50%);
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
  width: 18px;
  padding: 0;
  transform: translateX(-50%);
  border: 0;
  background: transparent;
  cursor: ew-resize;
  transition: left var(--focus-transition-duration) cubic-bezier(0.22, 1, 0.36, 1);
  will-change: left;
}

.log-window-control__handle::after {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 5px;
  transform: translateX(-50%);
  border: 1px solid color-mix(in srgb, var(--color-accent) 80%, white);
  border-radius: 2px;
  background: var(--color-accent);
  box-shadow: 0 0 0 1px rgb(0 0 0 / 25%), 0 1px 5px rgb(0 0 0 / 35%);
  content: '';
}

.log-window-control__handle:hover,
.log-window-control__handle:focus-visible {
  outline: none;
}

.log-window-control__handle:hover::after,
.log-window-control__handle:focus-visible::after {
  width: 7px;
}

.log-window-control__timeline.is-dragging .log-window-control__selection {
  cursor: grabbing;
}

.log-window-control__timeline.is-dragging .log-window-control__selection,
.log-window-control__timeline.is-dragging .log-window-control__handle {
  transition: none;
}

.log-window-control__timeline.is-dragging.is-focus-transitioning .log-window-control__selection {
  transition: left var(--focus-transition-duration) cubic-bezier(0.22, 1, 0.36, 1), width var(--focus-transition-duration) cubic-bezier(0.22, 1, 0.36, 1);
}

.log-window-control__timeline.is-dragging.is-focus-transitioning .log-window-control__handle {
  transition: left var(--focus-transition-duration) cubic-bezier(0.22, 1, 0.36, 1);
}

.log-window-control__timeline-labels {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 3px;
  color: var(--color-text);
  font-size: 12px;
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
  color: var(--color-text);
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
  .log-window-control__panel {
    grid-template-columns: 1fr;
  }
}
</style>
