# Part 1: Signal Engine

**Area:** apps/visualizer · **Depends on:** Part 0 · **Size:** M

## Goal

A pure-Python, I/O-free engine that evaluates virtual signal definitions over timestamped updates, with a small op registry. No FastAPI, SQLite, ZMQ, asyncio, or file access in this package. Read [00-architecture.md](00-architecture.md) §4 (semantics) and §6 (invariants) first; they are binding.

The scope is deliberately small: five ops plus the `expr` head op (`expression`: `%s` = Nth selected signal, evaluated over a whitelisted arithmetic AST — no user code execution). The point is a correct, extensible foundation, not a large catalog.

## Package layout

```
src/wts/
  __init__.py
  errors.py        # WtsValidationError (list of {code, signal, message})
  schema.py        # VirtualSignalDef, OperationDef; parse/validate; canonical_json; def_hash
  graph.py         # dependency resolution: topological order, cycle path, depth limit, ancestors
  ops/
    __init__.py    # registry: OPS dict, @register, describe_all(); explicitly imports basic, combine, expr, filters
    base.py        # Op base class, HeadOp base class, ParamSpec
    basic.py       # scale, bias
    combine.py     # combine
    expr.py        # expr (+ the safe expression evaluator)
    filters.py     # moving_avg, lowpass
  engine.py        # VirtualSignalEngine
  batch.py         # run_batch helper
  README.md        # how to add an op
```

*PyInstaller note:* `src/wts/ops/__init__.py` must explicitly import `basic`, `combine`, and `filters` at the top level so PyInstaller's static import scanner bundles the modules and executes their `@register` decorators at startup.

## Op interface

```python
@dataclass(frozen=True)
class ParamSpec:
    name: str
    type: Literal["float", "int", "string", "enum", "bool"]
    default: Any = None
    required: bool = False
    min: float | None = None
    max: float | None = None
    choices: tuple[str, ...] | None = None
    unit: str | None = None
    help: str = ""

class Op(ABC):
    type: ClassVar[str]                      # "scale"
    label: ClassVar[str]                     # human name for the UI
    is_head: ClassVar[bool] = False          # True only on HeadOp subclasses
    params: ClassVar[tuple[ParamSpec, ...]]
    def __init__(self, **params): ...        # validates against `params`
    def reset(self) -> None: ...
    def notify_gap(self, ts: float) -> None: ...
    @abstractmethod
    def apply(self, ts: float, value: float) -> float | None: ...

class HeadOp(Op):                            # multi-input first stage of a chain
    is_head: ClassVar[bool] = True
    arity: ClassVar[tuple[int, int | None]]  # (min_inputs, max_inputs or None)
    @abstractmethod
    def apply_vector(self, ts: float, values: Sequence[float],
                     stamps: Sequence[float]) -> float | None: ...
```

