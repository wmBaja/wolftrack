<script setup lang="ts">
import { computed, h, nextTick, onBeforeUnmount, onMounted, provide, ref, shallowRef, watch } from 'vue'
import { GridviewVue, Orientation } from 'dockview-vue'
import type { GridviewReadyEvent, VueComponent } from 'dockview-vue'
import type { Direction, GridviewApi } from 'dockview-vue'
import 'dockview-vue/dist/styles/dockview.css'
import ContextMenu from '@imengyu/vue3-context-menu'
import { confirmDialog } from '@/core/dialog'
import { useWidgetStore } from '@/core/stores/widgetStore'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'
import { commands, panels } from '@/shell/registries'
import DashboardTilePanel from '@/shell/DashboardTilePanel.vue'
import PluginErrorBoundary from '@/shell/PluginErrorBoundary.vue'
import type { TileLayoutState } from '@/core/workspace'
import { commandsForTab } from '@/shell/contextCommands'

const props = defineProps<{ tabId?: string }>()
const workspaceStore = useWorkspaceStore()
const widgetStore = useWidgetStore()
const dashboardTabId = computed(() => props.tabId ?? workspaceStore.document.activeTabId)
const dashboard = computed(() => workspaceStore.getDashboardTab(dashboardTabId.value))
const dashboardWidgets = computed(() => dashboard.value?.layout.widgets ?? [])
const dashboardCommands = computed(() => commandsForTab(commands.entries.value, dashboard.value, true))
const dashboardPanels = computed(() => panels.entries.value
  .filter((panel) => panel.location === 'dashboard')
  .sort((a, b) => (a.order ?? 0) - (b.order ?? 0)))
const tileComponents = { widget: DashboardTilePanel as unknown as VueComponent }
const importInput = ref<HTMLInputElement>()
const gridApi = shallowRef<GridviewApi>()
const viewportElement = ref<HTMLDivElement>()
const canvasElement = ref<HTMLDivElement>()
const minimumCanvasWidth = ref(0)
const minimumCanvasHeight = ref(0)
const manualCanvasWidth = ref(0)
const manualCanvasHeight = ref(0)
const canvasResizeHover = ref<'width' | 'height' | null>(null)
const activeCanvasResize = ref<{
  pointerId: number
  axis: 'width' | 'height'
  startPosition: number
  lastPosition: number
  lastClientX: number
  lastClientY: number
  startSize: number
  target: HTMLElement
  mode: 'border' | 'sash'
} | null>(null)
let syncingPanels = false
let saveTimer: ReturnType<typeof setTimeout> | undefined
let resizeAutogrowTimer: ReturnType<typeof setInterval> | undefined
let resizeCursorPanel: HTMLElement | undefined
const disposables: Array<{ dispose: () => void }> = []
const MIN_WIDGET_WIDTH = 320
const MIN_WIDGET_HEIGHT = 220
const BORDER_RESIZE_HIT_SIZE = 32
const OUTER_EDGE_ALIGNMENT_TOLERANCE = 24

onMounted(() => { void workspaceStore.load() })
onBeforeUnmount(() => {
  window.removeEventListener('pointermove', resizeCanvas, true)
  window.removeEventListener('pointerup', finishCanvasResize)
  window.removeEventListener('pointercancel', finishCanvasResize)
  if (resizeAutogrowTimer) clearInterval(resizeAutogrowTimer)
  disposables.forEach((disposable) => disposable.dispose())
  if (saveTimer) clearTimeout(saveTimer)
  persistTileState()
})

watch(() => dashboardWidgets.value.map((widget) => String(widget.i)).join('|'), async () => {
  await nextTick()
  syncPanels()
})

function onGridReady({ api }: GridviewReadyEvent) {
  gridApi.value = api
  const state = dashboard.value?.layout.state
  const widgetIds = new Set(dashboardWidgets.value.map(widget => String(widget.i)))
  const canvasSize = readSavedCanvasSize(state)
  manualCanvasWidth.value = canvasSize?.width ?? 0
  manualCanvasHeight.value = canvasSize?.height ?? 0

  if (state) {
    try {
      api.fromJSON(state as TileLayoutState as never)
    } catch (error) {
      console.warn('Could not restore dashboard tile layout; rebuilding it:', error)
      api.clear()
    }
  }

  syncingPanels = true
  syncPanels()
  syncingPanels = false

  // Restored tile state is only accepted when it contains no unknown panel IDs.
  if (api.panels.some(panel => !widgetIds.has(panel.id))) {
    syncingPanels = true
    api.clear()
    syncPanels()
    syncingPanels = false
  }

  disposables.push(api.onDidLayoutChange(() => {
    updateCanvasMinimums()
    if (syncingPanels) return
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(persistTileState, 120)
  }))
  disposables.push(api.onDidRemovePanel((panel) => {
    if (syncingPanels) return
    widgetStore.removeWidget(panel.id, dashboardTabId.value)
  }))
}

