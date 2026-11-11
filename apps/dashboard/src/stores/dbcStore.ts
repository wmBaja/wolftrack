import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getVisualizerBase } from '@/lib/visualizer'

export interface DbcSignal {
  id: string
  node: string
  message: string
  name: string
  unit: string
}

export interface DbcFileInfo {
  name: string
  size: number
  mtime: number
}

const DBC_FILE_NAME_PATTERN = /^[^/\\]+\.dbc$/

export const useDbcStore = defineStore('dbcStore', () => {
  const availableDbcs = ref<DbcFileInfo[]>([])
  const activeDbc = ref<string | null>(null)
  const signals = ref<DbcSignal[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const mutatingName = ref<string | null>(null)

  function isValidDbcFilename(filename: string) {
    return filename.trim() === filename && DBC_FILE_NAME_PATTERN.test(filename) && !filename.includes('..')
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
    if (!isValidDbcFilename(newName)) {
      error.value = 'New filename must be a .dbc file name.'
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
    isValidDbcFilename,
  }
})
