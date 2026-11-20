# WTS log path (Part 3): derived virtual signals over SQLite

How virtual signals are computed and served for `.blf` logs.

## Cache key and raw index

`{basename}_{size}_{mtime}_{dbc_hash8}.sqlite` — the first 8 hex chars of the
active setup's DBC hash (`nodbc` when none). Because the DBC is part of the
key:

- switching DBCs on the same log can never serve stale or missing signals;
- switching **back** to an indexed (log, DBC) pair is a cache hit — the BLF
  is not re-parsed;
- promoting a legacy `.dbc` to a `.wts` keeps the same DBC text, so the hash
  (and therefore the index) is unchanged.

The raw `signals` table is written once and **never modified** afterwards
(I3). `/api/dbc/select` (and first-upload auto-select, and delete of the
active file) re-index the configured log so the index always matches the
active setup — previously it silently went stale.

## Derived storage

Same SQLite file, separate tables (created lazily on older caches):

```sql
derived_signals(timestamp REAL, signal_id TEXT, value REAL)  -- + index
derived_meta(signal_id TEXT PRIMARY KEY, def_hash TEXT, row_count INT, computed_at REAL)
```

A virtual signal is **fresh** iff `derived_meta.def_hash` equals its current
`def_hash` (which includes every upstream definition's hash, so editing
`WTS.A` invalidates `WTS.B` but editing `unit`/`category`/`description` does
not invalidate anything, D8).

## Compute post-pass (D9)

One path for first index and later edits: a worker thread with its own
connection (`WAL`, `timeout=30`, closed via `contextlib.closing`) over
**full-resolution** raw rows:

1. stale = hash mismatch or missing meta; removed = meta without a definition;
2. minimal subgraph via `subgraph_defs` (targets + WTS ancestors) — fresh
   unrelated signals sharing raw inputs are not re-evaluated;
3. one cursor per required raw id, `ORDER BY timestamp` (index-backed),
   `heapq.merge`d into `(ts, id, value)` rows, fed to the shared `run_batch`
   helper — identical to the live path by construction (I1);
4. output rows go to a connection-scoped `TEMP` staging table, then one
   transaction per signal swaps them into `derived_signals` + `derived_meta`:
   readers never see a half-computed signal, old values stay visible until
   the swap;
5. `removed` ids get rows + meta deleted; cancellation between batches keeps
   the previous rows intact;
6. rapid edits are debounced ~300 ms; if definitions change mid-compute the
   job re-runs with the latest.

## Status and query

- `get_status().derived = {status: idle|computing|ready|error, progress,
  pending:[ids]}`. Raw `status` reaches `ready` independently — raw charts
  never wait for derived compute, and raw queries are not blocked behind it
  (separate connections).
- `/api/logfile/query` routes `WTS.*` ids to `derived_signals` (same bucket
  SQL) and returns `{data, pending}`; pending ids get empty arrays and the
  frontend shows "calculating…" and retries with backoff.
- `_state_lock` is held only long enough to grab the connection reference,
  never across SQL execution.

## CSV/XLSX export (Q6)

Exports append `derived_signals` rows (`signal_name = WTS.<name>`, unit from
the definition), interleaved by timestamp. While derived compute is running
the export returns **409** rather than a partial export. With no virtual
signals the export is byte-identical to before.

## Known limitation

Timestamps are absolute UTC epoch seconds from the DAQ's RTC. Rows are read
`ORDER BY timestamp`, so if the DAQ clock stepped **backward during a
recording**, rows around the step interleave and a stateful filter sees the
step as out-of-order input (its samples are skipped, never reordered). This
is a pre-existing property of raw indexing, not something this part repairs.
