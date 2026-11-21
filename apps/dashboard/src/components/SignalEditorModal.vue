<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useWtsStore } from '@/stores/wtsStore'
import { useDbcStore } from '@/stores/dbcStore'
import type {
  OperationDef,
  ParamSpec,
  VirtualSignalDefinition,
  WtsValidationErrorDetail,
} from '@/types/wts'
import { opParams } from '@/types/wts'

const props = defineProps<{
  mode: 'create' | 'edit'
  initialDefinition: VirtualSignalDefinition | null
}>()

const emit = defineEmits<{
  (e: 'saved'): void
  (e: 'close'): void
}>()

const wtsStore = useWtsStore()
const dbcStore = useDbcStore()

const NAME_PATTERN = /^[A-Za-z_][A-Za-z0-9_]{0,63}$/

const name = ref(props.initialDefinition?.name ?? '')
const unit = ref(props.initialDefinition?.unit ?? '')
const category = ref(props.initialDefinition?.category ?? 'Custom')
const description = ref(props.initialDefinition?.description ?? '')
const inputs = ref<string[]>([...(props.initialDefinition?.inputs ?? [])])

// Head stage: an expression over the inputs (default for multi-input) or
// the legacy combine op. Wire ops flatten params next to `type`; the editor
// keeps them in a record and re-flattens on save.
const initialOps = props.initialDefinition?.operations ?? []
const startsWithHead =
  initialOps[0]?.type === 'combine' || initialOps[0]?.type === 'expr'
type HeadMode = 'none' | 'expr' | 'combine'
const headMode = ref<HeadMode>(
  initialOps[0]?.type === 'combine'
    ? 'combine'
    : initialOps[0]?.type === 'expr'
      ? 'expr'
      : 'none',
)
const expression = ref<string>(
  String(opParams(initialOps[0] ?? ({ type: '' })).expression ?? '%s'),
)
const combineOperator = ref<string>(
  String(opParams(initialOps[0] ?? ({ type: '' })).operator ?? 'add'),
)
interface OpStep {
  type: string
  params: Record<string, string | number | boolean | null>
}
const operations = ref<OpStep[]>(
  (startsWithHead ? initialOps.slice(1) : initialOps).map(op => ({
    type: op.type,
    params: opParams(op),
  })),
)

const validationErrors = ref<WtsValidationErrorDetail | null>(null)
const genericError = ref<string | null>(null)
const modalRef = ref<HTMLElement>()
/** Name the signal had when the editor opened; a change triggers rename. */
const originalName = ref(props.initialDefinition?.name ?? '')

const catalog = computed(() => wtsStore.catalog)
const postHeadOps = computed(
  () => catalog.value?.operations.filter(op => !op.is_head) ?? [],
)
const combineOperators = computed(() => catalog.value?.combine_operators ?? [])
const showHeadRow = computed(() => inputs.value.length > 1 || headMode.value !== 'none')

// Adding the second input to a signal without a head opens Expression mode.
watch(
  () => inputs.value.length,
  (now, prev) => {
    if (now > 1 && (prev ?? 0) <= 1 && headMode.value === 'none') {
      headMode.value = 'expr'
    }
  },
)

// --- inputs ---------------------------------------------------------------

const inputSearch = ref('')

/** Ids that would create a cycle: the signal itself + transitive dependents. */
const excludedInputs = computed(() => {
  if (props.mode !== 'edit' || !props.initialDefinition) return new Set<string>()
  const ownId = `WTS.${props.initialDefinition.name}`
  return new Set<string>([ownId, ...wtsStore.dependentsOf(ownId)])
})

const inputOptions = computed(() => {
  const query = inputSearch.value.toLowerCase().trim()
  const chosen = new Set(inputs.value)
  return dbcStore.signals
    .filter(signal => !chosen.has(signal.id))
    .filter(signal => !excludedInputs.value.has(signal.id))
    .filter(
      signal =>
        !query ||
        signal.id.toLowerCase().includes(query) ||
        (signal.display_name ?? '').toLowerCase().includes(query),
    )
    .slice(0, 100)
})

const unitOf = (signalId: string) =>
  dbcStore.signals.find(signal => signal.id === signalId)?.unit ?? ''

