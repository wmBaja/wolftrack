<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { GridviewVue, Orientation } from 'dockview-vue'
import type { GridviewReadyEvent, VueComponent } from 'dockview-vue'
import type { GridviewApi } from 'dockview-vue'
import 'dockview-vue/dist/styles/dockview.css'
import { useWidgetStore } from '@/core/stores/widgetStore'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'
import { confirmDialog } from '@/core/dialog'
import { commands, panels } from '@/shell/registries'
import DashboardTilePanel from '@/shell/DashboardTilePanel.vue'
import PluginErrorBoundary from '@/shell/PluginErrorBoundary.vue'
import type { TileLayoutState } from '@/core/workspace'

const props = defineProps<{ tabId?: string }>()
const workspaceStore = useWorkspaceStore()
const widgetStore = useWidgetStore()
const dashboardTabId = computed(() => props.tabId ?? workspaceStore.document.activeTabId)
const dashboard = computed(() => workspaceStore.getDashboardTab(dashboardTabId.value))
const dashboardWidgets = computed(() => dashboard.value?.layout.widgets ?? [])
const dashboardPanels = computed(() => panels.entries.value
  .filter((panel) => panel.location === 'dashboard')
  .sort((a, b) => (a.order ?? 0) - (b.order ?? 0)))
const dashboardCommands = computed(() => [...commands.entries.value].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)))
const tileComponents = { widget: DashboardTilePanel as unknown as VueComponent }
const addMenuOpen = ref(false)
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

async function runCommand(command: (typeof dashboardCommands.value)[number]) {
  addMenuOpen.value = false
  await command.run({ tabId: dashboardTabId.value })
}

async function clearDashboard() {
  const ok = await confirmDialog(
    'Delete All Widgets',
    'Are you sure you want to delete all widgets in this dashboard?',
    { confirmText: 'Delete', danger: true },
  )
  if (ok) widgetStore.clearAll(dashboardTabId.value)
}

function disablePanel(panelId: string) {
  panels.entries.value = panels.entries.value.filter((panel) => panel.id !== panelId)
}

</script>

<template>
  <div class="dashboard-tiles-container">
    <PluginErrorBoundary
      v-for="panel in dashboardPanels"
      :key="panel.id"
      :owner-id="panel.id"
      @disable="disablePanel(panel.id)"
    >
      <component :is="panel.component" />
    </PluginErrorBoundary>
    <header class="tiles-toolbar">
      <div class="tiles-add-control">
        <button type="button" aria-label="Add widget" :aria-expanded="addMenuOpen" @click="addMenuOpen = !addMenuOpen">
          + Widget
        </button>
        <div v-if="addMenuOpen" class="tiles-add-menu" role="menu">
          <button
            v-for="command in dashboardCommands"
            :key="command.id"
            type="button"
            role="menuitem"
            @click="runCommand(command)"
          >
            {{ command.icon ? `${command.icon} ` : '' }}{{ command.title }}
          </button>
        </div>
      </div>
      <span>{{ dashboardWidgets.length }} tiles</span>
      <button type="button" :disabled="dashboardWidgets.length === 0" @click="clearDashboard">Clear dashboard</button>
    </header>
    <GridviewVue
      class="tile-grid"
      :orientation="Orientation.VERTICAL"
      :components="tileComponents"
      @ready="onGridReady"
    />
  </div>
</template>

<style scoped>
.dashboard-tiles-container { display: flex; width: 100%; height: 100%; min-width: 0; min-height: 0; flex-direction: column; }
.tiles-toolbar {
  display: flex;
  min-height: 36px;
  align-items: center;
  gap: 8px;
  padding: 3px 8px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-panel);
  color: var(--color-text-muted);
}
.tiles-toolbar > span { flex: 1; }
.tiles-toolbar button {
  padding: 3px 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-bg);
  color: var(--color-text);
  cursor: pointer;
}
.tiles-toolbar button:disabled { cursor: not-allowed; opacity: .5; }
.tiles-add-control { position: relative; }
.tiles-add-menu {
  position: absolute;
  z-index: 30;
  top: calc(100% + 4px);
  left: 0;
  display: flex;
  min-width: 190px;
  flex-direction: column;
  padding: 4px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background: var(--color-panel);
}
.tiles-add-menu button { text-align: left; }
.tile-grid { flex: 1; min-height: 0; }
</style>
