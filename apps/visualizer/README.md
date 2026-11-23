# Backend architecture and API contract

## Request and telemetry flow

`app.py` owns process setup, CORS, authentication, lifecycle startup and the explicit router list. Feature HTTP routes live in `api/`; shared serialization and export helpers live in `api/common.py`. The router list is explicit so PyInstaller can discover every module.

`core/pipeline/manager.py` reads frames from a configured `DataSource`, decodes frames with the active DBC supplied by `core/dbc_manager.py`, and sends batches through `core/ws_manager.py`. The WebSocket manager owns each connection's subscribed signal set and live window. The pipeline decodes the union of subscribed signals; the manager filters each batch to each client's signal set and removes connection state at disconnect.

The processor classes in `core/pipeline/processor.py` remain unwired and are not part of the live data flow. The log query index is managed separately by `core/pipeline/log_query.py`.

## API authentication and versioning

Electron creates a cryptographically random token for each launch and passes it as `WOLFTRACK_AUTH_TOKEN`. Renderer HTTP requests send it as a Bearer token; `/ws/stream` receives it as the `token` query parameter. A directly launched backend creates a private random token when the environment variable is absent, so authenticated clients must be launched by Electron or given that token by the host process. Test clients can provide a fixed token to `BackendSecurityMiddleware`.

The default bind address is loopback (`FASTAPI_HOST=127.0.0.1`). Non-loopback binding requires the explicit `WOLFTRACK_ALLOW_REMOTE_BINDING=true` override. The Host header must resolve to loopback unless that override is set. CORS permits the packaged `null`/`file://` origins and the development server at port 3000; WebSocket origins are checked against the same set.

`GET /api/version` returns the application version and `visualizerApi` semver. The API version describes the backend contract used by plugins: additive compatible changes increment the minor version, and any breaking contract change increments the major version. The app version tracks the dashboard release version.

## Launch and packaging

The backend remains launchable as `uv run python src/app.py` and as the PyInstaller executable. Electron reads only `WOLFTRACK_WS_PORT=<n>` from stdout for startup discovery; keep that marker unchanged. The packaged backend uses `--onedir`: on this Linux development host, three launches reached the authenticated API in a median 0.584 s, compared with 0.811 s for `--onefile`. The installer bundles the directory contents under `resources/backend/`.
