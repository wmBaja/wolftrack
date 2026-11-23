import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginVitest from '@vitest/eslint-plugin'
import pluginPlaywright from 'eslint-plugin-playwright'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

// To allow more languages other than `ts` in `.vue` files, uncomment the following lines:
// import { configureVueProject } from '@vue/eslint-config-typescript'
// configureVueProject({ scriptLangs: ['ts', 'tsx'] })
// More info at https://github.com/vuejs/eslint-config-typescript/#advanced-setup

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}'],
  },

  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**', '**/dist-electron/**', '**/electron/**']),

  pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,
  
  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*'],
  },
  
  {
    ...pluginPlaywright.configs['flat/recommended'],
    files: ['e2e/**/*.{test,spec}.{js,ts,jsx,tsx}'],
  },
  skipFormatting,
  {
    name: 'app/feature-import-boundaries',
    files: ['src/features/**/*.{ts,vue}'],
    rules: {
      'no-restricted-imports': ['error', {
        patterns: [
          { group: ['@/components/**', '@/stores/**', '@/lib/**', '@/types/**', '@/features/**'], message: 'Features may import only the SDK, core, and files within their own feature.' },
          { group: ['../*/**', '../../*'], message: 'Features may not import another feature by relative path.' },
        ],
      }],
    },
  },
  {
    name: 'app/shell-import-boundaries',
    files: ['src/shell/**/*.{ts,vue}'],
    rules: {
      'no-restricted-imports': ['error', {
        patterns: [{ group: ['@/features/**'], message: 'The shell must discover features through registries.' }],
      }],
    },
  },
  {
    name: 'app/shell-test-feature-activation',
    files: ['src/shell/__tests__/**/*.ts'],
    rules: { 'no-restricted-imports': 'off' },
  },
)
