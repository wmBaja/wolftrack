# Part 2: `.wts` File, Persistence, and API

**Area:** apps/visualizer · **Depends on:** Part 1 · **Size:** L

## Goal

Load, validate, save, import, and export `.wts` files; make `DBCManager` manage them alongside legacy `.dbc` files; expose virtual signals through `/api/signals`; add a minimal CRUD API. After this part the **API contract is frozen** so the dashboard (Part 5) can build against a mock.

No values are computed here. This part touches neither `LogQueryService` nor the live loop except the hook stub in 2.8.

## Current code to know

- `src/dbc_manager.py` (133 lines): `dbc_dir = <WOLFTRACK_USER_DATA>/dbc`; `_get_dbc_path()` rejects anything that is not a plain `*.dbc` filename; `select_dbc()` loads via `cantools.database.load_file`; `get_signals()` returns `{id, node, message, name, unit}` per sender node.
- Rename/delete act on a single file. A single-file `.wts` means no sidecar to keep in sync.
- `src/api/routes.py`: `/api/dbc` returns `{available: [{name,size,mtime}], active}`. `upload_config` sets `config.pipeline.dbc_file = <base>/dbc/<active>`. That field is informational on the backend, but the dashboard checks that it is truthy before fetching signals, so for `.wts` set it to the real path of the active setup file.
- `PipelineManager` and `LogFileDataSource` receive the cantools `db` object, not a filename.

## Design

### New modules

```
src/wts/wts_file.py   # WtsFile dataclass; parse/serialize; dbc_text; dbc_hash; from_dbc_bytes; atomic_write; limits
```

`WtsFile` holds: `name`, `dbc_filename`, `dbc_encoding`, `dbc_lines`, `signals: list[VirtualSignalDef]`, `signal_info: dict`, `extras: dict` (unknown top-level keys), `source_path`, `is_legacy_dbc: bool`.

### DBCManager changes

- **Directories:** legacy `.dbc` stays in `<user_data>/dbc/`; `.wts` lives in new `<user_data>/wts/`. `get_available_dbcs()` returns both with an additive `"type": "dbc" | "wts"`.
- **Filename validation:** accept `.dbc` or `.wts`, routed to the right directory; keep every existing traversal check. Rename must preserve the extension (changing it is a 400).
- **Active setup:** keep `active_dbc_filename` (same meaning) and add `active_wts: WtsFile | None`. For a legacy `.dbc` this is an ephemeral `WtsFile(is_legacy_dbc=True)` with no signals. `get_active_dbc()` is unchanged in contract (cantools DB; `load_string` for `.wts`, `load_file` for `.dbc`).
- **New accessors:** `get_active_dbc_hash()`, `get_virtual_signals()` (valid ones), `get_wts_version()` (int incremented on any signal/DBC/active-file change; the live runtime polls it to hot-reload, Part 4), `get_active_setup_path()`.
- **Mutations** (`upsert_virtual_signal`, `delete_virtual_signal`) validate, update memory, write atomically, bump the version. If the active setup is a legacy `.dbc`, **promote first** (D3): create `wts/<stem>.wts` (suffix `-1`, `-2`, ... on collision), select it, then apply. Never modify the original `.dbc`.
- **Upload:** `.dbc` as today. `.wts` is fully parsed and validated before anything is written (5 MB cap, JSON, schema, DBC loads in cantools, limits). Name collision $\Rightarrow$ 409; never overwrite silently. First-uploaded-file auto-select behavior applies to `.wts` too.
- **Delete/rename of the active file** keep existing behavior.
- Selecting a setup with broken definitions succeeds; broken ones are flagged.

### Validation and "broken" definitions

`validate_definitions(defs, dbc_signal_ids)` $\Rightarrow$ `(valid_defs, issues)`, issue = `{signal, severity, code, message}`. A definition is **broken** (kept in the file, excluded from computation, returned with `broken: true, broken_reason`) when an input id is absent from both the DBC and other valid definitions, an op type is unknown, or it depends on a broken definition. Hard errors (cycle, invalid params, duplicate name, limit exceeded, `kind != "continuous"`) reject an API write with 422; on file *load* they mark the definition broken instead of failing the whole file.

### `/api/signals` output

