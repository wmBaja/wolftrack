<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { useDaqConnectionStore } from '@/core/stores/daqConnectionStore'
import DataSourcePanel from './components/DataSourcePanel.vue'

const daqConnection = useDaqConnectionStore()
const filenameTemplate = ref('')
const filenameTemplateInput = ref<HTMLInputElement | null>(null)
const isTemplateSuggestionsOpen = ref(false)
const filenameTemplateOptions = [
  { token: '%T', description: 'timestamp — date and time' },
  { token: '%C', description: 'count — sequential file number' },
  { token: '%Y', description: 'year' }, { token: '%m', description: 'month' },
  { token: '%d', description: 'day' }, { token: '%H', description: 'hour' },
  { token: '%M', description: 'minute' }, { token: '%S', description: 'second' },
]
const disabled = computed(() => daqConnection.loggingActive
  || daqConnection.loggingStatus === 'starting' || daqConnection.loggingStatus === 'stopping')

function selectOption(token: string) {
  const input = filenameTemplateInput.value
  const caret = input?.selectionStart ?? filenameTemplate.value.length
  const percent = filenameTemplate.value.slice(0, caret).lastIndexOf('%')
  if (percent < 0) return
  filenameTemplate.value = `${filenameTemplate.value.slice(0, percent)}${token}${filenameTemplate.value.slice(caret)}`
  isTemplateSuggestionsOpen.value = false
  void nextTick(() => {
    const nextCaret = percent + token.length
    filenameTemplateInput.value?.focus()
    filenameTemplateInput.value?.setSelectionRange(nextCaret, nextCaret)
  })
}
</script>

<template>
  <div class="data-source-toolbar">
    <div class="filename-template-control">
      <input
        id="daq-log-filename-input" ref="filenameTemplateInput" v-model="filenameTemplate"
        class="filename-template-input" type="text" placeholder="Log name (optional)"
        aria-label="Log filename template" :disabled="disabled"
        @input="isTemplateSuggestionsOpen = filenameTemplate[(filenameTemplateInput?.selectionStart ?? 0) - 1] === '%'"
        @keydown.esc="isTemplateSuggestionsOpen = false"
        @blur="isTemplateSuggestionsOpen = false"
      />
      <div v-if="isTemplateSuggestionsOpen && !disabled" class="filename-template-suggestions" role="listbox" aria-label="Filename template options">
        <button v-for="option in filenameTemplateOptions" :key="option.token" type="button" class="filename-template-option" role="option" @mousedown.prevent @click="selectOption(option.token)">
          <strong>{{ option.token }}</strong><span>{{ option.description }}</span>
        </button>
      </div>
    </div>
    <button id="daq-logging-toggle-btn" class="daq-logging-btn" :class="{ active: daqConnection.loggingActive }" :disabled="!daqConnection.canToggleLogging" @click="daqConnection.toggleLogging(filenameTemplate)">
      {{ daqConnection.loggingActive ? 'Stop Logging' : 'Start Logging' }}
    </button>
    <DataSourcePanel />
  </div>
</template>

<style scoped>
.data-source-toolbar { display: flex; align-items: center; gap: 0.75rem }
.daq-logging-btn { padding: 8px 14px; border: 1px solid var(--color-blue-border); border-radius: 8px; background: var(--color-blue-bg-glow); color: var(--color-blue-text); font-size: 12px; font-weight: 700 }
.daq-logging-btn.active { border-color: var(--color-danger-border); background: var(--color-danger-bg); color: var(--color-danger-text) }
.daq-logging-btn:disabled { opacity: .45; cursor: not-allowed }
.filename-template-control { position: relative; width: 270px }
.filename-template-input { width: 100%; padding: 7px 10px; border: 1px solid var(--color-border); border-radius: 7px; background: rgb(255 255 255 / 4%); color: var(--color-text); font-size: 12px }
.filename-template-suggestions { position: absolute; top: calc(100% + 5px); z-index: 70; display: flex; width: 270px; flex-direction: column; padding: 4px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-panel) }
.filename-template-option { display: flex; gap: 8px; padding: 7px 8px; border: 0; background: transparent; color: var(--color-muted); text-align: left }
</style>
