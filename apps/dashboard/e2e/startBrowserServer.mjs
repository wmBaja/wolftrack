import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const dashboardRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const viteEntry = path.resolve(dashboardRoot, '../../node_modules/vite/bin/vite.js')
const server = spawn(process.execPath, [viteEntry, '--host', '127.0.0.1'], {
  cwd: dashboardRoot,
  env: { ...process.env, WOLFTRACK_BROWSER_TEST: '1' },
  stdio: 'inherit',
})

server.on('exit', (code) => process.exit(code ?? 1))
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => server.kill(signal))
}