function repositionPanel(sourceId: string, targetId: string, direction: Direction) {
  const api = gridApi.value
  const source = api?.getPanel(sourceId)
  const target = api?.getPanel(targetId)
  if (!api || !source || !target) return
  const sourceLayout = api.panels.find((panel) => panel.id === sourceId)
  const minimumWidth = Math.max(MIN_WIDGET_WIDTH, sourceLayout?.minimumWidth ?? MIN_WIDGET_WIDTH)
  const minimumHeight = Math.max(MIN_WIDGET_HEIGHT, sourceLayout?.minimumHeight ?? MIN_WIDGET_HEIGHT)

  syncingPanels = true
  try {
    // Gridview.movePanel calculates the target path before removing the source.
    // Removing a panel can collapse that branch and invalidate the cached path.
    api.removePanel(source)
    api.addPanel({
      id: sourceId,
      component: 'widget',
      params: { widgetId: sourceId, tabId: dashboardTabId.value },
      minimumWidth,
      minimumHeight,
      position: { direction, referencePanel: targetId },
    })
  } finally {
    syncingPanels = false
  }
  updateCanvasMinimums()
  persistTileState()
}

provide('wolftrack-reposition-panel', repositionPanel)

function syncPanels() {
  const api = gridApi.value
  if (!api) return
  const ids = dashboardWidgets.value.map(widget => String(widget.i))
  const wanted = new Set(ids)

  syncingPanels = true
  try {
    for (const panel of [...api.panels]) {
      if (!wanted.has(panel.id)) api.removePanel(panel)
      else {
        const savedMinimums = findSavedPanelMinimums(panel.id)
        panel.api.setConstraints({
          minimumWidth: Math.max(MIN_WIDGET_WIDTH, panel.minimumWidth, savedMinimums?.width ?? 0),
          minimumHeight: Math.max(MIN_WIDGET_HEIGHT, panel.minimumHeight, savedMinimums?.height ?? 0),
        })
      }
    }

    ids.forEach((id, index) => {
      if (api.getPanel(id)) return
      const previous = index > 0 ? ids[index - 1] : undefined
      api.addPanel({
        id,
        component: 'widget',
        params: { widgetId: id, tabId: dashboardTabId.value },
        minimumWidth: MIN_WIDGET_WIDTH,
        minimumHeight: MIN_WIDGET_HEIGHT,
        ...(previous ? {
          position: {
            direction: index % 2 === 0 ? 'below' : 'right',
            referencePanel: previous,
          },
        } : {}),
      })
    })
  } finally {
    syncingPanels = false
  }
  updateCanvasMinimums()
  persistTileState()
}

function updateCanvasMinimums() {
  const api = gridApi.value
  minimumCanvasWidth.value = api?.panels.length ? api.minimumWidth : 0
  minimumCanvasHeight.value = api?.panels.length ? api.minimumHeight : 0
}

function readSavedCanvasSize(state: TileLayoutState | null | undefined) {
  if (!state || typeof state !== 'object') return undefined
  const canvasSize = (state as Record<string, unknown>).canvasSize
  if (!canvasSize || typeof canvasSize !== 'object') return undefined
  const saved = canvasSize as Record<string, unknown>
  return {
    width: typeof saved.width === 'number' ? saved.width : 0,
    height: typeof saved.height === 'number' ? saved.height : 0,
  }
}

