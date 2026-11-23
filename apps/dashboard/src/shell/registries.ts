import { shallowRef } from 'vue'
import type {
  CommandContribution,
  PanelContribution,
  ViewContribution,
  WidgetContribution,
} from '@wolftrack/plugin-sdk'

function registry<T>(keyOf: (contribution: T) => string) {
  const entries = shallowRef<T[]>([])
  return {
    entries,
    register(contribution: T) {
      const key = keyOf(contribution)
      entries.value = [...entries.value.filter((item) => keyOf(item) !== key), contribution]
      return () => {
        if (entries.value.includes(contribution)) {
          entries.value = entries.value.filter((item) => item !== contribution)
        }
      }
    },
    get(key: string) {
      return entries.value.find((item) => keyOf(item) === key)
    },
  }
}

export const widgets = registry<WidgetContribution>((item) => item.type)
export const views = registry<ViewContribution>((item) => item.id)
export const panels = registry<PanelContribution>((item) => item.id)
export const commands = registry<CommandContribution>((item) => item.id)

export function clearRegistries() {
  widgets.entries.value = []
  views.entries.value = []
  panels.entries.value = []
  commands.entries.value = []
}
