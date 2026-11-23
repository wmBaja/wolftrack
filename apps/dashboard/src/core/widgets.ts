/** Core widget record and default creation support. */
import type { WidgetConfig as WidgetConfigType } from '@wolftrack/plugin-sdk'

export type { WidgetConfig } from '@wolftrack/plugin-sdk'
export interface Widget {
  i: string | number
  type: string
  title: string
  config: WidgetConfigType
  signals: string[]
  createdAt: number
  [key: string]: unknown
}

// Generate unique ID using timestamp + random string
function generateUniqueId(): string {
  return `widget-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

export function createWidget(type: string): Widget {
  const id = generateUniqueId()

  return {
    i: id,
    type,
    title: `${type.charAt(0).toUpperCase() + type.slice(1)} Widget`,
    config: {},
    signals: [],
    createdAt: Date.now(),
  }
}
