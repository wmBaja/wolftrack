<script lang="ts" setup>
import { onMounted, onUnmounted } from 'vue'
import { dialogState, closeDialog } from '@/types/dialog'

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && dialogState.open) {
    closeDialog()
  }
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
</script>

<template>
  <Transition name="fade">
    <div
      v-if="dialogState.open && dialogState.options"
      class="dialog"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      aria-describedby="dialog-message"
      @click.self="closeDialog()"
    >
      <section class="dialog-content">
        <p class="dialog-eyebrow" :class="{ 'is-danger': dialogState.options.danger }">
          {{
            dialogState.options.eyebrow ??
            (dialogState.options.danger ? 'Destructive action' : 'Confirmation required')
          }}
        </p>
        <h2 id="dialog-title">{{ dialogState.options.title }}</h2>
        <p id="dialog-message" class="dialog-message">{{ dialogState.options.body }}</p>

        <div class="dialog-actions">
          <button
            v-for="btn in dialogState.options.buttons"
            :key="btn.id"
            type="button"
            class="dialog-button"
            :class="{ 'is-danger': btn.danger, 'is-primary': btn.primary }"
            @click="closeDialog(btn.id)"
          >
            {{ btn.text }}
          </button>
        </div>
      </section>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 150ms ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.dialog {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(5 10 18 / 72%);
}

.dialog-content {
  width: min(420px, 100%);
  border: 1px solid var(--color-border);
  background: var(--color-panel);
  padding: 28px;
  border-radius: 14px;
  box-shadow: 0 20px 48px rgb(0 0 0 / 35%);
}

.dialog-eyebrow {
  margin: 0 0 8px;
  color: var(--color-text);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.dialog-eyebrow.is-danger {
  color: var(--color-danger);
}

.dialog-content h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 22px;
}

.dialog-message {
  margin: 12px 0 0;
  color: var(--color-text);
  line-height: 1.5;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}

.dialog-button {
  border: 1px solid var(--color-border);
  border-radius: 7px;
  cursor: pointer;
  font-weight: 700;
  padding: 9px 14px;
  background: transparent;
  color: var(--color-text);
}

.dialog-button.is-primary {
  background: var(--color-accent);
  color: var(--color-text);
}

.dialog-button.is-danger {
  background: var(--color-danger-bg);
  border-color: var(--color-danger-border);
  color: var(--color-danger-text);
}

.dialog-button:hover {
  filter: brightness(1.15);
}

.dialog-button:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
</style>
