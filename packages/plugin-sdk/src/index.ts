/** Stable, type-only contracts shared by the shell and feature modules. */
export interface WidgetConfig {
  [key: string]: unknown
}

export interface WidgetContribution {
  type: string
  title: string
  component: unknown
  defaults: { w: number; h: number; minW: number; minH: number }
  icon?: string
}

export interface ViewContribution {
  id: string
  title: string
  component: unknown
  icon?: string
}

export interface PanelContribution {
  id: string
  component: unknown
  location: 'toolbar' | 'dashboard' | 'overlay'
  alignment?: 'left' | 'right'
  order?: number
  label?: string
  icon?: string
}

export interface CommandContribution {
  id: string
  title: string
  icon?: string
  order?: number
  run: (context: { x: number; y: number; w: number; h: number }) => void | Promise<void>
}

export interface PluginManifest {
  id: string
  name: string
  version: string
  engines?: { dashboardApi?: string; visualizerApi?: string }
  ui?: string
  backend?: string
  contributes?: {
    widgets?: string[]
    views?: string[]
    panels?: string[]
    commands?: string[]
  }
  permissions?: Array<'data:read' | 'storage' | 'backend'>
}

export interface PluginDataContext {
  useSignals: (consumerId: string, signalIds: string[]) => unknown
  availableSignals: () => string[]
}

export interface PluginContext {
  widgets: { register: (contribution: WidgetContribution) => () => void }
  views: { register: (contribution: ViewContribution) => () => void }
  panels: { register: (contribution: PanelContribution) => () => void }
  commands: { register: (contribution: CommandContribution) => () => void }
  data: PluginDataContext
  electron: { openFile: (filters: Array<{ name: string; extensions: string[] }>) => Promise<string | null> }
}

export type FeatureActivate = (context: PluginContext) => void | (() => void)
