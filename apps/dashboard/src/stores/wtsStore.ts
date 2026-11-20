import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getVisualizerBase } from '@/lib/visualizer'
import { useDbcStore } from '@/stores/dbcStore'
import { useWidgetStore } from '@/stores/widgetStore'
import { invalidateSignalsEverywhere } from '@/stores/wtsRefresh'
import {
  isWtsDependentsDetail,
  isWtsValidationErrorDetail,
  type OperationCatalog,
  type VirtualSignalDefinition,
  type WtsDependentsDetail,
  type WtsIssue,
  type WtsMutationResult,
  type WtsValidationErrorDetail,
} from '@/types/wts'

/** Result of a save: validation detail on 422, generic message otherwise. */
export interface WtsSaveResult {
  ok: boolean
  validation?: WtsValidationErrorDetail
  dependents?: WtsDependentsDetail
  message?: string
  /** Set when the backend promoted a legacy .dbc to a new .wts setup. */
  promotedTo?: string | null
}

export const useWtsStore = defineStore('wts', () => {
  const definitions = ref<VirtualSignalDefinition[]>([])
  const issues = ref<WtsIssue[]>([])
  const catalog = ref<OperationCatalog | null>(null)
  const wtsVersion = ref(0)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  /** One-line notice after a .dbc -> .wts promotion (shown once). */
  const promotionNotice = ref<string | null>(null)

  async function fetchCatalog(): Promise<void> {
    try {
      const baseUrl = await getVisualizerBase()
      const res = await fetch(`${baseUrl}/api/wts/operations`)
      if (!res.ok) throw new Error(`Failed to fetch operation catalog (${res.status})`)
      catalog.value = await res.json()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    }
  }

  async function fetchDefinitions(): Promise<void> {
    try {
      const baseUrl = await getVisualizerBase()
      const res = await fetch(`${baseUrl}/api/wts/signals`)
      if (!res.ok) throw new Error(`Failed to fetch virtual signals (${res.status})`)
      const data = await res.json()
      definitions.value = data.signals || []
      issues.value = data.issues || []
      wtsVersion.value = data.wts_version ?? 0
    } catch {
      // Older backends have no /api/wts at all: empty state, not an error.
      definitions.value = []
      issues.value = []
      error.value = null
    }
  }

  async function save(definition: VirtualSignalDefinition): Promise<WtsSaveResult> {
    isSaving.value = true
    error.value = null
    try {
      const baseUrl = await getVisualizerBase()
      const res = await fetch(
        `${baseUrl}/api/wts/signals/${encodeURIComponent(definition.name)}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ definition }),
        },
      )
      const payload = await res.json().catch(() => null)
      if (!res.ok) {
        const detail = payload?.detail
        if (res.status === 422 && isWtsValidationErrorDetail(detail)) {
          return { ok: false, validation: detail }
        }
        const message =
          typeof detail === 'string' ? detail : `Save failed (${res.status})`
        error.value = message
        return { ok: false, message }
      }

      const result = payload as WtsMutationResult
      await afterMutation(result)
      return { ok: true, promotedTo: result?.promoted_to ?? null }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e)
      error.value = message
      return { ok: false, message }
    } finally {
      isSaving.value = false
    }
  }

  /** Rename a virtual signal; widgets, inputs, and signal_info follow. */
  async function rename(name: string, newName: string): Promise<WtsSaveResult> {
    isSaving.value = true
    error.value = null
    try {
      const baseUrl = await getVisualizerBase()
      const res = await fetch(
        `${baseUrl}/api/wts/signals/${encodeURIComponent(name)}/rename`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ new_name: newName }),
        },
      )
      const payload = await res.json().catch(() => null)
      if (!res.ok) {
        const detail = payload?.detail
        if (res.status === 422 && isWtsValidationErrorDetail(detail)) {
          return { ok: false, validation: detail }
        }
        const message =
          typeof detail === 'string' ? detail : `Rename failed (${res.status})`
        error.value = message
        return { ok: false, message }
      }

      const result = payload as WtsMutationResult
      // Charts reference signals by id; swap the id in every widget, then
      // treat the old + new + dependent ids as changed for cache invalidation.
      useWidgetStore().renameSignalId(`WTS.${name}`, `WTS.${newName}`)
      await afterMutation(result)
      return { ok: true, promotedTo: null }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e)
      error.value = message
      return { ok: false, message }
    } finally {
      isSaving.value = false
    }
  }

  async function remove(name: string): Promise<WtsSaveResult> {
    isSaving.value = true
    error.value = null
    try {
      const baseUrl = await getVisualizerBase()
      const res = await fetch(
        `${baseUrl}/api/wts/signals/${encodeURIComponent(name)}`,
        { method: 'DELETE' },
      )
      const payload = await res.json().catch(() => null)
      if (!res.ok) {
        const detail = payload?.detail
        if (res.status === 409 && isWtsDependentsDetail(detail)) {
          return { ok: false, dependents: detail }
        }
        const message =
          typeof detail === 'string' ? detail : `Delete failed (${res.status})`
        error.value = message
        return { ok: false, message }
      }

      const result = payload as WtsMutationResult
      await afterMutation(result)
      return { ok: true, promotedTo: result?.promoted_to ?? null }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e)
      error.value = message
      return { ok: false, message }
    } finally {
      isSaving.value = false
    }
  }

  async function afterMutation(result: WtsMutationResult | null): Promise<void> {
    // Refresh definitions and the chart-facing signal list. The backend
    // already re-indexed the log path where needed; the frontend must NOT
    // trigger a re-upload/re-index here — a plain signals refresh is enough.
    const before = new Map(definitions.value.map(def => [`WTS.${def.name}`, def.def_hash]))
    await fetchDefinitions()
    const dbcStore = useDbcStore()
    await dbcStore.fetchSignals()

    // Invalidate the edited/removed signals and their transitive dependents
    // in both chart modes (5.6). Anything whose hash changed or vanished is
    // stale; the backend recomputed exactly that set.
    const changed: string[] = []
    for (const [id, hash] of before) {
      const after = definitions.value.find(def => `WTS.${def.name}` === id)
      if (!after || after.def_hash !== hash) changed.push(id)
    }
    invalidateSignalsEverywhere(changed)

    if (result?.promoted_to) {
      promotionNotice.value = `Saved to new setup “${result.promoted_to}”; your original DBC is unchanged.`
      // The active file name changed server-side: resync the list without
      // touching the log pipeline (no upload_config call).
      await dbcStore.fetchDbcs()
    }
  }

  /** Transitive virtual-signal dependents of a signal id (defs graph). */
  function dependentsOf(signalId: string): string[] {
    const found = new Set<string>()
    let frontier = [signalId]
    while (frontier.length > 0) {
      const next: string[] = []
      for (const definition of definitions.value) {
        const id = `WTS.${definition.name}`
        if (found.has(id)) continue
        if (definition.inputs?.some(input => frontier.includes(input))) {
          found.add(id)
          next.push(id)
        }
      }
      frontier = next
    }
    return [...found]
  }

  return {
    definitions,
    issues,
    catalog,
    wtsVersion,
    isSaving,
    error,
    promotionNotice,
    fetchCatalog,
    fetchDefinitions,
    save,
    rename,
    remove,
    dependentsOf,
  }
})
