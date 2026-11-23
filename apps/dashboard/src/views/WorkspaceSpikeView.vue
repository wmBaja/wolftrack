<script setup lang="ts">
import { computed, defineComponent, h } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { DockviewVue, GridviewVue, Orientation, themeDark } from 'dockview-vue'
import type { DockviewReadyEvent, GridviewReadyEvent, VueComponent } from 'dockview-vue'
import 'dockview-vue/dist/styles/dockview.css'
import DashboardGrid from '@/shell/DashboardGrid.vue'

const route = useRoute()
const activeCandidate = computed(() => route.query.candidate ?? 'dockview')
const popoutUrl = window.location.href

const tileComponents: Record<string, VueComponent> = {
  tile: defineComponent({
    props: ['params'],
    setup(props) {
      return () => h('div', { class: 'tile-sample' }, String(props.params.title))
    },
  }),
}

function setupDashboards({ api }: DockviewReadyEvent) {
  api.addPanel({ id: 'dashboard-a', component: 'dashboard', title: 'Dashboard A' })
  api.addPanel({ id: 'dashboard-b', component: 'dashboard', title: 'Dashboard B' })
}

function setupTiles({ api }: GridviewReadyEvent) {
  const first = api.addPanel({ id: 'tile-a', component: 'tile', params: { title: 'Tile A' } })
  api.addPanel({
    id: 'tile-b', component: 'tile', params: { title: 'Tile B' },
    position: { direction: 'right', referencePanel: first.id },
  })
  api.addPanel({
    id: 'tile-c', component: 'tile', params: { title: 'Tile C' },
    position: { direction: 'below', referencePanel: first.id },
  })
}
</script>

<template>
  <section class="spike-page">
    <header>
      <h1>Workspace spike</h1>
      <nav>
        <RouterLink to="/workspace-spike?candidate=dockview">Dockview tabs</RouterLink>
        <RouterLink to="/workspace-spike?candidate=gridview">Gridview tiles</RouterLink>
      </nav>
      <p>
        Dockview panels mount the existing dashboard and its saved charts. Add a chart first if the
        saved dashboard is empty. Compare tab switching, edge splits, pop-out, and chart behavior.
      </p>
    </header>

    <DockviewVue
      v-if="activeCandidate === 'dockview'"
      class="spike-layout"
      :theme="themeDark"
      :popout-url="popoutUrl"
      @ready="setupDashboards"
    >
      <template #panel-dashboard>
        <DashboardGrid />
      </template>
    </DockviewVue>

    <GridviewVue
      v-else
      class="spike-layout"
      :orientation="Orientation.VERTICAL"
      :components="tileComponents"
      @ready="setupTiles"
    />
  </section>
</template>

<style scoped>
.spike-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--navbar-height));
  min-height: 480px;
  padding: 12px;
  gap: 12px;
}

header h1 { font-size: 1.25rem; font-weight: 600; }
header nav { display: flex; gap: 12px; }
header p { color: var(--color-text-muted); }
.spike-layout { flex: 1; min-height: 0; }
.tile-sample { display: grid; width: 100%; height: 100%; place-items: center; color: var(--color-text); }
</style>
