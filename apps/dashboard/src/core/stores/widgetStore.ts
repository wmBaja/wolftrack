import { computed } from 'vue'
import { defineStore } from 'pinia'
import { createWidget, type Widget } from '@/core/widgets'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'

const GRID_COLUMNS = 16

interface GridPosition {
  x: number
  y: number
}

interface GridSize {
  w: number
  h: number
}

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

  function addWidget(
    type: string,
    position: { x: number; y: number; w?: number; h?: number },
    tabId?: string,
  ): Widget {
    const target = workspaceStore.getDashboardTab(tabId)
    const newWidget = createWidget(type, position)
    if (!target) return newWidget
    const availablePosition = findAvailablePosition(position, newWidget, target.id)
    newWidget.x = availablePosition.x
    newWidget.y = availablePosition.y
    target.layout.widgets.push(newWidget)
    return newWidget
  }

  function findAvailablePosition(preferredPosition: GridPosition, size: GridSize, tabId?: string): GridPosition {
    const dashboardWidgets = getWidgets(tabId)
    const maxX = Math.max(0, GRID_COLUMNS - size.w)
    const preferred = {
      x: Math.max(0, Math.min(Math.round(preferredPosition.x), maxX)),
      y: Math.max(0, Math.round(preferredPosition.y)),
    }

    if (isSpaceAvailable(preferred, size, tabId)) return preferred

    let closestPosition: GridPosition | undefined
    let closestDistance = Number.POSITIVE_INFINITY
    const maxWidgetBottom = dashboardWidgets.reduce((bottom, widget) => Math.max(bottom, widget.y + widget.h), 0)

    for (let y = 0; y <= maxWidgetBottom; y += 1) {
      for (let x = 0; x <= maxX; x += 1) {
        const position = { x, y }
        if (!isSpaceAvailable(position, size, tabId)) continue

        const distance = Math.hypot(x - preferred.x, y - preferred.y)
        if (distance < closestDistance) {
          closestDistance = distance
          closestPosition = position
        }
      }
    }

    return closestPosition ?? { x: preferred.x, y: maxWidgetBottom }
  }

  function isSpaceAvailable(position: GridPosition, size: GridSize, tabId?: string): boolean {
    return getWidgets(tabId).every((widget) => !widgetsOverlap({ ...position, ...size }, widget))
  }

  function widgetsOverlap(a: GridPosition & GridSize, b: GridPosition & GridSize): boolean {
    return a.x < b.x + b.w &&
      a.x + a.w > b.x &&
      a.y < b.y + b.h &&
      a.y + a.h > b.y
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

  function updateLayout(newLayout: Widget[], tabId?: string): void {
    const target = workspaceStore.getDashboardTab(tabId)
    if (!target) return
    newLayout.forEach(item => {
      const widget = target.layout.widgets.find(widget => String(widget.i) === String(item.i))
      if (widget) {
        widget.x = item.x
        widget.y = item.y
        widget.w = item.w
        widget.h = item.h
      }
    })
  }

  function clearAll(tabId?: string): void {
    const target = workspaceStore.getDashboardTab(tabId)
    if (target) target.layout.widgets = []
  }

  function overwriteLayout(newWidgets: Widget[], tabId?: string): void {
    const target = workspaceStore.getDashboardTab(tabId)
    if (target) target.layout.widgets = newWidgets
  }

  return {
    widgets,
    widgetCount,
    getWidgets,
    getWidgetById,
    addWidget,
    findAvailablePosition,
    removeWidget,
    updateWidget,
    updateLayout,
    clearAll,
    overwriteLayout,
  }
})
