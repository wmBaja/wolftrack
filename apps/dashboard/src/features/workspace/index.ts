import type { FeatureActivate } from '@wolftrack/plugin-sdk'
import WorkspaceSummaryView from './WorkspaceSummaryView.vue'

export const activate: FeatureActivate = ({ views }) => {
  return views.register({
    id: 'workspace.guide',
    pluginId: 'core',
    title: 'Workspace Guide',
    icon: 'ⓘ',
    component: WorkspaceSummaryView,
  })
}
