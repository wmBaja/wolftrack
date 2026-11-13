# WolfTrack

WolfTrack is a cross-platform Electron application for viewing live and recorded CAN telemetry. The Vue dashboard launches the bundled FastAPI visualizer backend and exchanges data with it over HTTP and WebSockets.

## Repository layout

```text
apps/dashboard/   Electron and Vue application
apps/visualizer/  FastAPI telemetry backend
packages/         Shared packages (empty during phase 1)
plugins/          First-party plugins (empty during phase 1)
```

## Development

Requirements: Node `^20.19.0 || >=22.12.0`, Python 3.12 or newer, and [uv](https://docs.astral.sh/uv/).

```bash
npm install
cd apps/visualizer && uv sync
cd ../..
npm run dev
```

The dashboard starts the visualizer from `apps/visualizer` by default. Set `WOLFTRACK_VISUALIZER_DIR` only when developing against another visualizer checkout.

Useful commands from the repository root:

```bash
npm run type-check
npm run test:unit
npm run test:e2e
npm run lint
npm run electron:build
```

Run backend commands from `apps/visualizer`:

```bash
uv run python src/app.py
uv run --with pytest pytest
uv run pyinstaller --name wolftrack-visualizer --onefile --noconfirm --clean --paths src src/app.py
```

`npm run electron:build` builds the visualizer binary, copies it into the Electron package, and writes installers to `apps/dashboard/release/`.
