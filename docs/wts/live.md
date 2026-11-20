# WTS live path (Part 4): virtual signals on the ZMQ stream

How virtual signals update in real time, and the clock rules that keep
them alive through real-world stream weirdness.

## Q1 / V1 — DAQ timestamp unit: **verified against real captures**

Checked 2026-11-20 against real WolfTrack DAQ captures
(`~/.config/wolftrack/logs/uploads/morn.blf`, 18,960 frames, and
`~/Downloads/brakerun1.blf`, 150,280 frames, recorded by
`wolftrack-logger`, which forwards `can.Message.timestamp` from socketcan
verbatim into the ZMQ `can_batch` frames):

- unit is **seconds** (float64 UTC epoch — values ≈ 1.78e9 resolve to the
  actual capture dates), not ms or ns;
- present on **every** frame (0 missing in 169k frames);
- no backward steps *within* a single capture.

The runtime is built for the cases the captures don't show but reality
delivers: a **DAQ reboot mid-session** or a **looped ZMQ replay** *can* step
the clock backward, and network gaps make it jump forward.

## Data flow (`PipelineManager._run_loop`)

- `LiveWtsRuntime` (`src/wts/live.py`) wraps the shared engine with
  `max_gap_seconds=1.0` — the only WTS module with stream-clock state, and
  still no I/O, no wall clock.
- **Decode gating**: a frame decodes if any of its signals is subscribed
  **or** in `runtime.raw_inputs` (the transitive raw inputs of every
  definition). Charting only `WTS.Brake_Bias` still decodes its raw inputs
  (D13 always-on); with no definitions the gating is byte-for-byte the old
  behavior and `runtime.process` is never called (I9, fast-path bypass).
- **One update per frame** (D6): all needed values from one frame go into
  one `runtime.process(ts, values)` call. Outputs are appended to
  `live_batch` only for subscribed `WTS.*` ids — subscription changes what
  is *emitted*, never what is *computed*.
- **Hot reload (D13)**: the loop compares `get_wts_version()` each
  iteration; on change it rebuilds the runtime (state restarts empty),
  refreshes `db`, and clears `arb_id_cache` — which also fixes the old
  limitation that switching DBCs while live did nothing until restart. A
  rebuild failure logs and keeps the old runtime; the loop never dies.
- **Reset** on `start()`; nothing leaks between sessions.

## Time semantics (D11, I8, I10)

`delta = ts - last_ts`, `limit = max_gap_seconds`:

| delta | meaning | action |
| :-- | :-- | :-- |
| `> limit` | forward jump / dropped data | `notify_gap` (state cleared, output proceeds) |
| `< -limit` | **clock step** (reboot / looped replay) | full `reset()`, adopt new base, next batch carries `clock_step: true` (additive field) |
| `-limit .. 0` | out-of-order jitter | skip that sample, no state change |
| frame has no `timestamp` | malformed | skip for WTS + one WARNING per session; the raw fallback (`time.time()`) is untouched and **never** used for virtual signals |

`dropped_batches > 0` in a batch → `notify_gap` too (gaps are real even
when the RTC looks continuous).

A clock step first flushes the in-flight batch so every per-signal
timestamp array stays non-decreasing on the wire (I8); the `clock_step`
flag rides the next (new-time-base) batch.

## Failure isolation (4.3)

Frame decode errors: counted, DEBUG-logged at most every 100th (was a bare
`except Exception: pass`). Engine errors: counted, ERROR rate-limited.
Neither kills the loop; later frames are unaffected.

## Event-loop budget (I11)

`scripts/bench_live_wts.py` (run, not a CI gate). Measured 2026-11-20 on
the dev machine (Ryzen-class laptop):

| defs | per-frame p50 | p99 | headroom |
| :-- | :-- | :-- | :-- |
| 5 | 0.015 ms | 0.020 ms | 3,238 frames per 50 ms window |
| 30 | 0.090 ms | 0.103 ms | 555 frames per 50 ms window |

Target is 5,000 f/s × 30 defs (250 frames per window): met with ~2×
headroom on the *Python* work alone; no need for the restricted-always-on
or worker-thread mitigations. Re-measure on the RPi/laptop pair the team
actually drives with before revisiting.

## Wire format

`live_batch` is unchanged except the optional `clock_step: true`.
Frontends must ignore unknown fields (they do).