`combine` is the built-in `HeadOp`. A head op is only allowed as the first operation; it receives the latest value of every input plus `stamps` (each input's last-update timestamp, so an op can notice a stale held input). It is evaluated when at least one input changed and all inputs have been seen at least once. Everything after the head is a chain of single-value `Op`s (`is_head == False`). *(groundwork: future ops that take several signals and keep state, such as a GPS-based timer, are one `HeadOp` subclass plus `@register`, with no engine change. Do not build any of them here.)*

`describe_all()` returns a JSON-serializable catalog:
```json
{
  "operations": [
    { "type": "scale", "label": "Scale", "is_head": false, "params": [...] },
    ...
  ],
  "combine_operators": ["add", "subtract", "multiply", "divide"]
}
```
Include `is_head` on every entry in `operations` so the Part 6 editor knows which ops belong in the post-head operation list (`!op.is_head`) vs. head position. **Registering a class with `@register` must be the only step needed to add an op** (D15).

## Operations

| Op | Params | Behavior and edge cases |
| :-- | :-- | :-- |
| `combine` | `operator`: `add`, `subtract` ($a - b - c \dots$), `multiply`, `divide` (exactly 2 inputs) | Validate in `__init__` or schema validation: `divide` with `len(inputs) != 2` raises a validation error. `divide` by zero $\Rightarrow$ **no sample** (`None`). |
| `expr` | `expression` | Head op: each literal `%s` binds to the Nth input in selection order; compiled once to a whitelisted arithmetic AST (numbers, `+ - * / // % **`, a fixed function table, `pi`/`e`). Arithmetic faults (`/0`, `sqrt(-1)`, overflow) $\Rightarrow$ **no sample**; more placeholders than inputs $\Rightarrow$ validation error. |
| `scale` | `factor` | `value * factor`. |
| `bias` | `offset` | `value + offset`. |
| `moving_avg` | `window_seconds` ($0 < w \le 600$) | Time-based window of `(ts, value)`; running sum recomputed every 10,000 updates and whenever `len(window) <= 1` to eliminate floating-point subtraction drift. Emits from the first sample. `notify_gap` clears the window and resets the running sum to `0.0`. |
| `lowpass` | `cutoff_hz` ($> 0$) | First-order RC, $\alpha = \Delta t / (\text{rc} + \Delta t)$, $\text{rc} = 1 / (2\pi f)$. First sample passes through. $\Delta t \le 0 \Rightarrow$ skip. `notify_gap` makes the next sample pass through. |

Any op returning `None` stops the chain for that update. Results that are `NaN` or infinite become `None` at the end of the chain. More ops (abs, clamp, derivative, integral, ...) are follow-ups: one class plus tests each.

## Engine behavior

Implement exactly as specified in 00-architecture §4, plus:

- **Construction** validates every definition (schema, op params, input count vs. `combine` and `divide` arity, post-head ops must have `is_head == False`, name rules, `kind == "continuous"` per D10), builds the graph, orders processors topologically. It raises one `WtsValidationError` carrying **all** errors found, not just the first.
- **`def_hash` calculation (`schema.py` + `graph.py`)** hashes canonical JSON of `{ "kind": def.kind, "inputs": def.inputs, "operations": def.operations }` plus the `def_hash` of each upstream `WTS.*` input. Cosmetic fields (`unit`, `category`, `description`) are **excluded** from `def_hash` so editing them does not invalidate cached SQLite rows in Part 3.
- **`required_inputs(wanted_ids=None)`** returns the raw ids needed (transitively) to compute `wanted_ids` (or everything). Part 3 uses it to know which signals to read; Part 4 uses it to know which signals to decode.
- **`subgraph_defs(defs, wanted_ids)`** (in `graph.py`): returns the subset of `defs` consisting of `wanted_ids` and all of their transitive `WTS.*` ancestors in topological order. Part 3 uses this so recomputing a subset of stale signals does not re-evaluate unrelated fresh virtual signals that happen to share raw inputs.
- **`max_gap_seconds`** (default `None`): when set:
  1. A processor whose time since its last evaluation exceeds `max_gap_seconds` receives `notify_gap(ts)` before processing.
  2. For multi-input processors, if any input's held timestamp is older than `max_gap_seconds` (`ts - min(stamps) > max_gap_seconds`), the processor calls `notify_gap(ts)` and emits `None` for that update so a dead CAN node's frozen value is not combined with live inputs forever.
  Off by default; the log path leaves it off, and the live runtime (Part 4) sets it.
- **Output timestamps strictly increasing per signal** (I8).
- **`stats()`** returns counters (`skipped_non_monotonic`, `none_results`); the engine never logs.
- Do not keep references to the caller's `values` dict.
- **Batch helper** `run_batch(engine, rows)` (in `src/wts/batch.py`, still pure): takes any iterable of `(ts, signal_id, value)` rows already sorted by `ts`, groups equal timestamps into one `update`, and **yields** output rows lazily (so the Part 3 post-pass can stream from SQLite cursors). The post-pass and the tests both use it, which is how I1 is guaranteed by construction for the log path; Part 4's live test compares against it.

## Tasks

- [x] 1.1 `errors.py`, `schema.py` (parse, validate, `canonical_json`, `def_hash` of `{kind, inputs, operations}` + upstream hashes via `graph.py`).
- [x] 1.2 `ops/` registry, `describe_all()` (including `is_head`), explicit submodule imports in `ops/__init__.py`, and the five ops. (`expr` head op added later; see `src/wts/README.md`.)
- [x] 1.3 `graph.py` (topological order, cycle reported as a path, depth limit 16, `subgraph_defs`).
- [x] 1.4 `engine.py`, `batch.py`.
- [x] 1.5 Tests below, and `src/wts/README.md` ("add an op in 3 steps").

## Tests (`tests/wts/`)

1. **Per-op unit tests** with hand-computed expectations (arithmetic in comments), including `divide` rejecting 1 or 3 inputs and `moving_avg` zero-drift check when window drains to 0 or 1 sample.
2. **Same-timestamp regression:** two inputs, prior 50/50 then true values 80 and 20 $\Rightarrow$ exactly one sample $80/(80+20)$-style result at that timestamp, no intermediate (D6).
3. **Zero-order hold:** inputs at different rates; nothing emitted until all inputs seen; output times equal the union of input update times.
4. **Chaining (D5) & `def_hash`:** `WTS.B` depends on `WTS.A`; downstream sees the value in the same update; a cycle is rejected with its path; depth 17 rejected; `ratio` built from three chained definitions works; changing `unit`/`category`/`description` does not change `def_hash`, while changing an upstream op changes both `WTS.A` and `WTS.B` hashes.
5. **No fabricated data:** divide by zero, NaN, inf $\Rightarrow$ no sample.
6. **Monotonicity:** equal/backward `ts` skipped and counted; state not corrupted.
7. **Gaps & stale inputs:** `notify_gap` effects per op; `max_gap_seconds` triggers it automatically when set (including suppressing output when one input in a 2-input `combine` stops updating for longer than `max_gap_seconds`) and never when `None`.
8. **Delivery independence (I1):** seeded stream with random rates, jitter, and duplicate-timestamp groups; run (a) one `update` per group in a loop and (b) `run_batch`; assert **exact equality**.
9. **Purity (I2):** source scan of `src/wts/` for `time.time`, `datetime.now`, `random`, `open(`, `sqlite3`, `asyncio`, `os.`; `kind != "continuous"` rejected (D10).
10. **Catalog:** `describe_all()` is JSON-serializable; every op has a label, `is_head`, and complete `ParamSpec`s; registering a dummy op in a test makes it appear.
11. **Head-op extension point:** a test-only, 3-input, stateful `HeadOp` registered inside the test module works end to end (engine, `run_batch`, delivery-independence test, `describe_all()`), and receives correct `stamps` when inputs update at different rates. This proves plugins can add multi-input ops without engine changes.

## Acceptance criteria

- All tests pass; `uv run pytest tests/wts -q` takes under 5 s.
- Throughput sanity (not a gate): 100,000 updates through a 5-definition set in well under a second on a laptop; note the number in the PR.
- No new third-party dependencies.

## Gotchas

- Use `math.isfinite`, not equality, for NaN/inf handling.
- Timestamps are UTC epoch seconds as float64 (D11). Compute `dt` as a difference of timestamps; never convert units or subtract an offset inside ops. The engine does not handle clock steps; the live runtime does.
- Keep per-update allocations low in the hot path where it stays readable; do not micro-optimize beyond that.
- `moving_avg`'s deque holds `(ts, value)` pairs; the 600 s cap is deliberate.
## Notes from implementation

- Throughput sanity (this machine, 2026-11-20): 100,000 updates × 5
  definitions (incl. lowpass + moving_avg) in ~1.05 s ≈ 95k updates/s.
- Engine tests: `uv run pytest tests/wts -q` → 64 tests, ~0.2 s.