Both raw and virtual entries merge optional `display_name`, `description`, `min`, `max` from `signal_info` (precedence: `signal_info` > virtual signal's own fields > DBC). Virtual entries map `definition.category` to `"message"` so `SignalTree.vue` groups them under node `"WT Signals"` without special tree logic, while also including `"category"` explicitly:

```json
{
  "id": "WTS.Front_Brake_Bias",
  "node": "WT Signals",
  "message": "Brakes",
  "category": "Brakes",
  "name": "Front_Brake_Bias",
  "unit": "%",
  "is_virtual": true,
  "kind": "continuous",
  "description": "Front share of total brake pressure",
  "inputs": ["Brakes.Front_Psi", "Brakes.Rear_Psi"],
  "operations": [{ "type": "combine", "operator": "divide" }],
  "broken": false,
  "broken_reason": null
}
```

Old clients ignore unknown fields (I7).

## API contract

Errors use FastAPI's `{"detail": ...}`. Validation failures (422): `detail: {"errors": [{signal, code, message}], "warnings": [...]}`.

| Method & path | Purpose | Request | Response |
| :-- | :-- | :-- | :-- |
| `GET /api/dbc` | List setups | n/a | `{available: [{name,size,mtime,type}], active}` |
| `POST /api/dbc/upload` | Upload `.dbc` or `.wts` | multipart `file` | `{status, message}`; 400 invalid, 409 `.wts` name collision |
| `POST /api/dbc/select` | Select setup | form `filename` | as today; also re-indexes the active log (Part 3) |
| `PATCH /api/dbc/{filename}` | Rename | `{new_name}` | as today; extension must match |
| `DELETE /api/dbc/{filename}` | Delete | n/a | as today |
| `GET /api/dbc/{filename}/download` | Export file | n/a | bytes, `Content-Disposition: attachment` |
| `GET /api/signals` | Raw + virtual signals | n/a | `{signals: [...]}` |
| `GET /api/wts/operations` | Op catalog (D15) | n/a | `{operations: [{type,label,is_head,params:[ParamSpec]}], combine_operators: [...]}` |
| `GET /api/wts/signals` | Definitions in the active file | n/a | `{signals: [def + broken flags], issues: [...], wts_version}` |
| `PUT /api/wts/signals/{name}` | Create or update | `{definition}` (`name` must match path) | `{signal, def_hash, wts_version, promoted_to: str\|null}`; 422 on errors |
| `DELETE /api/wts/signals/{name}` | Delete | n/a | `{wts_version}`; **409** `{dependents: [...]}` if others depend on it |

`promoted_to` tells the frontend a legacy `.dbc` was wrapped so it can refresh the file list and show a notice. After any mutation the route calls the hook stub (2.8).

Not in this scope: dry-run validate endpoint, preview endpoint, signal-info write endpoints. (`PUT` already returns full validation errors; `signal_info` is hand-edited in the file.)

## Tasks

- [x] 2.1 `wts_file.py`: parse/serialize, canonical key order, `extras` preservation, DBC encoding handling, hash.
- [x] 2.2 DBC round-trip: decode bytes (`utf-8`, else `cp1252`, record which), normalize line endings, split to lines. **Test** `load_file(original)` vs `load_string(embedded)` produce identical messages/signals for `dbc/stig25(1).dbc`.
- [x] 2.3 Atomic write + `.bak`.
- [x] 2.4 `DBCManager`: dual directories, `type`, validation, `active_wts`, promotion, accessors, version.
- [x] 2.5 Mutations + validation (uses Part 1 `schema`/`graph`; `signal_info` unknown ids $\Rightarrow$ warnings).
- [x] 2.6 Routes (new `src/api/wts_routes.py` with its own `APIRouter`, registered in `app.py`), download route, `/api/signals` extension (merging `signal_info` onto both raw and virtual signals), `/api/wts/operations` from `describe_all()`.
- [x] 2.7 Set `config.pipeline.dbc_file` to `get_active_setup_path()` in `upload_config` and rename routes.
- [x] 2.8 Hook stub `on_wts_changed(changed_ids)` called after any mutation/select/DBC change (Part 3 implements the log-side recompute; Part 4 needs no hook because the live runtime polls `get_wts_version()`; here it is a no-op with a test that it is called).
- [x] 2.9 Write `docs/wts/api.md` from the table above and keep it in sync.

## Tests

- Round-trip parse $\rightarrow$ serialize $\rightarrow$ parse equality; unknown top-level keys preserved; key order stable (golden file) (I5).
- Rejections: path traversal in names, oversize file, bad JSON, `version` too new, unknown op type (422), cycle, duplicate name, $> 200$ signals, $> 16$ ops, `kind: "event"` (422 "not supported yet") (I6).
- Broken-on-load: a file with one bad input id opens; that signal is flagged; others work.
- Promotion: legacy `.dbc` + first PUT $\Rightarrow$ new `.wts`, original `.dbc` byte-identical, active switched, `promoted_to` set.
- Delete with dependents $\Rightarrow$ 409 listing them.
- Atomicity: monkeypatch `os.replace` to fail; original file intact.
- Rename/delete `.wts`; extension change rejected.
- `TestClient` contract tests for every endpoint; `GET /api/dbc` and `GET /api/signals` still valid for a legacy-only setup (I7), and `signal_info` overrides work for both raw and virtual signal ids.
- Existing tests unchanged and green.

## Acceptance criteria

- With a `.dbc` active, `PUT /api/wts/signals/Bias_Test` creates a `.wts`, and `GET /api/signals` lists `WTS.Bias_Test` under node `WT Signals`.
- Exporting then re-uploading the `.wts` under another name gives an identical signal list.
- The contract in this file is implemented exactly; deviations update this doc in the same PR.

## Gotchas

- `cantools.database.load_string` needs `database_format="dbc"`.
- Signal ids contain dots; virtual signal routes use `name` (no dots by the name regex).
- Never keep a stale `WtsFile` after a mutation; the manager's in-memory copy is the source of truth until the next atomic write.