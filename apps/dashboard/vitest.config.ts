import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
import viteConfig from './vite.config'

const dashboardRoot = fileURLToPath(new URL('./', import.meta.url))

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/testSetup.ts'],
      exclude: [...configDefaults.exclude, 'e2e/**'],
      root: dashboardRoot,
    },
  }),
)
