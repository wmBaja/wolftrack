<!-- src/components/widgets/BaseWidget.vue -->
<script setup lang="ts">
import { ref, computed, h, onBeforeUnmount} from 'vue'
import { useWidgetStore } from '@/stores/widgetStore'
import { useDbcStore } from '@/stores/dbcStore'
import { useDataSourceStore } from '@/stores/dataSourceStore'
import { useLiveDataStore } from '@/stores/liveDataStore'
import { useLogDataStore } from '@/stores/logDataStore'
import ContextMenu from '@imengyu/vue3-context-menu'
import type { MenuOptions } from '@imengyu/vue3-context-menu'
import type { WIDGET_TYPES } from '@/types/widgets'
import SignalTree from '@/components/SignalTree.vue'
import { watch } from 'vue'

interface Props {
  widgetId: string
  icon?: string
  customMenuItems?: MenuOptions['items']
}

const props = withDefaults(defineProps<Props>(), {
  icon: '📦',
  customMenuItems: () => []
})

const store = useWidgetStore()
const dbcStore = useDbcStore()
const widget = computed(() => store.getWidgetById(props.widgetId))

const isEditing = ref(false)
const isLoading = ref(false)
const localTitle = ref('')
const titleInputRef = ref<HTMLInputElement>()

const isConfiguring = ref(false)
const localSignals = ref<string[]>([...(widget.value?.signals || [])])

function toggleConfig() {
  isConfiguring.value = !isConfiguring.value
  if (!isConfiguring.value) {
    store.updateWidget(props.widgetId, { signals: [...localSignals.value] })
  } else {
    localSignals.value = [...(widget.value?.signals || [])]
  }
}

function removeSignal(sig: string) {
  localSignals.value = localSignals.value.filter(s => s !== sig)
}

function addSignalId(sigId: string) {
  if (!localSignals.value.includes(sigId)) {
    localSignals.value.push(sigId)
  }
}

const dataSourceStore = useDataSourceStore()
const liveDataStore = useLiveDataStore()
const logDataStore = useLogDataStore()
let logQueryTimeout: number | null = null

const queryLogData = () => {
    if (dataSourceStore.config.source !== 'logfile' || logDataStore.status.status !== 'ready') return
    const signals = widget.value?.signals || []
    if (signals.length > 0) {
        const { start_ts, end_ts } = logDataStore.queryWindow
        logDataStore.queryData(signals, start_ts, end_ts)
    }
}

watch(() => [
  logDataStore.status.status,
  widget.value?.signals,
  dataSourceStore.config.source,
  logDataStore.queryWindow.start_ts,
  logDataStore.queryWindow.end_ts,
], () => {
    if (logQueryTimeout) {
      window.clearTimeout(logQueryTimeout)
    }
    // Range sliders can emit many input events. Waiting briefly avoids a
    // request per pixel while still keeping the selected window responsive.
    logQueryTimeout = window.setTimeout(queryLogData, 150)
})

onBeforeUnmount(() => {
  if (logQueryTimeout) {
    window.clearTimeout(logQueryTimeout)
  }
})

async function handleRefresh() {
  if (dataSourceStore.config.source === 'zmq') {
      liveDataStore.clearBuffers()
  } else {
      queryLogData()
  }
}

function startEditTitle() {
  if (!widget.value) return
  localTitle.value = widget.value.title
  isEditing.value = true
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (!isEditing.value) return
      const el = titleInputRef.value
      if (!el) return
      el.focus()
      el.select()
    })
  })
}

function saveTitle() {
  const trimmed = localTitle.value.trim()
  if (trimmed && widget.value) {
    store.updateWidget(props.widgetId, { title: trimmed })
  }
  isEditing.value = false
}

function cancelEdit() {
  if (widget.value) {
    localTitle.value = widget.value.title
  }
  isEditing.value = false
}

function setLoading(value: boolean) {
  isLoading.value = value
}

