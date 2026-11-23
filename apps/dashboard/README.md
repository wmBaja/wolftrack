# WolfTrack dashboard

The dashboard is the Electron and Vue application. It launches the Python visualizer from
`../visualizer` during development and the packaged backend in production.

## Architecture at a glance

The frontend separates app composition (`shell`), shared application services (`core`), and
feature-owned UI (`features`). The SDK package defines the contracts used to connect those
parts.

```text
apps/dashboard/src/
├── shell/       App frame, navigation, dashboard, registries, and feature context
├── core/        Backend client, telemetry stores, data hook, dialog state, widget model
├── features/    Built-in feature modules and their Vue components
├── router/      Vue Router configuration
└── views/       Route-level screens

packages/plugin-sdk/src/  TypeScript contracts for contributions and PluginContext
```

```mermaid
flowchart TD
  Main[main.ts] --> Loader[eager feature discovery]
  Loader --> Activate[activate(ctx)]
  Activate --> Registries[widget / panel / command / view registries]
  Registries --> Nav[NavBar renders toolbar panels]
  Registries --> Grid[DashboardGrid renders widgets and dashboard panels]
  Registries --> App[App renders overlay panels]
  Grid --> WidgetStore[core widget store]
  Widget[ChartWidget] --> TimeHook[useTimeSeriesData]
  TimeHook --> TimeStore[timeSeriesDataStore]
  TimeStore --> Live[liveDataStore / WebSocket]
  TimeStore --> Log[logDataStore]
  Live --> Backend[FastAPI visualizer]
  Log --> Backend
```

## Startup and composition

1. `src/main.ts` creates the Vue app and eagerly discovers `src/features/*/index.ts` with
   `import.meta.glob`. It calls each module's `activate(ctx)` before mounting the app.
2. `src/shell/pluginContext.ts` builds the context. Its registry methods add contributions
   to reactive registries; widget registration also records the widget's title and default
   grid dimensions in `core/widgets.ts`. Feature activation can return a disposer to remove
   its registrations.
3. `src/App.vue` composes the navigation bar, current route, global dialog host, and
   registered overlay panels. `src/router/` maps routes to screens under `src/views/`.
4. The shell renders contributions by location. `NavBar.vue` mounts left- and right-aligned
   toolbar panels; `DashboardGrid.vue` mounts dashboard panels and widget components; `App.vue`
   mounts overlay panels. The shell does not import the built-in feature components directly.

The registries are keyed by stable IDs: widget `type`, and `id` for views, panels, and
commands. They expose reactive entry lists for rendering and a `get(id)` lookup. Toolbar
contributions can request left or right alignment. Panels currently render their own controls
and content; the shell places their component but does not build a generic panel UI around it.

## Layer responsibilities

### `shell/`

- Owns app-level composition and chooses where registered contributions appear.
- Provides `PluginContext` to feature activation and owns the reactive registries.
- Hosts the existing grid dashboard and its context menu, including layout import/export and
  clear-all actions.
- Renders `MissingWidget.vue` for a saved widget whose `type` has no current registration.

Shell components may depend on `core` and the SDK. They should discover feature UI through
registries instead of importing a feature's components.

### `core/`

- `backendClient.ts` builds authenticated HTTP and WebSocket access to the visualizer.
- `stores/liveDataStore.ts` owns the live WebSocket connection and non-reactive typed-array
  ring buffers. Its `dataVersion` is the reactive signal that tells chart consumers data has
  advanced.
- `stores/logDataStore.ts` owns log status, playback, query windows, and log data buffers.
- `stores/timeSeriesDataStore.ts` combines live and log data, tracks registered consumers,
  derives live signal subscriptions, and builds render-ready chart snapshots.
- `composables/useTimeSeriesData.ts` registers a component's signal needs and unregisters
  them on unmount. Widgets should use this data hook rather than reading live/log stores.
- `stores/widgetStore.ts` owns the current widget layout and its `dashboard-widgets`
  `localStorage` persistence. `widgets.ts` contains the widget record and registered defaults.
- `dialog.ts` stores the app-wide dialog state rendered by `shell/DialogBox.vue`.