function startCanvasResize(event: PointerEvent) {
  if (event.button !== 0) return
  const target = event.target instanceof Element ? event.target : null
  if (!target) return
  const sash = target.closest<HTMLElement>('.dv-sash')
  if (sash && gridApi.value && gridApi.value.panels.length > 1) {
    const split = sash.closest<HTMLElement>('.dv-split-view-container')
    if (!split) return
    const axis = split.classList.contains('dv-horizontal') ? 'width' : 'height'
    const position = axis === 'width' ? event.clientX : event.clientY
    activeCanvasResize.value = {
      pointerId: event.pointerId,
      axis,
      startPosition: position,
      lastPosition: position,
      lastClientX: event.clientX,
      lastClientY: event.clientY,
      startSize: axis === 'width'
        ? canvasElement.value?.getBoundingClientRect().width ?? 0
        : canvasElement.value?.getBoundingClientRect().height ?? 0,
      target: sash,
      mode: 'sash',
    }
    window.addEventListener('pointermove', resizeCanvas, true)
    window.addEventListener('pointerup', finishCanvasResize)
    window.addEventListener('pointercancel', finishCanvasResize)
    startResizeEdgeAutogrow()
    return
  }

  const panel = target.closest<HTMLElement>('.tile-panel')
  if (!panel) return
  const axis = resizableOuterEdge(panel, event.clientX, event.clientY)
  if (!axis) return
  event.preventDefault()
  event.stopPropagation()
  const canvas = canvasElement.value?.getBoundingClientRect()
  if (!canvas) return
  const position = axis === 'width' ? event.clientX : event.clientY
  activeCanvasResize.value = {
    pointerId: event.pointerId,
    axis,
    startPosition: position,
    lastPosition: position,
    lastClientX: event.clientX,
    lastClientY: event.clientY,
    startSize: axis === 'width' ? canvas.width : canvas.height,
    target: panel,
    mode: 'border',
  }
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  window.addEventListener('pointermove', resizeCanvas, true)
  window.addEventListener('pointerup', finishCanvasResize)
  window.addEventListener('pointercancel', finishCanvasResize)
  startResizeEdgeAutogrow()
}

function updateResizeCursor(event: PointerEvent) {
  const panel = event.target instanceof Element ? event.target.closest<HTMLElement>('.tile-panel') : null
  if (resizeCursorPanel && resizeCursorPanel !== panel) {
    resizeCursorPanel.style.cursor = ''
  }
  resizeCursorPanel = panel ?? undefined
  const activeResize = activeCanvasResize.value
  if (activeResize?.mode === 'border') {
    canvasResizeHover.value = activeResize.axis
    activeResize.target.style.cursor = activeResize.axis === 'width' ? 'ew-resize' : 'ns-resize'
    resizeCursorPanel = activeResize.target
    return
  }
  if (!panel || activeResize) {
    canvasResizeHover.value = null
    if (panel) {
      panel.style.cursor = ''
    }
    return
  }
  const edge = resizableOuterEdge(panel, event.clientX, event.clientY)
  canvasResizeHover.value = edge ?? null
  panel.style.cursor = edge === 'width' ? 'ew-resize' : edge === 'height' ? 'ns-resize' : ''
}

function resizableOuterEdge(panel: HTMLElement, x: number, y: number): 'width' | 'height' | undefined {
  const panelBounds = panel.getBoundingClientRect()
  const canvasBounds = canvasElement.value?.getBoundingClientRect()
  if (!canvasBounds) return undefined
  const extendsToRightEdge = panelBounds.right >= canvasBounds.right - OUTER_EDGE_ALIGNMENT_TOLERANCE
  const extendsToBottomEdge = panelBounds.bottom >= canvasBounds.bottom - OUTER_EDGE_ALIGNMENT_TOLERANCE
  const nearRight = extendsToRightEdge
    && x >= panelBounds.right - BORDER_RESIZE_HIT_SIZE
    && x <= panelBounds.right + 2
  const nearBottom = extendsToBottomEdge
    && y >= panelBounds.bottom - BORDER_RESIZE_HIT_SIZE
    && y <= panelBounds.bottom + 2
  return nearRight ? 'width' : nearBottom ? 'height' : undefined
}

function setManualCanvasDimension(axis: 'width' | 'height', size: number) {
  const viewport = viewportElement.value
  if (!viewport) return
  if (axis === 'width') {
    manualCanvasWidth.value = size > viewport.clientWidth ? Math.round(size) : 0
  } else {
    manualCanvasHeight.value = size > viewport.clientHeight ? Math.round(size) : 0
  }
}

function resizeCanvas(event: PointerEvent) {
  const resize = activeCanvasResize.value
  if (!resize || resize.pointerId !== event.pointerId) return
  const position = resize.axis === 'width' ? event.clientX : event.clientY
  resize.lastPosition = position
  resize.lastClientX = event.clientX
  resize.lastClientY = event.clientY
  if (resize.mode === 'border') {
    event.preventDefault()
    setManualCanvasDimension(resize.axis, resize.startSize + position - resize.startPosition)
  } else {
    const sashBounds = resize.target.getBoundingClientRect()
    const sashPosition = resize.axis === 'width'
      ? sashBounds.left + sashBounds.width / 2
      : sashBounds.top + sashBounds.height / 2
    const outwardDelta = position - sashPosition
    if (resize.target.classList.contains('dv-maximum') && outwardDelta > 0) {
      const currentSize = resize.axis === 'width'
        ? canvasElement.value?.getBoundingClientRect().width ?? resize.startSize
        : canvasElement.value?.getBoundingClientRect().height ?? resize.startSize
      setManualCanvasDimension(resize.axis, currentSize + outwardDelta)
    }
  }
}

