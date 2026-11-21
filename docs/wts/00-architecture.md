# 00: Architecture, Decisions, and Invariants (rev 3.1)

Scope: **signal processing for both log files and live DAQ data.** Domain-specific features (GPS, lap timing, event signals and aggregates, maps, plugins) are out of scope. Items marked *(groundwork)* exist so that deferred work (see [part-7-deferred-roadmap.md](part-7-deferred-roadmap.md)) does not force rewrites. Do not build the deferred features themselves.

## 1. Glossary

| Term | Meaning |
| :-- | :-- |
| **WTS file** | A `.wts` JSON file: embedded DBC + virtual signal definitions + signal info. |
| **Virtual signal** | A derived signal defined in a WTS file. Its id is `WTS.<name>`. |
| **Raw signal** | A signal decoded from CAN via the DBC. Id format `Message.Signal`. |
| **Definition** | The JSON object describing one virtual signal (inputs + operations). |
| **Engine** | The pure-Python evaluator that turns timestamped input samples into virtual signal samples. |
| **Update** | One call to `engine.update(ts, values)`: all samples sharing one timestamp (one CAN frame). |
| **Live runtime** | The thin wrapper that feeds frames from the ZMQ stream into an engine and handles reset, hot reload, and clock steps (Part 4). |
| **Derived table** | SQLite table holding computed virtual-signal rows, separate from the immutable raw `signals` table. |
| **Definition hash** | SHA-256 of a definition's canonical compute-affecting JSON (`kind`, `inputs`, `operations`) plus the hashes of every upstream virtual signal it depends on. Cosmetic metadata (`unit`, `category`, `description`) is excluded so metadata edits do not trigger SQLite recomputation. |

## 2. Decisions

**D1. Compute runs in the Python backend, never the frontend.**
Verified in code: `ws_manager.live_window_seconds` is stored but never read by the backend; the only trimming of live data is in the frontend (`liveDataStore.ts`, zmq source only). The backend sees the unbroken stream, so processors keep their own small state independent of any display window. Log mode must also compute on **full-resolution** data: `/api/logfile/query` downsamples by SQL bucketing, and filtering downsampled data would alias.

**D2. Scope is signal processing in both modes, with a small op set.**
Live and log share one engine. Everything domain-specific, plus event signals, plugins, and rich UI, is deferred (Part 7).

**D3. One file type: `.wts`. Legacy `.dbc` keeps working and stays visible.** *(Q5)*
A bare `.dbc` is treated as an ephemeral WTS file with no signals. The first time the user saves a virtual signal against it, the backend **promotes** it: writes `wts/<stem>.wts` embedding the DBC, selects it, and leaves the original `.dbc` untouched. Nobody is forced to migrate.

**D4. Virtual signals are declarative. No user code.**
A shared `.wts` must never execute arbitrary code. Operations come from a registry of typed, parameterized ops.

**D5. Virtual signals may depend on other virtual signals.**
Inputs can be raw ids or `WTS.*` ids. The engine builds a DAG, evaluates in topological order, rejects cycles, caps depth at 16. Built in now because retrofitting is painful, and because it replaces special-purpose ops (e.g. $a/(a+b) \times 100$ = a total signal, then divide, then scale).

**D6. The engine takes whole timestamped updates, not single samples.**
`update(ts, {signal_id: value, ...})`; each affected processor evaluates **once** per update. A per-signal API produced a bogus intermediate sample (measured: 61.5 emitted, then 80.0, at the same timestamp, for true inputs 80 and 20), which also creates duplicate timestamps that break uPlot and the SQL bucketing.

**D7. The engine is mode-agnostic.**
No file, DB, network, asyncio, or wall-clock access. The log path and the live path both group rows with equal timestamp into one `update`, exactly as one CAN frame would be. A delivery-independence test (Part 1) proves output does not depend on how updates are delivered, and Parts 3 and 4 reuse it.

**D8. Raw index is immutable; derived rows live in separate tables with a definition hash.**
Cache key is `{blf}_{size}_{mtime}_{dbc_hash8}.sqlite`. `signals` (raw) is never modified after publish. `derived_signals` + `derived_meta(signal_id, def_hash, ...)` hold virtual rows. Any definition whose hash does not match is recomputed on open. Edits never trigger a `.blf` re-parse and a stale cache can never serve outdated derived values. Because `def_hash` excludes `unit`, `category`, and `description`, cosmetic edits are instantaneous.

