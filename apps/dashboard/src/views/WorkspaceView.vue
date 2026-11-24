<script setup lang="ts">
import { computed, h, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { DockviewVue, themeDark } from 'dockview-vue'
import type { DockviewReadyEvent } from 'dockview-vue'
import 'dockview-vue/dist/styles/dockview.css'
import ContextMenu from '@imengyu/vue3-context-menu'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'
import { views } from '@/shell/registries'
import DashboardTiles from '@/shell/DashboardTiles.vue'
import PluginErrorBoundary from '@/shell/PluginErrorBoundary.vue'
import WorkspaceDockviewTab from '@/shell/WorkspaceDockviewTab.vue'
import WorkspaceViewPanel from '@/shell/WorkspaceViewPanel.vue'

const workspaceStore = useWorkspaceStore()
const dockApi = shallowRef<DockviewReadyEvent['api']>()
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

  api.panels.find((panel) => panel.id === workspaceStore.document.activeTabId)?.api.setActive()
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

    api.panels.find((panel) => panel.id === workspaceStore.document.activeTabId)?.api.setActive()
  } finally {
    syncingPanels = false
  }
}

async function createDashboard(groupId?: string) {
  const tab = workspaceStore.addDashboard()
  await nextTick()
  syncPanels()
  movePanelToGroup(tab.id, groupId)
  activatePanel(tab.id)
}

async function createView(view: (typeof views.entries.value)[number], groupId?: string) {
  const tab = workspaceStore.addView(view)
  await nextTick()
  syncPanels()
  movePanelToGroup(tab.id, groupId)
  activatePanel(tab.id)
}

function movePanelToGroup(tabId: string, groupId?: string) {
  if (!groupId) return
  const api = dockApi.value
  const group = api?.groups.find((item) => item.id === groupId)
  const panel = api?.panels.find((item) => item.id === tabId)
  if (group && panel && panel.api.group.id !== group.id) {
    panel.api.moveTo({ group, index: group.panels.length, skipSetActive: true })
  }
}

function activatePanel(tabId: string) {
  dockApi.value?.panels.find((item) => item.id === tabId)?.api.setActive()
}

function showAddTabMenu(event: MouseEvent, groupId?: string) {
  event.preventDefault()
  ContextMenu.showContextMenu({
    x: event.x,
    y: event.y,
    theme: 'mac dark',
    zIndex: 1000,
    items: [
      { label: 'New Dashboard', icon: h('span', '＋'), onClick: () => void createDashboard(groupId) },
      ...availableViews.value.map((view) => ({
        label: `${view.icon ? `${view.icon} ` : ''}${view.title}`,
        onClick: () => void createView(view, groupId),
      })),
    ],
  })
}

function showWorkspaceContextMenu(event: MouseEvent) {
  event.preventDefault()
  ContextMenu.showContextMenu({
    x: event.x,
    y: event.y,
    theme: 'mac dark',
    zIndex: 1000,
    items: [
      { label: 'Export Workspace', icon: h('span', '📤'), onClick: () => workspaceStore.exportWorkspace() },
      { label: 'Import Workspace', icon: h('span', '📥'), onClick: chooseImport },
    ],
  })
}