function startResizeEdgeAutogrow() {
  if (resizeAutogrowTimer) clearInterval(resizeAutogrowTimer)
  resizeAutogrowTimer = window.setInterval(expandCanvasAtViewportEdge, 60)
}

function expandCanvasAtViewportEdge() {
  const resize = activeCanvasResize.value
  const viewport = viewportElement.value
  const canvas = canvasElement.value
  if (!resize || !viewport || !canvas || resize.lastPosition <= resize.startPosition) return

  const bounds = viewport.getBoundingClientRect()
  const nearWindowEdge = resize.axis === 'width'
    ? resize.lastClientX >= bounds.right - 28
    : resize.lastClientY >= bounds.bottom - 28
  const sashAtLimit = resize.mode !== 'sash' || resize.target.classList.contains('dv-maximum')
  if (!nearWindowEdge || !sashAtLimit) return

  const size = resize.axis === 'width' ? canvas.getBoundingClientRect().width : canvas.getBoundingClientRect().height
  setManualCanvasDimension(resize.axis, size + 20)
}

function finishCanvasResize(event: PointerEvent) {
  if (activeCanvasResize.value?.pointerId !== event.pointerId) return
  const finishedResize = activeCanvasResize.value
  activeCanvasResize.value = null
  if (finishedResize.mode === 'border') {
    canvasResizeHover.value = finishedResize.axis
    finishedResize.target.style.cursor = finishedResize.axis === 'width' ? 'ew-resize' : 'ns-resize'
    resizeCursorPanel = finishedResize.target
  }
  window.removeEventListener('pointermove', resizeCanvas, true)
  window.removeEventListener('pointerup', finishCanvasResize)
  window.removeEventListener('pointercancel', finishCanvasResize)
  if (resizeAutogrowTimer) clearInterval(resizeAutogrowTimer)
  resizeAutogrowTimer = undefined
  persistTileState()
}

function findSavedPanelMinimums(widgetId: string) {
  const state = dashboard.value?.layout.state
  if (!state || typeof state !== 'object') return undefined
  const grid = (state as Record<string, unknown>).grid
  if (!grid || typeof grid !== 'object') return undefined
  const root = (grid as Record<string, unknown>).root

  function visit(node: unknown): { width: number; height: number } | undefined {
    if (!node || typeof node !== 'object') return undefined
    const record = node as Record<string, unknown>
    if (record.type === 'leaf' && record.data && typeof record.data === 'object') {
      const data = record.data as Record<string, unknown>
      if (data.id === widgetId) {
        return {
          width: typeof data.minimumWidth === 'number' ? data.minimumWidth : 0,
          height: typeof data.minimumHeight === 'number' ? data.minimumHeight : 0,
        }
      }
    }
    if (Array.isArray(record.data)) {
      for (const child of record.data) {
        const result = visit(child)
        if (result) return result
      }
    }
    return undefined
  }

  return visit(root)
}

function persistTileState() {
  const api = gridApi.value
  if (!api || syncingPanels) return
  const state = api.panels.length ? {
    ...JSON.parse(JSON.stringify(api.toJSON())),
    ...(manualCanvasWidth.value || manualCanvasHeight.value ? {
      canvasSize: {
        width: manualCanvasWidth.value || undefined,
        height: manualCanvasHeight.value || undefined,
      },
    } : {}),
  } as TileLayoutState : null
  workspaceStore.setDashboardTileState(dashboardTabId.value, state)
}

function handleDashboardContextMenu(event: MouseEvent) {
  event.preventDefault()
  ContextMenu.showContextMenu({
    x: event.x,
    y: event.y,
    theme: 'mac dark',
    zIndex: 1000,
    items: [
      ...dashboardCommands.value.map((command) => ({
        label: command.title,
        icon: h('span', command.icon ?? ''),
        onClick: () => command.run({ tabId: dashboardTabId.value }),
      })),
      { divided: true },
      {
        label: 'Export Workspace',
        icon: h('span', '📤'),
        onClick: () => workspaceStore.exportWorkspace(),
      },
      {
        label: 'Import Workspace',
        icon: h('span', '📥'),
        onClick: requestImportWorkspace,
      },
      {
        label: 'Clear All Widgets',
        icon: h('span', '🗑️'),
        customClass: 'context-menu-danger',
        onClick: clearDashboard,
      },
    ],
  })
}

