<script setup lang="ts">
import { h, nextTick, onBeforeUnmount, ref } from 'vue'
import type { DockviewPanelApi } from 'dockview-vue'
import ContextMenu from '@imengyu/vue3-context-menu'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'

const props = defineProps<{ api: DockviewPanelApi }>()
const emit = defineEmits<{ importWorkspace: [] }>()
const workspaceStore = useWorkspaceStore()
const editing = ref(false)
const title = ref(props.api.title ?? '')
const titleInput = ref<HTMLInputElement>()
const titleListener = props.api.onDidTitleChange(({ title: newTitle }) => { title.value = newTitle })

onBeforeUnmount(() => titleListener.dispose())

async function startRename() {
  editing.value = true
  await nextTick()
  titleInput.value?.select()
}

function saveTitle() {
  const newTitle = title.value.trim()
  if (newTitle) {
    props.api.setTitle(newTitle)
    workspaceStore.renameTab(props.api.id, newTitle)
  } else {
    title.value = props.api.title ?? ''
  }
  editing.value = false
}

function cancelRename() {
  title.value = props.api.title ?? ''
  editing.value = false
}

function showContextMenu(event: MouseEvent) {
  event.preventDefault()
  event.stopPropagation()
  ContextMenu.showContextMenu({
    x: event.x,
    y: event.y,
    theme: 'mac dark',
    zIndex: 1000,
    items: [
      { label: 'Rename', icon: h('span', '✏️'), onClick: () => void startRename() },
      { label: 'Close tab', icon: h('span', '✕'), onClick: () => props.api.close() },
      { divided: true },
      { label: 'Export Workspace', icon: h('span', '📤'), onClick: () => workspaceStore.exportWorkspace() },
      { label: 'Import Workspace', icon: h('span', '📥'), onClick: () => emit('importWorkspace') },
    ],
  })
}
</script>

<template>
  <div class="workspace-dockview-tab" @dblclick.stop="startRename" @contextmenu.stop="showContextMenu">
    <input
      v-if="editing"
      ref="titleInput"
      v-model="title"
      class="workspace-dockview-tab__input"
      aria-label="Tab name"
      @click.stop
      @keydown.enter.prevent="saveTitle"
      @keydown.esc.prevent="cancelRename"
      @blur="saveTitle"
    >
    <span v-else class="workspace-dockview-tab__title" :title="title">{{ title }}</span>
    <button
      v-if="!editing"
      type="button"
      class="workspace-dockview-tab__close"
      :aria-label="`Close ${title}`"
      @pointerdown.stop
      @click.stop="props.api.close()"
    >
      ×
    </button>
  </div>
</template>

<style scoped>
.workspace-dockview-tab {
  display: flex;
  width: 100%;
  min-width: 0;
  height: 100%;
  align-items: center;
  gap: 6px;
  padding: 0 7px 0 10px;
  color: inherit;
}

.workspace-dockview-tab__title {
  overflow: hidden;
  flex: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-dockview-tab__input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: inherit;
  font: inherit;
}

.workspace-dockview-tab__close {
  display: grid;
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
  place-items: center;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  line-height: 1;
  transition: background-color 120ms ease, color 120ms ease;
}

.workspace-dockview-tab__close:hover { background: var(--color-hover); color: var(--color-text); }
.workspace-dockview-tab__close:focus-visible { outline: 2px solid var(--color-accent); }
</style>
