import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'
import { useWidgetStore } from '@/core/stores/widgetStore'
import { parseWorkspaceDocument, parseWorkspaceImport } from '@/core/workspace'

const legacyWidget = {
  i: 'saved-plugin-widget',
  type: 'sample-plugin/plot',
  title: 'Saved plugin plot',
  x: 0,
  y: 0,
  w: 4,
  h: 4,
  config: {},
  signals: ['Vehicle.speed'],
  createdAt: 1,
}

describe('workspace store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('migrates the legacy widget list and keeps a one-time backup', async () => {
    const oldValue = JSON.stringify([legacyWidget])
    localStorage.setItem('dashboard-widgets', oldValue)
    const workspace = useWorkspaceStore()

    await workspace.load()

    expect(workspace.tabs[0]).toMatchObject({
      kind: 'dashboard',
      dataContextId: 'shared',
      layout: { type: 'tiles', widgets: [{ type: 'sample-plugin/plot' }], state: null },
    })
    expect(localStorage.getItem('dashboard-widgets')).toBeNull()
    expect(localStorage.getItem('dashboard-widgets-migrated-v1')).toBe(oldValue)
    expect(localStorage.getItem('wolftrack-workspace-dev')).toContain('sample-plugin/plot')
  })

  it('imports legacy arrays and versioned workspaces without requiring widget registrations', () => {
    const legacyImport = parseWorkspaceImport([legacyWidget])
    expect(legacyImport?.kind).toBe('legacy')

    const document = {
      format: 'wolftrack-workspace',
      version: 2,
      activeTabId: 'view-tab',
      tabs: [
        {
          id: 'dash-tab',
          kind: 'dashboard',
          title: 'Dashboard',
          dataContextId: 'shared',
          layout: { type: 'grid', widgets: [legacyWidget] },
        },
        {
          id: 'view-tab',
          kind: 'view',
          title: 'Guide',
          dataContextId: 'shared',
          viewType: 'workspace.guide',
          pluginId: 'core',
          state: { visited: true },
        },
      ],
    }

    expect(parseWorkspaceDocument(document)).toMatchObject({
      activeTabId: 'view-tab',
      tabs: [
        { kind: 'dashboard', layout: { type: 'tiles', widgets: [{ type: 'sample-plugin/plot' }], state: null } },
        { kind: 'view', viewType: 'workspace.guide', state: { visited: true } },
      ],
    })
  })

  it('imports legacy geometry as an approximate tile layout without retaining grid fields', () => {
    const imported = parseWorkspaceImport([legacyWidget])
    expect(imported).toEqual({
      kind: 'legacy',
      widgets: [{
        i: 'saved-plugin-widget',
        type: 'sample-plugin/plot',
        title: 'Saved plugin plot',
        config: {},
        signals: ['Vehicle.speed'],
        createdAt: 1,
      }],
    })
  })

  it('round trips a version 3 tile workspace state', () => {
    const tileState = { grid: { root: null }, width: 500, height: 300, orientation: 1 }
    const document = {
      format: 'wolftrack-workspace',
      version: 3,
      activeTabId: 'dash-tab',
      tabs: [{
        id: 'dash-tab', kind: 'dashboard', title: 'Dashboard', dataContextId: 'shared',
        layout: { type: 'tiles', widgets: [legacyWidget], state: tileState },
      }],
    }
    expect(parseWorkspaceDocument(document)?.tabs[0]).toMatchObject({
      layout: { type: 'tiles', state: tileState, widgets: [{ i: 'saved-plugin-widget' }] },
    })
  })

  it('rewrites version 2 grid workspaces as version 3 tiles', async () => {
    localStorage.setItem('wolftrack-workspace-dev', JSON.stringify({
      format: 'wolftrack-workspace', version: 2, activeTabId: 'dash-tab', tabs: [{
        id: 'dash-tab', kind: 'dashboard', title: 'Dashboard', dataContextId: 'shared',
        layout: { type: 'grid', widgets: [legacyWidget] },
      }],
    }))
    const workspace = useWorkspaceStore()

    await workspace.load()

    const saved = JSON.parse(localStorage.getItem('wolftrack-workspace-dev') ?? 'null')
    expect(saved).toMatchObject({
      version: 3,
      tabs: [{ layout: { type: 'tiles', state: null, widgets: [{ i: 'saved-plugin-widget' }] } }],
    })
  })

  it('does not reimport a legacy key after its migration marker exists', async () => {
    localStorage.setItem('dashboard-widgets-migrated-v1', JSON.stringify([legacyWidget]))
    localStorage.setItem('dashboard-widgets', JSON.stringify([legacyWidget]))
    const workspace = useWorkspaceStore()

    await workspace.load()

    expect(workspace.tabs[0]?.kind === 'dashboard' && workspace.tabs[0].layout.widgets).toEqual([])
    expect(localStorage.getItem('dashboard-widgets')).toBeNull()
  })

  it('moves a tile between dashboards while keeping the widget record', () => {
    const workspace = useWorkspaceStore()
    const source = workspace.tabs[0]
    if (!source || source.kind !== 'dashboard') throw new Error('Default dashboard is missing')
    source.layout.widgets.push({
      i: 'movable', type: 'chart', title: 'Movable', config: {}, signals: ['Vehicle.speed'], createdAt: 1,
    })
    const destination = workspace.addDashboard()
    const widgetStore = useWidgetStore()

    expect(widgetStore.moveWidget('movable', source.id, destination.id)).toBe(true)
    expect(source.layout.widgets).toEqual([])
    expect(destination.layout.widgets).toMatchObject([{ i: 'movable', signals: ['Vehicle.speed'] }])
  })
})
