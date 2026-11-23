<script setup lang="ts">
import { computed, type Component } from 'vue'
import { RouterView } from 'vue-router'
import NavBar from './shell/NavBar.vue'
import DialogBox from '@/shell/DialogBox.vue'
import { panels } from '@/shell/registries'
import PluginErrorBoundary from '@/shell/PluginErrorBoundary.vue'

const overlayPanels = computed(() => panels.entries.value.filter((panel) => panel.location === 'overlay'))

function disablePanel(id: string) {
  panels.entries.value = panels.entries.value.filter((panel) => panel.id !== id)
}
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <NavBar />
    <main class="flex-1">
      <RouterView />
      <DialogBox />
    </main>
    <PluginErrorBoundary
      v-for="panel in overlayPanels"
      :key="panel.id"
      :owner-id="panel.id"
      @disable="disablePanel(panel.id)"
    >
      <component :is="panel.component as Component" />
    </PluginErrorBoundary>
  </div>
</template>
