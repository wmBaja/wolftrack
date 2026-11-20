<script setup lang="ts">
import { RouterView } from 'vue-router'
import NavBar from './components/NavBar.vue'
import DaqReconnectDialog from './components/DaqReconnectDialog.vue'
import DialogBox from '@/components/DialogBox.vue'
import { useLiveDataStore } from './stores/liveDataStore.ts'
import { useDataSourceStore } from './stores/dataSourceStore.ts'
import { useDaqConnectionStore } from './stores/daqConnectionStore.ts'
import { useDbcStore } from './stores/dbcStore.ts'
import { useWtsStore } from './stores/wtsStore.ts'
import { onMounted, onUnmounted } from 'vue'

const liveDataStore = useLiveDataStore()
const dataSourceStore = useDataSourceStore()
const daqConnectionStore = useDaqConnectionStore()
const dbcStore = useDbcStore()
const wtsStore = useWtsStore()

onMounted(async () => {
  void liveDataStore.connect()
  await dataSourceStore.fetchConfig()
  // WTS: the op catalog belongs to this backend connection (never cached
  // across restarts); definitions follow the active setup.
  void wtsStore.fetchCatalog()
  void wtsStore.fetchDefinitions()
  void dbcStore.fetchDbcs()
  await daqConnectionStore.fetchVisualizerLiveSource()
  if (daqConnectionStore.isConnected || daqConnectionStore.isReady) {
    daqConnectionStore.startConnectionPolling()
  }
})

onUnmounted(() => {
  liveDataStore.disconnect()
  daqConnectionStore.stopConnectionPolling()
  daqConnectionStore.cancelReconnect()
})
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <NavBar />

    <main class="flex-1">
      <RouterView />
      <DialogBox />
    </main>

    <DaqReconnectDialog
      v-if="daqConnectionStore.reconnectRecoveryActive"
      :target="daqConnectionStore.target"
      :error="daqConnectionStore.error"
      :next-attempt-at="daqConnectionStore.reconnectNextAttemptAt"
      :reconnecting="daqConnectionStore.reconnectInProgress"
      @force-reconnect="daqConnectionStore.forceReconnect"
      @cancel="daqConnectionStore.cancelReconnect"
    />
  </div>
</template>
