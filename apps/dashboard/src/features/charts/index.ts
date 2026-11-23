import type { FeatureActivate } from '@wolftrack/plugin-sdk'
import BaseWidget from './components/BaseWidget.vue'
import ChartWidget from './components/ChartWidget.vue'

export const activate: FeatureActivate = ({ widgets, commands }) => {
  const removeBase = widgets.register({
    type: 'base', title: 'Base Widget', component: BaseWidget,
    defaults: { w: 4, h: 4, minW: 2, minH: 2 }, icon: '📦',
  })
  const removeChart = widgets.register({
    type: 'chart', title: 'Chart Widget', component: ChartWidget,
    defaults: { w: 5, h: 15, minW: 4, minH: 4 }, icon: '📈',
  })
  const removeCommand = commands.register({
    id: 'charts.add-chart', title: 'Add Chart Widget', icon: '➕', order: 10,
    run: ({ x, y, w, h }) => {
      void import('@/core/stores/widgetStore').then(({ useWidgetStore }) => {
        useWidgetStore().addWidget('chart', { x, y, w, h })
      })
    },
  })
  return () => { removeBase(); removeChart(); removeCommand() }
}
