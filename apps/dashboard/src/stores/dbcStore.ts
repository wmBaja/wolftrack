import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getVisualizerBase } from '@/lib/visualizer'
import type { OperationDef } from '@/types/wts'

export interface DbcSignal {
  id: string
  node: string
  message: string
  name: string
  unit: string
  // Additive WTS fields (absent on older backends and on raw signals).
  is_virtual?: boolean
  kind?: string
  category?: string
  description?: string
  inputs?: string[]
  operations?: OperationDef[]
  broken?: boolean
  broken_reason?: string | null
  display_name?: string
  min?: number
  max?: number
}

export interface DbcFileInfo {
  name: string
  size: number
  mtime: number
  /** Missing on older backends ⇒ "dbc". */
  type?: 'dbc' | 'wts'
}

export const SETUP_FILE_NAME_PATTERN = /^[^/\\]+\.(dbc|wts)$/

export const useDbcStore = defineStore('dbcStore', () => {
  const availableDbcs = ref<DbcFileInfo[]>([])
  const activeDbc = ref<string | null>(null)
  const signals = ref<DbcSignal[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const mutatingName = ref<string | null>(null)

  function isValidSetupFilename(filename: string) {
    return filename.trim() === filename && SETUP_FILE_NAME_PATTERN.test(filename) && !filename.includes('..')
  }

  /** Renaming must keep the file's extension (.dbc stays .dbc, .wts stays .wts). */
  function isValidRename(filename: string, newName: string) {
    const extension = filename.endsWith('.wts') ? '.wts' : '.dbc'
    return newName.endsWith(extension) && isValidSetupFilename(newName)
  }

  async function getResponseError(response: Response, fallback: string) {
    try {
      const payload = await response.json() as { detail?: string }
      return payload.detail ?? fallback
    } catch {
      return fallback
    }
  }

  async function fetchDbcs() {
    try {
      const baseUrl = await getVisualizerBase()
      const res = await fetch(`${baseUrl}/api/dbc`)
      if (!res.ok) throw new Error('Failed to fetch DBCs')
      const data = await res.json()
      availableDbcs.value = data.available
      activeDbc.value = data.active
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    }
  }

  async function fetchSignals() {
    try {
      const baseUrl = await getVisualizerBase()
      const res = await fetch(`${baseUrl}/api/signals`)
      if (!res.ok) throw new Error('Failed to fetch signals')
      const data = await res.json()
      signals.value = data.signals || []
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    }
  }

  async function uploadDbc(file: File) {
    isLoading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const baseUrl = await getVisualizerBase()
      const res = await fetch(`${baseUrl}/api/dbc/upload`, {
        method: 'POST',
        body: formData
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Upload failed')
      }
      
      await fetchDbcs()
      await fetchSignals()
      return true
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function selectDbc(filename: string) {
    isLoading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('filename', filename)
      
      const baseUrl = await getVisualizerBase()
      const res = await fetch(`${baseUrl}/api/dbc/select`, {
        method: 'POST',
        body: formData
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Select failed')
      }
      
      await fetchDbcs()
      await fetchSignals()
      return true
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function deleteDbc(filename: string) {
    isLoading.value = true
    mutatingName.value = filename
    error.value = null
    try {
      const baseUrl = await getVisualizerBase()
      const res = await fetch(`${baseUrl}/api/dbc/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      })
      if (!res.ok) {
        throw new Error(await getResponseError(res, 'Delete failed'))
      }
      
      await fetchDbcs()
      await fetchSignals()
      return true
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
      return false
    } finally {
      isLoading.value = false
      mutatingName.value = null
    }
  }

  async function renameDbc(filename: string, newName: string) {
    if (!isValidRename(filename, newName)) {
      error.value = `New filename must be a ${
        filename.endsWith('.wts') ? '.wts' : '.dbc'
      } file name.`
      return false
    }

    isLoading.value = true
    mutatingName.value = filename
    error.value = null
    try {
      const baseUrl = await getVisualizerBase()
      const res = await fetch(`${baseUrl}/api/dbc/${encodeURIComponent(filename)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName }),
      })
      if (!res.ok) {
        throw new Error(await getResponseError(res, 'Rename failed'))
      }

      await fetchDbcs()
      await fetchSignals()
      return true
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
      return false
    } finally {
      isLoading.value = false
      mutatingName.value = null
    }
  }

  return {
    availableDbcs,
    activeDbc,
    signals,
    isLoading,
    error,
    mutatingName,
    fetchDbcs,
    fetchSignals,
    uploadDbc,
    selectDbc,
    deleteDbc,
    renameDbc,
    isValidSetupFilename,
    isValidRename,
  }
})
