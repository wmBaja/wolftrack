/** Core widget record and default creation support. */
import type { WidgetConfig as WidgetConfigType } from '@wolftrack/plugin-sdk'

export type { WidgetConfig } from '@wolftrack/plugin-sdk'

export interface Widget {
  i: string | number
  type: string
  title: string
  x: number
  y: number
  w: number
  h: number
  minW?: number
  minH?: number
  static?: boolean
  config: WidgetConfigType
  signals: string[]
  createdAt: number
}

const UNKNOWN_WIDGET_DEFAULTS = { w: 4, h: 4, minW: 2, minH: 2 }
const registeredDefaults = new Map<string, {
  title: string
  defaults: typeof UNKNOWN_WIDGET_DEFAULTS
}>()

export function registerWidgetDefaults(
  type: string,
  contribution: { title: string; defaults: typeof UNKNOWN_WIDGET_DEFAULTS },
) {
  const registration = contribution
  registeredDefaults.set(type, registration)
  return () => {
    if (registeredDefaults.get(type) === registration) registeredDefaults.delete(type)
  }
}

// Generate unique ID using timestamp + random string
function generateUniqueId(): string {
  return `widget-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

export function createWidget(type: string, position: {x: number, y: number, w?: number, h?: number}): Widget {
  const contribution = registeredDefaults.get(type)
  const defaults = contribution?.defaults ?? UNKNOWN_WIDGET_DEFAULTS
  const id = generateUniqueId()

  return {
    i: id,
    type,
    title: contribution?.title ?? `${type.charAt(0).toUpperCase() + type.slice(1)} Widget`,
    x: position.x,
    y: position.y,
    w: position.w ?? defaults.w,
    h: position.h ?? defaults.h,
    minW: defaults.minW,
    minH: defaults.minH,
    config: {},
    signals: [],
    createdAt: Date.now(),
    static: false,
  }
}
