/** Stable, type-only contracts shared by the shell and feature modules. */
export interface WidgetConfig {
  [key: string]: unknown
}

export interface WidgetContribution {
  type: string
  title: string
  component: unknown
  icon?: string
}

export interface ViewContribution {
  id: string
  title: string
  component: unknown
  pluginId?: string
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
  run: (context: { tabId?: string }) => void | Promise<void>
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

export interface SignalDescriptor {
  id: string
  name: string
  unit: string
}

export interface SignalSeries extends SignalDescriptor {
  timestamps: ArrayLike<number>
  values: ArrayLike<number>
}

export interface SignalDataSnapshot {
  source: 'live' | 'logfile'
  signals: Record<string, SignalSeries | undefined>
  viewport: { start: number; end: number } | null
  revision: number
  timeOrigin: number | null
}

/** Structural ref shape keeps the SDK independent of Vue at runtime. */
export interface ReactiveValue<T> {
  readonly value: T
}

export type MaybeReactive<T> = T | ReactiveValue<T>

export interface SignalDataHandle {
  readonly snapshot: ReactiveValue<SignalDataSnapshot>
  refresh(): Promise<void>
}

export interface PluginDataContext {
  /** Current built-in data context; workspace tabs may select contexts in a later phase. */
  readonly contextId: string
  useSignals: (consumerId: string, signalIds: MaybeReactive<readonly string[]>) => SignalDataHandle
  availableSignals: () => SignalDescriptor[]
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
