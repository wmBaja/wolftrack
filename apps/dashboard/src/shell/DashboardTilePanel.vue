<script setup lang="ts">
import { computed, ref, type Component } from 'vue'
import type { Direction, GridviewApi, GridviewPanelApi } from 'dockview-vue'
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
const moveMenuOpen = ref(false)
const replaceMenuOpen = ref(false)
const widget = computed(() => widgetStore.getWidgetById(props.params.widgetId))
const component = computed<Component>(() => widgets.get(widget.value?.type ?? '')?.component ?? MissingWidget)
const availableWidgets = computed(() => [...widgets.entries.value].sort((a, b) => a.title.localeCompare(b.title)))
const otherDashboards = computed(() => workspaceStore.tabs.filter(
  (tab) => tab.kind === 'dashboard' && tab.id !== props.params.tabId,
))

function moveToDashboard(tabId: string) {
  widgetStore.moveWidget(props.params.widgetId, props.params.tabId, tabId)
  moveMenuOpen.value = false
}

function replaceWidget(type: string, title: string) {
  widgetStore.updateWidget(props.params.widgetId, { type, title, config: {}, signals: [] }, props.params.tabId)
  replaceMenuOpen.value = false
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
    >
      <header class="tile-panel__toolbar">
        <span class="tile-panel__drag-handle" draggable="true" aria-label="Move tile" @dragstart="startTileDrag">⠿</span>
        <span class="tile-panel__title">{{ widget?.title ?? 'Unavailable widget' }}</span>
        <div class="tile-panel__actions">
          <div class="tile-panel__move">
            <button type="button" :aria-expanded="replaceMenuOpen" @click="replaceMenuOpen = !replaceMenuOpen">
              Replace…
            </button>
            <div v-if="replaceMenuOpen" class="tile-panel__move-menu" role="menu">
              <button
                v-for="contribution in availableWidgets"
                :key="contribution.type"
                type="button"
                role="menuitem"
                @click="replaceWidget(contribution.type, contribution.title)"
              >
                {{ contribution.title }}
              </button>
            </div>
          </div>
          <div v-if="otherDashboards.length" class="tile-panel__move">
            <button type="button" :aria-expanded="moveMenuOpen" @click="moveMenuOpen = !moveMenuOpen">
              Move to dashboard…
            </button>
            <div v-if="moveMenuOpen" class="tile-panel__move-menu" role="menu">
              <button
                v-for="dashboard in otherDashboards"
                :key="dashboard.id"
                type="button"
                role="menuitem"
                @click="moveToDashboard(dashboard.id)"
              >
                {{ dashboard.title }}
              </button>
            </div>
          </div>
          <button type="button" :aria-label="maximized ? 'Restore tile size' : 'Maximize tile'" @click="maximized = !maximized">
            {{ maximized ? 'Restore' : 'Maximize' }}
          </button>
          <button type="button" aria-label="Close tile" @click="widgetStore.removeWidget(params.widgetId, params.tabId)">×</button>
        </div>
      </header>
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
.tile-panel__toolbar {
  display: flex;
  min-height: 34px;
  align-items: center;
  gap: 8px;
  padding: 3px 7px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-panel-header);
}
.tile-panel__drag-handle { color: var(--color-text-muted); cursor: grab; }
.tile-panel__title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tile-panel__actions { display: flex; align-items: center; gap: 4px; }
.tile-panel__actions button {
  padding: 2px 6px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-bg);
  color: var(--color-text);
  cursor: pointer;
  white-space: nowrap;
}
.tile-panel__move { position: relative; }
.tile-panel__move-menu {
  position: absolute;
  z-index: 10;
  top: calc(100% + 3px);
  right: 0;
  display: flex;
  min-width: 150px;
  flex-direction: column;
  padding: 4px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background: var(--color-panel);
}
.tile-panel__move-menu button { text-align: left; }
.tile-panel__content { flex: 1; min-width: 0; min-height: 0; }
</style>
