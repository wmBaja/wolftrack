<script setup lang="ts">
import { computed, ref, onBeforeUnmount, onMounted } from 'vue'
import { useDbcStore } from '@/stores/dbcStore'
import { useLogStore } from '@/stores/logStore'
import { useDaqConnectionStore } from '@/stores/daqConnectionStore'

const dbcStore = useDbcStore()
const logStore = useLogStore()
const daqConnection = useDaqConnectionStore()

const isOpen = ref(false)
const activeTab = ref<'logs' | 'dbc'>('dbc')
const renameTarget = ref<{ type: 'log' | 'dbc'; name: string } | null>(null)
const renameValue = ref('')
const deleteTarget = ref<{ type: 'log' | 'dbc'; names: string[] } | null>(null)
const selectedLogNames = ref<string[]>([])
const selectedDbcNames = ref<string[]>([])
const selectionAnchor = ref<{ type: 'log' | 'dbc'; name: string } | null>(null)
const isBulkDownloading = ref(false)

const selectedLogCount = computed(() => selectedLogNames.value.length)
const selectedDbcCount = computed(() => selectedDbcNames.value.length)
const selectableLogNames = computed(() => logStore.availableLogs
  .filter((log) => !isActiveLog(log))
  .map((log) => log.name))

const renameIsValid = computed(() => {
  if (!renameTarget.value) return false
  const { type, name } = renameTarget.value
  const newName = renameFilename.value
  const isValid = type === 'log'
    ? logStore.isValidLogFilename(newName)
    : dbcStore.isValidDbcFilename(newName)
  return isValid && newName !== name
})

const renameExtension = computed(() => {
  if (!renameTarget.value) return ''
  return renameTarget.value.name.slice(renameTarget.value.name.lastIndexOf('.'))
})

const renameFilename = computed(() => `${renameValue.value}${renameExtension.value}`)

function togglePanel() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    dbcStore.fetchDbcs()
    if (activeTab.value === 'logs') {
      logStore.fetchLogs()
    }
  }
}

// DBC Tab logic
function handleDbcUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) {
    dbcStore.uploadDbc(file)
  }
}

function selectDbc(filename: string) {
  dbcStore.selectDbc(filename)
}

function deleteDbc(filename: string) {
  deleteTarget.value = { type: 'dbc', names: [filename] }
}

function showLogsTab() {
  activeTab.value = 'logs'
  if (isOpen.value) {
    logStore.fetchLogs()
  }
}

function downloadLog(name: string, url: string) {
  logStore.downloadLog({ name, url })
}

async function downloadSelectedLogs() {
  if (isBulkDownloading.value) return

  const selectedLogs = logStore.availableLogs.filter((log) => selectedLogNames.value.includes(log.name))
  if (selectedLogs.length === 0) return

  isBulkDownloading.value = true
  try {
    for (const log of selectedLogs) {
      await logStore.downloadLog(log)
    }
  } finally {
    isBulkDownloading.value = false
  }
}

function startRename(type: 'log' | 'dbc', name: string) {
  if (
    (type === 'log' && (isActiveLog({ name }) || logStore.mutatingName !== null))
    || (type === 'dbc' && dbcStore.mutatingName !== null)
  ) return

  renameTarget.value = { type, name }
  renameValue.value = name.slice(0, name.lastIndexOf('.'))
}

function cancelRename() {
  renameTarget.value = null
  renameValue.value = ''
}

async function saveRename() {
  if (!renameTarget.value || !renameIsValid.value) return

  const { type, name } = renameTarget.value
  const renamed = type === 'log'
    ? await logStore.renameLog(name, renameFilename.value)
    : await dbcStore.renameDbc(name, renameFilename.value)

  if (renamed) cancelRename()
}

