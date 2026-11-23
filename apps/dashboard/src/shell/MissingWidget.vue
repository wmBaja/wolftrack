<script setup lang="ts">
import { computed } from 'vue'
import { useWidgetStore } from '@/core/stores/widgetStore'

const props = defineProps<{ widgetId: string }>()
const store = useWidgetStore()
const widget = computed(() => store.getWidgetById(props.widgetId))
</script>

<template>
  <div class="missing-widget">
    <strong>Widget unavailable</strong>
    <span>The “{{ widget?.type }}” widget is not registered.</span>
  </div>
</template>

<style scoped>
.missing-widget {
  display: flex;
  height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: var(--color-muted);
  text-align: center;
}
</style>
