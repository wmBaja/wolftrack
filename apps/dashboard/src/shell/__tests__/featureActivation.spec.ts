import { afterEach, describe, expect, it } from 'vitest'
import { activateFeatures } from '@/shell/pluginContext'
import { clearRegistries, commands, panels, widgets } from '@/shell/registries'

afterEach(() => clearRegistries())

describe('feature activation', () => {
  it('registers the existing UI features through the shared context and disposes them', async () => {
    const [charts, dataSource, exportFeature, fileManager] = await Promise.all([
      import('@/features/charts/index'),
      import('@/features/data-source/index'),
      import('@/features/export/index'),
      import('@/features/file-manager/index'),
    ])
    const deactivate = activateFeatures({ charts, dataSource, exportFeature, fileManager })

    expect(widgets.get('chart')).toBeDefined()
    expect(widgets.get('base')).toBeDefined()
    expect(panels.entries.value.map((panel) => panel.id).sort()).toEqual([
      'data-source', 'data-source-lifecycle', 'export', 'file-manager', 'log-window-control',
    ])
    expect(commands.get('charts.add-chart')).toBeDefined()

    deactivate()
    expect(widgets.entries.value).toHaveLength(0)
    expect(panels.entries.value).toHaveLength(0)
    expect(commands.entries.value).toHaveLength(0)
  })
})