async function confirmDelete() {
  if (!deleteTarget.value) return

  const { type, names } = deleteTarget.value
  const deletedNames: string[] = []
  for (const name of names) {
    const deleted = type === 'log'
      ? await logStore.deleteLog(name)
      : await dbcStore.deleteDbc(name)
    if (deleted) deletedNames.push(name)
  }

  if (type === 'log') {
    selectedLogNames.value = selectedLogNames.value.filter((name) => !deletedNames.includes(name))
  } else {
    selectedDbcNames.value = selectedDbcNames.value.filter((name) => !deletedNames.includes(name))
  }
  deleteTarget.value = null
}

function toggleFileSelection(type: 'log' | 'dbc', name: string) {
  const selected = type === 'log' ? selectedLogNames.value : selectedDbcNames.value
  const next = selected.includes(name)
    ? selected.filter((selectedName) => selectedName !== name)
    : [...selected, name]

  if (type === 'log') selectedLogNames.value = next
  else selectedDbcNames.value = next
}

function getSelectableNames(type: 'log' | 'dbc') {
  return type === 'log'
    ? selectableLogNames.value
    : dbcStore.availableDbcs.map((dbc) => dbc.name)
}

function handleFileClick(type: 'log' | 'dbc', name: string, event: MouseEvent) {
  if (type === 'log' && isActiveLog({ name })) return

  const names = getSelectableNames(type)
  const selected = type === 'log' ? selectedLogNames.value : selectedDbcNames.value
  const anchor = selectionAnchor.value?.type === type ? selectionAnchor.value.name : null

  if (event.shiftKey && anchor && names.includes(anchor)) {
    const start = Math.min(names.indexOf(anchor), names.indexOf(name))
    const end = Math.max(names.indexOf(anchor), names.indexOf(name))
    const next = [...new Set([...selected, ...names.slice(start, end + 1)])]
    if (type === 'log') selectedLogNames.value = next
    else selectedDbcNames.value = next
    return
  }

  selectionAnchor.value = { type, name }
  if (event.ctrlKey || event.metaKey) {
    toggleFileSelection(type, name)
  } else if (type === 'dbc') {
    selectDbc(name)
  }
}

function isSelected(type: 'log' | 'dbc', name: string) {
  return (type === 'log' ? selectedLogNames.value : selectedDbcNames.value).includes(name)
}

function selectAll(type: 'log' | 'dbc') {
  const availableNames = type === 'log'
    ? selectableLogNames.value
    : dbcStore.availableDbcs.map((dbc) => dbc.name)

  if (type === 'log') selectedLogNames.value = availableNames
  else selectedDbcNames.value = availableNames
}

function clearSelection(type: 'log' | 'dbc') {
  if (type === 'log') selectedLogNames.value = []
  else selectedDbcNames.value = []
  if (selectionAnchor.value?.type === type) selectionAnchor.value = null
}

function requestBulkDelete(type: 'log' | 'dbc') {
  const names = type === 'log'
    ? selectedLogNames.value.filter((name) => selectableLogNames.value.includes(name))
    : selectedDbcNames.value
  if (names.length > 0) deleteTarget.value = { type, names: [...names] }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape' || !isOpen.value) return

  if (renameTarget.value) {
    cancelRename()
    return
  }

  clearSelection(activeTab.value === 'logs' ? 'log' : 'dbc')
}

function isRenaming(type: 'log' | 'dbc', name: string) {
  return renameTarget.value?.type === type && renameTarget.value.name === name
}

function isLogActionDisabled(log: { name: string; active?: boolean }) {
  return isActiveLog(log) || logStore.mutatingName !== null
}

function isDbcActionDisabled() {
  return dbcStore.mutatingName !== null
}

defineExpose({ togglePanel })