All Pinia stores currently live under `core/stores`, including DAQ, data-source, DBC, and
file-related stores that are used mainly by one feature. This keeps current cross-feature
dependencies within one shared layer, but makes `core` broader than its intended long-term
role. Keep features from importing one another; move state behind narrower context APIs as
those seams become clear.

### `features/`

Each built-in feature has an `index.ts` entry point that exports `activate(ctx)`. Its
components and feature UI live beside that entry point:

| Feature | Contributions today |
| --- | --- |
| `charts` | `base` and `chart` widget types; the “Add Chart Widget” command |
| `data-source` | Toolbar configuration and logging controls; connection lifecycle overlay |
| `export` | Export toolbar panel |
| `file-manager` | Left-side file-manager toolbar control; log-window control in the dashboard |

The chart remains a **widget**; `features/charts` is its code owner, while the widget registry
is the extension point the dashboard uses to create it. A feature can contribute multiple
kinds of UI through the same context.

### `packages/plugin-sdk/`

This package currently contains TypeScript interfaces only: widget, view, panel, and command
contributions; manifest shapes; and `PluginContext`. The package is shared by the dashboard
workspace, but it is not yet a runtime plugin framework. It does not validate manifests,
load external code, enforce plugin permissions, or isolate plugin code.

## Telemetry data flow

1. A chart widget reads its configured signal IDs from the widget store.
2. `useTimeSeriesData(consumerId, signalIds)` registers those signals with
   `timeSeriesDataStore` and removes the registration when the widget unmounts.
3. The store aggregates signal needs. For live data, it asks `liveDataStore` to subscribe to
   the active signal set. For log data, it requests overview/detail windows from
   `logDataStore` and selects the current query window for the chart snapshot.
4. The chart renders the snapshot through `UplotChart`. Live ring buffers stay non-reactive;
   the version counter triggers the chart to rebuild its view without wrapping the buffers
   in Vue reactivity.

The context also exposes `ctx.data.useSignals` and `ctx.data.availableSignals`. The built-in
chart currently calls the core composable directly, and `useSignals` is typed as `unknown` in
the SDK. Treat the context API as an incomplete transition seam until its return type is
useful and built-in widgets consume it.

## Widget layout behavior

The dashboard still uses `grid-layout-plus`. Widget types are open strings rather than a
closed enum. A registered widget contribution supplies its component and default dimensions;
unknown types use generic dimensions if a new widget is created from imported data.

The saved `dashboard-widgets` localStorage value is still a bare array. Loading retains
unknown widget records, and layout import accepts unknown string types and preserves their
configuration. If a type is unavailable, the placeholder displays its type while leaving the
saved record intact. A versioned workspace file, tab persistence, and dockview are later
workspace work; they are not implemented by these registries.

## Extension rules and current limits

- Feature code should import the SDK, `core`, and files inside its own feature. Do not import
  another feature. The ESLint config blocks common cross-feature alias paths; this is a
  development guardrail, not a runtime security boundary.
- Register UI through `ctx` and return cleanup functions for registrations. Avoid adding
  feature-specific imports to `NavBar.vue`, `DashboardGrid.vue`, or `App.vue`.
- Do not give feature code the generic Electron IPC channel. The preload exposes grouped
  `backend`, `files`, and `daq` methods; `ctx.electron` currently exposes only `openFile`.
- Built-in feature discovery is eager and bundled. There is no install/enable/disable flow,
  external UI loader, backend plugin loader, API compatibility gate, or plugin safe mode yet.
- `views` is part of the SDK and has a registry, but the shell does not currently host
  registered views. `manifest` types are also preparatory and are not consumed at runtime.
- `ctx.electron.openFile` is a narrow API surface, not per-plugin permission enforcement.
  External plugins remain future work and require their own lifecycle and security design.

## Development and checks

From the repository root:

```bash
npm install
uv sync --project apps/visualizer
npm run dev
```

Run dashboard checks from the repository root:

```bash
npm run type-check
npm run lint
npm run test:unit
npm run test:e2e
npm run build
```

The Playwright browser smoke server starts Vite without launching Electron. To run only
Chromium locally, use `npm run test:e2e -- --project=chromium` from this directory.
