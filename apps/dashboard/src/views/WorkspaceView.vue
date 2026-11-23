<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { DockviewVue, themeDark } from 'dockview-vue'
import type { DockviewReadyEvent } from 'dockview-vue'
import 'dockview-vue/dist/styles/dockview.css'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'
import { views } from '@/shell/registries'
import DashboardGrid from '@/shell/DashboardGrid.vue'
import PluginErrorBoundary from '@/shell/PluginErrorBoundary.vue'
import WorkspaceViewPanel from '@/shell/WorkspaceViewPanel.vue'

const workspaceStore = useWorkspaceStore()
const dockApi = shallowRef<DockviewReadyEvent['api']>()
const addMenuOpen = ref(false)
const importInput = ref<HTMLInputElement>()
const availableViews = computed(() => [...views.entries.value].sort((a, b) => a.title.localeCompare(b.title)))
let syncingPanels = false
const disposables: Array<{ dispose: () => void }> = []

onMounted(async () => { await workspaceStore.load() })
onBeforeUnmount(() => {
  disposables.forEach((disposable) => disposable.dispose())
  void workspaceStore.flush()
})

watch(
  () => workspaceStore.tabs.map((tab) => `${tab.id}:${tab.title}`).join('|'),
  () => { void nextTick(syncPanels) },
)

function onDockviewReady({ api }: DockviewReadyEvent) {
  dockApi.value = api
  for (const tab of workspaceStore.tabs) {
    api.addPanel({
      id: tab.id,
      component: tab.kind === 'dashboard' ? 'dashboard-panel' : 'view-panel',
      title: tab.title,
      params: { tabId: tab.id },
      renderer: 'onlyWhenVisible',
      inactive: tab.id !== workspaceStore.document.activeTabId,
    })
  }

  disposables.push(api.onDidActivePanelChange(({ panel }) => {
    if (panel) workspaceStore.activateTab(panel.id)
  }))
  disposables.push(api.onDidRemovePanel((panel) => {
    if (!syncingPanels) workspaceStore.removeTab(panel.id)
  }))
  disposables.push(api.onDidMutateLayout((event) => {
    if (!syncingPanels && event.kind === 'move') {
      workspaceStore.reorderTabs(api.panels.map((panel) => panel.id))
    }
  }))

  const activePanel = api.panels.find((panel) => panel.id === workspaceStore.document.activeTabId)
  activePanel?.api.setActive()
}

function syncPanels() {
  const api = dockApi.value
  if (!api || !workspaceStore.loaded) return

  syncingPanels = true
  try {
    const tabIds = new Set(workspaceStore.tabs.map((tab) => tab.id))
    for (const panel of [...api.panels]) {
      if (!tabIds.has(panel.id)) api.removePanel(panel)
    }

    for (const tab of workspaceStore.tabs) {
      const existing = api.panels.find((panel) => panel.id === tab.id)
      if (existing) {
        existing.api.setTitle(tab.title)
      } else {
        api.addPanel({
          id: tab.id,
          component: tab.kind === 'dashboard' ? 'dashboard-panel' : 'view-panel',
          title: tab.title,
          params: { tabId: tab.id },
          renderer: 'onlyWhenVisible',
          inactive: true,
        })
      }
    }

    const activePanel = api.panels.find((panel) => panel.id === workspaceStore.document.activeTabId)
    activePanel?.api.setActive()
  } finally {
    syncingPanels = false
  }
}

async function createDashboard() {
  addMenuOpen.value = false
  const tab = workspaceStore.addDashboard()
  await nextTick()
  syncPanels()
  activatePanel(tab.id)
}

async function createView(view: (typeof views.entries.value)[number]) {
  addMenuOpen.value = false
  const tab = workspaceStore.addView(view)
  await nextTick()
  syncPanels()
  activatePanel(tab.id)
}

function activatePanel(tabId: string) {
  const panel = dockApi.value?.panels.find((item) => item.id === tabId)
  panel?.api.setActive()
}

