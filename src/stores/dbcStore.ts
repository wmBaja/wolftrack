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

export const lookupName: Record<string, string> = {
  'FrontBrakePressure': 'Front Brake Pressure',
  'RearBrakePressure': 'Rear Brake Pressure',
  'FLSuspension_raw': 'Front Left Suspension',
  'FRSuspension_raw': 'Front Right Suspension',
  'RLSuspension_raw': 'Rear Left Suspension',
  'RRSuspension_raw': 'Rear Right Suspension',
  'IMU_Data_accel_x': 'Acceleration X',
  'IMU_Data_accel_y': 'Acceleration Y',
  'IMU_Data_accel_z': 'Acceleration Z',
  'IMU_Data_angular_vel_x': 'Angular Velocity X',
  'IMU_Data_angular_vel_y': 'Angular Velocity Y',
  'IMU_Data_angular_vel_z': 'Angular Velocity Z',
  'IMU_Data_linear_accel_x': 'Linear Acceleration X',
  'IMU_Data_linear_accel_y': 'Linear Acceleration Y',
  'IMU_Data_linear_accel_z': 'Linear Acceleration Z',
  'IMU_Data_rotation_i': 'Rotation I',
  'IMU_Data_rotation_j': 'Rotation J',
  'IMU_Data_rotation_k': 'Rotation K',
  'IMU_Data_rotation_real': 'Rotation Real',
  'SteeringAngleData_angleDegrees': 'Steering Angle',
  'IRCVTTempData_ambientDegreesC': 'IRCVT Ambient Temp',
  'IRCVTTempData_objectDegreesC': 'IRCVT Object Temp',
  'EngineRpmData_rpm': 'Engine RPM',
  'WheelSpeedRpmData_rpm': 'Wheel Speed RPM',
  'ThrottlePos_raw': 'Throttle Position',
}

export const lookupCategory: Record<string, string> = {
  'BrakePressure': 'Brake Pressure',
  'Front_Suspension': 'Front Suspension',
  'Rear_Suspension': 'Rear Suspension',
  'IMU_Data': 'IMU',
  'IMU_Stats': 'IMU Stats',
  'SteeringAngleData': 'Steering',
  'SteeringAngleStats': 'Steering Angle Stats',
  'IRCVTTempData': 'CVT Temperature',
  'IRCVTTempStats': 'CVT Temperature Stats',
  'RPMData': 'RPM',
  'RPMStats': 'RPM Stats',
  'ThrottlePosition': 'Throttle',
}

export const lookupNode: Record<string, string> = {
  'FrontNode': 'Front Node',
  'RearNode': 'Rear Node',
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