function addInput(signalId: string) {
  inputs.value = [...inputs.value, signalId]
}

function removeInput(index: number) {
  inputs.value = inputs.value.filter((_, position) => position !== index)
}

function moveInput(index: number, direction: -1 | 1) {
  const target = index + direction
  if (target < 0 || target >= inputs.value.length) return
  const next = [...inputs.value]
  const item = next[index]!
  next[index] = next[target]!
  next[target] = item
  inputs.value = next
}

// --- operations -----------------------------------------------------------

function catalogEntry(type: string) {
  return catalog.value?.operations.find(op => op.type === type)
}

function defaultParams(type: string): Record<string, string | number | boolean | null> {
  const params: Record<string, string | number | boolean | null> = {}
  for (const spec of catalogEntry(type)?.params ?? []) {
    if (spec.default !== null && spec.default !== undefined) params[spec.name] = spec.default
    else if (spec.type === 'bool') params[spec.name] = false
  }
  return params
}

function addOperation(type: string) {
  operations.value = [...operations.value, { type, params: defaultParams(type) }]
}

function removeOperation(index: number) {
  operations.value = operations.value.filter((_, position) => position !== index)
}

function moveOperation(index: number, direction: -1 | 1) {
  const target = index + direction
  if (target < 0 || target >= operations.value.length) return
  const next = [...operations.value]
  const item = next[index]!
  next[index] = next[target]!
  next[target] = item
  operations.value = next
}

function paramValue(step: OpStep, spec: ParamSpec): string {
  const value = step.params[spec.name]
  return value === null || value === undefined ? '' : String(value)
}

function setParam(step: OpStep, spec: ParamSpec, raw: string) {
  if (spec.type === 'float' || spec.type === 'int') {
    // Keep the raw string while typing; the backend is the validator.
    step.params[spec.name] = raw === '' ? null : Number(raw)
    if (raw !== '' && !Number.isFinite(Number(raw))) step.params[spec.name] = raw
  } else if (spec.type === 'bool') {
    step.params[spec.name] = raw === 'true'
  } else {
    step.params[spec.name] = raw
  }
}

// --- save ------------------------------------------------------------------

const definition = computed<VirtualSignalDefinition>(() => {
  // Flatten params next to type (the backend's wire shape).
  const chain: OperationDef[] = operations.value.map(step => ({
    type: step.type,
    ...step.params,
  }))
  const head: OperationDef[] =
    headMode.value === 'combine'
      ? [{ type: 'combine', operator: combineOperator.value }]
      : headMode.value === 'expr'
        ? [{ type: 'expr', expression: expression.value }]
        : []
  return {
    name: name.value,
    kind: 'continuous',
    category: category.value || 'Custom',
    unit: unit.value,
    description: description.value,
    inputs: inputs.value,
    operations: [...head, ...chain],
  }
})

const canSave = computed(() => {
  if (wtsStore.isSaving) return false
  if (!NAME_PATTERN.test(name.value)) return false
  if (inputs.value.length === 0) return false
  if (headMode.value === 'expr' && !expression.value.trim()) return false
  if (inputs.value.length === 1 && operations.value.length === 0 && headMode.value === 'none')
    return false
  return true
})

async function save() {
  validationErrors.value = null
  genericError.value = null

  // Renamed in edit mode: rename first (rewrites references + charts),
  // then fall through to a normal save of the (possibly edited) body.
  if (
    props.mode === 'edit' &&
    name.value !== originalName.value &&
    NAME_PATTERN.test(name.value)
  ) {
    const renamed = await wtsStore.rename(originalName.value, name.value)
    if (!renamed.ok) {
      if (renamed.validation) validationErrors.value = renamed.validation
      else genericError.value = renamed.message ?? 'Rename failed'
      return
    }
    // Rename took effect: from here on this is an update of the new name.
    originalName.value = name.value
  }

  const result = await wtsStore.save(definition.value)
  if (result.ok) {
    emit('saved')
    emit('close')
    return
  }
  if (result.validation) validationErrors.value = result.validation
  else genericError.value = result.message ?? 'Save failed'
}

// --- shell -----------------------------------------------------------------

