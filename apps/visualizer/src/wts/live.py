"""Live-path wrapper around :class:`VirtualSignalEngine` (Part 4).

The one module in ``src/wts/`` that is stateful about the *stream* clock.
Still no I/O, no wall clock, no logging: it consumes the DAQ timestamps
that the caller feeds it and reports clock steps as return values.

Time semantics (D11, Q1 — verified against a real DAQ capture, see
docs/wts/live.md): ``ts`` values are UTC epoch **seconds** (float64) from
the DAQ's RTC. Because the DAQ and the laptop clocks are not guaranteed to
agree, and because a DAQ reboot or a looped ZMQ replay can make the stream
clock step *backward*, the runtime classifies every delta:

``delta = ts - last_ts`` with ``limit = max_gap_seconds``:

- ``delta > limit``: forward jump / dropped data. ``engine.notify_gap``
  (the engine applies its own per-signal gap rule on top), output proceeds.
- ``delta < -limit``: **clock step** (I10). Full ``engine.reset()``,
  ``last_ts`` adopts the new base, and ``process`` reports a clock step so
  the caller can flag the next ``live_batch`` with ``clock_step: true``.
- ``-limit <= delta <= 0``: out-of-order jitter. The sample is skipped for
  virtual-signal purposes (never reordered).
- otherwise: normal in-order sample.
"""
from __future__ import annotations

from typing import Mapping

from wts.engine import VirtualSignalEngine
from wts.schema import VirtualSignalDef

CLOCK_STEP_COUNT = "clock_steps"


class LiveWtsRuntime:
    """Feed stream frames to the engine with clock-step tolerance.

    ``version`` is the ``DBCManager.get_wts_version()`` value the current
    definitions were read at; the pipeline loop compares it to decide when
    to rebuild (hot reload, D13).
    """

    def __init__(
        self,
        definitions: list[VirtualSignalDef],
        version: int = 0,
        max_gap_seconds: float = 1.0,
    ) -> None:
        self.engine = VirtualSignalEngine(definitions, max_gap_seconds=max_gap_seconds)
        self.version = version
        self.raw_inputs: frozenset[str] = frozenset(self.engine.required_inputs())
        self.max_gap_seconds = max_gap_seconds
        self._last_ts: float | None = None
        self._clock_steps = 0
        self._missing_timestamps = 0

    # ------------------------------------------------------------------ API

    def process(
        self, ts: float | None, values: Mapping[str, float]
    ) -> tuple[dict[str, float], bool]:
        """Evaluate one frame. Returns ``(outputs, clock_step)``.

        ``ts is None`` (frame without a DAQ timestamp) is skipped for
        virtual-signal purposes and counted; the caller logs it once per
        session. Never substitute the wall clock here.
        """
        if ts is None:
            self._missing_timestamps += 1
            return {}, False

        clock_step = False
        if self._last_ts is not None:
            delta = ts - self._last_ts
            if delta < -self.max_gap_seconds:
                # Backward clock step: reset and resume immediately on the
                # new time base (I10) — otherwise every stateful signal
                # would freeze until the old clock caught back up.
                self.engine.reset()
                self._clock_steps += 1
                clock_step = True
            elif delta > self.max_gap_seconds:
                # Forward jump: clear previous-sample state; output proceeds
                # on the new value.
                self.engine.notify_gap(ts)
            elif delta <= 0.0:
                # Out-of-order or duplicate timestamp: skip for WTS.
                return {}, False
        self._last_ts = ts
        return self.engine.update(ts, values), clock_step

    def note_dropped(self, ts: float | None) -> None:
        """``dropped_batches > 0``: the gap is real even if timestamps are
        continuous (sender batching)."""
        if ts is None:
            return
        self.engine.notify_gap(ts)

    def reset(self) -> None:
        """New live session (start / source reconnect): no state leaks over."""
        self.engine.reset()
        self._last_ts = None

    def stats(self) -> dict[str, int]:
        stats = dict(self.engine.stats())
        stats[CLOCK_STEP_COUNT] = self._clock_steps
        stats["missing_timestamps"] = self._missing_timestamps
        return stats