**D9. One compute path for log derived signals: a post-pass over SQLite**, not inline in the BLF decode loop. Same code for first index and edit-after-index.

**D10. `kind` is reserved in the schema; only `"continuous"` is accepted.** *(groundwork for event signals)*
Definitions may carry `kind: "continuous"` (default). Any other value is rejected with a clear "not supported yet" error, never silently treated as continuous.

**D11. Time is UTC epoch seconds from the DAQ's RTC, and the stream clock can step.** *(Q1)*
While the RPi does not sync NTP mid-run on track, timestamps can still jump **backward or forward during a live session** if the DAQ reboots/browns out without the ZMQ subscriber disconnecting, if an RTC coin-cell glitches, or when developers replay a looped capture stream. Rules:
- The engine treats timestamps as opaque monotonic floats (float64 epoch seconds resolve about $0.2\ \mu\text{s}$; no unit conversion, no offset subtraction). It skips non-increasing timestamps (counted, never reordered), supports `notify_gap(ts)`, and has an opt-in `max_gap_seconds` (default off) that stateful ops respond to.
- The **live runtime** owns clock-step handling (Part 4): a backward jump larger than `max_gap_seconds` resets the engine, because otherwise the monotonic rule would freeze every virtual signal until time catches up. Small backward deltas are out-of-order jitter and are skipped.
- Time-based ops use **seconds**, never sample counts, so live and log agree at any sample rate.
- Virtual-signal timing never uses the backend's wall clock.
- The log path reads rows `ORDER BY timestamp`, so it is monotonic by construction; a clock step inside a recording would interleave rows (existing limitation of raw indexing, not addressed here).

**D12. Virtual signal ids are name-derived: `id = "WTS." + name`.** Only `name` is stored. Renaming is unsupported in v1 (delete + recreate); widgets in `localStorage` reference ids.

**D13. Live processing is always-on, backend-side, and keeps no history buffer in v1.**
- Processors hold their own small state ($O(1)$ or bounded by a time window), so the display window is irrelevant to them.
- During a live session every defined virtual signal is evaluated, **not gated by subscription**. Only what is appended to `live_batch` is gated by `subscribed_signals`. State therefore never depends on when someone opened a chart.
- Definition edits take effect without reconnecting: the runtime compares `DBCManager.get_wts_version()` each loop iteration and rebuilds (state restarts empty).
- Reconnect resets state.
- Raw-history deques and live-session recording (the other ways to give operators more history) are deferred with their design recorded in Part 7.

**D14. API changes are additive.** Existing endpoints and response shapes keep working so a newer backend never breaks an older dashboard during rollout.

**D15. UI is minimal; the op registry and catalog endpoint are the extension seam.**
A separate plugin roadmap exists. This plan builds no plugin API and no rich editor. It guarantees only that (a) ops register through one registry, (b) `GET /api/wts/operations` self-describes them (distinguishing multi-input head ops via `is_head: true` from single-input chain ops), and (c) the dashboard editor renders from that catalog and lives in one replaceable component.

## 3. The `.wts` file format (v1)

UTF-8 JSON, 2-space indent, stable key order (readable diffs). Extension `.wts`.

```json
{
  "format": "wolftrack-signals",
  "version": 1,
  "name": "Baja 2026 Setup",
  "dbc": {
    "filename": "baja_2026.dbc",
    "encoding": "cp1252",
    "lines": [
      "VERSION \"\"",
      "",
      "BO_ 256 ENGINE: 8 ECU",
      " SG_ RPM : 0|16@1+ (0.25,0) [0|16383.75] \"rpm\" Vector__XXX"
    ]
  },
  "signals": [
    {
      "name": "Brake_Total",
      "kind": "continuous",
      "category": "Brakes",
      "unit": "psi",
      "inputs": ["Brakes.Front_Psi", "Brakes.Rear_Psi"],
      "operations": [{ "type": "combine", "operator": "add" }]
    },
    {
      "name": "Front_Brake_Bias",
      "kind": "continuous",
      "category": "Brakes",
      "unit": "%",
      "description": "Front share of total brake pressure, smoothed",
      "inputs": ["Brakes.Front_Psi", "WTS.Brake_Total"],
      "operations": [
        { "type": "combine", "operator": "divide" },
        { "type": "scale", "factor": 100 },
        { "type": "lowpass", "cutoff_hz": 5.0 }
      ]
    }
  ],
  "signal_info": {
    "Brakes.Front_Psi": {
      "display_name": "Front brake pressure",
      "description": "Master cylinder, front circuit",
      "min": 0,
      "max": 2000
    }
  }
}
```

