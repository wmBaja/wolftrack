# WolfTrack dashboard

The Electron and Vue application lives here. It launches the Python visualizer from `../visualizer` while developing and the packaged backend in production.

From the repository root, install dependencies and start the app with:

```bash
npm install
cd apps/visualizer && uv sync
cd ../..
npm run dev
```

Run dashboard-only commands from this directory when needed:

```bash
npm run type-check
npm run test:unit
npm run test:e2e
npm run electron:build
```
