<script setup lang="ts">
import { ref } from 'vue'
import FileManagerPanel from './components/FileManagerPanel.vue'

const panel = ref<InstanceType<typeof FileManagerPanel> | null>(null)
function togglePanel() { panel.value?.togglePanel() }
defineExpose({ togglePanel })
</script>

<template>
  <button type="button" class="file-manager-toggle" aria-label="Toggle File Manager" @click="togglePanel">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" /></svg>
  </button>
  <FileManagerPanel ref="panel" />
</template>

<style scoped>
.file-manager-toggle { padding: 0.5rem; border-radius: 0.375rem; color: var(--color-muted) }
.file-manager-toggle:hover { background: var(--color-hover); color: var(--color-text) }
</style>