Rules:

- **DBC storage.** `lines` is the DBC text split on line endings (normalized to `\n`, written back as `\n`), one line per element so git diffs stay readable. `encoding` records how the original bytes were decoded (`utf-8`, else `cp1252`, which is what `cantools` assumes for DBC). The **DBC hash** in cache keys is SHA-256 of `"\n".join(lines)`.
- **Loading the DBC** uses `cantools.database.load_string(text, database_format="dbc")`. Part 2 tests that `load_file(original)` and `load_string(embedded)` yield identical messages/signals for `dbc/stig25(1).dbc`.
- **`signal_info`** annotates any signal id (raw or virtual) and is **read-only in this scope**: loaded, validated, and merged into `GET /api/signals` (`display_name`, `description`, `min`, `max`) for both raw and virtual signals. There is no API or UI to edit it yet; users can edit the file by hand. Precedence: `signal_info` > virtual signal's own fields > DBC. Unknown ids produce a warning.
- **Unknown top-level keys are preserved** on load and save (held in `extras`, re-emitted). This protects files from older app versions and gives plugins and a future `.wtc` a place to store data without a format change (namespace the key, e.g. `"x-myplugin"`). *(groundwork)*
- **`version`** is an integer. A higher version than the app supports is rejected with a clear error.
- **Limits** (on load and API writes): file $\le 5\text{ MB}$, $\le 200$ virtual signals, $\le 16$ operations per signal, dependency depth $\le 16$, names match `^[A-Za-z_][A-Za-z0-9_]{0,63}$`, names unique.
- **Broken definitions** (input id not in the DBC or other valid definitions, unknown op type, depends on a broken one) load but are marked `broken` with a reason, are excluded from computation, and are shown in the UI. One bad signal must not stop a file from opening.
- **Writes are atomic**: write `<file>.tmp`, `fsync`, `os.replace`; keep one `<file>.bak`.

### Virtual signal definition fields

| Field | Type | Notes |
| :-- | :-- | :-- |
| `name` | string | Required. |
| `kind` | `"continuous"` | Reserved (D10). Default `continuous`. |
| `category` | string | Tree grouping (mapped to `message` in `/api/signals`). Default `"Custom"`. |
| `unit` | string | Default `""`. |
| `description` | string | Optional. |
| `inputs` | string[] | 1+ signal ids (raw or `WTS.*`). Order matters for subtract/divide. |
| `operations` | object[] | Ordered. If `inputs.length > 1`, the first op must be `combine`. |

### Operation catalog (this scope)

`combine` (`add`, `subtract`, `multiply`, `divide`), `scale`, `bias`, `moving_avg` (`window_seconds`), `lowpass` (`cutoff_hz`). Further ops (abs, clamp, derivative, integral, ...) are added later by registering a class; see Part 1.

The catalog is **self-describing**: each op declares parameter specs (name, type, default, min/max, unit, help) and `is_head: bool`, and `GET /api/wts/operations` serves them (D15).

## 4. Engine semantics (authoritative)

```python
engine = VirtualSignalEngine(defs, max_gap_seconds=None)   # validates, builds DAG
engine.required_inputs(wanted_ids=None) -> set[str]        # raw ids needed (transitive)
engine.update(ts: float, values: dict[str, float]) -> dict[str, float]   # outputs keyed by WTS id
engine.notify_gap(ts: float) -> None
engine.reset() -> None
engine.stats() -> dict                                      # counters, for logging by the caller
```

