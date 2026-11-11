<script setup lang="ts">
import { computed, ref } from 'vue'
import { getVisualizerBase } from '@/lib/visualizer'

type ExportStatus = 'idle' | 'loading' | 'success'
type ExportFormat = 'csv' | 'xlsx'

interface ExportTimezoneOption {
  value: string
  label: string
}

const exportTimezoneOptions: ExportTimezoneOption[] = [
  { value: 'America/New_York', label: 'Eastern' },
  { value: 'America/Chicago', label: 'Central' },
  { value: 'America/Denver', label: 'Mountain' },
  { value: 'America/Los_Angeles', label: 'Pacific' },
  { value: 'America/Anchorage', label: 'Alaska' },
  { value: 'Pacific/Honolulu', label: 'Hawaii-Aleutian' },
  { value: 'America/Phoenix', label: 'Arizona' },
]

const isOpen = ref(false)
const selectedFile = ref<File | null>(null)
const selectedFilename = ref('')
const status = ref<ExportStatus>('idle')
const errorMessage = ref<string | null>(null)
const selectedTimezone = ref<string>('America/New_York')
const selectedFormat = ref<ExportFormat>('csv')

function resetStatus() {
  status.value = 'idle'
  errorMessage.value = null
}

function openPanel() {
  isOpen.value = true
}

function handleFileChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0] ?? null
  selectedFile.value = file
  selectedFilename.value = file?.name ?? ''
  resetStatus()
}

function getStatusLabel() {
  if (errorMessage.value) {
    return errorMessage.value
  }

  return status.value
}

function parseDownloadFilename(header: string | null): string {
  if (!header) {
    return selectedFormat.value === 'csv' ? 'wolftrack-export.csv' : 'wolftrack-export.xlsx'
  }

  const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1])
  }

  const quotedMatch = header.match(/filename="([^"]+)"/i)
  if (quotedMatch?.[1]) {
    return quotedMatch[1]
  }

  const plainMatch = header.match(/filename=([^;]+)/i)
  if (plainMatch?.[1]) {
    return plainMatch[1].trim()
  }

  return selectedFormat.value === 'csv' ? 'wolftrack-export.csv' : 'wolftrack-export.xlsx'
}

function buildExportUrl(baseUrl: string) {
  const endpoint = selectedFormat.value === 'csv' ? 'export_csv' : 'export_xlsx'
  const exportUrl = new URL(`${baseUrl}/api/${endpoint}`)
  exportUrl.searchParams.set('timezone_name', selectedTimezone.value)
  return exportUrl.toString()
}