function formatSize(bytes: number) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatDate(timestamp: number) {
  const date = timestamp > 1_000_000_000_000 ? new Date(timestamp) : new Date(timestamp * 1000)

  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatLogDate(log: { name: string; mtime?: number }) {
  if (typeof log.mtime === 'number') {
    return formatDate(log.mtime)
  }

  return null
}

function getLogTimestamp(log: { name: string; mtime?: number }) {
  if (typeof log.mtime === 'number') {
    return log.mtime > 1_000_000_000_000 ? log.mtime : log.mtime * 1000
  }

  return Number.NEGATIVE_INFINITY
}

function getActiveLogName() {
  const explicitlyActive = logStore.availableLogs.find((log) => log.active)
  if (explicitlyActive) {
    return explicitlyActive.name
  }

  if (daqConnection.loggingStatus !== 'active' && daqConnection.loggingStatus !== 'starting') {
    return null
  }

  if (logStore.availableLogs.length === 0) {
    return null
  }

  return logStore.availableLogs.reduce((latest, log) => {
    return getLogTimestamp(log) > getLogTimestamp(latest) ? log : latest
  }).name
}

function isActiveLog(log: { name: string; active?: boolean }) {
  return getActiveLogName() === log.name
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  dbcStore.fetchDbcs()
  dbcStore.fetchSignals()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <Transition name="slide-right">
    <div v-if="isOpen" class="file-manager-drawer">
      <!-- Header -->
      <div class="drawer-header">
        <h2 class="drawer-title">File Manager</h2>
        <button class="close-btn" @click="isOpen = false" aria-label="Close">✕</button>
      </div>

      <!-- Tabs -->
      <div class="tabs">
        <button
          id="file-manager-logs-tab"
          class="tab-btn"
          :class="{ active: activeTab === 'logs' }"
          @click="showLogsTab"
        >
          Logs
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'dbc' }"
          @click="activeTab = 'dbc'"
        >
          DBC
        </button>
      </div>

      <!-- Content -->
      <div class="drawer-content" @click.self="activeTab === 'logs' ? clearSelection('log') : clearSelection('dbc')">
        <!-- Logs Tab -->
        <div v-if="activeTab === 'logs'" class="tab-pane" @click.self="clearSelection('log')">
          <div class="logs-header">
            <div class="logs-source">
              <span class="logs-label">DAQ Log API</span>
              <span class="logs-target">
                {{ daqConnection.target.host || 'No DAQ selected' }}<template v-if="daqConnection.target.port">:{{ daqConnection.target.port }}</template>/api/logs
              </span>
            </div>
            <button class="refresh-btn" @click="logStore.fetchLogs" :disabled="logStore.isLoading">Refresh</button>
          </div>
          <div class="selection-toolbar">
            <button type="button" @click="selectAll('log')" :disabled="selectableLogNames.length === 0">Select all</button>
            <span v-if="selectedLogCount" class="selection-count">{{ selectedLogCount }} selected</span>
            <button
              v-if="selectedLogCount"
              type="button"
              class="selection-icon-btn"
              :disabled="isBulkDownloading || logStore.downloadingName !== null"
              :title="isBulkDownloading ? 'Saving selected logs…' : 'Download selected logs'"
              :aria-label="isBulkDownloading ? 'Saving selected logs' : 'Download selected logs'"
              @click="downloadSelectedLogs"
            >
              <svg viewBox="0 0 20 20" fill="currentColor" width="15" height="15" aria-hidden="true">
                <path fill-rule="evenodd" d="M10 2a1 1 0 0 1 1 1v7.586l2.293-2.293a1 1 0 0 1 1.414 1.414l-4 4a1 1 0 0 1-1.414 0l-4-4a1 1 0 0 1 1.414-1.414L9 10.586V3a1 1 0 0 1 1-1Zm-6 14a1 1 0 0 1 1-1h10a1 1 0 1 1 0 2H5a1 1 0 0 1-1-1Z" clip-rule="evenodd" />
              </svg>
            </button>
            <button v-if="selectedLogCount" type="button" class="bulk-delete-btn selection-icon-btn" title="Delete selected logs" aria-label="Delete selected logs" @click="requestBulkDelete('log')">
              <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14" aria-hidden="true">
                <path fill-rule="evenodd" d="M9 2a1 1 0 0 0-.894.553L7.382 4H4a1 1 0 0 0 0 2v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V6a1 1 0 1 0 0-2h-3.382l-.724-1.447A1 1 0 0 0 11 2H9zM7 8a1 1 0 0 1 2 0v6a1 1 0 1 1-2 0V8zm5-1a1 1 0 0 0-1 1v6a1 1 0 1 0 2 0V8a1 1 0 0 0-1-1z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
          <div v-if="logStore.error" class="error-msg">{{ logStore.error }}</div>
          <div class="file-list" @click.self="clearSelection('log')">
            <div v-if="logStore.isLoading" class="empty-state">
              <p>Loading logs...</p>
            </div>
            <div v-else-if="logStore.availableLogs.length === 0" class="empty-state">
              <p>No DAQ log files were returned by the logger API.</p>
            </div>
            <div
              v-for="log in logStore.availableLogs"
              :key="log.name"
              class="file-item"
              :class="{ 'is-logging': isActiveLog(log), 'is-selected': isSelected('log', log.name) }"
              @click="handleFileClick('log', log.name, $event)"
            >
              <div v-if="!isRenaming('log', log.name)" class="file-info">
                <span class="status-indicator"></span>
                <div class="file-details">
                  <span
                    class="filename renameable-filename"
                    :title="isActiveLog(log) ? 'Stop logging before renaming this file' : 'Double-click to rename'"
                    @dblclick.stop="startRename('log', log.name)"
                  >{{ log.name }}</span>
                  <span class="file-stats">
                    <template v-if="typeof log.size === 'number'">{{ formatSize(log.size) }}</template>
                    <template v-if="typeof log.size === 'number' && formatLogDate(log)"> &bull; </template>
                    <template v-if="formatLogDate(log)">{{ formatLogDate(log) }}</template>
                    <template v-if="typeof log.size !== 'number' && !formatLogDate(log)">{{ log.url }}</template>
                  </span>
                </div>
              </div>
              <div v-else class="rename-row">
                <input
                  v-model="renameValue"
                  class="rename-input"
                  :aria-label="`New filename stem for ${log.name}`"
                  @keydown.enter.prevent="saveRename"
                  @keydown.escape.prevent="cancelRename"
                />
                <span class="rename-extension" aria-hidden="true">{{ renameExtension }}</span>
                <button class="rename-save-btn" :disabled="!renameIsValid || logStore.mutatingName !== null" @click.stop="saveRename">Save</button>
                <button class="rename-cancel-btn" :disabled="logStore.mutatingName !== null" @click.stop="cancelRename">Cancel</button>
              </div>
              <div v-if="!isRenaming('log', log.name)" class="file-actions">
                <button
                  :id="`download-log-${log.name.replace(/\./g, '-')}-btn`"
                  class="download-btn"
                  :disabled="logStore.downloadingName === log.name || logStore.mutatingName !== null || isBulkDownloading"
                  @click.stop="downloadLog(log.name, log.url)"
                  :title="logStore.downloadingName === log.name ? 'Saving…' : 'Download'"
                  :aria-label="logStore.downloadingName === log.name ? `Saving ${log.name}` : `Download ${log.name}`"
                >
                  <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16" aria-hidden="true">
                    <path fill-rule="evenodd" d="M10 2a1 1 0 0 1 1 1v7.586l2.293-2.293a1 1 0 0 1 1.414 1.414l-4 4a1 1 0 0 1-1.414 0l-4-4a1 1 0 0 1 1.414-1.414L9 10.586V3a1 1 0 0 1 1-1Zm-6 14a1 1 0 0 1 1-1h10a1 1 0 1 1 0 2H5a1 1 0 0 1-1-1Z" clip-rule="evenodd" />
                  </svg>
                </button>
                <button
                  class="delete-btn"
                  :disabled="isLogActionDisabled(log)"
                  @click.stop="deleteTarget = { type: 'log', names: [log.name] }"
                  :title="isActiveLog(log) ? 'Stop logging before deleting this file' : 'Delete'"
                  aria-label="Delete log"
                >
                  <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14" aria-hidden="true">
                    <path fill-rule="evenodd" d="M9 2a1 1 0 0 0-.894.553L7.382 4H4a1 1 0 0 0 0 2v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V6a1 1 0 1 0 0-2h-3.382l-.724-1.447A1 1 0 0 0 11 2H9zM7 8a1 1 0 0 1 2 0v6a1 1 0 1 1-2 0V8zm5-1a1 1 0 0 0-1 1v6a1 1 0 1 0 2 0V8a1 1 0 0 0-1-1z" clip-rule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- DBC Tab -->
        <div v-if="activeTab === 'dbc'" class="tab-pane" @click.self="clearSelection('dbc')">
          <div class="upload-section">
            <label class="upload-btn">
              <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
                <path fill-rule="evenodd" d="M10 3a1 1 0 0 1 1 1v5h5a1 1 0 1 1 0 2h-5v5a1 1 0 1 1-2 0v-5H4a1 1 0 1 1 0-2h5V4a1 1 0 0 1 1-1z" clip-rule="evenodd" />
              </svg>
              Upload DBC
              <input type="file" accept=".dbc" @change="handleDbcUpload" hidden />
            </label>
          </div>
          <div class="selection-toolbar">
            <button type="button" @click="selectAll('dbc')" :disabled="dbcStore.availableDbcs.length === 0">Select all</button>
            <span v-if="selectedDbcCount" class="selection-count">{{ selectedDbcCount }} selected</span>
            <button v-if="selectedDbcCount" type="button" class="bulk-delete-btn selection-icon-btn" title="Delete selected DBCs" aria-label="Delete selected DBCs" @click="requestBulkDelete('dbc')">
              <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14" aria-hidden="true">
                <path fill-rule="evenodd" d="M9 2a1 1 0 0 0-.894.553L7.382 4H4a1 1 0 0 0 0 2v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2 2V6a1 1 0 1 0 0-2h-3.382l-.724-1.447A1 1 0 0 0 11 2H9zM7 8a1 1 0 0 1 2 0v6a1 1 0 1 1-2 0V8zm5-1a1 1 0 0 0-1 1v6a1 1 0 1 0 2 0V8a1 1 0 0 0-1-1z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>

          <div v-if="dbcStore.error" class="error-msg">{{ dbcStore.error }}</div>

          <div class="file-list" @click.self="clearSelection('dbc')">
            <div v-if="dbcStore.availableDbcs.length === 0" class="empty-state">
              <p>No DBC files uploaded yet.</p>
            </div>
            <div
              v-for="filename in dbcStore.availableDbcs"
              :key="filename.name"
              class="file-item"
              :class="{ 'is-active': dbcStore.activeDbc === filename.name, 'is-selected': isSelected('dbc', filename.name) }"
              @click="handleFileClick('dbc', filename.name, $event)"
            >
              <div v-if="!isRenaming('dbc', filename.name)" class="file-info">
                <span class="status-indicator"></span>
                <div class="file-details">
                  <span
                    class="filename renameable-filename"
                    title="Double-click to rename"
                    @dblclick.stop="startRename('dbc', filename.name)"
                  >{{ filename.name }}</span>
                  <span class="file-stats">{{ formatSize(filename.size) }} &bull; {{ formatDate(filename.mtime) }}</span>
                </div>
              </div>
              <div v-else class="rename-row">
                <input
                  v-model="renameValue"
                  class="rename-input"
                  :aria-label="`New filename stem for ${filename.name}`"
                  @keydown.enter.prevent="saveRename"
                  @keydown.escape.prevent="cancelRename"
                />
                <span class="rename-extension" aria-hidden="true">{{ renameExtension }}</span>
                <button class="rename-save-btn" :disabled="!renameIsValid || dbcStore.mutatingName !== null" @click.stop="saveRename">Save</button>
                <button class="rename-cancel-btn" :disabled="dbcStore.mutatingName !== null" @click.stop="cancelRename">Cancel</button>
              </div>
              <div v-if="!isRenaming('dbc', filename.name)" class="file-actions">
                <button class="delete-btn" :disabled="isDbcActionDisabled()" @click.stop="deleteDbc(filename.name)" title="Delete" aria-label="Delete DBC">
                  <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14" aria-hidden="true">
                    <path fill-rule="evenodd" d="M9 2a1 1 0 0 0-.894.553L7.382 4H4a1 1 0 0 0 0 2v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2 2V6a1 1 0 1 0 0-2h-3.382l-.724-1.447A1 1 0 0 0 11 2H9zM7 8a1 1 0 0 1 2 0v6a1 1 0 1 1-2 0V8zm5-1a1 1 0 0 0-1 1v6a1 1 0 1 0 2 0V8a1 1 0 0 0-1-1z" clip-rule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>

  <!-- Backdrop -->
  <Transition name="fade">
    <div v-if="isOpen" class="backdrop" @click="isOpen = false"></div>
  </Transition>
  <ConfirmDialog
    :show="deleteTarget !== null"
    title="Delete file?"
    :message="deleteTarget ? `Delete ${deleteTarget.names.length === 1 ? deleteTarget.names[0] : `${deleteTarget.names.length} selected files`}? This cannot be undone.` : ''"
    confirm-text="Delete"
    danger
    @confirm="confirmDelete"
    @cancel="deleteTarget = null"
    @close="deleteTarget = null"
  />
</template>

<style scoped>
.file-manager-drawer {
  position: fixed;
  top: var(--navbar-height);
  left: 0;
  bottom: 0;
  width: 350px;
  background: var(--color-panel);
  border-right: 1px solid var(--color-border);
  z-index: 60;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5);
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 20px;
  border-bottom: 2px solid var(--color-border);
}

