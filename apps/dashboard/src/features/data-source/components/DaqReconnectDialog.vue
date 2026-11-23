<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  target: { host: string, port: number }
  error: string | null
  nextAttemptAt: number | null
  reconnecting: boolean
}>()

const emit = defineEmits<{
  forceReconnect: []
  cancel: []
}>()

const now = ref(Date.now())
let countdownTimer: number | null = null

const secondsUntilRetry = computed(() => {
  if (!props.nextAttemptAt) return null
  return Math.max(0, Math.ceil((props.nextAttemptAt - now.value) / 1000))
})

const statusMessage = computed(() => {
  if (props.reconnecting) return 'Reconnecting to the DAQ…'
  if (secondsUntilRetry.value !== null) {
    return `Retrying automatically in ${secondsUntilRetry.value} second${secondsUntilRetry.value === 1 ? '' : 's'}…`
  }
  return 'Preparing the next reconnect attempt…'
})

function startCountdown() {
  if (countdownTimer !== null) return
  now.value = Date.now()
  countdownTimer = window.setInterval(() => {
    now.value = Date.now()
  }, 250)
}

function stopCountdown() {
  if (countdownTimer === null) return
  window.clearInterval(countdownTimer)
  countdownTimer = null
}

watch(() => props.nextAttemptAt, (nextAttemptAt) => {
  if (nextAttemptAt) startCountdown()
  else stopCountdown()
}, { immediate: true })

onMounted(() => {
  if (props.nextAttemptAt) startCountdown()
})
onBeforeUnmount(stopCountdown)
</script>

<template>
  <div class="reconnect-dialog" role="alertdialog" aria-modal="true" aria-labelledby="reconnect-dialog-title">
    <section class="reconnect-dialog__content">
      <p class="reconnect-dialog__eyebrow">DAQ connection interrupted</p>
      <h2 id="reconnect-dialog-title">Connection to the DAQ was lost</h2>
      <p class="reconnect-dialog__target">{{ target.host ? `${target.host}:${target.port}` : 'No DAQ target selected' }}</p>
      <p class="reconnect-dialog__message">{{ error || 'Check the DAQ and network connection, then try again.' }}</p>
      <p class="reconnect-dialog__status" aria-live="polite">{{ statusMessage }}</p>

      <div class="reconnect-dialog__actions">
        <button
          class="reconnect-dialog__force"
          type="button"
          :disabled="reconnecting"
          @click="emit('forceReconnect')"
        >
          Force Reconnect
        </button>
        <button
          class="reconnect-dialog__cancel"
          type="button"
          :disabled="reconnecting"
          @click="emit('cancel')"
        >
          Cancel
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.reconnect-dialog {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(5 10 18 / 72%);
}

.reconnect-dialog__content {
  width: min(440px, 100%);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: var(--color-panel);
  box-shadow: 0 20px 48px rgb(0 0 0 / 35%);
  padding: 28px;
}

.reconnect-dialog__eyebrow {
  margin: 0 0 8px;
  color: var(--color-danger);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.reconnect-dialog h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 22px;
}

.reconnect-dialog__target,
.reconnect-dialog__message,
.reconnect-dialog__status {
  margin: 12px 0 0;
}

.reconnect-dialog__target {
  color: var(--color-blue-text);
  font-family: monospace;
}

.reconnect-dialog__message {
  color: var(--color-text);
}

.reconnect-dialog__status {
  color: var(--color-muted);
  font-size: 14px;
}

.reconnect-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}

.reconnect-dialog__actions button {
  border: 1px solid var(--color-border);
  border-radius: 7px;
  cursor: pointer;
  font-weight: 700;
  padding: 9px 14px;
}

.reconnect-dialog__force {
  background: var(--color-accent);
  color: var(--color-text);
}

.reconnect-dialog__cancel {
  background: transparent;
  color: var(--color-text);
}

.reconnect-dialog__actions button:disabled {
  cursor: wait;
  opacity: .6;
}
</style>