function handleContextMenu(event: MouseEvent) {
  event.preventDefault()
  event.stopPropagation()

  const menuItems: MenuOptions['items'] = [
    {
      label: isConfiguring.value ? 'Close Config' : 'Configure Signals',
      icon: h('span', '⚙️'),
      onClick: toggleConfig,
    },
    {
      label: 'Edit Title',
      icon: h('span', '✏️'),
      onClick: startEditTitle,
    },
    {
      label: 'Refresh',
      icon: h('span', '🔄'),
      onClick: handleRefresh,
    },
  ]

  // Add custom menu items
  if (props.customMenuItems && props.customMenuItems.length > 0) {
    menuItems.push(...props.customMenuItems)
    menuItems.push({ divided: true })
  }

  // Add common actions
  menuItems.push(
    {
      label: 'Duplicate',
      icon: h('span', '📋'),
      onClick: () => {
        if (widget.value) {
          store.addWidget(widget.value.type as WIDGET_TYPES, {
            x: widget.value.x + 1,
            y: widget.value.y + 1,
            w: widget.value.w,
            h: widget.value.h,
          })
        }
      },
    },
    { divided: true },
    {
      label: 'Delete',
      icon: h('span', '🗑️'),
      customClass: 'context-menu-danger',
      onClick: () => store.removeWidget(props.widgetId),
    }
  )

  ContextMenu.showContextMenu({
    x: event.x,
    y: event.y,
    items: menuItems,
    theme: 'mac dark',
    zIndex: 1000,
  })
}

defineExpose({ handleRefresh, startEditTitle, setLoading, toggleConfig })
</script>

<template>
  <div
    v-if="widget"
    class="base-widget"
    :class="{
      'base-widget--editing': isEditing,
      'base-widget--loading': isLoading
    }"
    @contextmenu="handleContextMenu"
  >
    <header class="base-widget__header">
      <div class="base-widget__title-section">
        <span class="base-widget__icon" role="img" :aria-label="widget?.type || 'widget'">
          {{ icon }}
        </span>

        <input
          v-if="isEditing"
          ref="titleInputRef"
          v-model="localTitle"
          @blur="saveTitle"
          @keyup.enter="saveTitle"
          @keyup.escape="cancelEdit"
          class="base-widget__title-input"
          placeholder="Widget title..."
          maxlength="50"
        />

        <h3
          v-else
          class="base-widget__title"
          @dblclick="startEditTitle"
          :title="widget?.title"
        >
          {{ widget.title }}
        </h3>
      </div>
    </header>

    <!-- Widget Content -->
    <main class="base-widget__content">
      <div v-if="isConfiguring" class="config-panel">
        <h4>Signals Config</h4>
        <div class="signal-list">
          <div v-for="sig in localSignals" :key="sig" class="signal-tag">
            {{ sig }}
            <button @click="removeSignal(sig)">×</button>
          </div>
        </div>
        <SignalTree
          :signals="dbcStore.signals"
          :selected-signals="localSignals"
          @add="addSignalId"
          @remove="removeSignal"
        />
        <button class="save-btn" @click="toggleConfig">Done</button>
      </div>
      <slot
        v-else
        :widget="widget"
        :is-loading="isLoading"
        :refresh="handleRefresh"
      ></slot>
    </main>

    <!-- Loading Overlay -->
    <Transition name="fade">
      <div v-if="isLoading" class="base-widget__loading-overlay">
        <div class="base-widget__spinner" role="status" aria-label="Loading...">
          <span class="sr-only">Loading...</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.base-widget {
  background: var(--color-panel);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.4);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.base-widget:hover {
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.base-widget--editing {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.base-widget--loading {
  pointer-events: none;
}

/* Header */
.base-widget__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-panel-header);
  flex-shrink: 0;
  min-height: 10px;
}

.base-widget__title-section {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.base-widget__icon {
  font-size: 20px;
  flex-shrink: 0;
  line-height: 1;
  filter: grayscale(0.3);
}

.base-widget__title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
  transition: color 0.2s;
}

.base-widget__title:hover {
  color: var(--color-accent);
}

.base-widget__title-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid var(--color-accent);
  border-radius: 4px;
  font-size: 14px;
  font-weight: 600;
  background: var(--color-panel);
  color: var(--color-text);
  outline: none;
  transition: border-color 0.2s;
}

.base-widget__title-input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.base-widget__content {
  flex: 1;
  padding: 16px;
  overflow: hidden;
  min-height: 0;
  height: 100%;
}

.base-widget__loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 14, 26, 0.7);
  backdrop-filter: blur(2px);
  z-index: 10;
}

.base-widget__spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-top: 3px solid var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* Config Panel Styles */
.config-panel {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.signal-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.signal-tag {
  background: var(--color-accent);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.signal-tag button {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 14px;
}

.save-btn {
  margin-top: 10px;
  padding: 8px 16px;
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  flex-shrink: 0;
}
.save-btn:hover {
  opacity: 0.9;
}
</style>
