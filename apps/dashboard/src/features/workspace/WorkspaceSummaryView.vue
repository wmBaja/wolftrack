<script setup lang="ts">
defineProps<{ state: Record<string, unknown> }>()
const emit = defineEmits<{ 'update:state': [state: Record<string, unknown>] }>()
</script>

<template>
  <section class="workspace-summary">
    <h1>Workspace guide</h1>
    <p>Use dashboards to arrange charts. This view is an example of a registered workspace view.</p>
    <button type="button" @click="emit('update:state', { visited: true })">
      Save view state
    </button>
    <span v-if="state.visited === true" role="status">View state saved with this tab.</span>
  </section>
</template>

<style scoped>
.workspace-summary {
  display: flex;
  height: 100%;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 12px;
  padding: 32px;
}

h1 { font-size: 1.5rem; }
p { max-width: 540px; color: var(--color-text-muted); }
button {
  padding: 7px 12px;
  border-radius: 5px;
  background: var(--color-accent);
  color: white;
}
</style>