async function clearDashboard() {
  const ok = await confirmDialog(
    'Delete All Widgets',
    'Are you sure you want to delete all widgets in this dashboard?',
    { confirmText: 'Delete', danger: true },
  )
  if (ok) widgetStore.clearAll(dashboardTabId.value)
}

function requestImportWorkspace() {
  importInput.value?.click()
}

async function importWorkspace(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !window.confirm('Replace the current workspace with this file?')) return
  const imported = await workspaceStore.importWorkspaceFile(file)
  if (!imported) window.alert('This file is not a valid workspace or legacy widget layout.')
}

function disablePanel(panelId: string) {
  panels.entries.value = panels.entries.value.filter((panel) => panel.id !== panelId)
}

</script>

<template>
  <div
    class="dashboard-tiles-container"
    :data-canvas-resize-hover="canvasResizeHover ?? undefined"
    @contextmenu="handleDashboardContextMenu"
  >
    <div class="dashboard-panel-host">
      <PluginErrorBoundary
        v-for="panel in dashboardPanels"
        :key="panel.id"
        :owner-id="panel.id"
        @disable="disablePanel(panel.id)"
      >
        <component :is="panel.component" />
      </PluginErrorBoundary>
    </div>
    <div
      ref="viewportElement"
      class="dashboard-viewport"
      :style="{
        '--dashboard-min-width': `${minimumCanvasWidth}px`,
        '--dashboard-min-height': `${minimumCanvasHeight}px`,
        '--dashboard-user-width': `${manualCanvasWidth}px`,
        '--dashboard-user-height': `${manualCanvasHeight}px`,
      }"
    >
      <div
        ref="canvasElement"
        class="dashboard-canvas"
        @pointerdown.capture="startCanvasResize"
        @pointermove.capture="updateResizeCursor"
      >
        <GridviewVue
          class="tile-grid"
          :orientation="Orientation.VERTICAL"
          :components="tileComponents"
          @ready="onGridReady"
        />
      </div>
    </div>
    <input ref="importInput" class="hidden" type="file" accept=".json,application/json" @change="importWorkspace">
  </div>
</template>

<style scoped>
.dashboard-tiles-container { position: relative; display: flex; width: 100%; height: 100%; min-width: 0; min-height: 0; flex-direction: column; }
.dashboard-panel-host { position: absolute; z-index: 5; inset: 0; pointer-events: none; }
.dashboard-panel-host :deep(.error-content) { pointer-events: none; }
.dashboard-panel-host :deep(.error-card) { pointer-events: auto; }
.dashboard-viewport {
  position: absolute;
  inset: 0;
  overflow: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border) transparent !important;
}
.dashboard-viewport::-webkit-scrollbar {
  width: 10px;
  height: 10px;
  background: transparent !important;
}
.dashboard-viewport::-webkit-scrollbar-track,
.dashboard-viewport::-webkit-scrollbar-track-piece,
.dashboard-viewport::-webkit-scrollbar-corner,
.dashboard-viewport::-webkit-scrollbar-button {
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
.dashboard-viewport::-webkit-scrollbar-button { display: none !important; width: 0; height: 0; }
.dashboard-viewport::-webkit-scrollbar-thumb {
  border: 2px solid transparent;
  border-radius: 5px;
  background: var(--color-border);
  background-clip: padding-box;
}
.dashboard-viewport::-webkit-scrollbar-thumb:hover { background: var(--color-accent); }
.dashboard-viewport::-webkit-scrollbar-corner { background: transparent; }
.dashboard-canvas {
  width: max(100%, var(--dashboard-min-width, 0px), var(--dashboard-user-width, 0px));
  height: max(100%, var(--dashboard-min-height, 0px), var(--dashboard-user-height, 0px));
}
.tile-grid { width: 100%; height: 100%; min-width: 0; min-height: 0; }
.dashboard-tiles-container[data-canvas-resize-hover="width"]::before,
.dashboard-tiles-container[data-canvas-resize-hover="height"]::before {
  position: absolute;
  z-index: 109;
  display: block;
  content: '';
  pointer-events: none;
}
.dashboard-tiles-container[data-canvas-resize-hover="width"]::before {
  top: 0;
  right: 0;
  bottom: 0;
  width: 28px;
  background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--color-accent) 13%, transparent));
}
.dashboard-tiles-container[data-canvas-resize-hover="height"]::before {
  right: 0;
  bottom: 0;
  left: 0;
  height: 28px;
  background: linear-gradient(180deg, transparent, color-mix(in srgb, var(--color-accent) 13%, transparent));
}
</style>
