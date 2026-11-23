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
      workspace: {
        load: () => Promise<unknown>
        save: (document: unknown) => Promise<boolean>
        popoutConfig: () => Promise<{ enabled: boolean; url: string }>
      }
      daq: { discoverServices: () => Promise<DaqDiscoveryService[]> }
    } | undefined
  }
}
