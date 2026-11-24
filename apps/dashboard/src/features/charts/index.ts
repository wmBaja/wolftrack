import type { FeatureActivate } from '@wolftrack/plugin-sdk'
import { defineComponent, h } from 'vue'
import BaseWidget from './components/BaseWidget.vue'
import ChartWidget from './components/ChartWidget.vue'

export const activate: FeatureActivate = (ctx) => {
  const { widgets, commands } = ctx
  const ContextChartWidget = defineComponent({
    name: 'ContextChartWidget',
    props: { widgetId: { type: String, required: true } },
    setup(props) {
      return () => h(ChartWidget, { widgetId: props.widgetId, dataApi: ctx.data })
    },
  })
  const removeBase = widgets.register({
    type: 'base', title: 'Base Widget', component: BaseWidget,
    icon: '📦',
  })
  const removeChart = widgets.register({
    type: 'chart', title: 'Chart Widget', component: ContextChartWidget,
    icon: '📈',
  })
  const removeCommand = commands.register({
    id: 'charts.add-chart', title: 'Add Chart Widget', icon: '➕', order: 10,
    context: { kind: 'dashboard' },
    run: ({ tabId }) => {
      void import('@/core/stores/widgetStore').then(({ useWidgetStore }) => {
        useWidgetStore().addWidget('chart', tabId)
      })
    },
  })
  return () => { removeBase(); removeChart(); removeCommand() }
}