function renameActiveTab() {
  const tab = workspaceStore.activeTab
  if (!tab) return
  const title = window.prompt('Rename tab', tab.title)
  if (!title?.trim()) return
  workspaceStore.renameTab(tab.id, title)
  dockApi.value?.panels.find((panel) => panel.id === tab.id)?.api.setTitle(title.trim())
}

function closeActiveTab() {
  const tabId = workspaceStore.document.activeTabId
  const panel = dockApi.value?.panels.find((item) => item.id === tabId)
  if (panel) dockApi.value?.removePanel(panel)
  else workspaceStore.removeTab(tabId)
}

function chooseImport() {
  importInput.value?.click()
}

async function importWorkspace(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !window.confirm('Replace the current workspace with this file?')) return
  const imported = await workspaceStore.importWorkspaceFile(file)
  if (!imported) {
    window.alert('This file is not a valid workspace or legacy widget layout.')
    return
  }
  await nextTick()
  syncPanels()
}

function disablePanel(tabId: string) {
  workspaceStore.removeTab(tabId)
}
</script>

<template>
  <main v-if="workspaceStore.loaded" class="workspace-page">
    <header class="workspace-toolbar">
      <div class="workspace-actions">
        <div class="add-control">
          <button type="button" aria-label="Add workspace tab" :aria-expanded="addMenuOpen" @click="addMenuOpen = !addMenuOpen">
            + Add tab
          </button>
          <div v-if="addMenuOpen" class="add-menu" role="menu">
            <button type="button" role="menuitem" @click="createDashboard">New Dashboard</button>
            <button
              v-for="view in availableViews"
              :key="view.id"
              type="button"
              role="menuitem"
              @click="createView(view)"
            >
              {{ view.icon ? `${view.icon} ` : '' }}{{ view.title }}
            </button>
          </div>
        </div>
        <button type="button" aria-label="Rename active tab" @click="renameActiveTab">Rename</button>
        <button type="button" aria-label="Close active tab" @click="closeActiveTab">Close tab</button>
      </div>
      <div class="workspace-actions">
        <button type="button" @click="workspaceStore.exportWorkspace">Export</button>
        <button type="button" @click="chooseImport">Import</button>
        <input ref="importInput" class="hidden" type="file" accept=".json,application/json" @change="importWorkspace">
      </div>
    </header>

    <div class="workspace-dockview">
      <DockviewVue
        class="dockview-root"
        style="width: 100%; height: 100%"
        :theme="themeDark"
        :disable-floating-groups="true"
        :dnd-edges="false"
        @ready="onDockviewReady"
      >
        <template #panel-dashboard-panel="{ params }">
          <PluginErrorBoundary :owner-id="'core dashboard'" @disable="disablePanel(params.tabId)">
            <DashboardGrid :tab-id="params.tabId" />
          </PluginErrorBoundary>
        </template>
        <template #panel-view-panel="{ params }">
          <WorkspaceViewPanel :tab-id="params.tabId" />
        </template>
      </DockviewVue>
    </div>
  </main>
  <div v-else class="workspace-loading" role="status">Loading workspace…</div>
</template>

<style scoped>
.workspace-page {
  display: flex;
  height: calc(100vh - var(--navbar-height));
  min-height: 0;
  flex-direction: column;
}

.workspace-toolbar {
  display: flex;
  min-height: 42px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 10px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-panel);
}

.workspace-actions { display: flex; align-items: center; gap: 6px; }
.workspace-actions > button,
.add-control > button {
  padding: 5px 9px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background: var(--color-bg);
  color: var(--color-text);
  cursor: pointer;
}
.add-control { position: relative; }
.add-menu {
  position: absolute;
  z-index: 20;
  top: calc(100% + 5px);
  left: 0;
  display: flex;
  min-width: 190px;
  flex-direction: column;
  padding: 5px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-panel);
  box-shadow: 0 8px 24px rgb(0 0 0 / 30%);
}
.add-menu button { padding: 7px 9px; text-align: left; color: var(--color-text); }
.add-menu button:hover { background: var(--color-hover); }
.workspace-dockview { flex: 1; min-height: 0; }
.dockview-root { width: 100%; height: 100%; }
.workspace-loading { display: grid; min-height: 40vh; place-items: center; color: var(--color-text-muted); }
</style>
