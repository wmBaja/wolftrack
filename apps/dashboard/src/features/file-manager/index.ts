import type { FeatureActivate } from '@wolftrack/plugin-sdk'
import FileManagerToolbar from './FileManagerToolbar.vue'
import LogWindowControl from './components/LogWindowControl.vue'

export const activate: FeatureActivate = ({ panels }) => {
  const removePanel = panels.register({
    id: 'file-manager', component: FileManagerToolbar, location: 'toolbar', alignment: 'left', order: 10,
    label: 'Toggle File Manager', icon: '☰',
  })
  const removeLogControl = panels.register({
    id: 'log-window-control', component: LogWindowControl, location: 'dashboard', order: 10,
  })
  return () => { removePanel(); removeLogControl() }
}