/** Drag/resize geometry; persisted so the editor opens where it was left. */
const GEOMETRY_KEY = 'wts-editor-geometry'

interface Geometry {
  left: number | null
  top: number | null
  width: number | null
  height: number | null
}

function loadGeometry(): Geometry {
  try {
    const saved = JSON.parse(localStorage.getItem(GEOMETRY_KEY) ?? '')
    const num = (value: unknown) =>
      typeof value === 'number' && Number.isFinite(value) ? value : null
    return {
      left: num(saved?.left),
      top: num(saved?.top),
      width: num(saved?.width),
      height: num(saved?.height),
    }
  } catch {
    return { left: null, top: null, width: null, height: null }
  }
}

const geometry = ref<Geometry>(loadGeometry())

const modalStyle = computed(() => {
  const style: Record<string, string> = {}
  const g = geometry.value
  if (g.left !== null && g.top !== null) {
    style.position = 'fixed'
    style.left = `${g.left}px`
    style.top = `${g.top}px`
    style.margin = '0'
  }
  if (g.width !== null) style.width = `${g.width}px`
  if (g.height !== null) {
    style.height = `${g.height}px`
    // Explicit user height replaces the vh cap (already viewport-clamped).
    style.maxHeight = 'none'
  }
  return style
})

function persistGeometry() {
  try {
    localStorage.setItem(GEOMETRY_KEY, JSON.stringify(geometry.value))
  } catch {
    /* storage full or unavailable: geometry just won't persist */
  }
}

