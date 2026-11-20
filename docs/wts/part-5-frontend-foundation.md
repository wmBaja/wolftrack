# Part 5: Frontend Foundation

**Area:** apps/dashboard · **Depends on:** Part 2 (build against a mock), Parts 3-4 (real data) · **Size:** M

## Goal

The dashboard understands `.wts` files and virtual signals: the file manager handles both file types, the signal tree shows virtual signals, charts display them in log and live mode, and edits made through the API refresh correctly. **No authoring UI here** (Part 6), and nothing beyond what is listed: a separate plugin roadmap owns richer UI.

## Current code to know

- `src/stores/dbcStore.ts`: `DbcSignal {id,node,message,name,unit}`, file CRUD against `/api/dbc/*`, `isValidDbcFilename` (regex `^[^/\\]+\.dbc$`).
- `src/stores/dataSourceStore.ts` **also** keeps a `dbcSignals` list fetched from `/api/signals`. Two copies of the signal list exist; both must refresh after WTS changes (or be consolidated, task 5.2).
- `src/components/FileManagerPanel.vue` (~970 lines): "logs" and "dbc" tabs; upload, select, rename, bulk delete, all keyed to `.dbc`.
- `src/components/SignalTree.vue`: builds node $\rightarrow$ message $\rightarrow$ signal from `props.signals`; virtual signals with `node: "WT Signals"` and `message: <category>` group automatically.
- `src/lib/chartData.ts` `buildChartRenderModel` takes unit/label from signal metadata, so virtual signals chart without changes once they are in the list.
- `src/stores/logDataStore.ts`: `overviewBuffers` / `detailBuffers` keyed by signal id; `requestOverviewData` only fetches ids missing from `overviewBuffers`; status polled via `/api/logfile/status`.
- `src/stores/liveDataStore.ts`: non-reactive `RingBuffer` per signal id (capacity 10,000), trimmed by time window when `source === 'zmq'`; `setSubscribedSignals` already sends subscriptions over the WebSocket.
- `src/stores/widgetStore.ts`: widgets persist `signals: string[]` in `localStorage` (`dashboard-widgets`), so a widget can reference a signal that no longer exists.
- Backend URLs come from `getVisualizerBase()`; never hardcode a port.
- Dashboard CI downloads the backend's `nightly` build. Only rely on backend features already merged to `dev`.

## Tasks

- [ ] **5.1 Types.** Extend `DbcSignal` with optional `is_virtual`, `kind`, `category`, `description`, `inputs`, `operations`, `broken`, `broken_reason`, `display_name`, `min`, `max`. Add `src/types/wts.ts`: `VirtualSignalDefinition`, `OperationDef`, `OperationCatalog` (including `is_head: boolean` on operation entries), `ParamSpec`.
- [ ] **5.2 One signal list.** Make `dbcStore.signals` the single source; have `dataSourceStore.dbcSignals` read from it or delete the duplicate fetch. Check every consumer first (`grep -rn dbcSignals src`).
- [ ] **5.3 `wtsStore.ts`** (new Pinia setup store): state `definitions`, `catalog`, `wtsVersion`, `isSaving`, `error`; actions `fetchCatalog`, `fetchDefinitions`, `save(def)` (`PUT /api/wts/signals/{name}`), `remove(name)` (`DELETE`; surface `dependents` on 409). Call `fetchCatalog()` when connecting to the backend and `fetchDefinitions()` whenever the active setup loads or changes. After save/delete: refetch `/api/signals` and `fetchDefinitions()`, run the refresh in 5.6, and if the response has `promoted_to`, update the active filename and file list in `dbcStore` (via `GET /api/dbc`, **without** triggering a redundant log re-index from the frontend) and show a one-line notice.
- [ ] **5.4 File manager.** Show `.dbc` and `.wts` together with a small type badge (missing `type` $\Rightarrow$ `"dbc"` for older backends); upload accepts `.dbc,.wts`; `isValidDbcFilename` becomes `isValidSetupFilename` accepting both and rename keeps the extension; an "Export" action on `.wts` rows downloads via `GET /api/dbc/{name}/download` using the same fetch $\rightarrow$ blob $\rightarrow$ anchor pattern as `ExportPanel.vue`. Show backend 409/422 messages verbatim in the existing error area.
- [ ] **5.5 Signal tree.** Render virtual signals normally; mark `is_virtual` with a subtle badge, show a warning icon with tooltip for `broken`, and use `display_name`/`description` (from `signal_info`) in the tooltip when present. No create/edit controls here.
- [ ] **5.6 Refresh on change.** For the edited or deleted signal and its dependents (computed from loaded definitions):
  - *Log mode:* delete its entries from `logDataStore.overviewBuffers`, `detailBuffers`, `detailSignalIds`, then re-request. While `/api/logfile/status` reports `derived.status === "computing"` or the query response lists the id in `pending`, show "calculating…" and retry with short backoff. Store the retry timer ID / abort controller in `logDataStore` and cancel it when switching logs, switching setups, or resetting the store so orphaned timers never leak. Extend the `LogStatus` type with the optional `derived` block.
  - *Live mode:* add `liveDataStore.clearSignal(id)` (delete the `RingBuffer`, bump `dataVersion`) so old-definition data is never mixed with new; re-send the subscription.
- [ ] **5.7 Clock step.** When a `live_batch` carries `clock_step: true`, clear **all** live buffers (raw and virtual; uPlot needs ascending x and a backward clock step from a DAQ reboot or looped replay breaks that for raw signals too) and reset sample-rate stats. Older backends never send the flag.
- [ ] **5.8 Missing signals.** If a widget references an id absent from `dbcStore.signals`, `ChartWidget` shows it greyed with a "missing signal" label and a one-click remove; never crash `buildChartRenderModel` and never request it from the backend. Deleting a charted virtual signal must not break the dashboard.
- [ ] **5.9 Calculating state.** Plain "calculating…" text in the chart header while any charted signal is pending. Reuse existing styling.
- [ ] **5.10 Tests** (Vitest in `src/stores/__tests__/` and `src/lib/__tests__/`): `wtsStore` actions with mocked `fetch` (success, 422 with errors, 409 with dependents, promotion without redundant re-index); buffer invalidation and polling timer cleanup in log and live; `clock_step` handling; `chartData` with virtual-signal metadata; missing-signal path; filename validation; older-backend shapes (no `type`, no `derived`, no `kind`).
- [ ] **5.11** Run `npm run type-check`, `npm run lint`, `npm run test:unit -- --run`; fix what you introduce.

## Acceptance criteria

- With a `.wts` loaded in the backend: virtual signals appear under "WT Signals", can be added to a chart, and plot in **both log and live mode**.
- Uploading, exporting, renaming, and deleting `.wts` files works and the list stays in sync with the backend.
- Editing a definition via curl then refreshing the chart shows new data with no stale points.
- Deleting a charted virtual signal leaves the dashboard functional with a clear "missing signal" indicator.
- Type-check, lint, and unit tests pass.

## Gotchas

- Do not put `RingBuffer`s or sample arrays into reactive state; keep the non-reactive pattern and use `dataVersion`.
- uPlot needs strictly ascending x values; the backend guarantees this per virtual signal (I8). `uPlot.join` is already used for multi-series.
- The `localStorage` widget layout is user data; never migrate or rewrite it beyond the missing-signal UI.
- Keep the diff in `FileManagerPanel.vue` small; if a change needs more than a few dozen lines, extract a component instead of growing it.