.drawer-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text);
}

.close-btn {
  background: none;
  border: none;
  color: var(--color-muted);
  cursor: pointer;
  font-size: 16px;
  padding: 4px;
  border-radius: 6px;
  transition: all 0.2s;
}
.close-btn:hover {
  color: var(--color-text);
  background: var(--color-hover);
}

.tabs {
  display: flex;
  padding: 0 20px;
  border-bottom: 1px solid var(--color-border);
  background: rgba(0, 0, 0, 0.1);
}

.tab-btn {
  flex: 1;
  padding: 8px 0;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--color-muted);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.tab-btn:hover {
  color: var(--color-text);
}
.tab-btn.active {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}

.drawer-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.upload-section {
  margin-bottom: 20px;
}

.logs-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.logs-source {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.logs-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-muted);
}

.logs-target {
  font-size: 12px;
  color: var(--color-text);
  word-break: break-all;
}

.selection-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  margin: 0 0 14px;
}

.selection-toolbar button {
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: rgb(255 255 255 / 3%);
  color: var(--color-text);
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .01em;
  padding: 6px 10px;
  transition: border-color .15s ease, background .15s ease, color .15s ease, transform .15s ease;
}

.selection-toolbar button:hover:not(:disabled) {
  border-color: var(--color-blue-border);
  background: var(--color-blue-bg-glow);
  color: var(--color-blue-text);
  transform: translateY(-1px);
}