function startDrag(event: PointerEvent) {
  if ((event.target as HTMLElement).closest('button')) return
  const modal = modalRef.value
  if (!modal) return
  const rect = modal.getBoundingClientRect()
  const startX = event.clientX
  const startY = event.clientY
  const originLeft = rect.left
  const originTop = rect.top

  const onMove = (move: PointerEvent) => {
    const left = Math.min(
      Math.max(originLeft + move.clientX - startX, 8 - rect.width + 140),
      window.innerWidth - 140,
    )
    const top = Math.min(
      Math.max(originTop + move.clientY - startY, 4),
      window.innerHeight - 48,
    )
    geometry.value = { ...geometry.value, left, top }
  }
  const onUp = () => {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    persistGeometry()
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
  event.preventDefault()
}

function startResize(event: PointerEvent) {
  const modal = modalRef.value
  if (!modal) return
  const rect = modal.getBoundingClientRect()
  const startX = event.clientX
  const startY = event.clientY
  if (geometry.value.left === null || geometry.value.top === null) {
    // Pin the top-left before growing so the modal doesn't jump under
    // flex centering.
    geometry.value = { ...geometry.value, left: rect.left, top: rect.top }
  }

  const onMove = (move: PointerEvent) => {
    geometry.value = {
      ...geometry.value,
      width: Math.min(
        Math.max(rect.width + move.clientX - startX, 380),
        window.innerWidth - 16,
      ),
      height: Math.min(
        Math.max(rect.height + move.clientY - startY, 260),
        window.innerHeight - 16,
      ),
    }
  }
  const onUp = () => {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    persistGeometry()
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
  event.preventDefault()
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.stopPropagation()
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  modalRef.value?.focus()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <!-- body-level: grid items create stacking contexts that would trap the overlay -->
  <Teleport to="body">
  <div class="editor-overlay" @click.self="emit('close')">
    <div ref="modalRef" class="editor-modal" tabindex="-1" role="dialog" aria-modal="true"
         :aria-label="mode === 'create' ? 'New WT signal' : `Edit WTS.${name}`"
         :style="modalStyle">
      <header class="editor-header" data-testid="editor-header" @pointerdown="startDrag">
        <h3>{{ mode === 'create' ? 'New WT Signal' : `Edit WTS.${name}` }}</h3>
        <button type="button" class="close-btn" aria-label="Close" @click="emit('close')">×</button>
      </header>

      <div class="editor-body custom-scrollbar">
        <label class="field">
          <span class="field-label">Name</span>
          <span class="name-row">
            <span class="name-prefix">WTS.</span>
            <input
              v-model="name"
              type="text"
              data-testid="signal-name"
              placeholder="Brake_Bias"
            />
          </span>
          <small v-if="mode === 'edit'" class="field-note" data-testid="rename-note">
            Renaming updates signals that use this signal and any charts
            plotting it.
          </small>
        </label>

        <div class="field-row">
          <label class="field">
            <span class="field-label">Unit</span>
            <input v-model="unit" type="text" data-testid="signal-unit" placeholder="psi" />
          </label>
          <label class="field">
            <span class="field-label">Category</span>
            <input v-model="category" type="text" data-testid="signal-category" placeholder="Custom" />
          </label>
        </div>

        <label class="field">
          <span class="field-label">Description (optional)</span>
          <input v-model="description" type="text" data-testid="signal-description" />
        </label>

        <div class="field">
          <span class="field-label">Inputs (order matters for subtract / divide)</span>
          <input
            v-model="inputSearch"
            type="search"
            class="input-search"
            data-testid="input-search"
            placeholder="Search signals…"
            aria-label="Search input signals"
          />
          <ol v-if="inputs.length" class="input-list" data-testid="input-list">
            <li v-for="(signalId, index) in inputs" :key="signalId" class="input-item">
              <span class="input-name">{{ signalId }}</span>
              <span v-if="unitOf(signalId)" class="input-unit">{{ unitOf(signalId) }}</span>
              <button type="button" aria-label="Move up" :disabled="index === 0"
                      @click="moveInput(index, -1)">↑</button>
              <button type="button" aria-label="Move down" :disabled="index === inputs.length - 1"
                      @click="moveInput(index, 1)">↓</button>
              <button type="button" aria-label="Remove input" @click="removeInput(index)">×</button>
            </li>
          </ol>
          <ul v-else class="field-note">No inputs yet — pick at least one below.</ul>
          <button
            v-if="inputs.length === 1 && headMode === 'none'"
            type="button"
            class="option-btn add-expr-btn"
            data-testid="add-expr-btn"
            @click="headMode = 'expr'"
          >
            + Expression (%s)
          </button>
          <ul class="option-list" data-testid="input-options">
            <li v-for="option in inputOptions" :key="option.id">
              <button type="button" class="option-btn" @click="addInput(option.id)">
                + {{ option.id }}
                <span v-if="option.unit" class="input-unit">{{ option.unit }}</span>
                <span v-if="option.is_virtual" class="virtual-tag">WT</span>
              </button>
            </li>
          </ul>
        </div>

        <div v-if="showHeadRow" class="field" data-testid="head-row">
          <span class="field-label">Combine inputs</span>
          <div class="head-mode-toggle" role="group" aria-label="Head operation">
            <button
              type="button"
              class="mode-btn"
              data-testid="head-expr-btn"
              :class="{ active: headMode === 'expr' }"
              @click="headMode = 'expr'"
            >
              Expression
            </button>
            <button
              type="button"
              class="mode-btn"
              data-testid="head-combine-btn"
              :class="{ active: headMode === 'combine' }"
              @click="headMode = 'combine'"
            >
              Combine
            </button>
          </div>
          <template v-if="headMode === 'expr'">
            <input
              v-model="expression"
              type="text"
              data-testid="expr-input"
              spellcheck="false"
              aria-label="Expression"
              placeholder="%s / %s"
            />
            <ol v-if="inputs.length" class="expr-map" data-testid="expr-map">
              <li v-for="(signalId, i) in inputs" :key="signalId">
                {{ i + 1 }}: %s → {{ signalId }}
              </li>
            </ol>
          </template>
          <select v-else v-model="combineOperator" data-testid="combine-select"
                  aria-label="Combine operator">
            <option v-for="operator in combineOperators" :key="operator" :value="operator">
              {{ operator }}
            </option>
          </select>
        </div>

        <div class="field">
          <span class="field-label">Operations</span>
          <ol class="op-list" data-testid="op-list">
            <li v-for="(step, index) in operations" :key="index" class="op-step">
              <div class="op-step-header">
                <span class="op-label">{{ catalogEntry(step.type)?.label ?? step.type }}</span>
                <button type="button" aria-label="Move operation up" :disabled="index === 0"
                        @click="moveOperation(index, -1)">↑</button>
                <button type="button" aria-label="Move operation down"
                        :disabled="index === operations.length - 1"
                        @click="moveOperation(index, 1)">↓</button>
                <button type="button" aria-label="Remove operation"
                        @click="removeOperation(index)">×</button>
              </div>
              <div class="op-params">
                <label v-for="spec in catalogEntry(step.type)?.params ?? []" :key="spec.name"
                       class="param">
                  <span class="param-label">
                    {{ spec.name }}<template v-if="spec.unit"> ({{ spec.unit }})</template>
                  </span>
                  <select v-if="spec.type === 'enum'"
                          :value="paramValue(step, spec)"
                          :data-testid="`param-${step.type}-${spec.name}`"
                          @change="setParam(step, spec, ($event.target as HTMLSelectElement).value)">
                    <option v-for="choice in spec.choices ?? []" :key="choice" :value="choice">
                      {{ choice }}
                    </option>
                  </select>
                  <select v-else-if="spec.type === 'bool'"
                          :value="paramValue(step, spec)"
                          @change="setParam(step, spec, ($event.target as HTMLSelectElement).value)">
                    <option value="true">true</option>
                    <option value="false">false</option>
                  </select>
                  <input v-else-if="spec.type === 'float' || spec.type === 'int'"
                         type="number"
                         :step="spec.type === 'int' ? 1 : 'any'"
                         :min="spec.min ?? undefined"
                         :max="spec.max ?? undefined"
                         :value="paramValue(step, spec)"
                         :required="spec.required"
                         :data-testid="`param-${step.type}-${spec.name}`"
                         :aria-label="`${catalogEntry(step.type)?.label ?? step.type}: ${spec.name}`"
                         @input="setParam(step, spec, ($event.target as HTMLInputElement).value)" />
                  <input v-else
                         type="text"
                         :value="paramValue(step, spec)"
                         :required="spec.required"
                         :aria-label="`${catalogEntry(step.type)?.label ?? step.type}: ${spec.name}`"
                         @input="setParam(step, spec, ($event.target as HTMLInputElement).value)" />
                  <small class="param-help">{{ spec.help }}</small>
                </label>
              </div>
            </li>
          </ol>
          <select
            class="add-op-select"
            data-testid="add-op-select"
            aria-label="Add operation"
            value=""
            @change="addOperation(($event.target as HTMLSelectElement).value); ($event.target as HTMLSelectElement).value = ''">
            <option value="" disabled>+ Add operation…</option>
            <option v-for="op in postHeadOps" :key="op.type" :value="op.type">
              {{ op.label }}
            </option>
          </select>
          <small v-if="!catalog" class="field-note">Loading operation catalog…</small>
        </div>
      </div>

      <footer class="editor-footer">
        <ul v-if="validationErrors" class="error-list" data-testid="error-list">
          <li v-for="(issue, index) in validationErrors.errors" :key="index">
            <strong v-if="issue.signal">{{ issue.signal }}:</strong> {{ issue.message }}
          </li>
        </ul>
        <p v-else-if="genericError" class="error-list" data-testid="error-list">{{ genericError }}</p>
        <div class="footer-buttons">
          <button type="button" class="cancel-btn" @click="emit('close')">Cancel</button>
          <button type="button" class="save-btn" data-testid="save-btn"
                  :disabled="!canSave" @click="save">
            {{ wtsStore.isSaving ? 'Saving…' : 'Save' }}
          </button>
        </div>
      </footer>
      <span class="resize-handle" data-testid="resize-handle" aria-hidden="true"
            title="Drag to resize" @pointerdown="startResize"></span>
    </div>
  </div>
  </Teleport>
</template>

<style scoped>
.editor-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}

.editor-modal {
  position: relative;
  width: min(560px, 92vw);
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg, #14161a);
  color: var(--color-text, #e5e7eb);
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.35));
  border-radius: 8px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
}

.editor-modal:focus {
  outline: none;
}

.resize-handle {
  position: absolute;
  right: 2px;
  bottom: 2px;
  width: 16px;
  height: 16px;
  cursor: nwse-resize;
  touch-action: none;
  /* corner notch glyph */
  background:
    linear-gradient(135deg,
      transparent 0 45%, var(--color-border, rgba(128, 128, 128, 0.6)) 45% 55%,
      transparent 55% 70%, var(--color-border, rgba(128, 128, 128, 0.6)) 70% 80%,
      transparent 80%);
  border-bottom-right-radius: 8px;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-border, rgba(128, 128, 128, 0.25));
  cursor: grab;
  user-select: none;
  touch-action: none;
}

