<script setup lang="ts">
import { computed, type Component } from 'vue'
import { panels } from '@/shell/registries'
import PluginErrorBoundary from '@/shell/PluginErrorBoundary.vue'

const sortPanels = (a: (typeof panels.entries.value)[number], b: (typeof panels.entries.value)[number]) => (a.order ?? 0) - (b.order ?? 0)
const leftToolbarPanels = computed(() => panels.entries.value
  .filter((panel) => panel.location === 'toolbar' && panel.alignment === 'left')
  .sort(sortPanels))
const rightToolbarPanels = computed(() => panels.entries.value
  .filter((panel) => panel.location === 'toolbar' && panel.alignment !== 'left')
  .sort(sortPanels))

function disablePanel(id: string) {
  panels.entries.value = panels.entries.value.filter((panel) => panel.id !== id)
}
</script>

<template>
  <nav class="bg-[var(--color-panel)] border-b border-[var(--color-border)] h-[var(--navbar-height)]">
    <div class="mx-auto px-4">
      <div class="flex items-center justify-between h-14">
        <div class="flex items-center gap-4 h-full">
          <PluginErrorBoundary
            v-for="panel in leftToolbarPanels"
            :key="panel.id"
            :owner-id="panel.id"
            @disable="disablePanel(panel.id)"
          >
            <component :is="panel.component as Component" />
          </PluginErrorBoundary>
          <img src="@/assets/images/bajaLogo-dark.png" alt="Pack Motorsports Baja SAE Logo" class="min-w h-full py-1" />
        </div>
        <div class="flex items-center gap-3">
          <PluginErrorBoundary
            v-for="panel in rightToolbarPanels"
            :key="panel.id"
            :owner-id="panel.id"
            @disable="disablePanel(panel.id)"
          >
            <component :is="panel.component as Component" />
          </PluginErrorBoundary>
        </div>
      </div>
    </div>
  </nav>
</template>
