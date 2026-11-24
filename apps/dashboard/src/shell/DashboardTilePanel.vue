<script setup lang="ts">
import { computed, h, inject, onBeforeUnmount, ref, type Component } from 'vue'
import type { Direction, GridviewPanelApi } from 'dockview-vue'
import ContextMenu from '@imengyu/vue3-context-menu'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'
import { useWidgetStore } from '@/core/stores/widgetStore'
import { widgets } from '@/shell/registries'
import MissingWidget from '@/shell/MissingWidget.vue'
import PluginErrorBoundary from '@/shell/PluginErrorBoundary.vue'

let pointerTileDrag: {
  sourceId: string
  pointerId: number
  startX: number
  startY: number
  dragging: boolean
} | undefined
let activeDropTarget: HTMLElement | undefined
let activeDropDirection: Direction | undefined
let activeDropOverlay: HTMLDivElement | undefined
let activeDropRegion: HTMLDivElement | undefined

const props = defineProps<{
  params: { widgetId: string; tabId: string }
  api: GridviewPanelApi
}>()
const workspaceStore = useWorkspaceStore()
const widgetStore = useWidgetStore()
const repositionPanel = inject<(sourceId: string, targetId: string, direction: Direction) => void>(
  'wolftrack-reposition-panel',
)
const maximized = ref(false)
const widget = computed(() => widgetStore.getWidgetById(props.params.widgetId))
const component = computed<Component>(() => widgets.get(widget.value?.type ?? '')?.component ?? MissingWidget)
const availableWidgets = computed(() => [...widgets.entries.value].sort((a, b) => a.title.localeCompare(b.title)))
const otherDashboards = computed(() => workspaceStore.tabs.filter(
  (tab) => tab.kind === 'dashboard' && tab.id !== props.params.tabId,
))

onBeforeUnmount(() => {
  if (pointerTileDrag?.sourceId !== props.params.widgetId) return
  window.removeEventListener('pointermove', moveTilePointer)
  window.removeEventListener('pointerup', finishTilePointer)
  window.removeEventListener('pointercancel', finishTilePointer)
  pointerTileDrag = undefined
  clearDropPreview()
})

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

function startTileMove(event: PointerEvent) {
  if (event.button !== 0 || !(event.target instanceof Element)
    || !event.target.closest('.base-widget__header')) return
  if (event.target instanceof Element && event.target.closest('button, input, select, textarea')) {
    return
  }
  clearDropPreview()
  pointerTileDrag = {
    sourceId: props.params.widgetId,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    dragging: false,
  }
  window.addEventListener('pointermove', moveTilePointer, { passive: false })
  window.addEventListener('pointerup', finishTilePointer)
  window.addEventListener('pointercancel', finishTilePointer)
}

function moveTilePointer(event: PointerEvent) {
  const drag = pointerTileDrag
  if (!drag || event.pointerId !== drag.pointerId) return
  if (!drag.dragging) {
    const distance = Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY)
    if (distance < 6) return
    drag.dragging = true
  }

  event.preventDefault()
  const element = document.elementFromPoint(event.clientX, event.clientY)
  const target = element instanceof Element ? element.closest('.tile-panel') as HTMLElement | null : null
  if (!target || target.dataset.widgetId === drag.sourceId) {
    clearDropPreview()
    return
  }
  showDropPreview(target, directionAt(target, event.clientX, event.clientY))
}

function finishTilePointer(event: PointerEvent) {
  const drag = pointerTileDrag
  if (!drag || event.pointerId !== drag.pointerId) return
  window.removeEventListener('pointermove', moveTilePointer)
  window.removeEventListener('pointerup', finishTilePointer)
  window.removeEventListener('pointercancel', finishTilePointer)

  const targetId = activeDropTarget?.dataset.widgetId
  const direction = activeDropDirection
  clearDropPreview()
  pointerTileDrag = undefined
  if (drag.dragging && targetId && direction && targetId !== drag.sourceId) {
    repositionPanel?.(drag.sourceId, targetId, direction)
  }
}

function clearDropPreview() {
  activeDropOverlay?.remove()
  activeDropTarget = undefined
  activeDropDirection = undefined
  activeDropOverlay = undefined
  activeDropRegion = undefined
}

function directionAt(target: HTMLElement, x: number, y: number): Direction {
  const bounds = target.getBoundingClientRect()
  const horizontal = Math.abs(x - (bounds.left + bounds.width / 2)) / bounds.width
    > Math.abs(y - (bounds.top + bounds.height / 2)) / bounds.height
  return horizontal
    ? x < bounds.left + bounds.width / 2 ? 'left' : 'right'
    : y < bounds.top + bounds.height / 2 ? 'above' : 'below'
}

function showDropPreview(target: HTMLElement, direction: Direction) {
  if (activeDropTarget !== target) {
    clearDropPreview()
    activeDropTarget = target
    activeDropOverlay = document.createElement('div')
    activeDropRegion = document.createElement('div')
    activeDropOverlay.className = 'tile-drop-preview'
    activeDropOverlay.setAttribute('aria-hidden', 'true')
    activeDropRegion.className = 'tile-drop-preview__region'

    Object.assign(activeDropOverlay.style, {
      position: 'absolute',
      inset: '0',
      zIndex: '2147483647',
      overflow: 'hidden',
      borderRadius: '6px',
      border: '1px solid color-mix(in srgb, var(--color-accent) 55%, transparent)',
      boxSizing: 'border-box',
      pointerEvents: 'none',
    })
    Object.assign(activeDropRegion.style, {
      position: 'absolute',
      boxSizing: 'border-box',
      background: 'color-mix(in srgb, var(--color-accent) 16%, transparent)',
    })
    activeDropOverlay.append(activeDropRegion)
    target.append(activeDropOverlay)
  }

  activeDropDirection = direction
  if (!activeDropRegion) return
  Object.assign(activeDropRegion.style, { top: '', right: '', bottom: '', left: '', border: '0' })
  if (direction === 'above') {
    Object.assign(activeDropRegion.style, { top: '0', right: '0', bottom: '50%', left: '0', borderBottom: '2px solid var(--color-accent)' })
  } else if (direction === 'below') {
    Object.assign(activeDropRegion.style, { top: '50%', right: '0', bottom: '0', left: '0', borderTop: '2px solid var(--color-accent)' })
  } else if (direction === 'left') {
    Object.assign(activeDropRegion.style, { top: '0', right: '50%', bottom: '0', left: '0', borderRight: '2px solid var(--color-accent)' })
  } else if (direction === 'right') {
    Object.assign(activeDropRegion.style, { top: '0', right: '0', bottom: '0', left: '50%', borderLeft: '2px solid var(--color-accent)' })
  }
}

</script>

<template>
  <Teleport to="body" :disabled="!maximized">
    <section
      class="tile-panel"
      :class="{ 'tile-panel--maximized': maximized }"
      :data-widget-id="params.widgetId"
      @pointerdown="startTileMove"
      @contextmenu="showWidgetMenu"
    >
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
  position: relative;
  display: flex;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  isolation: isolate;
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
.tile-panel__content { flex: 1; min-width: 0; min-height: 0; }
:deep(.base-widget__header) { cursor: grab; }
:deep(.base-widget__header:active) { cursor: grabbing; }
</style>
