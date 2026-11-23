import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'
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
      layout: { type: 'grid', widgets: [{ type: 'sample-plugin/plot' }] },
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
        { kind: 'dashboard', layout: { widgets: [{ type: 'sample-plugin/plot' }] } },
        { kind: 'view', viewType: 'workspace.guide', state: { visited: true } },
      ],
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
})