.editor-header:active {
  cursor: grabbing;
}

.editor-header h3 {
  margin: 0;
  font-size: 14px;
}

.close-btn {
  border: none;
  background: none;
  color: inherit;
  font-size: 18px;
  cursor: pointer;
}

.editor-body {
  padding: 12px 14px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.field-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted, #9ca3af);
}

.field-note {
  font-size: 11px;
  color: var(--color-text-muted, #9ca3af);
  margin: 0;
  list-style: none;
  padding: 0;
}

input,
select {
  background: var(--color-panel, rgba(255, 255, 255, 0.06));
  color: inherit;
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.35));
  border-radius: 4px;
  padding: 5px 7px;
  font-size: 12px;
}

input[readonly] {
  opacity: 0.7;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 2px;
}

.name-prefix {
  font-size: 12px;
  color: var(--color-text-muted, #9ca3af);
}

.name-row input {
  flex: 1;
}

.input-search {
  width: 100%;
  box-sizing: border-box;
}

.input-list,
.op-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.input-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 6px;
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.3));
  border-radius: 4px;
  font-size: 12px;
}

.input-name {
  flex: 1;
}

.input-unit {
  color: var(--color-text-muted, #9ca3af);
  font-size: 10px;
}

.input-item button,
.op-step-header button {
  border: none;
  background: none;
  color: inherit;
  cursor: pointer;
  padding: 0 3px;
}

.input-item button:disabled,
.op-step-header button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.option-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 140px;
  overflow-y: auto;
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.2));
  border-radius: 4px;
}

