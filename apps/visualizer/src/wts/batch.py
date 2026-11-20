"""Batch helper: feed SQLite-style rows through an engine lazily.

Used by the log post-pass (Part 3) and by the delivery-independence tests
(I1): streaming ``update`` calls and :func:`run_batch` over the same sample
sequence must produce identical output.
"""
from __future__ import annotations

from typing import Iterable, Iterator

from wts.engine import VirtualSignalEngine


def run_batch(
    engine: VirtualSignalEngine,
    rows: Iterable[tuple[float, str, float]],
) -> Iterator[tuple[float, str, float]]:
    """Group equal-timestamp ``(ts, signal_id, value)`` rows into updates.

    ``rows`` must arrive sorted by ``ts``. Output rows
    ``(ts, signal_id, value)`` are yielded lazily so callers can stream from
    database cursors without buffering.
    """
    current_ts: float | None = None
    pending: dict[str, float] = {}

    for ts, signal_id, value in rows:
        if current_ts is None:
            current_ts = ts
        if ts != current_ts:
            yield from _flush(engine, current_ts, pending)
            pending = {}
            current_ts = ts
        pending[signal_id] = value

    if current_ts is not None and pending:
        yield from _flush(engine, current_ts, pending)


def _flush(
    engine: VirtualSignalEngine, ts: float, values: dict[str, float]
) -> Iterator[tuple[float, str, float]]:
    outputs = engine.update(ts, values)
    for signal_id, value in outputs.items():
        yield ts, signal_id, value
