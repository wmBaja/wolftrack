<script setup lang="ts">
import { onMounted, ref, h, type Component, watch } from 'vue'
import { GridLayout, GridItem } from 'grid-layout-plus'
import { useWidgetStore } from '@/stores/widgetStore'
import ContextMenu from '@imengyu/vue3-context-menu'
import BaseWidget from '@/components/widgets/BaseWidget.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ChartWidget from '@/components/widgets/ChartWidget.vue'
import { WIDGET_TYPES, type Widget } from '@/types/widgets'

const widgetStore = useWidgetStore()

interface WidgetExpose {
  handleRefresh: () => Promise<void>
  startEditTitle: () => void
  setLoading: (value: boolean) => void
}

interface GridPosition {
  x: number
  y: number
}

interface GridSize {
  w: number
  h: number
}

const componentMap: Record<string, Component> = {
  [WIDGET_TYPES.BASE]: BaseWidget,
  [WIDGET_TYPES.CHART]: ChartWidget,
}

const widgetRefs = ref<Record<string, WidgetExpose>>({})
const showClearAllConfirm = ref(false)
const gridWrapperRef = ref<HTMLElement>()
const GRID_COLS = 16
const GRID_ROW_HEIGHT = 30
const GRID_MARGIN = 5
const FALLBACK_CHART_SIZE = { w: 5, h: 15 }

onMounted(() => {
  widgetStore.loadFromLocalStorage()
})

watch(
  () => widgetStore.widgets.length,
  () => {
    const currentIds = new Set(widgetStore.widgets.map((w) => w.i))
    Object.keys(widgetRefs.value).forEach((id) => {
      if (!currentIds.has(id)) {
        delete widgetRefs.value[id]
      }
    })
  },
)

function handleLayoutUpdate(newLayout: Widget[]) {
  widgetStore.updateLayout(newLayout)
}

function setWidgetRef(widgetId: string, el: WidgetExpose | null) {
  if (el) {
    widgetRefs.value[widgetId] = el
  }
}

function getGridMetrics() {
  if (!gridWrapperRef.value) return null

  const gridRect = gridWrapperRef.value.getBoundingClientRect()
  const rowPitch = GRID_ROW_HEIGHT + GRID_MARGIN
  const totalMarginWidth = GRID_MARGIN * (GRID_COLS - 1)
  const availableWidth = gridRect.width - totalMarginWidth
  const colWidth = availableWidth / GRID_COLS

  return { gridRect, colWidth, rowPitch }
}

function getInitialChartSize(): GridSize {
  const metrics = getGridMetrics()
  if (!metrics) return FALLBACK_CHART_SIZE

  const targetWidth = metrics.gridRect.width / 3
  const targetHeight = metrics.gridRect.height / 2

  return {
    w: Math.max(
      4,
      Math.min(
        GRID_COLS,
        Math.round((targetWidth + GRID_MARGIN) / (metrics.colWidth + GRID_MARGIN)),
      ),
    ),
    h: Math.max(4, Math.round((targetHeight + GRID_MARGIN) / (GRID_ROW_HEIGHT + GRID_MARGIN))),
  }
}

function mouseToGridPosition(event: MouseEvent, size: GridSize = { w: 1, h: 1 }): GridPosition {
  if (!gridWrapperRef.value) return { x: 0, y: 0 }

  const metrics = getGridMetrics()
  if (!metrics) return { x: 0, y: 0 }

  // Calculate relative position within the grid
  const relativeX = event.clientX - metrics.gridRect.left + gridWrapperRef.value.scrollLeft
  const relativeY = event.clientY - metrics.gridRect.top + gridWrapperRef.value.scrollTop

  // Convert pixel position to grid coordinates
  const col = Math.floor(relativeX / (metrics.colWidth + GRID_MARGIN))
  const row = Math.floor(relativeY / metrics.rowPitch)

  return {
    x: Math.max(0, Math.min(col, GRID_COLS - size.w)),
    y: Math.max(0, row),
  }
}

function handleGridContextMenu(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (target.closest('.vue-grid-item')) {
    return
  }

  event.preventDefault()

  const chartSize = getInitialChartSize()
  const gridPos = mouseToGridPosition(event, chartSize)

  ContextMenu.showContextMenu({
    x: event.x,
    y: event.y,
    theme: 'mac dark',
    zIndex: 1000,
    items: [
      {
        label: 'Add Chart Widget',
        icon: h('span', '➕'),
        onClick: () => widgetStore.addWidget(WIDGET_TYPES.CHART, { ...gridPos, ...chartSize }),
      },
      { divided: true },
      {
        label: 'Clear All Widgets',
        icon: h('span', '🗑️'),
        customClass: 'context-menu-danger',
        onClick: () => {
          showClearAllConfirm.value = true
        },
      },
    ],
  })
}
</script>

<template>
  <div class="dashboard-grid-container" @contextmenu="handleGridContextMenu">
    <div ref="gridWrapperRef" class="grid-wrapper custom-scrollbar">
      <GridLayout
        v-model:layout="widgetStore.widgets"
        :col-num="GRID_COLS"
        :row-height="GRID_ROW_HEIGHT"
        :resize-option="{
          edges: { right: true, bottom: true },
        }"
        :is-draggable="true"
        :is-resizable="true"
        :is-bounded="false"
        :responsive="false"
        :margin="[GRID_MARGIN, GRID_MARGIN]"
        :use-css-transforms="true"
        :prevent-collision="true"
        :vertical-compact="false"
        @layout-updated="handleLayoutUpdate"
      >
        <GridItem
          v-for="item in widgetStore.widgets"
          :key="item.i"
          v-bind="item"
          drag-allow-from=".base-widget__header"
          drag-ignore-from=".base-widget__content"
        >
          <component
            :is="componentMap[(item as Widget).type] || BaseWidget"
            :ref="(el: WidgetExpose | null) => setWidgetRef(String(item.i), el)"
            :widget-id="item.i"
            :data-widget-id="item.i"
          />
        </GridItem>
      </GridLayout>
    </div>

    <ConfirmDialog
      :show="showClearAllConfirm"
      title="Delete All Widgets"
      message="Are you sure you want to delete all widgets?"
      confirm-text="Delete"
      cancel-text="Cancel"
      danger
      @confirm="widgetStore.clearAll()"
      @close="showClearAllConfirm = false"
    />
  </div>
</template>

<style scoped>
.dashboard-grid-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--navbar-height));
  padding: 5px;
}

.grid-wrapper {
  flex: 1;
  overflow: auto;
  min-height: 0;
}

:deep(.vue-grid-item) {
  transition: all 200ms ease;
  pointer-events: auto;
}

:deep(.vue-grid-item.resizing) {
  opacity: 0.9;
  z-index: 100;
}

:deep(.vue-grid-item.dragging) {
  z-index: 100;
  opacity: 0.8;
}
</style>
