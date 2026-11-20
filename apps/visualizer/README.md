# WolfTrack Visualizer (backend)

FastAPI backend for the WolfTrack dashboard. Reads CAN data from a `.blf` log file
(indexed into SQLite) or live from the DAQ over ZeroMQ, decodes it with a DBC via
`cantools`, and serves it over REST and a WebSocket. Packaged into a single
executable with PyInstaller and spawned by the Electron app on a dynamic port.

## Commands

```bash
uv sync                      # install dependencies (Python 3.12)
uv run pytest                # run tests
uv run python src/app.py     # run the backend (prints WOLFTRACK_WS_PORT=<port>)
```

`WOLFTRACK_USER_DATA` is the data directory (DBCs in `dbc/`, `.wts` files in
`wts/`, uploaded logs in `logs/uploads/`, index caches in `logs/cache/`).

Packaging check (run when you add imports or modules):

```bash
uv run pyinstaller --name wolftrack-visualizer --onefile --noconfirm --clean --paths src src/app.py
```

The repository-wide conventions and the active WolfTrack Signals (WTS) initiative
are documented in the monorepo root [`AGENTS.md`](../../AGENTS.md) and
[`docs/wts/`](../../docs/wts/).
