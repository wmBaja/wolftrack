import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import {
  createDashboardTab,
  createViewTab,
  createWorkspaceDocument,
  parseWorkspaceDocument,
  parseWorkspaceImport,
  parseWidgets,
  type WorkspaceDocument,
  type WorkspaceTab,
} from '@/core/workspace'
import type { Widget } from '@/core/widgets'
import type { ViewContribution } from '@wolftrack/plugin-sdk'

const SAVE_DELAY_MS = 350
const WORKSPACE_STORAGE_KEY = 'wolftrack-workspace-dev'
const LEGACY_WIDGETS_KEY = 'dashboard-widgets'
const LEGACY_WIDGETS_BACKUP_KEY = 'dashboard-widgets-migrated-v1'

export const useWorkspaceStore = defineStore('workspace', () => {
  const document = ref<WorkspaceDocument>(createWorkspaceDocument())
  const loaded = ref(false)
  let saveTimer: ReturnType<typeof setTimeout> | undefined

  const tabs = computed(() => document.value.tabs)
  const activeTab = computed(() => tabs.value.find(tab => tab.id === document.value.activeTabId))
  const activeDashboard = computed(() => activeTab.value?.kind === 'dashboard' ? activeTab.value : undefined)
  const widgetSignalIds = computed(() => [...new Set(tabs.value
    .filter((tab) => tab.kind === 'dashboard')
    .flatMap((tab) => tab.layout.widgets.flatMap((widget) => widget.signals))
    .filter(Boolean))])

  watch(document, scheduleSave, { deep: true })

  async function load() {
    if (loaded.value) return

    let stored: unknown = null
    if (window.electronAPI?.workspace) {
      try {
        stored = await window.electronAPI.workspace.load()
      } catch (error) {
        console.error('Failed to load workspace from app data:', error)
      }
    } else {
      const raw = localStorage.getItem(WORKSPACE_STORAGE_KEY)
      if (raw) stored = parseJson(raw)
    }

    const parsed = parseWorkspaceDocument(stored)
    const legacyRaw = localStorage.getItem(LEGACY_WIDGETS_KEY)
    let migrated = false

    if (parsed) {
      document.value = parsed
    } else {
      const initial = createWorkspaceDocument()
      if (legacyRaw && !localStorage.getItem(LEGACY_WIDGETS_BACKUP_KEY)) {
        const legacyWidgets = parseWidgets(parseJson(legacyRaw))
        const firstDashboard = initial.tabs.find((tab) => tab.kind === 'dashboard')
        if (legacyWidgets && firstDashboard?.kind === 'dashboard') {
          firstDashboard.layout.widgets = legacyWidgets
        }
        migrated = true
      }
      document.value = initial
    }

    archiveLegacyWidgets(legacyRaw)
    loaded.value = true
    if (!parsed || migrated) await saveNow()
  }

  function scheduleSave() {
    if (!loaded.value) return
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => { void saveNow() }, SAVE_DELAY_MS)
  }

  async function saveNow() {
    if (!loaded.value) return
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = undefined
    try {
      if (window.electronAPI?.workspace) {
        await window.electronAPI.workspace.save(document.value)
      } else {
        localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(document.value))
      }
    } catch (error) {
      console.error('Failed to save workspace:', error)
    }
  }

  function getDashboardTab(tabId?: string) {
    const tab = tabs.value.find((item) => item.id === (tabId ?? document.value.activeTabId))
    return tab?.kind === 'dashboard' ? tab : undefined
  }

  function setDashboardWidgets(tabId: string, widgets: Widget[]) {
    const tab = getDashboardTab(tabId)
    if (!tab) return
    tab.layout.widgets = widgets
  }

  function addDashboard(title = `Dashboard ${tabs.value.filter(tab => tab.kind === 'dashboard').length + 1}`) {
    const tab = createDashboardTab(title)
    document.value.tabs.push(tab)
    document.value.activeTabId = tab.id
    return tab
  }

  function addView(view: ViewContribution) {
    const tab = createViewTab(view.id, view.pluginId ?? 'core', view.title)
    document.value.tabs.push(tab)
    document.value.activeTabId = tab.id
    return tab
  }

  function activateTab(tabId: string) {
    if (tabs.value.some(tab => tab.id === tabId)) document.value.activeTabId = tabId
  }

  function renameTab(tabId: string, title: string) {
    const tab = tabs.value.find(item => item.id === tabId)
    if (tab && title.trim()) tab.title = title.trim()
  }

  function reorderTabs(tabIds: string[]) {
    if (tabIds.length !== tabs.value.length || new Set(tabIds).size !== tabs.value.length) return
    const tabById = new Map(tabs.value.map((tab) => [tab.id, tab]))
    const reordered = tabIds.map((id) => tabById.get(id))
    if (reordered.some((tab) => !tab)) return
    document.value.tabs = reordered as WorkspaceTab[]
  }

  function removeTab(tabId: string) {
    const index = tabs.value.findIndex(tab => tab.id === tabId)
    if (index < 0) return
    if (tabs.value.length <= 1) {
      const replacement = createDashboardTab('Dashboard 1')
      document.value.tabs = [replacement]
      document.value.activeTabId = replacement.id
      return
    }

    document.value.tabs.splice(index, 1)
    if (document.value.activeTabId === tabId) {
      const nextTab = document.value.tabs[Math.min(index, document.value.tabs.length - 1)]
      if (nextTab) document.value.activeTabId = nextTab.id
    }
  }

  function updateViewState(tabId: string, state: Record<string, unknown>) {
    const tab = tabs.value.find((item) => item.id === tabId)
    if (tab?.kind === 'view') tab.state = state
  }

  function importValue(value: unknown) {
    const imported = parseWorkspaceImport(value)
    if (!imported) return false
    if (imported.kind === 'workspace') {
      document.value = imported.document
      return true
    }

    const target = activeDashboard.value ?? tabs.value.find((tab): tab is Extract<WorkspaceTab, { kind: 'dashboard' }> => tab.kind === 'dashboard')
    if (!target) return false
    target.layout.widgets = imported.widgets
    document.value.activeTabId = target.id
    return true
  }

  function exportWorkspace() {
    const content = JSON.stringify(document.value, null, 2)
    const url = URL.createObjectURL(new Blob([content], { type: 'application/json' }))
    const link = globalThis.document.createElement('a')
    link.href = url
    link.download = 'wolftrack-workspace.json'
    link.click()
    URL.revokeObjectURL(url)
  }

  async function importWorkspaceFile(file: File) {
    try {
      return importValue(JSON.parse(await file.text()))
    } catch {
      return false
    }
  }

  async function flush() {
    await saveNow()
  }

  return {
    document,
    loaded,
    tabs,
    activeTab,
    activeDashboard,
    widgetSignalIds,
    load,
    saveNow,
    flush,
    getDashboardTab,
    setDashboardWidgets,
    addDashboard,
    addView,
    activateTab,
    renameTab,
    reorderTabs,
    removeTab,
    updateViewState,
    importValue,
    importWorkspaceFile,
    exportWorkspace,
  }
})

function archiveLegacyWidgets(raw: string | null) {
  if (raw === null) return
  if (!localStorage.getItem(LEGACY_WIDGETS_BACKUP_KEY)) {
    localStorage.setItem(LEGACY_WIDGETS_BACKUP_KEY, raw)
  }
  localStorage.removeItem(LEGACY_WIDGETS_KEY)
}

function parseJson(value: string): unknown {
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}
