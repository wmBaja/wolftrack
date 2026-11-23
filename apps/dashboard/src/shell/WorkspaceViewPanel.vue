<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'
import { views } from '@/shell/registries'
import PluginErrorBoundary from '@/shell/PluginErrorBoundary.vue'

const props = defineProps<{ tabId: string }>()
const workspaceStore = useWorkspaceStore()
const tab = computed(() => workspaceStore.tabs.find((item) => item.id === props.tabId))
const contribution = computed(() => tab.value?.kind === 'view' ? views.get(tab.value.viewType) : undefined)

function updateState(state: Record<string, unknown>) {
  workspaceStore.updateViewState(props.tabId, state)
}
</script>

<template>
  <PluginErrorBoundary
    v-if="tab?.kind === 'view' && contribution"
    :owner-id="tab.pluginId"
    @disable="workspaceStore.removeTab(tab.id)"
  >
    <component
      :is="contribution.component as Component"
      :state="tab.state"
      @update:state="updateState"
    />
  </PluginErrorBoundary>
  <section v-else class="missing-view">
    <h2>View unavailable</h2>
    <p>The view “{{ tab?.kind === 'view' ? tab.viewType : '' }}” is not registered.</p>
    <button type="button" @click="workspaceStore.removeTab(props.tabId)">Close tab</button>
  </section>
</template>

<style scoped>
.missing-view {
  display: flex;
  height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--color-text-muted);
}
.missing-view h2 { color: var(--color-text); }
.missing-view button { padding: 5px 10px; border: 1px solid var(--color-border); border-radius: 5px; }
</style>