.option-btn {
  width: 100%;
  text-align: left;
  border: none;
  background: none;
  color: inherit;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  gap: 6px;
  align-items: center;
}

.option-btn:hover {
  background: var(--color-panel, rgba(255, 255, 255, 0.07));
}

.virtual-tag {
  font-size: 9px;
  font-weight: 700;
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.4));
  border-radius: 3px;
  padding: 0 3px;
}

.head-mode-toggle {
  display: flex;
  gap: 4px;
  margin: 2px 0 4px;
}

.mode-btn {
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.4));
  border-radius: 4px;
  background: none;
  color: inherit;
  padding: 3px 10px;
  font-size: 12px;
  cursor: pointer;
}

.mode-btn.active {
  background: var(--color-panel, rgba(255, 255, 255, 0.12));
  font-weight: 600;
}

.expr-map {
  list-style: none;
  margin: 4px 0 0;
  padding: 0;
  font-size: 11px;
  opacity: 0.8;
}

.add-expr-btn {
  border: 1px dashed var(--color-border, rgba(128, 128, 128, 0.4));
  border-radius: 4px;
  margin: 4px 0;
}

.op-step {
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.3));
  border-radius: 4px;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.op-step-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.op-label {
  flex: 1;
  font-size: 12px;
  font-weight: 600;
}

.op-params {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.param {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 120px;
}

.param-label {
  font-size: 10px;
  color: var(--color-text-muted, #9ca3af);
}

.param-help {
  font-size: 10px;
  color: var(--color-text-muted, #9ca3af);
}

.add-op-select {
  align-self: flex-start;
  margin-top: 6px;
}

.editor-footer {
  border-top: 1px solid var(--color-border, rgba(128, 128, 128, 0.25));
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.error-list {
  margin: 0;
  padding: 6px 8px 6px 22px;
  border-radius: 4px;
  background: rgba(239, 68, 68, 0.12);
  color: #fca5a5;
  font-size: 12px;
}

.footer-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.cancel-btn,
.save-btn {
  border: none;
  border-radius: 4px;
  padding: 6px 14px;
  font-size: 12px;
  cursor: pointer;
}

.cancel-btn {
  background: transparent;
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.35));
  color: inherit;
}

.save-btn {
  background: var(--color-accent, #3b82f6);
  color: white;
}

.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