- **Zero-order hold.** The engine remembers the latest value and timestamp (`stamps`) of each input. A processor emits only when (a) at least one of its inputs changed in this update (raw or upstream output) and (b) every input has been seen at least once.
- **Single evaluation per update**, in topological order; an upstream output produced in this update is visible downstream in the same call.
- **Monotonic per processor.** If `ts <=` the processor's last output time, skip and count. Never reorder. Clock steps are the live runtime's job (D11).
- **Deterministic and pure.** Output depends only on the sequence of updates.
- **No fabricated data.** Division by zero, NaN, or infinity produce *no sample*, not 0 or a clamped number.
- **Gaps and stale held inputs.** `notify_gap` makes stateful ops discard previous-sample state. If `max_gap_seconds` is set:
  1. When the time since the processor's last evaluation exceeds `max_gap_seconds`, the engine calls `notify_gap(ts)` on that processor before evaluating.
  2. For multi-input processors, if any input's held timestamp is stale (`ts - min(stamps) > max_gap_seconds`), the processor calls `notify_gap(ts)` and returns `None` (no sample) for that update so a dead CAN node is never combined with fresh data indefinitely.
  The log path leaves `max_gap_seconds` unset (BLF files carry no dropped-batch information); the live runtime sets it.
- **Time-based windows**, causal filters only (no look-ahead), so live and log agree.
- **Multi-input ops *(groundwork)*.** The first op of a chain may be a *head op* receiving every input: `HeadOp.apply_vector(ts, values, stamps)`, where `stamps` holds each input's last-update timestamp so an op can detect a stale held input. `combine` is the built-in head op; plugins can register stateful ones without engine changes. Only the head position may take multiple inputs.

## 5. Data flow

```
LOG MODE                                              LIVE MODE
--------                                              ---------
.blf --python-can--> decode (DBC) --> SQLite          ZMQ frames --> decode (DBC)
                      signals (raw, immutable)                          |
                          |                                             v
                          v  post-pass (worker thread)         LiveWtsRuntime (always on)
        rows merged by timestamp, grouped                      one engine.update per frame
        --> engine.update (via run_batch)                               |
                          |                                             v
                          v                                  live_batch (subscribed ids only)
        derived_signals + derived_meta (def_hash)                       |
                          |                                             v
        /api/logfile/query (bucketed)                      WebSocket -> liveDataStore
                          |                                             |
                          v                                             v
                   logDataStore ------------> charts (a virtual signal looks like any other)
```

## 6. Invariants (enforced by tests)

| # | Invariant | Where tested |
| :-- | :-- | :-- |
| I1 | **Delivery-independence.** Same sample sequence $\Rightarrow$ identical outputs whether delivered as streaming `update` calls or via the batch helper; the log path and the live path each equal the batch helper. | Parts 1, 3, 4 |
| I2 | No wall-clock, randomness, or I/O in `src/wts/` (engine/ops). | Part 1 |
| I3 | Raw `signals` table is never written after the index is published. | Part 3 |
| I4 | Derived rows are a pure function of (raw rows, compute-affecting definitions). Editing a definition changes only that signal and its dependents; editing cosmetic fields (`unit`, `category`, `description`) does not recompute rows. | Part 3 |
| I5 | `.wts` round-trip preserves unknown keys and DBC content. | Part 2 |
| I6 | Uploaded files are validated; no path traversal; size-capped; unknown op types rejected, never executed. | Part 2 |
| I7 | Existing API responses remain valid for an older frontend. | Parts 2-4 |
| I8 | Output timestamps per virtual signal are strictly increasing. | Parts 1, 4 |
| I9 | **No-op when unused.** With no virtual signals defined, the live path decodes and emits exactly what it did before this feature. | Part 4 |
| I10 | A backward clock step never freezes virtual signals; they resume immediately on the new time base. | Part 4 |
| I11 | The live loop is never blocked by virtual-signal work beyond the measured budget. | Part 4 benchmark |

## 7. Non-goals (this scope)

Event signals and aggregates (lap times, averages) · GPS, tracks, lap/sector timing · map widget · plugin system · signal-info editing UI/API · signal preview, templates, duplicate · dashboard/`.wtc` container · scripting (arbitrary user code stays out; bounded head-position arithmetic expressions shipped as the `expr` op — a whitelisted AST, not scripting) · offline/zero-phase filters · raw-history buffers and live-session recording. Renaming virtual signals shipped after v1 (`PUT /api/wts/signals/{name}/rename`: dependent inputs, `signal_info`, and chart widgets are rewritten atomically). Each remaining item has its groundwork and design notes in Part 7.