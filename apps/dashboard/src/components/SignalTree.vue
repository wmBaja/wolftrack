<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { DbcSignal } from '@/stores/dbcStore'
import SignalRowActions from '@/components/SignalRowActions.vue'
import SignalEditorModal from '@/components/SignalEditorModal.vue'
import { useWtsStore } from '@/stores/wtsStore'
import { confirmDialog } from '@/types/dialog'
import { lookupName, lookupCategory, lookupNode, formatName } from '@/stores/dbcStore';

const props = defineProps<{
  signals: DbcSignal[]
  selectedSignals: string[]
}>()

const emit = defineEmits<{
  (e: 'add', id: string): void
  (e: 'remove', id: string): void
}>()

const wtsStore = useWtsStore()
const expanded = ref<Set<string>>(new Set())
const searchQuery = ref('')

// --- virtual signal authoring (Part 6.4) ----------------------------------
const editor = ref<{ mode: 'create' | 'edit'; name: string | null } | null>(null)
const editorDefinition = computed(() => {
  if (editor.value?.mode !== 'edit' || !editor.value.name) return null
  return wtsStore.definitions.find(def => def.name === editor.value!.name) ?? null
})

function startCreate() {
  editor.value = { mode: 'create', name: null }
}

function startEdit(signalName: string) {
  editor.value = { mode: 'edit', name: signalName }
}

async function deleteVirtual(signalName: string) {
  const confirmed = await confirmDialog(
    'Delete Virtual Signal',
    `Delete WTS.${signalName}? Charts using it will show a missing signal.`,
    { confirmText: 'Delete', danger: true },
  )
  if (!confirmed) return
  const result = await wtsStore.remove(signalName)
  if (!result.ok && result.dependents) {
    await confirmDialog(
      'Cannot Delete',
      `Used by: ${result.dependents.dependents.join(', ')}. Delete those first.`,
      { confirmText: 'OK', removeCancel: true },
    )
  }
}

function toggleExpand(key: string) {
  if (expanded.value.has(key)) {
    expanded.value.delete(key)
  } else {
    expanded.value.add(key)
  }
}

interface TreeSignal {
  id: string
  name: string
  definitionName: string
  unit: string
  selected: boolean
  isVirtual: boolean
  broken: boolean
  tooltip: string
}

interface TreeMessage {
  name: string
  signals: TreeSignal[]
}

interface TreeNode {
  name: string
  messages: TreeMessage[]
}

const treeData = computed<TreeNode[]>(() => {
  const nodesMap = new Map<string, Map<string, TreeSignal[]>>()
  const query = searchQuery.value.toLowerCase().trim()

  for (const sig of props.signals) {
    const nodeName = sig.node || 'Unassigned'
    const msgName = sig.message || 'Unknown Message'

    if (query) {
      if (!lookupName[sig.name]?.toLowerCase().includes(query) &&
          !lookupCategory[msgName]?.toLowerCase().includes(query) &&
          !lookupNode[nodeName]?.toLowerCase().includes(query) &&
          !sig.name.toLowerCase().includes(query) &&
          !msgName.toLowerCase().includes(query) &&
          !nodeName.toLowerCase().includes(query)) {
        continue
      }
    }

    if (!nodesMap.has(nodeName)) {
      nodesMap.set(nodeName, new Map())
    }
    const nodeMap = nodesMap.get(nodeName)!

    if (!nodeMap.has(msgName)) {
      nodeMap.set(msgName, [])
    }
    nodeMap.get(msgName)!.push({
      id: sig.id,
      name: sig.display_name || formatName(sig.name),
      definitionName: sig.name,
      unit: sig.unit,
      selected: props.selectedSignals.includes(sig.id),
      isVirtual: sig.is_virtual === true,
      broken: sig.broken === true,
      tooltip: [sig.description, sig.broken ? sig.broken_reason : null]
        .filter(Boolean)
        .join(' — '),
    })
  }

  const nodes: TreeNode[] = []

  for (const [nodeName, nodeMap] of nodesMap.entries()) {
    const messages: TreeMessage[] = []
    for (const [msgName, sigList] of nodeMap.entries()) {
      messages.push({
        name: msgName,
        signals: sigList.sort((a, b) => a.name.localeCompare(b.name))
      })
    }
    messages.sort((a, b) => a.name.localeCompare(b.name))
    nodes.push({ name: nodeName, messages })
  }

  nodes.sort((a, b) => a.name.localeCompare(b.name))
  return nodes
})

watch(searchQuery, (newQuery) => {
  if (newQuery.trim() !== '') {
    // Auto-expand all when searching
    for (const node of treeData.value) {
      expanded.value.add(node.name)
      for (const msg of node.messages) {
        expanded.value.add(node.name + '::' + msg.name)
      }
    }
  }
})

function handleSignalClick(sig: TreeSignal) {
  if (sig.selected) {
    emit('remove', sig.id)
  } else {
    emit('add', sig.id)
  }
}
</script>

