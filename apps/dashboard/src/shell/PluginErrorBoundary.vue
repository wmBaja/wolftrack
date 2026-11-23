<script setup lang="ts">
import { onErrorCaptured, ref } from 'vue'

defineProps<{ ownerId: string }>()
const emit = defineEmits<{ disable: [] }>()
const errorMessage = ref<string>()
const renderAttempt = ref(0)

onErrorCaptured((error) => {
  errorMessage.value = error instanceof Error ? error.message : String(error)
  return false
})

function retry() {
  errorMessage.value = undefined
  renderAttempt.value += 1
}
</script>

<template>
  <div class="error-boundary">
    <section v-if="errorMessage" class="error-card" role="alert">
      <strong>{{ ownerId }} could not be displayed</strong>
      <p>{{ errorMessage }}</p>
      <div class="error-actions">
        <button type="button" @click="retry">Retry</button>
        <button type="button" @click="emit('disable')">Disable</button>
      </div>
    </section>
    <div v-else :key="renderAttempt" class="error-content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.error-boundary {
  display: contents;
  pointer-events: auto;
}

.error-content {
  height: 100%;
  min-width: 0;
  min-height: 0;
  pointer-events: auto;
}

.error-card {
  display: flex;
  height: 100%;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  overflow: auto;
  color: var(--color-text);
  background: var(--color-panel);
}

.error-card p { color: var(--color-text-muted); overflow-wrap: anywhere; }
.error-actions { display: flex; gap: 8px; }
.error-actions button {
  padding: 5px 10px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background: var(--color-bg);
  color: var(--color-text);
  cursor: pointer;
}
</style>
