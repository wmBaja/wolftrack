# WolfTrack (monorepo)

WolfTrack is an Electron + Vue dashboard plus a FastAPI Python backend for live and
recorded CAN telemetry. This repository merges the former `wolftrack-dashboard`
(`apps/dashboard`) and `wolftrack-visualizer` (`apps/visualizer`) repositories.

## Active initiative: WolfTrack Signals (WTS)

User-defined **virtual signals** (combine, scale, bias, moving average, low-pass)
and the `.wts` file format, for **both `.blf` logs and live DAQ data**. The plan
lives in `docs/wts/`:

- `README.md`: parts, order, status checklist
- `00-architecture.md`: **decisions, file spec, engine semantics, invariants. Read first.**
- `part-N-*.md`: one file per implementation part; `part-7-deferred-roadmap.md` lists what is **not** to be built.

Work on one part at a time. If the plan and the code disagree, trust the code and
update the plan file in the same commit.

## Commands

Backend (from `apps/visualizer`):

```bash
uv sync                      # install dependencies (Python 3.12)
uv run pytest                # backend tests
uv run python src/app.py     # run the backend (prints WOLFTRACK_WS_PORT=<port>)
uv run pyinstaller --name wolftrack-visualizer --onefile --noconfirm --clean --paths src src/app.py
```

Frontend (from the repository root):

```bash
npm install
npm run dev                  # Electron + Vite dev
npm run type-check
npm run lint
npm run test:unit -- --run   # Vitest single run (via workspace script)
```

Environment: `WOLFTRACK_USER_DATA` is the backend data directory (DBCs in `dbc/`,
`.wts` files in `wts/`, uploaded logs in `logs/uploads/`, index caches in
`logs/cache/`). Tests must point it at a temporary directory.

## Backend conventions

- Source in `apps/visualizer/src/` imports **as top-level modules**
  (`from config import AppConfig`), never `from src.x import y`.
- Python 3.12. Type hints on public functions.
- Logging: `from logging_config import get_logger`. No `print` (except the one
  port line in `app.py`). No logging inside hot loops except rate-limited.
- API routes live in `src/api/`; register new routers in `app.py`.
- Tests in `apps/visualizer/tests/` (pytest, plain functions + fixtures; helpers in
  `tests/helpers/` build synthetic DBCs/BLFs). Mock `fetch`/network in unit tests.
- No new runtime dependencies without asking (PyInstaller binary, CI time).

## Rules for WTS work (hard constraints)

1. **`src/wts/` is pure.** No file I/O, network, SQLite, FastAPI, ZMQ, asyncio,
   wall clock (`time.time`, `datetime.now`), randomness, or mutable globals in the
   engine and ops. A test enforces this. (`src/wts/live.py` may be clock-stateful
   but still performs no I/O and never reads the wall clock.)
2. **Never fabricate data.** Division by zero, NaN, or infinity produce *no
   sample*, not 0 or a clamped number.
3. **Parity.** Live and log paths must produce identical virtual-signal output for
   identical input (one engine; equal-timestamp rows grouped into one `update`).
4. **Never block the asyncio event loop.** Log computation runs in a worker thread
   with its own SQLite connection (`contextlib.closing` everywhere).
5. **The raw `signals` table is immutable after publish.** Derived data lives in
   `derived_signals` / `derived_meta`, staged via a connection-scoped `TEMP` table.
6. **No user code execution.** Operations come from the typed registry only. Never
   `eval`/`exec`/`pickle` anything from a `.wts` or API payload.
7. **Validate untrusted input.** `.wts` uploads and API bodies: size caps, schema
   validation, filename traversal checks, reject unknown op types.
8. **API changes are additive.** Older dashboards must keep working.
9. **Atomic file writes** for anything under the user data directory (tmp + `os.replace`).
10. **Preserve unknown top-level keys** when reading and rewriting `.wts` files.
11. **Time.** DAQ timestamps are UTC epoch seconds from an RTC and the stream clock
    can step mid-session. Never use the backend wall clock for virtual-signal
    timing; only the live runtime handles clock steps (reset on a large backward step).
12. **No-op when unused.** With no virtual signals defined, the live path decodes
    and emits exactly what it did before.

## Frontend conventions

- Vue 3 `<script setup lang="ts">`; Pinia **setup stores**; alias `@/` → `src/`.
- State/API logic in `src/stores/` or `src/lib/`, not components. Tests in
  `__tests__/` folders next to code, mocking `fetch`.
- Live sample data is **non-reactive**: `RingBuffer`s live in plain `Map`s; bump a
  `dataVersion` ref to invalidate.
- `FileManagerPanel.vue`, `DataSourcePanel.vue`, `LogWindowControl.vue` are large:
  extract components rather than growing them.
- Never hardcode a port/host; use `getVisualizerBase()` / `getVisualizerWsUrl()`.
- The signal editor is catalog-driven (`GET /api/wts/operations`); do not hardcode
  op names/params/units/defaults in components. The backend is the validator.
- uPlot needs strictly ascending x values; on `live_batch.clock_step`, clear all
  live buffers.
- Never silently rewrite user data in `localStorage` (`dashboard-widgets`).
