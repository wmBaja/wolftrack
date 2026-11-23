import type { Widget } from './widgets'

export const WORKSPACE_FORMAT = 'wolftrack-workspace'
export const WORKSPACE_VERSION = 2

export interface DashboardTab {
  id: string
  kind: 'dashboard'
  title: string
  dataContextId: 'shared'
  layout: { type: 'grid'; widgets: Widget[] }
}

export interface ViewTab {
  id: string
  kind: 'view'
  title: string
  dataContextId: 'shared'
  viewType: string
  pluginId: string
  state: Record<string, unknown>
}

export type WorkspaceTab = DashboardTab | ViewTab

export interface WorkspaceDocument {
  format: typeof WORKSPACE_FORMAT
  version: typeof WORKSPACE_VERSION
  activeTabId: string
  tabs: WorkspaceTab[]
}

export function createWorkspaceDocument(): WorkspaceDocument {
  const tab = createDashboardTab('Dashboard 1')
  return {
    format: WORKSPACE_FORMAT,
    version: WORKSPACE_VERSION,
    activeTabId: tab.id,
    tabs: [tab],
  }
}

export function createDashboardTab(title: string): DashboardTab {
  return {
    id: createId(),
    kind: 'dashboard',
    title,
    dataContextId: 'shared',
    layout: { type: 'grid', widgets: [] },
  }
}

export function createViewTab(viewType: string, pluginId: string, title: string): ViewTab {
  return {
    id: createId(),
    kind: 'view',
    title,
    dataContextId: 'shared',
    viewType,
    pluginId,
    state: {},
  }
}

export function parseWidgets(value: unknown): Widget[] | null {
  if (!Array.isArray(value)) return null
  const widgets: Widget[] = []
  const ids = new Set<string>()

  for (const item of value) {
    if (!isRecord(item)
      || (typeof item.i !== 'string' && typeof item.i !== 'number')
      || typeof item.type !== 'string'
      || typeof item.title !== 'string'
      || !isFiniteNumber(item.x)
      || !isFiniteNumber(item.y)
      || !isFiniteNumber(item.w)
      || !isFiniteNumber(item.h)
      || !Array.isArray(item.signals)) {
      return null
    }
    const widgetId = String(item.i)
    if (ids.has(widgetId)) return null
    ids.add(widgetId)

    widgets.push({
      ...item,
      i: widgetId,
      type: item.type,
      title: item.title,
      x: item.x,
      y: item.y,
      w: item.w,
      h: item.h,
      config: isRecord(item.config) ? item.config : {},
      signals: item.signals.filter((signal): signal is string => typeof signal === 'string'),
      createdAt: isFiniteNumber(item.createdAt) ? item.createdAt : 0,
    } as Widget)
  }

  return widgets
}

export function parseWorkspaceDocument(value: unknown): WorkspaceDocument | null {
  if (!isRecord(value)
    || value.format !== WORKSPACE_FORMAT
    || value.version !== WORKSPACE_VERSION
    || typeof value.activeTabId !== 'string'
    || !Array.isArray(value.tabs)) {
    return null
  }

  const tabs: WorkspaceTab[] = []
  const ids = new Set<string>()
  const widgetIds = new Set<string>()
  for (const item of value.tabs) {
    if (!isRecord(item)
      || typeof item.id !== 'string'
      || ids.has(item.id)
      || typeof item.title !== 'string'
      || item.dataContextId !== 'shared') {
      return null
    }

    ids.add(item.id)
    if (item.kind === 'dashboard') {
      if (!isRecord(item.layout) || item.layout.type !== 'grid') return null
      const widgets = parseWidgets(item.layout.widgets)
      if (!widgets) return null
      for (const widget of widgets) {
        const widgetId = String(widget.i)
        if (widgetIds.has(widgetId)) return null
        widgetIds.add(widgetId)
      }
      tabs.push({
        id: item.id,
        kind: 'dashboard',
        title: item.title,
        dataContextId: 'shared',
        layout: { type: 'grid', widgets },
      })
      continue
    }

    if (item.kind === 'view'
      && typeof item.viewType === 'string'
      && typeof item.pluginId === 'string'
      && isRecord(item.state)) {
      tabs.push({
        id: item.id,
        kind: 'view',
        title: item.title,
        dataContextId: 'shared',
        viewType: item.viewType,
        pluginId: item.pluginId,
        state: item.state,
      })
      continue
    }

    return null
  }

  if (tabs.length === 0) return null
  const activeTabId = ids.has(value.activeTabId) ? value.activeTabId : tabs[0]!.id
  return {
    format: WORKSPACE_FORMAT,
    version: WORKSPACE_VERSION,
    activeTabId,
    tabs,
  }
}

export function parseWorkspaceImport(value: unknown):
  | { kind: 'workspace'; document: WorkspaceDocument }
  | { kind: 'legacy'; widgets: Widget[] }
  | null {
  if (Array.isArray(value)) {
    const widgets = parseWidgets(value)
    return widgets ? { kind: 'legacy', widgets } : null
  }

  const document = parseWorkspaceDocument(value)
  return document ? { kind: 'workspace', document } : null
}

function createId() {
  return globalThis.crypto?.randomUUID?.() ?? `tab-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
