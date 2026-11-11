<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { useDaqConnectionStore } from '@/stores/daqConnectionStore'
import DataSourcePanel from './DataSourcePanel.vue'
import ExportPanel from './ExportPanel.vue'
import FileManagerPanel from './FileManagerPanel.vue'

const fileManagerRef = ref<InstanceType<typeof FileManagerPanel> | null>(null)
const daqConnection = useDaqConnectionStore()
const filenameTemplate = ref('')
const filenameTemplateInput = ref<HTMLInputElement | null>(null)
const isTemplateSuggestionsOpen = ref(false)

const filenameTemplateOptions = [
  { token: '%T', description: 'timestamp — date and time' },
  { token: '%C', description: 'count — sequential file number' },
  { token: '%Y', description: 'year' },
  { token: '%m', description: 'month' },
  { token: '%d', description: 'day' },
  { token: '%H', description: 'hour' },
  { token: '%M', description: 'minute' },
  { token: '%S', description: 'second' },
]

const isFilenameTemplateDisabled = computed(() => {
  return daqConnection.loggingActive
    || daqConnection.loggingStatus === 'starting'
    || daqConnection.loggingStatus === 'stopping'
})

const loggingButtonLabel = computed(() => {
  return daqConnection.loggingActive ? 'Stop Logging' : 'Start Logging'
})

async function handleLoggingToggle() {
  await daqConnection.toggleLogging(filenameTemplate.value)
}

function handleFilenameTemplateInput() {
  const input = filenameTemplateInput.value
  const caretPosition = input?.selectionStart ?? filenameTemplate.value.length
  isTemplateSuggestionsOpen.value = filenameTemplate.value[caretPosition - 1] === '%'
}

function closeTemplateSuggestions() {
  isTemplateSuggestionsOpen.value = false
}

function selectFilenameTemplateOption(token: string) {
  const input = filenameTemplateInput.value
  const caretPosition = input?.selectionStart ?? filenameTemplate.value.length
  const beforeCaret = filenameTemplate.value.slice(0, caretPosition)
  const percentPosition = beforeCaret.lastIndexOf('%')

  if (percentPosition === -1) {
    return
  }

  filenameTemplate.value = `${filenameTemplate.value.slice(0, percentPosition)}${token}${filenameTemplate.value.slice(caretPosition)}`
  closeTemplateSuggestions()

  void nextTick(() => {
    const nextCaretPosition = percentPosition + token.length
    filenameTemplateInput.value?.focus()
    filenameTemplateInput.value?.setSelectionRange(nextCaretPosition, nextCaretPosition)
  })
}

function handleFilenameTemplateKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    closeTemplateSuggestions()
  }
}
</script>

<template>
  <nav class="bg-[var(--color-panel)] border-b border-[var(--color-border)] h-[var(--navbar-height)]">
    <div class="mx-auto px-4">
      <div class="flex items-center justify-between h-14">

        <div class="flex items-center gap-4 h-full">
          <button @click="fileManagerRef?.togglePanel()" class="p-2 text-[var(--color-muted)] hover:text-[var(--color-text)] transition-colors rounded-md hover:bg-[var(--color-hover)]" aria-label="Toggle File Manager">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <img src="@/assets/images/bajaLogo-dark.png" alt="Pack Motorsports Baja SAE Logo" class="min-w h-full py-1" />
        </div>

        <div class="flex items-center gap-3">
          <div class="filename-template-control">
            <input
              id="daq-log-filename-input"
              ref="filenameTemplateInput"
              v-model="filenameTemplate"
              class="filename-template-input"
              type="text"
              placeholder="Log name (optional)"
              aria-label="Log filename template"
              :disabled="isFilenameTemplateDisabled"
              @input="handleFilenameTemplateInput"
              @keydown="handleFilenameTemplateKeydown"
              @blur="closeTemplateSuggestions"
            />
            <div
              v-if="isTemplateSuggestionsOpen && !isFilenameTemplateDisabled"
              class="filename-template-suggestions"
              role="listbox"
              aria-label="Filename template options"
            >
              <button
                v-for="option in filenameTemplateOptions"
                :key="option.token"
                type="button"
                class="filename-template-option"
                role="option"
                @mousedown.prevent
                @click="selectFilenameTemplateOption(option.token)"
              >
                <strong>{{ option.token }}</strong>
                <span>{{ option.description }}</span>
              </button>
            </div>
          </div>
          <button
            id="daq-logging-toggle-btn"
            class="daq-logging-btn"
            :class="{ active: daqConnection.loggingActive }"
            :disabled="!daqConnection.canToggleLogging"
            @click="handleLoggingToggle"
          >
            {{ loggingButtonLabel }}
          </button>
          <ExportPanel />
          <DataSourcePanel />
        </div>

      </div>
    </div>
    <FileManagerPanel ref="fileManagerRef" />
  </nav>
</template>

<style scoped>
.daq-logging-btn {
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid var(--color-blue-border);
  background: var(--color-blue-bg-glow);
  color: var(--color-blue-text);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.01em;
  transition: all 0.15s;
}

.filename-template-control {
  position: relative;
  display: flex;
  align-items: center;
  width: 270px;
}

.filename-template-input {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid var(--color-border);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--color-text);
  font-size: 12px;
  outline: none;
}

.filename-template-input:focus {
  border-color: var(--color-blue-border);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.filename-template-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.filename-template-suggestions {
  position: absolute;
  top: calc(100% + 5px);
  left: 0;
  z-index: 70;
  display: flex;
  flex-direction: column;
  width: 270px;
  padding: 4px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-panel);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
}

.filename-template-option {
  display: flex;
  align-items: baseline;
  gap: 8px;
  width: 100%;
  padding: 7px 8px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--color-muted);
  font-size: 11px;
  text-align: left;
  cursor: pointer;
}

.filename-template-option:hover,
.filename-template-option:focus-visible {
  background: var(--color-hover);
  color: var(--color-text);
  outline: none;
}

.filename-template-option strong {
  min-width: 24px;
  color: var(--color-blue-text);
}

.daq-logging-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.22);
}

.daq-logging-btn.active {
  border-color: var(--color-danger-border);
  background: var(--color-danger-bg);
  color: var(--color-danger-text);
}

.daq-logging-btn.active:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.18);
}

.daq-logging-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
