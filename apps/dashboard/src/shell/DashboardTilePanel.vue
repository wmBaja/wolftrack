<script setup lang="ts">
import { computed, h, ref, type Component } from 'vue'
import type { Direction, GridviewApi, GridviewPanelApi } from 'dockview-vue'
import ContextMenu from '@imengyu/vue3-context-menu'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'
import { useWidgetStore } from '@/core/stores/widgetStore'
import { widgets } from '@/shell/registries'
import MissingWidget from '@/shell/MissingWidget.vue'
import PluginErrorBoundary from '@/shell/PluginErrorBoundary.vue'

const props = defineProps<{
  params: { widgetId: string; tabId: string }
  api: GridviewPanelApi
  containerApi: GridviewApi
}>()
const workspaceStore = useWorkspaceStore()
const widgetStore = useWidgetStore()
const maximized = ref(false)
const widget = computed(() => widgetStore.getWidgetById(props.params.widgetId))
const component = computed<Component>(() => widgets.get(widget.value?.type ?? '')?.component ?? MissingWidget)
const availableWidgets = computed(() => [...widgets.entries.value].sort((a, b) => a.title.localeCompare(b.title)))
const otherDashboards = computed(() => workspaceStore.tabs.filter(
  (tab) => tab.kind === 'dashboard' && tab.id !== props.params.tabId,
))

function moveToDashboard(tabId: string) {
  widgetStore.moveWidget(props.params.widgetId, props.params.tabId, tabId)
}

function replaceWidget(type: string, title: string) {
  widgetStore.updateWidget(props.params.widgetId, { type, title, config: {}, signals: [] }, props.params.tabId)
}

function showWidgetMenu(event: MouseEvent) {
  event.preventDefault()
  ContextMenu.showContextMenu({
    x: event.x,
    y: event.y,
    theme: 'mac dark',
    zIndex: 1000,
    items: [
      { label: maximized.value ? 'Restore' : 'Maximize', icon: h('span', maximized.value ? '↙' : '↗'), onClick: () => { maximized.value = !maximized.value } },
      { label: 'Replace…', icon: h('span', '🔄'), children: availableWidgets.value.map((entry) => ({ label: entry.title, onClick: () => replaceWidget(entry.type, entry.title) })) },
      ...(otherDashboards.value.length ? [{
        label: 'Move to dashboard…',
        icon: h('span', '↗'),
        children: otherDashboards.value.map((dashboard) => ({ label: dashboard.title, onClick: () => moveToDashboard(dashboard.id) })),
      }] : []),
      { divided: true },
      { label: 'Close widget', icon: h('span', '✕'), customClass: 'context-menu-danger', onClick: () => widgetStore.removeWidget(props.params.widgetId, props.params.tabId) },
    ],
  })
}

function startTileDrag(event: DragEvent) {
  event.dataTransfer?.setData('application/x-wolftrack-widget-id', props.params.widgetId)
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}

function dropTile(event: DragEvent) {
  const sourceId = event.dataTransfer?.getData('application/x-wolftrack-widget-id')
  if (!sourceId || sourceId === props.params.widgetId) return
  const source = props.containerApi.getPanel(sourceId)
  const bounds = event.currentTarget instanceof HTMLElement
    ? event.currentTarget.getBoundingClientRect()
    : null
  if (!source || !bounds) return
  const horizontal = Math.abs(event.clientX - (bounds.left + bounds.width / 2)) / bounds.width
    > Math.abs(event.clientY - (bounds.top + bounds.height / 2)) / bounds.height
  const direction: Direction = horizontal
    ? event.clientX < bounds.left + bounds.width / 2 ? 'left' : 'right'
    : event.clientY < bounds.top + bounds.height / 2 ? 'above' : 'below'
  const panels = props.containerApi.panels
  const sourceIndex = panels.findIndex(panel => panel.id === sourceId)
  const targetIndex = panels.findIndex(panel => panel.id === props.params.widgetId)
  if (sourceIndex < targetIndex) {
    const opposite: Record<Direction, Direction> = {
      left: 'right', right: 'left', above: 'below', below: 'above', within: 'within',
    }
    const target = props.containerApi.getPanel(props.params.widgetId)
    if (target) props.containerApi.movePanel(target, { direction: opposite[direction], reference: sourceId })
  } else {
    props.containerApi.movePanel(source, { direction, reference: props.params.widgetId })
  }
}
</script>

<template>
  <Teleport to="body" :disabled="!maximized">
    <section
      class="tile-panel"
      :class="{ 'tile-panel--maximized': maximized }"
      :data-widget-id="params.widgetId"
      @dragover.prevent
      @drop.prevent="dropTile"
      @contextmenu="showWidgetMenu"
    >
      <span class="tile-panel__drag-handle" draggable="true" aria-label="Move tile" @dragstart="startTileDrag">⠿</span>
      <div class="tile-panel__content">
        <PluginErrorBoundary :owner-id="String(widget?.type ?? 'unknown widget')" @disable="widgetStore.removeWidget(params.widgetId, params.tabId)">
          <component :is="component" :widget-id="params.widgetId" />
        </PluginErrorBoundary>
      </div>
    </section>
  </Teleport>
</template>

<style scoped>
.tile-panel {
  display: flex;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-panel);
}
.tile-panel--maximized {
  position: fixed;
  z-index: 120;
  inset: calc(var(--navbar-height) + 54px) 18px 18px;
  width: auto;
  height: auto;
  box-shadow: 0 12px 50px rgb(0 0 0 / 55%);
}
.tile-panel__drag-handle { position: absolute; z-index: 3; top: 7px; left: 7px; color: var(--color-text-muted); cursor: grab; }
.tile-panel__content { flex: 1; min-width: 0; min-height: 0; }
</style>
