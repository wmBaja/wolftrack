<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import DaqReconnectDialog from './components/DaqReconnectDialog.vue'
import { useLiveDataStore } from '@/core/stores/liveDataStore'
import { useDataSourceStore } from '@/core/stores/dataSourceStore'
import { useDaqConnectionStore } from '@/core/stores/daqConnectionStore'

const liveDataStore = useLiveDataStore()
const dataSourceStore = useDataSourceStore()
const daqConnectionStore = useDaqConnectionStore()

onMounted(async () => {
  void liveDataStore.connect()
  await dataSourceStore.fetchConfig()
  await daqConnectionStore.fetchVisualizerLiveSource()
  if (daqConnectionStore.isConnected || daqConnectionStore.isReady) daqConnectionStore.startConnectionPolling()
})

onUnmounted(() => {
  liveDataStore.disconnect()
  daqConnectionStore.stopConnectionPolling()
  daqConnectionStore.cancelReconnect()
})
</script>

<template>
  <DaqReconnectDialog
    v-if="daqConnectionStore.reconnectRecoveryActive"
    :target="daqConnectionStore.target"
    :error="daqConnectionStore.error"
    :next-attempt-at="daqConnectionStore.reconnectNextAttemptAt"
    :reconnecting="daqConnectionStore.reconnectInProgress"
    @force-reconnect="daqConnectionStore.forceReconnect"
    @cancel="daqConnectionStore.cancelReconnect"
  />
</template>
