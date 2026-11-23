<script setup lang="ts">
import { onMounted, ref, h, type Component, watch, computed } from 'vue'
import { GridLayout, GridItem } from 'grid-layout-plus'
import { useWidgetStore } from '@/core/stores/widgetStore'
import { confirmDialog } from '@/core/dialog'
import ContextMenu from '@imengyu/vue3-context-menu'
import MissingWidget from '@/shell/MissingWidget.vue'
import type { Widget } from '@/core/widgets'
import { commands, panels, widgets } from '@/shell/registries'
import PluginErrorBoundary from '@/shell/PluginErrorBoundary.vue'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'

const props = defineProps<{ tabId?: string }>()
const widgetStore = useWidgetStore()
const workspaceStore = useWorkspaceStore()
const dashboardTabId = computed(() => props.tabId ?? workspaceStore.document.activeTabId)
const dashboardWidgets = computed({
  get: () => widgetStore.getWidgets(dashboardTabId.value),
  set: (value: Widget[]) => workspaceStore.setDashboardWidgets(dashboardTabId.value, value),
})

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

const dashboardPanels = computed(() => panels.entries.value
  .filter((panel) => panel.location === 'dashboard')
  .sort((a, b) => (a.order ?? 0) - (b.order ?? 0)))
const dashboardCommands = computed(() => [...commands.entries.value].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)))

const widgetRefs = ref<Record<string, WidgetExpose>>({})
const gridWrapperRef = ref<HTMLElement>()
const GRID_COLS = 16
const GRID_ROW_HEIGHT = 30
const GRID_MARGIN = 5
const FALLBACK_CHART_SIZE = { w: 5, h: 15 }

onMounted(() => { void workspaceStore.load() })

watch(
  () => dashboardWidgets.value.length,
  () => {
    const currentIds = new Set(dashboardWidgets.value.map((w) => w.i))
    Object.keys(widgetRefs.value).forEach((id) => {
      if (!currentIds.has(id)) {
        delete widgetRefs.value[id]
      }
    })
  },
)

function handleLayoutUpdate(newLayout: Widget[]) {
  widgetStore.updateLayout(newLayout, dashboardTabId.value)
}

function setWidgetRef(widgetId: string, el: WidgetExpose | null) {
  if (el) {
    widgetRefs.value[widgetId] = el
  }
}

function disablePanel(panelId: string) {
  panels.entries.value = panels.entries.value.filter((panel) => panel.id !== panelId)
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

async function handleClearAll() {
  const ok = await confirmDialog(
    'Delete All Widgets',
    'Are you sure you want to delete all widgets?',
    { confirmText: 'Delete', danger: true },
  )
  if (ok) widgetStore.clearAll(dashboardTabId.value)
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
      ...dashboardCommands.value.map((command) => ({
        label: command.title,
        icon: h('span', command.icon ?? ''),
        onClick: () => command.run({ ...gridPos, ...chartSize, tabId: dashboardTabId.value }),
      })),
      {
        label: 'Export Workspace',
        icon: h('span', '📤'),
        onClick: () => workspaceStore.exportWorkspace(),
      },
      {
        label: 'Import Workspace',
        icon: h('span', '📥'),
        onClick: () => requestImportWorkspace(),
        divided: true,
      },
      {
        label: 'Clear All Widgets',
        icon: h('span', '🗑️'),
        customClass: 'context-menu-danger',
        onClick: handleClearAll,
      },
    ],
  })
}

function requestImportWorkspace() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = async () => {
    if (!input.files || !input.files[0]) return
    const file = input.files[0]
    try {
      const ok = await confirmDialog(
        'Import Workspace',
        'Import this workspace or legacy widget layout?',
        { confirmText: 'Import', danger: true },
      )
      if (!ok) return
      const imported = await workspaceStore.importWorkspaceFile(file)
      if (!imported) {
        await confirmDialog(
          'Import Workspace',
          'The selected file is not a valid workspace or legacy widget layout.',
          { confirmText: 'OK' , removeCancel: true },
        )
      }
    } catch {
      return
    }
  }
  input.click()
}
</script>

<template>
  <div class="dashboard-grid-container" @contextmenu="handleGridContextMenu">
    <PluginErrorBoundary
      v-for="panel in dashboardPanels"
      :key="panel.id"
      :owner-id="panel.id"
      @disable="disablePanel(panel.id)"
    >
      <component :is="panel.component as Component" />
    </PluginErrorBoundary>
    <div ref="gridWrapperRef" class="grid-wrapper custom-scrollbar">
      <GridLayout
        v-model:layout="dashboardWidgets"
        :col-num="GRID_COLS"
        :row-height="GRID_ROW_HEIGHT"
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
          v-for="item in dashboardWidgets"
          :key="item.i"
          :resize-option="{
            edges: { right: true, bottom: true },
          }"
          v-bind="item"
          drag-allow-from=".base-widget__header"
          drag-ignore-from=".base-widget__content"
        >
          <PluginErrorBoundary :owner-id="String(item.type)" @disable="widgetStore.removeWidget(String(item.i), dashboardTabId)">
            <component
              :is="(widgets.get((item as Widget).type)?.component as Component) || MissingWidget"
              :ref="(el: WidgetExpose | null) => setWidgetRef(String(item.i), el)"
              :widget-id="item.i"
              :data-widget-id="item.i"
            />
          </PluginErrorBoundary>
        </GridItem>
      </GridLayout>
    </div>
  </div>
</template>

<style scoped>
.dashboard-grid-container {
  display: flex;
  flex-direction: column;
  height: 100%;
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
