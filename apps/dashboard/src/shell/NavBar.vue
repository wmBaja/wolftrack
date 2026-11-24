<script setup lang="ts">
import { computed, h, type Component } from 'vue'
import ContextMenu from '@imengyu/vue3-context-menu'
import { commands, panels } from '@/shell/registries'
import { useWorkspaceStore } from '@/core/stores/workspaceStore'
import { commandsForTab } from '@/shell/contextCommands'
import PluginErrorBoundary from '@/shell/PluginErrorBoundary.vue'

const workspaceStore = useWorkspaceStore()
const sortPanels = (a: (typeof panels.entries.value)[number], b: (typeof panels.entries.value)[number]) => (a.order ?? 0) - (b.order ?? 0)
const leftToolbarPanels = computed(() => panels.entries.value
  .filter((panel) => panel.location === 'toolbar' && panel.alignment === 'left')
  .sort(sortPanels))
const rightToolbarPanels = computed(() => panels.entries.value
  .filter((panel) => panel.location === 'toolbar' && panel.alignment !== 'left')
  .sort(sortPanels))
const contextualCommands = computed(() => commandsForTab(commands.entries.value, workspaceStore.activeTab))
const isDashboardActive = computed(() => workspaceStore.activeTab?.kind === 'dashboard')

function runCommand(tabId: string, command: (typeof contextualCommands.value)[number]) {
  void command.run({ tabId })
}

function runActiveCommand(command: (typeof contextualCommands.value)[number]) {
  const tab = workspaceStore.activeTab
  if (tab) runCommand(tab.id, command)
}

function showAddWidgetMenu(event: MouseEvent) {
  const tab = workspaceStore.activeTab
  if (!tab || tab.kind !== 'dashboard' || contextualCommands.value.length === 0) return

  ContextMenu.showContextMenu({
    x: event.x,
    y: event.y,
    theme: 'mac dark',
    zIndex: 1000,
    items: contextualCommands.value.map((command) => ({
      label: command.title,
      icon: h('span', command.icon ?? ''),
      onClick: () => runCommand(tab.id, command),
    })),
  })
}

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
        <div class="navbar-control-groups">
          <div
            v-if="isDashboardActive || contextualCommands.length"
            class="navbar-action-group navbar-context-group"
            role="group"
            :aria-label="isDashboardActive ? 'Dashboard actions' : 'View actions'"
          >
            <button
              v-if="isDashboardActive"
              type="button"
              aria-label="Add widget"
              title="Add widget"
              class="contextual-navbar-action"
              :disabled="contextualCommands.length === 0"
              @click="showAddWidgetMenu"
            >
              <span aria-hidden="true">+</span>
              Add widget
            </button>
            <button
              v-for="command in isDashboardActive ? [] : contextualCommands"
              :key="command.id"
              type="button"
              :aria-label="command.title"
              :title="command.title"
              class="contextual-navbar-action"
              @click="runActiveCommand(command)"
            >
              <span v-if="command.icon" aria-hidden="true">{{ command.icon }}</span>
              {{ command.title }}
            </button>
          </div>
          <div
            v-if="rightToolbarPanels.length"
            class="navbar-action-group navbar-global-group"
            role="group"
            aria-label="Global controls"
          >
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
    </div>
  </nav>
</template>

<style scoped>
.navbar-control-groups {
  display: flex;
  align-items: center;
  gap: 12px;
}

.navbar-action-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.navbar-context-group {
  padding-right: 12px;
  border-right: 1px solid var(--color-border);
}

.contextual-navbar-action {
  display: inline-flex;
  min-width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 9px;
  border: 1px solid var(--color-border);
  border-radius: 7px;
  background: var(--color-bg);
  color: var(--color-text);
  cursor: pointer;
}

.contextual-navbar-action:hover:not(:disabled) { background: var(--color-hover); }
.contextual-navbar-action:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
