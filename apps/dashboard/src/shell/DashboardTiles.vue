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
let syncingPanels = false
let saveTimer: ReturnType<typeof setTimeout> | undefined
const disposables: Array<{ dispose: () => void }> = []

onMounted(() => { void workspaceStore.load() })
onBeforeUnmount(() => {
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

  syncingPanels = true
  try {
    // Gridview.movePanel calculates the target path before removing the source.
    // Removing a panel can collapse that branch and invalidate the cached path.
    api.removePanel(source)
    api.addPanel({
      id: sourceId,
      component: 'widget',
      params: { widgetId: sourceId, tabId: dashboardTabId.value },
      position: { direction, referencePanel: targetId },
    })
  } finally {
    syncingPanels = false
  }
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
    }

    ids.forEach((id, index) => {
      if (api.getPanel(id)) return
      const previous = index > 0 ? ids[index - 1] : undefined
      api.addPanel({
        id,
        component: 'widget',
        params: { widgetId: id, tabId: dashboardTabId.value },
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
  persistTileState()
}

function persistTileState() {
  const api = gridApi.value
  if (!api || syncingPanels) return
  const state = api.panels.length ? JSON.parse(JSON.stringify(api.toJSON())) as TileLayoutState : null
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
  <div class="dashboard-tiles-container" @contextmenu="handleDashboardContextMenu">
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
    <GridviewVue
      class="tile-grid"
      :orientation="Orientation.VERTICAL"
      :components="tileComponents"
      @ready="onGridReady"
    />
    <input ref="importInput" class="hidden" type="file" accept=".json,application/json" @change="importWorkspace">
  </div>
</template>

<style scoped>
.dashboard-tiles-container { position: relative; display: flex; width: 100%; height: 100%; min-width: 0; min-height: 0; flex-direction: column; }
.dashboard-panel-host { position: absolute; z-index: 5; inset: 0; pointer-events: none; }
.dashboard-panel-host :deep(.error-content) { pointer-events: none; }
.dashboard-panel-host :deep(.error-card) { pointer-events: auto; }
.tile-grid { flex: 1 1 0; width: 100%; height: 100%; min-height: 0; }
</style>
