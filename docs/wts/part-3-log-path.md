# Part 3: Log-File Path (SQLite Derived Signals)

**Area:** apps/visualizer · **Depends on:** Part 2 · **Size:** L

## Goal

Virtual signals are queryable from `.blf` logs through the existing `/api/logfile/query` endpoint, computed once on full-resolution data, cached safely, and recomputed only when a definition's compute-affecting fields (or anything upstream of it) change. A WTS edit never re-parses the `.blf`.

Read [00-architecture.md](00-architecture.md) D7-D9 and invariants I1, I3, I4 first.

## Current code to know (`src/pipeline/log_query.py`)

- Cache key is `{basename}_{size}_{mtime}.sqlite`. It ignores the DBC, so switching DBCs on the same log serves stale or missing signals.
- `_index_worker` decodes the `.blf` with python-can into `signals(timestamp REAL, signal_id TEXT, value REAL)`, creates `idx_sig_time(signal_id, timestamp)`, then publishes by `os.replace` of a `.partial` file. A cached file short-circuits to `ready`.
- `query()` holds `_state_lock` for the whole query and buckets with `GROUP BY CAST((timestamp - start) / bucket AS INTEGER)`, taking `MIN(timestamp), value` per bucket (SQLite returns the `value` from the row holding the min).
- Jobs are cancelled via `_active_job` / `_cancel_event` tokens. Reuse that pattern.
- `/api/dbc/select` swaps `pipeline_manager.source.db` but **does not re-index the log**, so the index goes stale after a DBC switch (existing bug; fixed here).
- `tests/test_log_query_service.py` hardcodes the cache-key format and calls `start_indexing(..., dbc=None)`.

## Design

### Cache key and raw index

`{basename}_{size}_{mtime}_{dbc_hash8}.sqlite`, where `dbc_hash8` is the first 8 hex chars of `DBCManager.get_active_dbc_hash()` (`nodbc` when none). `start_indexing(log_file, dbc, dbc_hash=None)`. The raw `signals` table is written once and never modified afterwards (I3).

### Derived storage (same file, separate tables)

```sql
CREATE TABLE IF NOT EXISTS derived_signals (timestamp REAL, signal_id TEXT, value REAL);
CREATE INDEX IF NOT EXISTS idx_derived_sig_time ON derived_signals(signal_id, timestamp);
CREATE TABLE IF NOT EXISTS derived_meta (
  signal_id   TEXT PRIMARY KEY,
  def_hash    TEXT NOT NULL,
  row_count   INTEGER NOT NULL,
  computed_at REAL NOT NULL
);
```

A virtual signal is **fresh** iff `derived_meta.def_hash` equals its current `def_hash` (which includes upstream definitions, so editing `WTS.A` invalidates `WTS.B` that depends on it, while editing cosmetic fields like `unit`, `category`, or `description` leaves `def_hash` unchanged). Opening a cached file that lacks these tables must work (create them lazily).

### Post-pass compute (`compute_virtual_signals`)

Runs in a worker thread with its **own** SQLite connection (WAL, `timeout=30`, wrapped in `contextlib.closing` so file handles never leak on Windows) and never holds `_state_lock` during the heavy loop.

1. Determine `stale` = ids whose meta is missing or mismatched; `removed` = meta ids no longer defined. `targets` = `stale` plus their downstream dependents.
2. Build the minimal subgraph of definitions needed to evaluate `targets` using `subgraph_defs(valid_defs, targets)` from Part 1 (`targets` union their transitive `WTS.*` ancestors), and instantiate `engine = VirtualSignalEngine(active_subgraph_defs)` (no `max_gap_seconds`). This ensures fresh unrelated virtual signals that share raw inputs are not needlessly re-evaluated in Python.
3. Inputs = `engine.required_inputs(targets)`.
4. For each raw input id open a cursor `SELECT timestamp, value FROM signals WHERE signal_id=? ORDER BY timestamp` (uses `idx_sig_time`), merge with `heapq.merge` on timestamp into `(ts, id, value)` rows, and feed them to **`run_batch`** from Part 1. Never `fetchall`. (Using the shared helper is what makes the log path equal the live path, I1.)
5. Write outputs for `targets` ids in batches into a connection-scoped temporary table `CREATE TEMP TABLE IF NOT EXISTS temp.derived_staging (timestamp REAL, signal_id TEXT, value REAL)` (cleared at the start of the job); report progress. Using a `TEMP` table avoids double write amplification on the main SQLite file and guarantees automatic cleanup if the connection closes.
6. Finish with one transaction per target signal: delete its old rows from `derived_signals`, `INSERT INTO derived_signals SELECT timestamp, signal_id, value FROM temp.derived_staging WHERE signal_id = ?`, upsert `derived_meta`. Readers never see a half-computed signal; the old values stay visible until the swap.
7. Delete rows and meta for `removed` ids.
8. Honor cancellation between batches; a cancelled job leaves the old derived rows intact. A new edit while computing cancels and restarts with the latest definitions (debounce about 300 ms to coalesce rapid edits).

### Status and query changes (additive)

