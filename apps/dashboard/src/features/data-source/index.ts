import type { FeatureActivate } from '@wolftrack/plugin-sdk'
import DataSourceToolbar from './DataSourceToolbar.vue'
import DataSourceLifecycle from './DataSourceLifecycle.vue'

export const activate: FeatureActivate = ({ panels }) => {
  const removePanel = panels.register({
    id: 'data-source', component: DataSourceToolbar, location: 'toolbar', order: 30,
    label: 'Data Source', icon: '🔌',
  })
  const removeLifecycle = panels.register({
    id: 'data-source-lifecycle', component: DataSourceLifecycle, location: 'overlay',
  })
  return () => { removePanel(); removeLifecycle() }
}