.selection-toolbar button:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.selection-toolbar button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.selection-toolbar .bulk-delete-btn {
  border-color: var(--color-danger-border);
  background: var(--color-danger-bg);
  color: var(--color-danger-text);
}

.selection-toolbar .bulk-delete-btn:hover:not(:disabled) {
  border-color: var(--color-danger);
  background: rgba(239, 68, 68, .2);
  color: var(--color-danger-text);
}

.selection-toolbar .selection-icon-btn {
  display: inline-grid;
  place-items: center;
  min-width: 30px;
  min-height: 30px;
  padding: 6px;
}

.selection-count {
  border: 1px solid var(--color-border);
  border-radius: 999px;
  color: var(--color-muted);
  font-size: 11px;
  padding: 5px 9px;
}

.upload-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 10px;
  background: var(--color-accent);
  color: white;
  border: 1px solid var(--color-blue-border);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 6px 18px rgb(59 130 246 / 16%);
  transition: background .2s, box-shadow .2s, transform .2s;
}
.upload-btn:hover {
  background: #2563eb;
  box-shadow: 0 8px 22px rgb(59 130 246 / 24%);
  transform: translateY(-1px);
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.file-item:hover {
  background: rgba(255, 255, 255, 0.06);
}
.file-item.is-active {
  background: var(--color-blue-bg-glow);
  border-color: var(--color-blue-border);
}
.file-item.is-active .status-indicator {
  background: var(--color-success);
  box-shadow: 0 0 8px var(--color-success);
}
.file-item.is-active .filename {
  color: var(--color-blue-text);
  font-weight: 500;
}
.file-item.is-logging .status-indicator {
  background: var(--color-success);
  box-shadow: 0 0 8px var(--color-success);
}

.file-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  overflow: hidden;
}

