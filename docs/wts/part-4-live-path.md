# Part 4: Live Path (ZMQ Stream)

**Area:** apps/visualizer · **Depends on:** Part 2 (can run in parallel with Part 3) · **Size:** M

## Goal

Virtual signals update in real time during a live DAQ session, regardless of which raw signals are charted, with state that is always on, resets correctly, survives definition edits, tolerates stream clock steps (DAQ reboots, RTC jumps, or looped ZMQ replays), and never stalls the event loop. With no virtual signals defined, live behavior is exactly what it is today.

Read [00-architecture.md](00-architecture.md) D1, D6, D7, D11, D13 and invariants I1, I7-I11.

## Current code to know (`src/pipeline/manager.py`, `src/ws_manager.py`, `src/api/routes.py`)

- `_run_loop` consumes `source.stream()`. ZMQ messages are `{"type": "can_batch", "frames": [...], "dropped_batches": n}`; each frame has `arbitration_id`, `data`, and `timestamp`. Today a missing `timestamp` falls back to wall-clock `time.time()`. The DAQ's timestamp is **UTC epoch seconds from an RTC** (Q1), which can step backward if the DAQ reboots mid-session or when replaying a looped ZMQ capture.
- A frame is decoded **only if** one of its raw signal ids is in `ws_manager.subscribed_signals`. A virtual-signal subscription must also cause its upstream raw signals to be decoded, even when those raw signals are not charted.
- `db` and `arb_id_cache` are captured **once** at loop start, so switching the DBC while live has no effect on the running loop (existing limitation). WTS hot reload needs the same refresh, so fix both together.
- Output is `live_batch`, flushed about every 50 ms via `ws_manager.broadcast_json`: `{type: "live_batch", signals: {id: {timestamps: [], values: []}}, dropped_batches}`.
- `ws_manager.subscribed_signals` is one global set replaced by whichever client last subscribed. Unchanged.
- Live data is trimmed in the frontend only; the backend never trims, so processors are unaffected by the display window (D1).

## Design

### `LiveWtsRuntime` (new, `src/wts/live.py`)

Thin wrapper over `VirtualSignalEngine(defs, max_gap_seconds=1.0)`. Lives in `src/wts/` but is the one module there that may be stateful about the clock; it still performs no I/O and does not read the wall clock.

```python
class LiveWtsRuntime:
    def __init__(self, defs, max_gap_seconds=1.0)
    version: int                         # DBCManager.wts_version it was built from
    raw_inputs: frozenset[str]           # every raw id any virtual signal needs (the always-on set)
    def process(self, ts, values) -> tuple[dict[str, float], bool]   # (outputs, clock_step)
    def note_dropped(self, ts) -> None   # dropped_batches > 0 => engine.notify_gap
    def reset(self) -> None
```

### Changes to `_run_loop`

1. **Decode gating.** Decode a frame if any of its signals is in `ws_manager.subscribed_signals` **or** in `runtime.raw_inputs`. With no virtual signals, `raw_inputs` is empty and the gating is identical to today (I9).
2. **Per frame (with fast-path bypass).** Decode once. If `runtime.raw_inputs` is non-empty, build `needed_values = {"Msg.Sig": value}` for raw inputs in `runtime.raw_inputs`, call `runtime.process(ts, needed_values)` **once per frame**, and append any subscribed virtual outputs to `live_batch`. When `runtime.raw_inputs` is empty, skip building `needed_values` and skip calling `runtime.process()` entirely so zero-WTS overhead is strictly zero.
3. **Hot reload.** Each iteration compare `dbc_manager.get_wts_version()` with `runtime.version`. On mismatch rebuild the runtime from the current valid definitions, refresh `db`, and clear `arb_id_cache` (this also fixes the DBC-switch limitation). State restarts empty; log at INFO.
4. **Reset.** `runtime.reset()` at `PipelineManager.start()` and whenever the source reconnects.
5. **Always-on (D13).** Every defined virtual signal is evaluated on every frame that carries its inputs, whether or not it is subscribed.
6. **Monotonic output.** Drop any virtual output with `ts <=` the last emitted timestamp for that id (I8) and count it.
7. **Time and clock steps (Q1, D11).** With `delta = ts - last_ts`:
   - `delta > max_gap_seconds`: forward jump or dropped data. The engine's own gap rule calls `notify_gap`.
   - `delta < -max_gap_seconds`: **clock step** (e.g., DAQ rebooted mid-session or a looped ZMQ capture wrapped around). Call `engine.reset()`, set `last_ts = ts`, and set `"clock_step": true` on the next `live_batch` (additive field). Without this a backward step would freeze every virtual signal until time caught up.
   - `-max_gap_seconds <= delta <= 0`: out-of-order jitter. Skip that sample for virtual-signal purposes.
   - `dropped_batches > 0` in the message: `note_dropped(ts)`.
   - **If a frame has no `timestamp`:** log one WARNING per session and **skip it for virtual-signal purposes**. Never substitute the backend's wall clock there (the laptop and RPi clocks are not guaranteed to agree). The existing raw-signal fallback is left unchanged.