function getDownloadMimeType() {
  return selectedFormat.value === 'csv'
    ? 'text/csv;charset=utf-8'
    : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

async function exportFile() {
  if (!selectedFile.value) {
    return
  }

  status.value = 'loading'
  errorMessage.value = null

  try {
    const baseUrl = await getVisualizerBase()
    const uploadData = new FormData()
    uploadData.append('source', 'logfile')
    uploadData.append('log_file_upload', selectedFile.value)
    uploadData.append('playback_speed', '0.0')

    const uploadResponse = await fetch(`${baseUrl}/api/upload_config`, {
      method: 'POST',
      body: uploadData,
    })
    if (!uploadResponse.ok) {
      const payload = await uploadResponse.json()
      throw new Error(payload.detail ?? 'Export upload failed.')
    }

    const exportResponse = await fetch(buildExportUrl(baseUrl))
    if (!exportResponse.ok) {
      const payload = await exportResponse.json()
      throw new Error(payload.detail ?? 'CSV export failed.')
    }

    const blob = await exportResponse.blob()
    const downloadName = parseDownloadFilename(exportResponse.headers.get('Content-Disposition'))
    const downloadBlob = new Blob([blob], { type: getDownloadMimeType() })
    const downloadUrl = URL.createObjectURL(downloadBlob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = downloadName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(downloadUrl)

    status.value = 'success'
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  }
}

const canExport = computed(() => selectedFile.value !== null && status.value !== 'loading')
</script>

<template>
  <button id="export-panel-btn" class="export-trigger" @click="openPanel">
    Export
  </button>

  <Transition name="fade">
    <div v-if="isOpen" class="backdrop" @click="isOpen = false" />
  </Transition>

  <Transition name="slide-down">
    <div v-if="isOpen" class="export-panel" role="dialog" aria-label="BLF CSV Export">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">BLF Export</h2>
          <p class="panel-subtitle">Upload a `.blf` log and download a decoded CSV.</p>
        </div>
        <button class="close-btn" @click="isOpen = false" aria-label="Close">x</button>
      </div>

      <div class="field-group">
        <label class="field-label" for="export-logfile-input">BLF File</label>
        <div class="file-picker-row">
          <span class="file-name">{{ selectedFilename || 'No file selected' }}</span>
          <div class="browse-btn-wrapper">
            <button id="export-logfile-browse-btn" class="browse-btn" type="button">Browse...</button>
            <input
              id="export-logfile-input"
              class="browse-input-overlay"
              type="file"
              accept=".blf"
              @change="handleFileChange"
            />
          </div>
        </div>
      </div>

      <div class="field-group">
        <label class="field-label" for="export-timezone-select">Timestamp Time Zone</label>
        <select id="export-timezone-select" v-model="selectedTimezone" class="select-input">
          <option
            v-for="timezone in exportTimezoneOptions"
            :key="timezone.value"
            :value="timezone.value"
          >
            {{ timezone.label }}
          </option>
        </select>
      </div>

      <div class="field-group">
        <label class="field-label">Format</label>
        <div class="format-toggle" role="radiogroup" aria-label="Export format">
          <label class="format-option" :class="{ active: selectedFormat === 'csv' }">
            <input id="export-format-csv" v-model="selectedFormat" type="radio" value="csv" name="export-format" />
            CSV
          </label>
          <label class="format-option" :class="{ active: selectedFormat === 'xlsx' }">
            <input id="export-format-xlsx" v-model="selectedFormat" type="radio" value="xlsx" name="export-format" />
            Excel
          </label>
        </div>
      </div>

      <div class="field-group">
        <label class="field-label">Status</label>
        <p id="export-status-line" class="status-line" :class="{ error: errorMessage }">{{ getStatusLabel() }}</p>
      </div>

      <div class="panel-footer">
        <button class="action-btn secondary" @click="isOpen = false">Close</button>
        <button
          id="export-csv-btn"
          class="action-btn primary"
          :disabled="!canExport"
          @click="exportFile"
        >
          {{ status === 'loading' ? 'Exporting...' : 'Export' }}
        </button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.export-trigger {
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.06);
  color: var(--color-text);
  font-size: 12px;
  font-weight: 700;
  transition: all 0.15s;
}

.export-trigger:hover {
  background: var(--color-hover);
}

.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 40;
}

.export-panel {
  position: fixed;
  top: calc(var(--navbar-height) + 8px);
  right: 16px;
  width: min(400px, calc(100vw - 24px));
  background: var(--color-panel);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  box-shadow: 0 24px 56px rgba(0, 0, 0, 0.6);
  z-index: 50;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text);
}

.panel-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-muted);
}

.close-btn {
  background: none;
  border: none;
  color: var(--color-muted);
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 6px;
}

.close-btn:hover {
  color: var(--color-text);
  background: var(--color-hover);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.file-picker-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-name {
  flex: 1;
  min-width: 0;
  padding: 8px 11px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 12px;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.select-input {
  width: 100%;
  min-width: 0;
  padding: 8px 11px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 12px;
  color: var(--color-text);
}

.format-toggle {
  display: flex;
  gap: 8px;
}

.format-option {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-muted);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.format-option.active {
  background: var(--color-blue-bg-glow);
  border-color: var(--color-blue-border);
  color: var(--color-blue-text);
}

.format-option input {
  margin: 0;
}

.browse-btn-wrapper {
  position: relative;
  overflow: hidden;
  display: flex;
}

.browse-btn {
  padding: 7px 12px;
  background: var(--color-blue-bg-glow);
  border: 1px solid var(--color-blue-border);
  border-radius: 7px;
  color: var(--color-blue-text);
  font-size: 12px;
  font-weight: 600;
}

.browse-input-overlay {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.status-line {
  margin: 0;
  font-size: 12px;
  color: var(--color-muted);
}

.status-line.error {
  color: var(--color-danger-text);
}

.panel-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 6px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.action-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.action-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.action-btn.primary {
  background: var(--color-accent);
  color: #fff;
}

.action-btn.secondary {
  background: rgba(255, 255, 255, 0.06);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-down-enter-active {
  animation: slideDown 0.2s ease;
}

.slide-down-leave-active {
  animation: slideDown 0.15s ease reverse;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-6px) scale(0.98);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-width: 640px) {
  .export-panel {
    right: 12px;
    left: 12px;
    width: auto;
  }

  .file-picker-row {
    flex-wrap: wrap;
  }
}
</style>
