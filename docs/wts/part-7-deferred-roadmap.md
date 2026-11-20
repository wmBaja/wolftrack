# Part 7: Deferred Roadmap and Groundwork

**Not scheduled. Nothing in this file is to be built as part of Parts 0-6.**

For each deferred item: what it is, **what the current plan already provides** (the groundwork), and the design notes worth keeping so the thinking is not lost. Start none of these without a concrete need and a plugin-roadmap decision.

---

## 1. Event signals and aggregates (lap times, "average of all laps")

**What.** Sparse signals (one sample per lap or per crossing) that are retained for a whole session, plus aggregates over them (running mean, min/max, count, last-$N$ mean).

**Why the current design does not break them.** Backend processors keep their own state, so the live display window never trims them (D1, D13). The frontend `RingBuffer` is the part that *would* trim them, which is why events need their own store.

**Groundwork present.** `kind` is reserved in the schema and only `"continuous"` is accepted (D10), so enabling `"event"` later needs no file migration. Virtual signals may depend on other virtual signals (D5), so an aggregate is just another definition whose input is an event signal. Ops register through one registry.

**Design notes for later.**
- *Retention.* Event signals are session data: live keeps a bounded per-signal event log (for example 10,000 entries) in the backend and sends an `event_snapshot` on subscribe so a reloaded dashboard recovers history; the frontend keeps a separate non-reactive `eventStore`, never time-trimmed.
- *Log queries.* Return all rows unbucketed for event signals (the existing `MIN(timestamp), value` bucket query would collapse two events in one bucket), capped with a `truncated` flag, plus an endpoint returning the full event list regardless of viewport.
- *Output timestamps.* Event ops should be allowed to return `(out_ts, value)` (or implement an `EventOp` interface) so a crossing can be stamped at an interpolated time; the engine already enforces strictly increasing output timestamps (I8), so such ops fit without breaking existing continuous `Op` classes.
- *Aggregates.* Running ops are $O(1)$ state; a bounded last-$N$ variant is $O(N)$. Users will want to exclude the out-lap or a spin: store exclusions as **session data, not in the `.wts`** (SQLite table in the log cache; a backend session set live) and recompute aggregates with the exclusion set.
- *Widgets.* A table widget (index, time, value) and a stat widget (latest/best/average) are the natural renderers; a line chart is the wrong visual.

## 2. GPS, tracks, lap and sector timing

**What.** Lap time, lap number, and sector/corner times computed from GPS position crossing user-defined gates.

**Groundwork present.** Multi-input stateful ops via `HeadOp` (Part 1) with `stamps` so an op can tell a held coordinate from a fresh one. The engine is pure and delivery-independent, so a GPS op behaves identically live and in logs. Unknown `.wts` keys are preserved (I5), so tracks can be stored under a namespaced key without a format change. **No dependency on lat and lon sharing a CAN message**: zero-order hold already pairs them from separate signals.

**Design notes for later.**
- *State.* A gate is a line segment; a lap timer needs only the previous fix and a few scalars. History is never needed.
- *Geometry.* Project lat/lon to local planar meters (equirectangular about the gate midpoint) before any distance or intersection math. Intersect the movement segment with the gate segment (cross products); interpolate the crossing time from the intersection fraction; optionally require a crossing direction.
- *Sanity.* Debounce with a minimum lap time; reject fixes whose implied speed is implausible; on a gap drop the previous fix and never guess a crossing.
- *Outputs.* One definition per output (lap time, lap number) avoids a multi-output engine; a UI template can create both. These are event signals (item 1).
- *Reference lap / delta time* needs a distance-along-track signal and a bounded stored reference trace; it is the first feature that genuinely needs per-lap history.

## 3. Map widget and track editor

**What.** A map (or offline XY trace) with gates overlaid and a way to define gates by clicking points.

**Groundwork present.** None needed beyond signals being chartable. This is entirely a frontend plugin concern. Paddock connectivity may be poor; prefer an offline-capable XY trace before any tile map.

## 4. Plugin system and richer UI

