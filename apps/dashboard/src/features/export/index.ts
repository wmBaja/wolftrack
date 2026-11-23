import type { FeatureActivate } from '@wolftrack/plugin-sdk'
import ExportPanel from './components/ExportPanel.vue'

export const activate: FeatureActivate = ({ panels }) => panels.register({
  id: 'export', component: ExportPanel, location: 'toolbar', order: 20,
  label: 'Export', icon: '📤',
})