8. **Failure isolation.** An exception inside the engine for one frame is logged (rate-limited) and skipped; it must not kill the loop. Replace the bare `except Exception: pass` around decode with a counter plus DEBUG logging.

### Event-loop budget (I11)

`engine.update` runs synchronously inside the asyncio loop. Add `scripts/bench_live_wts.py` (a script, not a CI gate): synthetic stream of $N\text{ frames/s} \times M\text{ definitions}$ reporting per-batch processing time p50/p99. **Initial target, to be adjusted after measuring on target hardware:** the loop keeps up with 5,000 frames/s and 30 definitions with p99 batch processing under 5 ms. If it misses, in order: optimize the hot path; then restrict always-on to definitions that need state; then move compute to a worker thread with a bounded queue. Do not do the last two without data.

### What this part does not do

No history buffers, no event signals, no recording of live sessions (Part 7). The wire format changes only by the optional `clock_step` flag.

## Tasks

- [x] 4.1 `src/wts/live.py` runtime (gap/clock-step logic) with unit tests.
- [x] 4.2 `PipelineManager` integration: gating, fast-path bypass when `not runtime.raw_inputs`, per-frame update, hot reload via `get_wts_version()`, DBC/`arb_id_cache` refresh, reset on start/reconnect.
- [x] 4.3 Replace silent exception swallowing with counted/logged handling.
- [x] 4.4 Test helper `tests/helpers/fake_source.py`: a `DataSource` that yields scripted `can_batch` messages built from a synthetic DBC.
- [x] 4.5 Benchmark script; paste results in the PR.
- [x] 4.6 `docs/wts/live.md`: time semantics (D11). **Verify against a real DAQ capture** that `timestamp` is in seconds (not ms/ns) and is present on every frame; record the result in the PR.

## Tests (fake source + synthetic DBC)

- **Upstream decoding:** subscribe only to `WTS.Brake_Bias`; its raw inputs are not subscribed; `live_batch` contains `WTS.Brake_Bias` and **no** raw signals.
- **Single sample per frame (D6):** the same-frame two-input case emits exactly one virtual sample.
- **Always-on state:** a `moving_avg` or `lowpass` accumulates before anyone subscribes; subscribing later yields values consistent with the full history.
- **Delivery independence (I1):** feed the same frames through the live loop and through `run_batch`; virtual outputs are equal.
- **No-op when unused (I9):** with no virtual signals defined, decode gating and `live_batch` content are identical to the pre-change behavior (use the existing live tests as the baseline).
- **Hot reload:** upsert a definition mid-stream; new output appears within one batch; old state cleared; no exception; `arb_id_cache` refreshed (add a message to the DBC to prove it).
- **Gaps:** `dropped_batches > 0` triggers `notify_gap`; a forward timestamp jump above `max_gap_seconds` is treated as a gap.
- **Clock step (I10):** feed frames, then a frame 3 s *earlier* than the last: the engine resets, the next batch has `clock_step: true`, and virtual output resumes immediately on the new time base. A 50 ms backward jitter is skipped with no reset. A forward step causes a gap, not a reset.
- **Missing timestamp:** a frame without `timestamp` yields no virtual output and one warning per session.
- **Reset:** reconnect clears state; nothing leaks from the previous session.
- **Failure isolation:** an op that raises on one frame does not stop later frames.
- **Subscription changes:** changing `subscribed_signals` mid-stream changes what is emitted, not what is computed.
- Existing live-source and route tests stay green (I7).

## Acceptance criteria

- With the DAQ simulator (or the fake source), a chart of a virtual signal updates live while its raw inputs are not charted.
- Editing a virtual signal during a session takes effect without reconnecting.
- Simulating a clock step (backward and forward) leaves virtual signals running.
- Benchmark numbers recorded; the loop meets the target or the PR documents which mitigation was chosen and why.

## Gotchas

- No `time.time()` anywhere in the virtual-signal path (the single existing raw fallback is the only wall-clock use).
- Per-signal arrays in `live_batch` must keep timestamps non-decreasing; with the monotonic rule they are strictly increasing per virtual signal.
- Rebuilding the runtime allocates; only do it on a version change, never per frame.
- `ws_manager.subscribed_signals` may contain ids that no longer exist (a deleted virtual signal still charted); ignore unknown ids and never raise.
## Notes from implementation

- Q1/V1 verified against real captures (see docs/wts/live.md): seconds,
  present on every frame.
- A clock step flushes the in-flight batch first so per-signal arrays on
  the wire stay non-decreasing (I8); the `clock_step` flag rides the next
  batch.
- Hot reload also refreshes `db` + `arb_id_cache`, fixing the pre-existing
  "DBC switch while live does nothing" limitation.
- Benchmarks (dev laptop): 30 defs p99 0.103 ms/frame, ~555 frames per
  50 ms window — target met without mitigations.