<template>
  <div class="signal-tree-container">
    <div class="search-bar">
      <input
        type="text"
        v-model="searchQuery"
        placeholder="Search signals..."
        class="search-input"
      />
      <button type="button" class="new-wt-btn" data-testid="new-wt-btn"
              title="Create a virtual signal" @click="startCreate">+ New WT Signal</button>
    </div>
    <p v-if="wtsStore.promotionNotice" class="promotion-notice" data-testid="promotion-notice">
      {{ wtsStore.promotionNotice }}
    </p>
    <div class="signal-tree custom-scrollbar">
      <div v-for="node in treeData" :key="node.name" class="tree-node">
        <div
          class="tree-item folder"
          @click="toggleExpand(node.name)"
        >
          <span class="chevron" :class="{ open: expanded.has(node.name) }">▶</span>
          <span class="icon">💻</span>
          <span class="label">{{ lookupNode[node.name] || node.name }}</span>
        </div>

        <div v-show="expanded.has(node.name)" class="tree-children">
          <div v-for="msg in node.messages" :key="node.name + '::' + msg.name" class="tree-message">
            <div
              class="tree-item folder"
              @click="toggleExpand(node.name + '::' + msg.name)"
            >
              <span class="chevron" :class="{ open: expanded.has(node.name + '::' + msg.name) }">▶</span>
              <span class="icon">✉️</span>
              <span class="label">{{ lookupCategory[msg.name] || msg.name }}</span>
            </div>

            <div v-show="expanded.has(node.name + '::' + msg.name)" class="tree-children signal-level">
              <div
                v-for="sig in msg.signals"
                :key="sig.id"
                class="tree-item leaf"
                :class="{ selected: sig.selected }"
                @click="handleSignalClick(sig)"
              >
                <span class="icon">📈</span>
                <span class="label">{{ lookupName[sig.name] || formatName(sig.name) }}</span>
                <span v-if="sig.isVirtual" class="virtual-badge" title="Virtual signal">WT</span>
                <span
                  v-if="sig.broken"
                  class="broken-icon"
                  :title="sig.tooltip || 'Broken definition'"
                >⚠️</span>
                <span v-if="sig.unit" class="unit" :title="sig.tooltip">({{ sig.unit }})</span>
                <SignalRowActions
                  v-if="sig.isVirtual"
                  @edit="startEdit(sig.definitionName)"
                  @delete="deleteVirtual(sig.definitionName)"
                />
                <span v-if="sig.selected" class="check">✓</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="treeData.length === 0" class="no-results">
        No signals found.
      </div>
    </div>

    <SignalEditorModal
      v-if="editor"
      :mode="editor.mode"
      :initial-definition="editorDefinition"
      @saved="() => {}"
      @close="editor = null"
    />
  </div>
</template>

<style scoped>
.signal-tree-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: 100%;
  min-height: 0;
}

.search-input {
  width: 100%;
  padding: 6px 10px;
  border-radius: 4px;
  border: 1px solid var(--color-border);
  background: var(--color-background);
  color: var(--color-text);
  font-size: 13px;
  outline: none;
}

.search-input:focus {
  border-color: var(--color-accent);
}

.signal-tree {
  font-family: monospace;
  font-size: 13px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 8px;
  color: var(--color-text);
  user-select: none;
}

.tree-children {
  padding-left: 16px;
}

.signal-level {
  padding-left: 24px;
}

.tree-item {
  display: flex;
  align-items: center;
  padding: 4px 6px;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
  gap: 6px;
}

.tree-item:hover {
  background: var(--color-panel);
}

.tree-item.leaf.selected {
  background: var(--color-accent);
  color: white;
}

.tree-item.leaf.selected:hover {
  filter: brightness(1.1);
}

.chevron {
  font-size: 10px;
  transition: transform 0.2s;
  display: inline-block;
  color: var(--color-text-muted);
}

.chevron.open {
  transform: rotate(90deg);
}

.icon {
  font-size: 14px;
}

.label {
  flex: 1;
}

.unit {
  color: var(--color-text-muted);
  font-size: 11px;
}

.leaf.selected .unit {
  color: rgba(255, 255, 255, 0.8);
}

.check {
  font-weight: bold;
}

.virtual-badge {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 0 4px;
  border-radius: 3px;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.4));
}

.new-wt-btn {
  margin-top: 6px;
  width: 100%;
  border: 1px dashed var(--color-border, rgba(128, 128, 128, 0.45));
  background: none;
  color: var(--color-text-muted);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 11px;
  cursor: pointer;
}

.new-wt-btn:hover {
  color: var(--color-text, inherit);
  border-color: var(--color-accent, #3b82f6);
}

.promotion-notice {
  margin: 6px 0 0;
  font-size: 11px;
  color: var(--color-text-muted);
}

.broken-icon {
  font-size: 11px;
}

.no-results {
  padding: 10px;
  text-align: center;
  color: var(--color-text-muted);
}
</style>
