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
      backend: { getPort: () => Promise<number>; getAuthToken: () => Promise<string> }
      files: {
        openFile: (filters: Array<{ name: string; extensions: string[] }>) => Promise<string | null>
        downloadFromUrl: (url: string, suggestedFilename: string) => Promise<boolean>
      }
      daq: { discoverServices: () => Promise<DaqDiscoveryService[]> }
    } | undefined
  }
}
