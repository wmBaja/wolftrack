import type { WorkspaceTab } from '@/core/workspace'
import type { CommandContribution } from '@wolftrack/plugin-sdk'

export function commandsForTab(
  contributions: readonly CommandContribution[],
  tab: WorkspaceTab | undefined,
  includeUnscopedDashboardCommands = false,
): CommandContribution[] {
  if (!tab) return []

  return contributions
    .filter((command) => {
      if (!command.context) return includeUnscopedDashboardCommands && tab.kind === 'dashboard'
      if (tab.kind === 'dashboard') return command.context.kind === 'dashboard'
      return command.context.kind === 'view' && command.context.viewType === tab.viewType
    })
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
}