function handleDockviewContextMenu(event: MouseEvent) {
  if (!(event.target instanceof Element)
    || !event.target.closest('.dv-tabs-and-actions-container')
    || event.target.closest('.dv-tab, .workspace-tab-add')) return
  showWorkspaceContextMenu(event)
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
    <div class="workspace-dockview" @contextmenu.capture="handleDockviewContextMenu">
      <DockviewVue
        class="dockview-root"
        style="width: 100%; height: 100%"
        :theme="themeDark"
        :popout-url="workspaceStore.popoutsEnabled ? workspaceStore.popoutUrl : undefined"
        :disable-floating-groups="true"
        @ready="onDockviewReady"
      >
        <template #defaultTab="tabProps">
          <WorkspaceDockviewTab :api="tabProps.api" @import-workspace="chooseImport" />
        </template>
        <template #leftHeaderActions="{ group }">
          <button
            type="button"
            class="workspace-tab-add"
            aria-label="Add workspace tab"
            aria-haspopup="menu"
            title="New dashboard"
            @click.stop="showAddTabMenu($event, group.id)"
            @contextmenu.prevent.stop="showAddTabMenu($event, group.id)"
          >
            +
          </button>
        </template>
        <template #panel-dashboard-panel="{ params }">
          <PluginErrorBoundary :owner-id="'core dashboard'" @disable="disablePanel(params.tabId)">
            <DashboardTiles :tab-id="params.tabId" />
          </PluginErrorBoundary>
        </template>
        <template #panel-view-panel="{ params }">
          <WorkspaceViewPanel :tab-id="params.tabId" />
        </template>
      </DockviewVue>
      <input ref="importInput" class="hidden" type="file" accept=".json,application/json" @change="importWorkspace">
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

.workspace-dockview { flex: 1; min-height: 0; }
.dockview-root {
  width: 100%;
  height: 100%;
}
:global(.workspace-page .dv-dockview) {
  --dv-group-view-background-color: var(--color-bg);
  --dv-tabs-and-actions-container-background-color: var(--color-panel);
  --dv-activegroup-visiblepanel-tab-background-color: var(--color-bg);
  --dv-activegroup-hiddenpanel-tab-background-color: var(--color-panel);
  --dv-inactivegroup-visiblepanel-tab-background-color: var(--color-bg);
  --dv-inactivegroup-hiddenpanel-tab-background-color: var(--color-panel);
  --dv-activegroup-visiblepanel-tab-color: var(--color-text);
  --dv-activegroup-hiddenpanel-tab-color: var(--color-text-muted);
  --dv-inactivegroup-visiblepanel-tab-color: var(--color-text);
  --dv-inactivegroup-hiddenpanel-tab-color: var(--color-text-muted);
  --dv-tab-divider-color: var(--color-border);
  --dv-tabs-container-scrollbar-color: var(--color-border);
  --dv-icon-hover-background-color: var(--color-hover);
  --dv-edge-dock-indicator-color: var(--color-accent);
  --dv-drag-over-background-color: color-mix(in srgb, var(--color-accent) 16%, transparent);
  --dv-drag-over-border: 1px solid var(--color-accent);
  --dv-tabs-and-actions-container-height: 38px;
  --dv-tab-margin: 3px 2px 0;
  --dv-tab-border-radius: 6px 6px 0 0;
  --dv-border-radius: 6px;
}
:global(.workspace-page .dv-tabs-and-actions-container) {
  box-sizing: border-box;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-panel);
}
:global(.workspace-page .dv-tabs-container) { gap: 3px; padding: 0 0 0 8px; }
:global(.workspace-page .dv-tab) {
  border: 1px solid transparent;
  border-bottom: 0;
  border-radius: 6px 6px 0 0;
  color: var(--color-text-muted);
  transition: background-color 120ms ease, color 120ms ease;
}
:global(.workspace-page .dv-tab.dv-inactive-tab:hover) {
  background: var(--color-hover);
  color: var(--color-text);
}
:global(.workspace-page .dv-tab.dv-active-tab) {
  border-color: var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
  box-shadow: inset 0 2px 0 var(--color-accent);
}
:global(.workspace-page .dv-left-actions-container) {
  display: flex;
  height: 100%;
  align-items: stretch;
  padding: 0 5px 0 2px;
}
.workspace-tab-add {
  display: grid;
  width: 24px;
  height: auto;
  align-self: stretch;
  place-items: center;
  margin-top: 3px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: var(--color-text);
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  transform: translateY(4px);
}
.workspace-tab-add:hover { background: var(--color-hover); }
.workspace-tab-add:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.workspace-loading { display: grid; min-height: 40vh; place-items: center; color: var(--color-text-muted); }
</style>
