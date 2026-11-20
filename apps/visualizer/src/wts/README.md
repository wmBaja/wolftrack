# `src/wts` — the WolfTrack Signals engine

Pure-Python virtual-signal evaluation shared by the log post-pass and the
live loop. **No I/O, no wall clock, no randomness here** (a test enforces it).
Semantics are authoritative in `docs/wts/00-architecture.md` §4; read it first.

```
schema.py   parse/validate definitions, canonical JSON, def hashes
graph.py    dependency DAG: topological order, cycles, depth, subgraphs
ops/        typed operation registry (see below)
engine.py   VirtualSignalEngine.update(ts, values) -> {WTS.<name>: value}
batch.py    run_batch(engine, rows): stream (ts, signal_id, value) rows
live.py     LiveWtsRuntime: clock-step handling for the ZMQ loop (Part 4)
```

## Engine contract

- One `update(ts, values)` per timestamp (one CAN frame); every affected
  processor evaluates **once** (D6). Never call it twice for one timestamp.
- Outputs appear only when at least one input changed and every input has
  been seen (zero-order hold); output timestamps per signal are strictly
  increasing (I8).
- `None` (no sample), NaN, and infinities are never emitted — divide by zero
  produces nothing, not zero (never fabricate data).
- `max_gap_seconds` (live only) makes multi-input ops refuse to combine
  stale held inputs with fresh ones; the log path leaves it unset.

## Add an op in 3 steps

1. Create a class in `ops/<module>.py`: subclass `Op` (single value) or
   `HeadOp` (multi-input, first position only), set `type`, `label`,
   `params: (ParamSpec(...), ...)`, implement `apply` / `apply_vector`, and
   decorate with `@register`. Return `None` to emit nothing; override
   `reset()`/`notify_gap()` if the op keeps state.
2. If it lives in a new module, add the import to the explicit list at the
   bottom of `ops/__init__.py` (PyInstaller does not follow dynamic imports).
3. Add unit tests in `tests/wts/test_ops.py` with hand-computed values.

The op then appears in `GET /api/wts/operations` automatically and the
dashboard editor renders its parameter form from the catalog — no frontend
change needed (D15).

## Ops in scope (v1)

| type        | params           | notes                                    |
| :--         | :--              | :--                                      |
| `combine`   | `operator`       | head op: add/subtract/multiply/divide     |
| `scale`     | `factor`         | value × factor                           |
| `bias`      | `offset`         | value + offset                           |
| `moving_avg`| `window_seconds` | time window, ≤ 600 s, drift-renormalized  |
| `lowpass`   | `cutoff_hz`      | first-order RC, causal                   |

Anything beyond this list (abs, clamp, derivative, integral, GPS timers…) is
deliberately deferred — see `docs/wts/part-7-deferred-roadmap.md`.
