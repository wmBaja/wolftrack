import { computed } from 'vue'
import { defineStore } from 'pinia'
import { createWidget, type Widget } from '@/core/widgets'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'

export const useWidgetStore = defineStore('widgets', () => {
  const workspaceStore = useWorkspaceStore()
  const widgets = computed(() => workspaceStore.activeDashboard?.layout.widgets ?? [])
  const widgetCount = computed(() => widgets.value.length)

  function getWidgets(tabId?: string) {
    return workspaceStore.getDashboardTab(tabId)?.layout.widgets ?? []
  }

  function getWidgetById(id: string): Widget | undefined {
    return workspaceStore.tabs
      .filter((tab) => tab.kind === 'dashboard')
      .flatMap((tab) => tab.layout.widgets)
      .find(widget => String(widget.i) === id)
  }

  function addWidget(type: string, tabId?: string): Widget {
    const target = workspaceStore.getDashboardTab(tabId)
    const newWidget = createWidget(type)
    if (!target) return newWidget
    target.layout.widgets.push(newWidget)
    return newWidget
  }

  function removeWidget(id: string, tabId?: string): void {
    const targets = tabId
      ? [workspaceStore.getDashboardTab(tabId)].filter((tab): tab is NonNullable<typeof tab> => Boolean(tab))
      : workspaceStore.tabs.filter((tab) => tab.kind === 'dashboard')
    const target = targets.find((tab) => tab.layout.widgets.some(widget => String(widget.i) === id))
    const index = target?.layout.widgets.findIndex(widget => String(widget.i) === id) ?? -1
    if (target && index !== -1) target.layout.widgets.splice(index, 1)
  }

  function updateWidget(id: string, updates: Partial<Widget>, tabId?: string): void {
    const targets = tabId
      ? [workspaceStore.getDashboardTab(tabId)].filter((tab): tab is NonNullable<typeof tab> => Boolean(tab))
      : workspaceStore.tabs.filter((tab) => tab.kind === 'dashboard')
    const widget = targets.flatMap((tab) => tab.layout.widgets).find(item => String(item.i) === id)
    if (widget) Object.assign(widget, updates)
  }

  function clearAll(tabId?: string): void {
    const target = workspaceStore.getDashboardTab(tabId)
    if (target) target.layout.widgets = []
  }

  function overwriteLayout(newWidgets: Widget[], tabId?: string): void {
    const target = workspaceStore.getDashboardTab(tabId)
    if (target) target.layout.widgets = newWidgets
  }

  function moveWidget(widgetId: string, fromTabId: string, toTabId: string) {
    if (fromTabId === toTabId) return false
    const source = workspaceStore.getDashboardTab(fromTabId)
    const destination = workspaceStore.getDashboardTab(toTabId)
    if (!source || !destination) return false
    const index = source.layout.widgets.findIndex(widget => String(widget.i) === widgetId)
    if (index < 0) return false
    const [widget] = source.layout.widgets.splice(index, 1)
    if (!widget) return false
    destination.layout.widgets.push(widget)
    return true
  }

  return {
    widgets,
    widgetCount,
    getWidgets,
    getWidgetById,
    addWidget,
    removeWidget,
    updateWidget,
    clearAll,
    overwriteLayout,
    moveWidget,
  }
})
