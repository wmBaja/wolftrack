<script setup lang="ts">
import { computed, type Component } from 'vue'
import { RouterView } from 'vue-router'
import NavBar from './shell/NavBar.vue'
import DialogBox from '@/shell/DialogBox.vue'
import { panels } from '@/shell/registries'

const overlayPanels = computed(() => panels.entries.value.filter((panel) => panel.location === 'overlay'))
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <NavBar />
    <main class="flex-1">
      <RouterView />
      <DialogBox />
    </main>
    <component v-for="panel in overlayPanels" :key="panel.id" :is="panel.component as Component" />
  </div>
</template>