**What.** Plugin-provided ops, widgets, and editors; signal preview, templates, duplicate, drag-reorder, categories, dependency views.

**Groundwork present (the extension seam, D15).** One op registry and a self-describing catalog endpoint; the editor is one replaceable component with a narrow interface (Part 6); namespaced unknown `.wts` keys for plugin data; additive API rules (D14). A dry-run **validate** endpoint and a **preview** endpoint are natural additions when the richer editor arrives (preview would compute over a short window of raw data in log mode).

## 5. Signal-info editing UI and API

**What.** Editing `display_name`, `description`, `min`, `max` for any signal from the app.

**Groundwork present.** `signal_info` is in the file format, validated, and merged into `GET /api/signals` (Part 2). Only the write endpoints (`PUT/DELETE /api/wts/signal-info/{signal_id:path}`) and a small popover are missing.

## 6. `.wtc` container (dashboards + signals)

**What.** A higher-level file that references or embeds a `.wts` and adds dashboard layouts (today in `localStorage` under `dashboard-widgets`), widget settings, and shared tracks.

**Groundwork present.** `.wts` preserves unknown keys and carries a `version`. Open decisions: embed vs. reference by hash; per-user vs. per-team files; behavior when importing a layout whose signals are missing (Part 5 already shows a "missing signal" state).

## 7. Raw-history buffers and live-session recording (more history for live operators)

This answers "what if a live operator needs more history than the display window?"

- **Tier 1 (what v1 does).** Streaming operators keep their own state. Covers scale, bias, filters, derivative, integral, and anything gate-based.
- **Tier 2: backend raw-history deques.** For windowed operators needing random access (rolling median, percentiles, RMS, FFT). Each op declares `history_seconds`; the runtime sizes a per-signal deque to the largest request; the log path reads the equivalent window from SQLite. Memory is small ($100\text{ Hz} \times 60\text{ s} \times 16\text{ B} \approx 100\text{ KB}$ per signal). Add only when an op needs it.
- **Tier 3: record live sessions to SQLite.** Write live frames into the same `signals` schema used by log indexing so a live session becomes "a log still being written". This gives durable history across backend restarts, scrub/time-travel, post-run analysis, and a single code path for derived signals (the Part 3 post-pass can run incrementally). Open points: writer thread with a bounded queue, file retention, interaction with the DAQ's own logging.
- Note the frontend `RingBuffer(10000)` already caps the effective window at about 100 s at 100 Hz regardless of `live_buffer_window_seconds`; that cap is a frontend display matter and does not affect virtual-signal computation.

## 8. Expression operation

**What.** An `expression` op such as `sqrt(a*a + b*b)` with named inputs.

**Constraints (D4).** Parse with Python's `ast` into a whitelisted node set (numbers, names, `+ - * / ** %`, comparisons, a small function allowlist); compile to a closure; enforce size and depth limits; no attribute access; never `eval`/`exec`; fuzz-test it. `ParamSpec` already supports a validated string parameter. Many cases are already covered by chaining definitions (D5), so do this only if users hit that limit.

## 9. More ops and offline filters

**More ops** (abs, clamp, derivative, integral, deadband, rate limit): one class plus tests each, via the registry. **Zero-phase (forward-backward) filters** cannot run live, so they would break delivery independence (I1) between modes. If ever added, mark them `offline_only`, hide them in live mode, and make that explicit in the UI and file.

## 10. Smaller items

- Renaming virtual signals with automatic widget-id migration (needs stable signal uids).
- Moving `/api/dbc/*` to `/api/setups/*` once the frontend no longer depends on the old names.
- Multi-client subscription isolation in `ws_manager` (today one global `subscribed_signals`).
- Per-definition opt-out of always-on live evaluation, only if the Part 4 benchmark ever shows a need.
- Signal quality flags (stale input, out-of-range) propagated to outputs; `stamps` on head ops is the hook.
- Importing/exporting only virtual signals (without the DBC) between setups.
- Detecting or repairing a clock step inside a recorded `.blf` (rows interleave today; see Part 3 gotchas).