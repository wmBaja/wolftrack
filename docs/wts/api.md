# WolfTrack Signals API (contract)

Frozen at Part 2 (2026-11-20). All errors use FastAPI's `{"detail": ...}`.
Validation failures (422): `detail: {"errors": [{signal, code, message}], "warnings": [...]}`.
All changes are additive: an older dashboard must keep working against this
backend (I7).

## Setup files (`.dbc` + `.wts` managed together)

| Method & path | Purpose | Request | Response |
| :-- | :-- | :-- | :-- |
| `GET /api/dbc` | List setups | – | `{available: [{name,size,mtime,type:"dbc"\|"wts"}], active}` |
| `POST /api/dbc/upload` | Upload `.dbc` or `.wts` | multipart `file` | `{status,message}`; 400 invalid (fully parsed before disk write), 409 name collision |
| `POST /api/dbc/select` | Select setup | form `filename` | `{status,message}`; also re-indexes the active log when the DBC changed |
| `PATCH /api/dbc/{filename}` | Rename | `{new_name}` | `{status,old_name,new_name}`; extension must match (400 otherwise), 409 when the target exists |
| `DELETE /api/dbc/{filename}` | Delete | – | `{status,message}`; also removes the `.bak` sidecar |
| `GET /api/dbc/{filename}/download` | Export file | – | bytes + `Content-Disposition: attachment` |

`GET /api/config` `dbc_file` is the absolute path of the active setup file
(`.dbc` or `.wts`), or `null`.

## Signals

`GET /api/signals` → `{signals: [...]}`. Raw entries keep their historic
fields (`id,node,message,name,unit`). Virtual entries add:

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
  "inputs": ["Brakes.Front_Psi", "WTS.Brake_Total"],
  "operations": [{"type": "combine", "operator": "divide"}],
  "broken": false,
  "broken_reason": null
}
```

Both kinds merge optional `display_name`, `description`, `min`, `max` from
`signal_info` (precedence: `signal_info` > virtual signal's own fields > DBC).

## WTS

| Method & path | Purpose | Request | Response |
| :-- | :-- | :-- | :-- |
| `GET /api/wts/operations` | Op catalog (D15) | – | `{operations: [{type,label,is_head,params:[ParamSpec]}], combine_operators: ["add","subtract","multiply","divide"]}` |
| `GET /api/wts/signals` | Definitions in the active file | – | `{signals: [def + broken + def_hash], issues: [{signal,code,message,severity}], wts_version}` |
| `PUT /api/wts/signals/{name}` | Create or update | `{definition}` (`name` must match path) | `{signal, def_hash, wts_version, promoted_to}`; 422 `{errors, warnings}` |
| `PUT /api/wts/signals/{name}/rename` | Rename (rewrites dependent inputs + `signal_info`) | `{new_name}` | `{signal, def_hash, wts_version, renamed_from, dependents}`; 400 invalid, 409 collision, 404 unknown |
| `DELETE /api/wts/signals/{name}` | Delete | – | `{wts_version}`; 409 `{dependents:[...]}`; 404 unknown |

`promoted_to` is non-null when saving against a legacy `.dbc` first created
`wts/<stem>.wts` (D3); the dashboard should refresh the file list and show a
notice. `def_hash` covers compute-affecting fields plus upstream hashes
(D8) — cosmetic edits (`unit`/`category`/`description`) keep it stable.

`ParamSpec` JSON: `{name, type: "float"|"int"|"string"|"enum"|"bool", default,
required, min, max, choices, unit, help}`. Head operations additionally
carry `min_inputs`/`max_inputs`.

## Log mode (Part 3)

| Endpoint | Addition |
| :-- | :-- |
| `GET /api/logfile/status` | adds `derived: {status: "idle"\|"computing"\|"ready"\|"error", progress: 0-100, pending: [ids]}` |
| `POST /api/logfile/query` | response adds `pending: [ids]`; ids still computing return empty arrays |

## Live mode (Part 4)

`live_batch` WebSocket messages may carry the additive field
`"clock_step": true` (stream clock jumped backward more than the gap limit;
the frontend must clear all live buffers — uPlot needs ascending x).

## Status semantics

- `broken: true` definitions load with the file, are excluded from
  computation, and appear in `issues` with a reason. One bad signal never
  stops a file from opening.
- `issues` items: `{signal, code, message, severity: "error"|"warning"}`;
  `signal_info` entries for unknown ids are warnings.
- `wts_version` increases on every signal/DBC/active-file change; the live
  runtime polls it for hot reload.
