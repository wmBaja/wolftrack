import { afterEach, describe, expect, it } from 'vitest'
import { clearRegistries, commands, panels, views, widgets } from '@/shell/registries'

afterEach(() => clearRegistries())

describe('contribution registries', () => {
  it('registers and removes contributions by their stable id', () => {
    const contribution = {
      type: 'test/chart', title: 'Test chart', component: {},
      defaults: { w: 4, h: 4, minW: 1, minH: 1 },
    }
    const dispose = widgets.register(contribution)

    expect(widgets.get('test/chart')).toBe(contribution)
    dispose()
    expect(widgets.get('test/chart')).toBeUndefined()
  })

  it('replaces an existing entry and exposes each contribution collection', () => {
    const first = { id: 'panel', component: {}, location: 'toolbar' as const }
    const second = { ...first, label: 'Updated' }
    panels.register(first)
    panels.register(second)

    expect(panels.entries.value).toEqual([second])

    views.register({ id: 'view', title: 'View', component: {} })
    commands.register({ id: 'command', title: 'Command', run: () => undefined })
    expect(views.entries.value).toHaveLength(1)
    expect(commands.entries.value).toHaveLength(1)
  })
})
