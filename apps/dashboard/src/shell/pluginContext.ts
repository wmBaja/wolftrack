import type { PluginContext } from '@wolftrack/plugin-sdk'
import { computed } from 'vue'
import { useTimeSeriesData } from '@/core/composables/useTimeSeriesData'
import { useDbcStore } from '@/core/stores/dbcStore'
import { registerWidgetDefaults } from '@/core/widgets'
import { commands, panels, views, widgets } from './registries'

export function createPluginContext(): PluginContext {
  return {
    widgets: {
      register(contribution) {
        const removeContribution = widgets.register(contribution)
        const removeDefaults = registerWidgetDefaults(contribution.type, contribution)
        return () => { removeContribution(); removeDefaults() }
      },
    },
    views,
    panels,
    commands,
    data: {
      useSignals(consumerId, signalIds) {
        const signals = 'value' in signalIds ? computed(() => signalIds.value) : signalIds
        return useTimeSeriesData(consumerId, signals)
      },
      availableSignals() {
        return useDbcStore().signals.map(({ id, name, unit }) => ({ id, name, unit }))
      },
    },
    electron: {
      openFile(filters) {
        return window.electronAPI?.files.openFile(filters) ?? Promise.resolve(null)
      },
    },
  }
}

export function activateFeatures(modules: Record<string, unknown>, context = createPluginContext()) {
  const disposers: Array<() => void> = []
  for (const module of Object.values(modules)) {
    if (!module || typeof module !== 'object' || !('activate' in module)) continue
    const activate = (module as { activate?: (ctx: PluginContext) => void | (() => void) }).activate
    if (typeof activate !== 'function') continue
    const cleanup = activate(context)
    if (cleanup) disposers.push(cleanup)
  }
  return () => disposers.reverse().forEach((dispose) => dispose())
}