.file-item.is-selected {
  background: var(--color-blue-bg-glow);
  border-color: var(--color-blue-border);
  box-shadow: inset 3px 0 0 var(--color-accent);
}


.filename {
  font-size: 13px;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-details {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.file-stats {
  font-size: 10px;
  color: var(--color-muted);
  margin-top: 1px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-muted);
  flex-shrink: 0;
  transition: all 0.3s;
}

.file-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.delete-btn,
.download-btn {
  background: none;
  border: none;
  color: var(--color-muted);
  padding: 4px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  opacity: 0;
}
.file-item:hover .delete-btn,
.file-item:hover .download-btn {
  opacity: 1;
}
.delete-btn:hover {
  color: var(--color-danger-text);
  background: rgba(239, 68, 68, 0.1);
}

.download-btn:hover {
  color: var(--color-blue-text);
  background: var(--color-blue-bg-glow);
}

.download-btn {
  min-width: 32px;
  min-height: 32px;
  padding: 8px;
}

.download-btn:disabled,
.delete-btn:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}

.renameable-filename {
  cursor: text;
}

.rename-row {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.rename-input {
  min-width: 0;
  flex: 1;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-bg);
  color: var(--color-text);
  padding: 4px 6px;
  font-size: 12px;
}

.rename-extension {
  color: var(--color-muted);
  font-size: 12px;
  white-space: nowrap;
}

.rename-save-btn,
.rename-cancel-btn {
  border: 0;
  border-radius: 4px;
  padding: 4px 6px;
  cursor: pointer;
  font-size: 11px;
}

.rename-save-btn {
  background: var(--color-blue-bg-glow);
  color: var(--color-blue-text);
}

.rename-cancel-btn {
  background: var(--color-hover);
  color: var(--color-text);
}

.rename-save-btn:disabled,
.rename-cancel-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.refresh-btn {
  padding: 7px 12px;
  background: var(--color-blue-bg-glow);
  border: 1px solid var(--color-blue-border);
  border-radius: 7px;
  color: var(--color-blue-text);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.22);
}

.refresh-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  color: var(--color-muted);
  font-size: 13px;
  padding: 20px 0;
}

.error-msg {
  color: var(--color-danger-text);
  font-size: 12px;
  margin-bottom: 12px;
  padding: 8px;
  background: var(--color-danger-bg);
  border-radius: 6px;
}

.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 50;
  top: var(--navbar-height);
}

/* Transitions */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s ease;
}
.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(-100%);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
