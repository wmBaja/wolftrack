export {}

declare global {
  interface DaqDiscoveryService {
    id: string
    host: string
    port: number
    label?: string
    lastUsedAt?: string
  }

  interface Window {
    electronAPI: {
      sendMessage: (message: unknown) => void
      onMessage: (callback: (args: unknown) => void) => void
      openFile: (filters: Electron.FileFilter[]) => Promise<string | null>
      getBackendPort: () => Promise<number>
      discoverDaqServices: () => Promise<DaqDiscoveryService[]>
      downloadFileFromUrl: (url: string, suggestedFilename: string) => Promise<boolean>
    } | undefined
  }
}
