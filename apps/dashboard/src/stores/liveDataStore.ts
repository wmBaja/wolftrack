import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useDataSourceStore } from './dataSourceStore'
import { useDaqConnectionStore } from './daqConnectionStore'
import { getVisualizerWsUrl } from '@/lib/visualizer'

export class RingBuffer {
  timestamps: Float64Array
  values: Float64Array
  head: number
  length: number
  capacity: number
  tail: number

  constructor(capacity: number) {
    this.capacity = capacity
    this.timestamps = new Float64Array(capacity)
    this.values = new Float64Array(capacity)
    this.head = 0
    this.tail = 0
    this.length = 0
  }

  push(timestamp: number, value: number) {
    this.timestamps[this.head] = timestamp
    this.values[this.head] = value
    this.head = (this.head + 1) % this.capacity
    if (this.length < this.capacity) {
      this.length++
    } else {
      this.tail = (this.tail + 1) % this.capacity
    }
  }

  trim(cutoffTimestamp: number) {
    while (this.length > 0 && this.timestamps[this.tail] !== undefined && this.timestamps[this.tail]! < cutoffTimestamp) {
      this.tail = (this.tail + 1) % this.capacity
      this.length--
    }
  }

  getArrays() {
    const ts = new Float64Array(this.length)
    const vs = new Float64Array(this.length)
    if (this.length === 0) return { timestamps: ts, values: vs }

    if (this.head > this.tail) {
      ts.set(this.timestamps.subarray(this.tail, this.head))
      vs.set(this.values.subarray(this.tail, this.head))
    } else {
      const firstPartLen = this.capacity - this.tail
      ts.set(this.timestamps.subarray(this.tail, this.capacity), 0)
      vs.set(this.values.subarray(this.tail, this.capacity), 0)
      ts.set(this.timestamps.subarray(0, this.head), firstPartLen)
      vs.set(this.values.subarray(0, this.head), firstPartLen)
    }
    return { timestamps: ts, values: vs }
  }
}

export const useLiveDataStore = defineStore('liveData', () => {
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const sessionStartTimestamp = ref<number | null>(null)

  // Non-reactive buffers for extreme performance
  const buffers = new Map<string, RingBuffer>()

  // Expose a dataVersion tick for charts that still want reactivity
  const dataVersion = ref(0)
  const subscribedSignals = ref<string[]>([])

  let ws: WebSocket | null = null

  function setSubscribedSignals(signals: string[]) {
    subscribedSignals.value = [...new Set(signals.filter(Boolean))]
    sendSubscription()
  }

  function sendSubscription() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    const dataSource = useDataSourceStore()
    ws.send(JSON.stringify({
      type: 'subscribe',
      signals: subscribedSignals.value,
      live_window_seconds: dataSource.config.live_buffer_window_seconds || 15.0
    }))
  }

  async function connect() {
    if (ws || isConnecting.value) return
    isConnecting.value = true

    const wsUrl = await getVisualizerWsUrl()
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      isConnected.value = true
      isConnecting.value = false
      console.log('Connected to Live Data Stream')
      sendSubscription()
    }

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)

        if (payload.type === 'live_source' || payload.type === 'status') {
          const dataSource = useDataSourceStore()
          const daqConnection = useDaqConnectionStore()
          dataSource.handleVisualizerMessage(payload)
          daqConnection.handleVisualizerMessage(payload)
          return
        }

        if (payload.type === 'live_batch' && payload.signals) {
          const dataSource = useDataSourceStore()
          let latestTimestamp: number | null = null

          for (const [signalId, data] of Object.entries(payload.signals)) {
            const typedData = data as { timestamps: number[], values: number[] }
            if (!buffers.has(signalId)) {
              // 10000 capacity per signal gives plenty of room for 100Hz for 15s (1500 pts)
              buffers.set(signalId, new RingBuffer(10000))
            }

            const buffer = buffers.get(signalId)!
            for (let i = 0; i < typedData.timestamps.length; i++) {
              const ts = typedData.timestamps[i]
              const val = typedData.values[i]
              if (ts === undefined || val === undefined) continue
              if (sessionStartTimestamp.value == null) {
                sessionStartTimestamp.value = ts
              }
              buffer.push(ts, val)
              latestTimestamp = latestTimestamp == null ? ts : Math.max(latestTimestamp, ts)
            }
          }

          if (dataSource.config.source === 'zmq' && latestTimestamp != null) {
            const cutoffTimestamp = latestTimestamp - dataSource.config.live_buffer_window_seconds
            for (const buffer of buffers.values()) {
              buffer.trim(cutoffTimestamp)
            }
          }
          dataVersion.value++
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message', err)
      }
    }

    ws.onclose = () => {
      isConnected.value = false
      isConnecting.value = false
      ws = null
      console.log('Disconnected from Live Data Stream. Attempting to reconnect...')
      setTimeout(connect, 3000)
    }

    ws.onerror = (err) => {
      console.error('WebSocket error:', err)
      ws?.close()
    }
  }

  function disconnect() {
    if (ws) {
      ws.close()
      ws = null
    }
  }

  function clearBuffers() {
    buffers.clear()
    sessionStartTimestamp.value = null
    dataVersion.value++
  }

  return {
    isConnected,
    buffers,
    dataVersion,
    subscribedSignals,
    sessionStartTimestamp,
    connect,
    disconnect,
    clearBuffers,
    setSubscribedSignals,
    sendSubscription
  }
})
