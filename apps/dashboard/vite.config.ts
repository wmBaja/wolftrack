import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'
import electron from 'vite-plugin-electron'
import renderer from 'vite-plugin-electron-renderer'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  base: './',

  server: {
    // This makes the server accessible via IP address as well as localhost
    port: 3000,
    host: true,
  },

  plugins: [
    vue(),
    vueDevTools(),
    tailwindcss(),
    // Use the electron plugin, which will build the main and preload scripts
    electron([
      {
        // The entry point for the Electron main process
        entry: 'electron/main.js',
      },
      {
        // The entry point for the preload script
        entry: 'electron/preload.js',
        onstart(options) {
          // This will start the renderer process once the main process is ready
          options.reload()
        },
      },
    ]),
    // Use the renderer plugin to handle the Vue app
    renderer(),
  ],

  build: {
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html'),
      },
    },
  },

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