- `get_status()` keeps its keys and adds `derived: {"status": "idle"|"computing"|"ready"|"error", "progress": 0-100, "pending": [signal ids]}`. Raw status becomes `ready` as soon as the raw index is done; raw charts never wait for derived compute.
- `query()` picks the table by id: `WTS.*` $\Rightarrow$ `derived_signals`, otherwise `signals`. Bucketing SQL unchanged.
- The response gains `pending: [ids]` listing requested virtual signals that are not fresh yet; those ids return empty arrays. The frontend polls status and re-queries (Part 5).
- Take `_state_lock` only long enough to obtain the path/state and open a read connection (closing it cleanly in a `finally` block or `with closing(...)`); do not hold `_state_lock` across SQL execution.

### Re-index triggers

- `/api/dbc/select` (and any change of the active DBC: upload that auto-selects, rename or delete of the active file): if `config.pipeline.source == "logfile"` and a log is configured, call `start_indexing(...)` with the new DBC and hash. The new cache key makes this a cache hit when that log+DBC pair was indexed before (including when a legacy `.dbc` is promoted to `.wts`, since `dbc_hash` is identical).
- WTS mutation (Part 2 `on_wts_changed`): call `compute_virtual_signals(new_defs)` on the already-open index.
- `upload_config` already calls `start_indexing`; pass the new args and run the compute after publish and after opening a cached file.

## Tasks

- [ ] 3.1 `dbc_hash` plumbing and the new cache key; update `tests/test_log_query_service.py` (`dbc=None` $\Rightarrow$ `nodbc`).
- [ ] 3.2 Derived tables, lazy creation on cached files, freshness check.
- [ ] 3.3 `compute_virtual_signals`: subgraph selection, cursor merge into `run_batch`, `TEMP` staging table, atomic swap, cancellation, progress.
- [ ] 3.4 Run compute automatically after raw index publish and after a cached open for all stale definitions.
- [ ] 3.5 `get_status()` `derived` block; `query()` table routing, short lock scope, and `pending`.
- [ ] 3.6 Implement `on_wts_changed` (debounced recompute) and fix `/api/dbc/select` re-indexing.
- [ ] 3.7 Benchmarks and `docs/wts/log.md`.
- [ ] 3.8 **Last, separate PR, easy to drop (Q6):** include virtual signals in the existing CSV export. `_collect_export_rows` re-streams the BLF through `LogFileDataSource`; append rows read from `derived_signals` (`signal_name` = `WTS.<name>`, unit from the definition), sorted by timestamp. If derived is still computing return 409 with a clear message. Existing raw export behavior and tests stay unchanged.

## Tests

- **Delivery independence (I1):** synthetic BLF (Part 0 helper) with same-frame multi-signal messages; run the log path; independently feed the same decoded rows through `run_batch`; assert identical derived rows.
- **No stale cache:** index with DBC A, then DBC B on the same log $\Rightarrow$ different cache files; switching back is a cache hit with no re-parse (monkeypatch the BLF reader and assert it is not called).
- **Edit without re-parse (I3):** after the raw index is ready, PUT a new definition $\Rightarrow$ derived rows appear; the BLF reader is never invoked; raw `signals` is unmodified.
- **Stale across restart:** compute, edit the definition on disk, create a new service on the same cache $\Rightarrow$ hash mismatch triggers recompute and values reflect the new definition.
- **Dependency invalidation & subgraph isolation (I4):** editing `WTS.A` recomputes `WTS.B`; editing an unrelated signal (even one sharing a raw input) does not touch `WTS.B` (check `computed_at`); editing only `unit` or `description` does not recompute.
- **Atomic swap:** a query during recompute returns old complete data, then new complete data, never a mixture (use a hook that pauses mid-compute).
- **Cancellation:** cancelling mid-compute keeps the previous rows; a second compute completes normally.
- **Concurrency:** raw queries during derived compute are not blocked beyond a small bound.
- **Pending semantics:** querying a virtual signal before compute finishes returns empty arrays plus `pending`.
- **Removed definitions:** deleting a signal removes its rows and meta.
- Existing log-query and export tests green (I7).

## Acceptance criteria

- Create a virtual signal on an already-indexed multi-minute log; it is chartable within seconds with no raw re-index.
- Quitting and reopening with an edited `.wts` never shows old derived values.
- Raw query latency is unchanged (compare before/after on the same fixture; record in the PR).
- Full suite green on Linux, Windows, and macOS CI.

## Gotchas

- Keep the existing `MIN(timestamp), value` bucket query as is; it is only correct for continuous signals.
- Set `PRAGMA journal_mode=WAL` on each new connection; close all connections and cursors explicitly (`with closing(sqlite3.connect(...)) as conn:`) on `query()`, worker exit, and `stop()` so no `-wal`/`-shm` files linger and Windows never raises `WinError 32` when cleaning up temporary test directories.
- A long log with several high-rate inputs produces many updates; keep per-update overhead low and insert in batches of 10,000 like the raw index.
- Timestamps are floats in seconds (absolute UTC epoch from the DAQ's RTC; the engine does not care). Rows are read `ORDER BY timestamp`, so if the clock stepped backward during a recording the overlapping rows interleave. That is an existing limitation of raw indexing; do not try to repair it here, but mention it in `docs/wts/log.md`.