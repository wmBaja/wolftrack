import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginVitest from '@vitest/eslint-plugin'
import pluginPlaywright from 'eslint-plugin-playwright'
import boundaries from 'eslint-plugin-boundaries'
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
    name: 'app/architecture-boundaries',
    files: ['src/**/*.{ts,vue}', '../../packages/plugin-sdk/src/**/*.ts'],
    plugins: { boundaries },
    settings: {
      'boundaries/root-path': '.',
      'boundaries/include': ['src/**/*', '../../packages/plugin-sdk/src/**/*'],
      'import/resolver': {
        typescript: { project: './tsconfig.app.json' },
        node: { extensions: ['.ts', '.vue'] },
      },
      'boundaries/elements': [
        { type: 'shell', pattern: 'src/shell/**' },
        { type: 'core', pattern: 'src/core/**' },
        { type: 'charts', pattern: 'src/features/charts/**' },
        { type: 'data-source', pattern: 'src/features/data-source/**' },
        { type: 'file-manager', pattern: 'src/features/file-manager/**' },
        { type: 'export', pattern: 'src/features/export/**' },
        { type: 'sdk', pattern: '../../packages/plugin-sdk/src/**' },
      ],
      'boundaries/files': [
        { pattern: '**/__tests__/**', category: 'test' },
        { pattern: '**/*.spec.ts', category: 'test' },
      ],
    },
    rules: {
      'boundaries/dependencies': ['error', {
        default: 'disallow',
        policies: [
          { from: { element: { type: 'shell' } }, allow: { to: { element: { types: ['shell', 'core', 'sdk'] } } } },
          { from: { element: { type: 'core' } }, allow: { to: { element: { types: ['core', 'sdk'] } } } },
          { from: { element: { type: 'charts' } }, allow: { to: { element: { types: ['charts', 'core', 'sdk'] } } } },
          { from: { element: { type: 'data-source' } }, allow: { to: { element: { types: ['data-source', 'core', 'sdk'] } } } },
          { from: { element: { type: 'file-manager' } }, allow: { to: { element: { types: ['file-manager', 'core', 'sdk'] } } } },
          { from: { element: { type: 'export' } }, allow: { to: { element: { types: ['export', 'core', 'sdk'] } } } },
          { from: { element: { type: 'sdk' } }, allow: { to: { element: { type: 'sdk' } } } },
          { from: { file: { categories: 'test' } }, allow: { to: { element: { types: ['shell', 'core', 'charts', 'data-source', 'file-manager', 'export', 'sdk'] } } } },
        ],
      }],
    },
  },
  {
    name: 'app/shell-test-feature-activation',
    files: ['src/shell/__tests__/**/*.ts'],
    rules: { 'no-restricted-imports': 'off' },
  },
)
