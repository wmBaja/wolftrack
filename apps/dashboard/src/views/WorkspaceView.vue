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
import WorkspaceViewPanel from '@/shell/WorkspaceViewPanel.vue'

const workspaceStore = useWorkspaceStore()
const dockApi = shallowRef<DockviewReadyEvent['api']>()
const importInput = ref<HTMLInputElement>()
const editingTabId = ref<string>()
const editingTitle = ref('')
const tabTitleInput = ref<HTMLInputElement>()
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
  const tab = workspaceStore.addDashboard()
  await nextTick()
  syncPanels()
  activatePanel(tab.id)
}

async function createView(view: (typeof views.entries.value)[number]) {
  const tab = workspaceStore.addView(view)
  await nextTick()
  syncPanels()
  activatePanel(tab.id)
}

function activatePanel(tabId: string) {
  const panel = dockApi.value?.panels.find((item) => item.id === tabId)
  panel?.api.setActive()
}

async function startRenameTab(tabId: string) {
  const tab = workspaceStore.tabs.find((item) => item.id === tabId)
  if (!tab) return
  editingTabId.value = tabId
  editingTitle.value = tab.title
  await nextTick()
  tabTitleInput.value?.select()
}

function saveTabTitle() {
  const title = editingTitle.value.trim()
  const tabId = editingTabId.value
  if (title && tabId) {
    workspaceStore.renameTab(tabId, title)
    dockApi.value?.panels.find((panel) => panel.id === tabId)?.api.setTitle(title)
  }
  editingTabId.value = undefined
}

function showTabMenu(event: MouseEvent, tabId?: string) {
  event.preventDefault()
  const tab = workspaceStore.tabs.find((item) => item.id === tabId)
  ContextMenu.showContextMenu({
    x: event.x,
    y: event.y,
    theme: 'mac dark',
    zIndex: 1000,
    items: [
      { label: 'New Dashboard', icon: h('span', '＋'), onClick: () => void createDashboard() },
      ...availableViews.value.map((view) => ({
        label: `${view.icon ? `${view.icon} ` : ''}${view.title}`,
        onClick: () => void createView(view),
      })),
      { divided: true },
      ...(tab ? [
        { label: 'Rename', icon: h('span', '✏️'), onClick: () => void startRenameTab(tab.id) },
        { label: 'Close tab', icon: h('span', '✕'), onClick: () => closeTab(tab.id) },
        { divided: true },
      ] : []),
      { label: 'Export Workspace', icon: h('span', '📤'), onClick: () => workspaceStore.exportWorkspace() },
      { label: 'Import Workspace', icon: h('span', '📥'), onClick: chooseImport },
    ],
  })
}

function closeTab(tabId: string) {
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
    <nav class="workspace-tabs" role="tablist" aria-label="Workspace tabs" @contextmenu="showTabMenu($event)">
      <div v-for="tab in workspaceStore.tabs" :key="tab.id" class="workspace-tab" :class="{ 'workspace-tab--active': tab.id === workspaceStore.document.activeTabId }" role="tab" :aria-selected="tab.id === workspaceStore.document.activeTabId" @click="activatePanel(tab.id)" @contextmenu.stop="showTabMenu($event, tab.id)" @dblclick.stop="startRenameTab(tab.id)">
        <input v-if="editingTabId === tab.id" :ref="(el) => { tabTitleInput = el as HTMLInputElement }" v-model="editingTitle" class="workspace-tab__rename" aria-label="Tab name" @click.stop @keydown.enter.prevent="saveTabTitle" @keydown.esc.prevent="editingTabId = undefined" @blur="saveTabTitle">
        <span v-else class="workspace-tab__title">{{ tab.title }}</span>
        <button v-if="editingTabId !== tab.id" type="button" class="workspace-tab__close" :aria-label="`Close ${tab.title}`" @click.stop="closeTab(tab.id)">×</button>
      </div>
      <button type="button" class="workspace-tab-add" aria-label="Add workspace tab" title="New dashboard" @click="createDashboard" @contextmenu.prevent="showTabMenu($event)">+</button>
      <input ref="importInput" class="hidden" type="file" accept=".json,application/json" @change="importWorkspace">
    </nav>

    <div class="workspace-dockview">
      <DockviewVue
        class="dockview-root"
        style="width: 100%; height: 100%"
        :theme="themeDark"
        :popout-url="workspaceStore.popoutsEnabled ? workspaceStore.popoutUrl : undefined"
        :disable-floating-groups="true"
        :dnd-edges="false"
        @ready="onDockviewReady"
      >
        <template #panel-dashboard-panel="{ params }">
          <PluginErrorBoundary :owner-id="'core dashboard'" @disable="disablePanel(params.tabId)">
          <DashboardTiles :tab-id="params.tabId" />
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

.workspace-tabs {
  display: flex;
  min-height: 36px;
  align-items: center;
  gap: 2px;
  padding: 3px 8px 0;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-panel);
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
}
.workspace-tabs::-webkit-scrollbar { display: none; }
.workspace-tab {
  display: flex;
  min-width: 100px;
  max-width: 220px;
  height: 32px;
  align-items: center;
  gap: 8px;
  padding: 0 8px 0 12px;
  border: 1px solid transparent;
  border-bottom: 0;
  border-radius: 6px 6px 0 0;
  color: var(--color-text-muted);
  cursor: pointer;
}
.workspace-tab--active {
  border-color: var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
}
.workspace-tab__title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.workspace-tab__rename { width: 100%; min-width: 0; border: 0; outline: 0; background: transparent; color: var(--color-text); }
.workspace-tab__close, .workspace-tab-add { display: grid; width: 22px; height: 22px; flex: 0 0 auto; place-items: center; border: 0; border-radius: 4px; background: transparent; color: inherit; cursor: pointer; }
.workspace-tab__close:hover, .workspace-tab-add:hover { background: var(--color-hover); color: var(--color-text); }
.workspace-tab-add { margin: 0 0 4px 3px; font-size: 20px; }
.workspace-dockview { flex: 1; min-height: 0; }
.dockview-root { width: 100%; height: 100%; }
:global(.workspace-page .dv-tabs-and-actions-container) { display: none !important; }
.workspace-loading { display: grid; min-height: 40vh; place-items: center; color: var(--color-text-muted); }
</style>
