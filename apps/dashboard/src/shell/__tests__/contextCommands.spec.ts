import { describe, expect, it } from 'vitest'
import { createDashboardTab, createViewTab } from '@/core/workspace'
import type { CommandContribution } from '@wolftrack/plugin-sdk'
import { commandsForTab } from '@/shell/contextCommands'

const contributions: CommandContribution[] = [
  { id: 'view.other', title: 'Other view action', context: { kind: 'view', viewType: 'other' }, run: () => undefined },
  { id: 'legacy', title: 'Legacy dashboard action', run: () => undefined },
  { id: 'dashboard.later', title: 'Later dashboard action', context: { kind: 'dashboard' }, order: 20, run: () => undefined },
  { id: 'view.guide', title: 'Guide action', context: { kind: 'view', viewType: 'guide' }, run: () => undefined },
  { id: 'dashboard.first', title: 'First dashboard action', context: { kind: 'dashboard' }, order: 10, run: () => undefined },
]

describe('commandsForTab', () => {
  it('returns only explicitly scoped commands for the active dashboard, in order', () => {
    expect(commandsForTab(contributions, createDashboardTab('Dashboard'))
      .map((command) => command.id)).toEqual(['dashboard.first', 'dashboard.later'])
  })

  it('returns commands only for the active view type', () => {
    expect(commandsForTab(contributions, createViewTab('guide', 'core', 'Guide'))
      .map((command) => command.id)).toEqual(['view.guide'])
  })

  it('preserves unscoped legacy commands in the dashboard context menu when requested', () => {
    expect(commandsForTab(contributions, createDashboardTab('Dashboard'), true)
      .map((command) => command.id)).toEqual(['legacy', 'dashboard.first', 'dashboard.later'])
  })

  it('returns no contextual commands without an active tab', () => {
    expect(commandsForTab(contributions, undefined)).toEqual([])
  })
})
