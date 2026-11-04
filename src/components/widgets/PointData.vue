<script setup lang="ts">
import type { Point } from '../DashboardGrid.vue'

defineProps<{
  pointDatas: Point[]
}>()
</script>

<template>
  <div
    v-for="item in pointDatas"
    :key="item.id"
    class="data-pt"
    :style="`--left: ${item.coords.x}px; --top: ${item.coords.y}px`"
  >
    <dl class="data-pt-info">
      <dd class="data-pt-detail">
        <b>({{ item.values.x.toFixed(3) }} {{ item.units.x }}, {{ item.values.y.toFixed(3) }} {{ item.units.y }})</b>
      </dd>
    </dl>
  </div>
</template>

<style scoped>
.data-pt {
  position: absolute;
  z-index: 20;
  border: 1px solid var(--color-border);
  background: var(--color-panel);
  border-radius: 6px;
  box-shadow: 0 8px 20px rgb(0 0 0 / 30%);
  padding: 6px 6px;
  min-width: 50px;
  max-width: min(300px, 75vw);
  left: var(--left);
  top: var(--top);
}

.data-pt-info {
  line-height: 1.5;
  margin: 0;
  display: flex;
  align-items: center;
  font-size: 12px;
}

.data-pt-detail {
  line-height: 1.5;
  color: var(--color-text-muted);
}
</style>
