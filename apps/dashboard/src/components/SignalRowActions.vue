<script setup lang="ts">
// Row actions for virtual signals in SignalTree (Part 6.4). A tiny child
// so the tree file does not grow; replaceable together with the editor.
defineEmits<{
  (e: 'edit'): void
  (e: 'delete'): void
}>()
</script>

<template>
  <span class="row-actions" @click.stop>
    <button type="button" class="row-action-btn" title="Edit virtual signal"
            aria-label="Edit virtual signal" @click="$emit('edit')">✎</button>
    <button type="button" class="row-action-btn danger" title="Delete virtual signal"
            aria-label="Delete virtual signal" @click="$emit('delete')">🗑</button>
  </span>
</template>

<style scoped>
.row-actions {
  display: inline-flex;
  gap: 2px;
  margin-left: 4px;
}

.row-action-btn {
  border: none;
  background: none;
  color: var(--color-text-muted, #9ca3af);
  cursor: pointer;
  font-size: 11px;
  padding: 1px 3px;
  border-radius: 3px;
}

.row-action-btn:hover {
  background: var(--color-panel, rgba(255, 255, 255, 0.08));
  color: var(--color-text, #e5e7eb);
}

.row-action-btn.danger:hover {
  color: var(--color-danger-text, #f87171);
}
</style>
